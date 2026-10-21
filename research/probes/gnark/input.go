package main

import (
	"encoding/binary"
	"encoding/hex"
	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/std/hash/sha2"
	"github.com/consensys/gnark/std/math/uints"
)

// shortcut: bounded eight-byte experiments; general input encoders require W19-W21.
type inputCircuit struct {
	Public [100]frontend.Variable `gnark:",public"`
	Salt   [32]frontend.Variable
	Units  [8]frontend.Variable
}

func (c *inputCircuit) bind(api frontend.API, classifierPin, profilePin string, threshold uint64) ([]frontend.Variable, error) {
	bytesAPI, err := uints.NewBytes(api)
	if err != nil {
		return nil, err
	}
	classifier, err := hex.DecodeString(classifierPin)
	if err != nil {
		return nil, err
	}
	profile, err := hex.DecodeString(profilePin)
	if err != nil {
		return nil, err
	}
	for i := 0; i < 96; i++ {
		api.ToBinary(c.Public[i], 8)
	}
	for i, b := range classifier {
		api.AssertIsEqual(c.Public[32+i], b)
	}
	api.ToBinary(c.Public[96], 4)
	api.ToBinary(c.Public[97], 2)
	api.ToBinary(c.Public[98], 32)
	api.AssertIsBoolean(c.Public[99])
	api.AssertIsEqual(c.Public[98], uint64(1<<31)+threshold)

	// A one-hot length covers every possible input, including empty and maximum.
	lengths := make([]frontend.Variable, 9)
	var total frontend.Variable = 0
	for n := range lengths {
		lengths[n] = api.IsZero(api.Sub(c.Public[96], n))
		total = api.Add(total, lengths[n])
	}
	api.AssertIsEqual(total, 1)
	active := make([]frontend.Variable, 8)
	small := make([]frontend.Variable, 8)
	positions := make([]frontend.Variable, 8)
	var encodedLength frontend.Variable = 0
	for i, unit := range c.Units {
		active[i] = 0
		for n := i + 1; n <= 8; n++ {
			active[i] = api.Add(active[i], lengths[n])
		}
		bits := api.ToBinary(unit, 8)
		small[i] = api.Mul(
			api.Sub(1, bits[5]), api.Sub(1, bits[6]), api.Sub(1, bits[7]),
			api.Sub(1, api.Mul(bits[3], bits[4])),
		)
		api.AssertIsEqual(api.Mul(api.Sub(1, active[i]), unit), 0)
		positions[i] = encodedLength
		encodedLength = api.Add(encodedLength, api.Mul(active[i], api.Sub(2, small[i])))
	}
	api.AssertIsEqual(c.Public[97], api.Add(1, active[4]))

	// Exact H("input", [derived_salt, profile, count, byte_list]) encoding.
	tag := []byte("hallmark/v1/input")
	header := make([]byte, 4)
	binary.BigEndian.PutUint32(header, uint32(len(tag)))
	preimage := uints.NewU8Array(append(header, tag...))
	preimage = append(preimage, uints.NewU8(0x84), uints.NewU8(0x58), uints.NewU8(0x20))
	for _, v := range c.Salt {
		preimage = append(preimage, bytesAPI.ValueOf(v))
	}
	preimage = append(preimage, uints.NewU8(0x58), uints.NewU8(0x20))
	preimage = append(preimage, uints.NewU8Array(profile)...)
	preimage = append(preimage, bytesAPI.ValueOf(c.Public[96]))
	preimage = append(preimage, bytesAPI.ValueOf(api.Add(0x80, c.Public[96])))
	prefixLength := len(preimage)
	for j := 0; j < 16; j++ {
		var value frontend.Variable = 0
		for i, unit := range c.Units {
			first := api.Mul(
				api.IsZero(api.Sub(positions[i], j)),
				api.Select(small[i], unit, 0x18),
			)
			second := api.Mul(
				api.IsZero(api.Sub(api.Add(positions[i], 1), j)),
				api.Sub(1, small[i]), unit,
			)
			value = api.Add(value, api.Mul(active[i], api.Add(first, second)))
		}
		preimage = append(preimage, bytesAPI.ValueOf(value))
	}
	hasher, err := sha2.New(api)
	if err != nil {
		return nil, err
	}
	hasher.Write(preimage)
	for i, b := range hasher.FixedLengthSum(api.Add(prefixLength, encodedLength)) {
		api.AssertIsEqual(bytesAPI.Value(b), c.Public[64+i])
	}
	return active, nil
}
