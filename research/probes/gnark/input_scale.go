package main

import (
	"bytes"
	"encoding/binary"
	"encoding/json"
	"errors"
	"io"
	"os"
	"regexp"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/backend/groth16"
	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/std/hash/sha2"
	"github.com/consensys/gnark/std/lookup/logderivlookup"
	"github.com/consensys/gnark/std/math/uints"
)

// A commitment component, not a classifier: count and digest are public.
type inputScaleCircuit struct {
	Public    [33]frontend.Variable `gnark:",public"`
	Salt      [32]frontend.Variable
	Units     []frontend.Variable
	Encoded   []frontend.Variable
	Positions []frontend.Variable
}

func newInputScale(size int) *inputScaleCircuit {
	return &inputScaleCircuit{
		Units: make([]frontend.Variable, size), Encoded: make([]frontend.Variable, 2*size+6),
		Positions: make([]frontend.Variable, size+1),
	}
}

func (c *inputScaleCircuit) Define(api frontend.API) error {
	bytesAPI, err := uints.NewBytes(api)
	if err != nil {
		return err
	}
	n := c.Public[0]
	bits := api.ToBinary(n, 16)
	api.ToBinary(api.Sub(len(c.Units), n), 16)
	wide := api.Sub(1, api.IsZero(api.FromBinary(bits[8:]...)))
	medium := api.ToBinary(api.Add(n, 65536-24), 17)[16]
	width := api.Add(1, medium, wide)
	first := api.Select(wide, 0x19, api.Select(medium, 0x18, n))
	second := api.Select(wide, api.FromBinary(bits[8:]...), n)
	third := api.FromBinary(bits[:8]...)
	encoded := logderivlookup.New(api)
	for _, value := range c.Encoded {
		bytesAPI.ValueOf(value)
		encoded.Insert(value)
	}
	for _, header := range []struct{ position, major frontend.Variable }{{0, 0}, {width, 0x80}} {
		values := encoded.Lookup(header.position, api.Add(header.position, 1), api.Add(header.position, 2))
		api.AssertIsEqual(values[0], api.Add(header.major, first))
		api.AssertIsEqual(api.Mul(medium, api.Sub(values[1], second)), 0)
		api.AssertIsEqual(api.Mul(wide, api.Sub(values[2], third)), 0)
	}
	api.AssertIsEqual(c.Positions[0], api.Mul(2, width))
	for i, unit := range c.Units {
		active := api.ToBinary(api.Add(n, 65536-i-1), 17)[16]
		bits := api.ToBinary(unit, 8)
		small := api.Mul(api.Sub(1, bits[5]), api.Sub(1, bits[6]), api.Sub(1, bits[7]),
			api.Sub(1, api.Mul(bits[3], bits[4])))
		api.AssertIsEqual(api.Mul(api.Sub(1, active), unit), 0)
		two := api.Mul(active, api.Sub(1, small))
		values := encoded.Lookup(api.Mul(active, c.Positions[i]), api.Mul(two, api.Add(c.Positions[i], 1)))
		api.AssertIsEqual(api.Mul(active, api.Sub(values[0], api.Select(small, unit, 0x18))), 0)
		api.AssertIsEqual(api.Mul(two, api.Sub(values[1], unit)), 0)
		// Explicit prefix witnesses avoid expanding a growing linear expression at every query.
		api.AssertIsEqual(c.Positions[i+1], api.Add(c.Positions[i], active, two))
	}
	length := c.Positions[len(c.Units)]
	for j, value := range c.Encoded {
		padding := api.ToBinary(api.Add(api.Sub(j, length), 1<<17), 18)[17]
		api.AssertIsEqual(api.Mul(padding, value), 0)
	}
	tag := []byte("hallmark/v1/input")
	header := make([]byte, 4)
	binary.BigEndian.PutUint32(header, uint32(len(tag)))
	preimage := uints.NewU8Array(append(header, tag...))
	preimage = append(preimage, uints.NewU8(0x84), uints.NewU8(0x58), uints.NewU8(0x20))
	for _, value := range c.Salt {
		preimage = append(preimage, bytesAPI.ValueOf(value))
	}
	preimage = append(preimage, uints.NewU8(0x58), uints.NewU8(0x20))
	// shortcut: synthetic profile pin; classifier integration requires an enrolled profile.
	for i := 0; i < 32; i++ {
		preimage = append(preimage, uints.NewU8('p'))
	}
	prefix := len(preimage)
	for _, value := range c.Encoded {
		preimage = append(preimage, bytesAPI.ValueOf(value))
	}
	hasher, err := sha2.New(api)
	if err != nil {
		return err
	}
	hasher.Write(preimage)
	for i, value := range hasher.FixedLengthSum(api.Add(prefix, length)) {
		api.AssertIsEqual(bytesAPI.Value(value), bytesAPI.Value(bytesAPI.ValueOf(c.Public[i+1])))
	}
	return nil
}

func runInputScale(action, rawSize string) (int, error) {
	size, err := number(rawSize, 16)
	if err != nil || (size != 8 && size != 32 && size != 256 && size != 32768) {
		return 0, errors.New("invalid input profile")
	}
	prototype := newInputScale(int(size))
	if action == "batch" {
		return inputScaleBatch(int(size))
	}
	return runRelation(action, prototype, func(private bool) (frontend.Circuit, error) {
		return inputScaleAssignment(int(size), "assignment.txt", private)
	})
}

func inputScaleAssignment(size int, name string, private bool) (frontend.Circuit, error) {
	c := newInputScale(size)
	count := 33
	if private {
		count += 32 + len(c.Units) + len(c.Encoded) + len(c.Positions)
	}
	values, err := readAssignmentFile(name, count)
	if err != nil {
		return nil, err
	}
	fields := [][]frontend.Variable{c.Public[:]}
	if private {
		fields = append(fields, c.Salt[:], c.Units, c.Encoded, c.Positions)
	}
	next := 0
	for _, field := range fields {
		for i := range field {
			field[i] = values[next]
			next++
		}
	}
	return c, nil
}

// Real prover attempts share a single key load; verification remains in fresh processes.
func inputScaleBatch(size int) (int, error) {
	handle, err := os.Open("cases.json")
	if err != nil {
		return 0, err
	}
	defer handle.Close()
	info, err := handle.Stat()
	if err != nil || !info.Mode().IsRegular() || info.Size() > 8192 {
		return 0, errors.New("invalid batch size")
	}
	var cases []struct {
		Name  string `json:"name"`
		Valid *bool  `json:"valid"`
	}
	decoder := json.NewDecoder(io.LimitReader(handle, 8193))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&cases); err != nil || len(cases) == 0 || len(cases) > 32 {
		return 0, errors.New("invalid batch")
	}
	if decoder.Decode(new(any)) != io.EOF {
		return 0, errors.New("trailing batch data")
	}
	seen := make(map[string]bool)
	namePattern := regexp.MustCompile(`^[a-z][a-z0-9-]{0,63}$`)
	for _, c := range cases {
		if !namePattern.MatchString(c.Name) || c.Valid == nil || seen[c.Name] {
			return 0, errors.New("invalid batch case")
		}
		seen[c.Name] = true
	}
	curve := ecc.BLS12_381
	ccs, pk := groth16.NewCS(curve), groth16.NewProvingKey(curve)
	if err := read("circuit.r1cs", ccs); err != nil {
		return 0, err
	}
	if err := read("pk.bin", pk); err != nil {
		return 0, err
	}
	for _, c := range cases {
		values, err := inputScaleAssignment(size, c.Name+".txt", true)
		if err != nil {
			return ccs.GetNbConstraints(), err
		}
		witness, err := frontend.NewWitness(values, curve.ScalarField())
		if err != nil {
			return ccs.GetNbConstraints(), err
		}
		proof, err := groth16.Prove(ccs, pk, witness)
		if (err == nil) != *c.Valid {
			return ccs.GetNbConstraints(), errors.New("unexpected prover outcome")
		}
		if err == nil {
			if err := write(c.Name+".proof", proof); err != nil {
				return ccs.GetNbConstraints(), err
			}
		}
		// Retain each completed attempt even if a later case fails.
		if err := write(c.Name+".json", bytes.NewBufferString("{\"expected_outcome_observed\":true}\n")); err != nil {
			return ccs.GetNbConstraints(), err
		}
	}
	return ccs.GetNbConstraints(), nil
}
