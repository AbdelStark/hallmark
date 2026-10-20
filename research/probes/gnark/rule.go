package main

import (
	"encoding/binary"
	"encoding/hex"
	"errors"
	"io"
	"os"
	"strings"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/backend/groth16"
	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/frontend/cs/r1cs"
	"github.com/consensys/gnark/std/hash/sha2"
	"github.com/consensys/gnark/std/math/uints"
)

// These pins are reproduced by build_gnark_rule_fixture.py; enrollment is synthetic.
const ruleClassifier = "45bab258e0553c47399246e3c9aedb3ac7bb321969f09b03d96220d7aa1b7a4b"
const ruleProfile = "1c90a8bd4419e53b0284c1d37684705c6bc695f6fd261d57d259011d84cab953"

// shortcut: this experiment supports one eight-byte marker program; general adapters require W19.
type ruleCircuit struct {
	Public [100]frontend.Variable `gnark:",public"`
	Salt   [32]frontend.Variable
	Units  [8]frontend.Variable
}

func (c *ruleCircuit) Define(api frontend.API) error {
	bytesAPI, err := uints.NewBytes(api)
	if err != nil {
		return err
	}
	classifier, err := hex.DecodeString(ruleClassifier)
	if err != nil {
		return err
	}
	profile, err := hex.DecodeString(ruleProfile)
	if err != nil {
		return err
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
	api.AssertIsEqual(c.Public[98], uint64(1<<31)+1)

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

	var noMatch frontend.Variable = 1
	for start := 0; start <= 5; start++ {
		matched := active[start+2]
		for j, b := range []byte("BAD") {
			matched = api.Mul(matched, api.IsZero(api.Sub(c.Units[start+j], b)))
		}
		noMatch = api.Mul(noMatch, api.Sub(1, matched))
	}
	api.AssertIsEqual(c.Public[99], noMatch)

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
		return err
	}
	hasher.Write(preimage)
	for i, b := range hasher.FixedLengthSum(api.Add(prefixLength, encodedLength)) {
		api.AssertIsEqual(bytesAPI.Value(b), c.Public[64+i])
	}
	return nil
}

func ruleAssignment(private bool) (*ruleCircuit, error) {
	count := 100
	if private {
		count += 40
	}
	handle, err := os.Open("assignment.txt")
	if err != nil {
		return nil, err
	}
	defer handle.Close()
	raw, err := io.ReadAll(io.LimitReader(handle, 8193))
	if err != nil || len(raw) > 8192 {
		return nil, errors.New("invalid assignment")
	}
	lines := strings.Split(string(raw), "\n")
	if len(lines) != count+1 || lines[count] != "" {
		return nil, errors.New("invalid assignment shape")
	}
	c := &ruleCircuit{}
	for i, line := range lines[:count] {
		// The circuit, not this transport parser, enforces narrower byte/count ranges.
		n, err := number(line, 32)
		if err != nil {
			return nil, err
		}
		switch {
		case i < 100:
			c.Public[i] = n
		case i < 132:
			c.Salt[i-100] = n
		default:
			c.Units[i-132] = n
		}
	}
	return c, nil
}

func runRule(command string) (int, error) {
	curve := ecc.BLS12_381
	switch command {
	case "rule-setup":
		ccs, err := frontend.Compile(curve.ScalarField(), r1cs.NewBuilder, &ruleCircuit{})
		if err != nil {
			return 0, err
		}
		pk, vk, err := groth16.Setup(ccs)
		if err != nil {
			return ccs.GetNbConstraints(), err
		}
		for _, artifact := range []struct {
			name string
			data io.WriterTo
		}{{"circuit.r1cs", ccs}, {"pk.bin", pk}, {"vk.bin", vk}} {
			if err := write(artifact.name, artifact.data); err != nil {
				return ccs.GetNbConstraints(), err
			}
		}
		return ccs.GetNbConstraints(), nil
	case "rule-prove":
		assignment, err := ruleAssignment(true)
		if err != nil {
			return 0, err
		}
		ccs := groth16.NewCS(curve)
		pk := groth16.NewProvingKey(curve)
		if err := read("circuit.r1cs", ccs); err != nil {
			return 0, err
		}
		if err := read("pk.bin", pk); err != nil {
			return 0, err
		}
		witness, err := frontend.NewWitness(assignment, curve.ScalarField())
		if err != nil {
			return 0, err
		}
		proof, err := groth16.Prove(ccs, pk, witness)
		if err != nil {
			return ccs.GetNbConstraints(), err
		}
		return ccs.GetNbConstraints(), write("proof.bin", proof)
	case "rule-verify":
		assignment, err := ruleAssignment(false)
		if err != nil {
			return 0, err
		}
		vk, proof := groth16.NewVerifyingKey(curve), groth16.NewProof(curve)
		if err := read("vk.bin", vk); err != nil {
			return 0, err
		}
		if err := read("proof.bin", proof); err != nil {
			return 0, err
		}
		witness, err := frontend.NewWitness(assignment, curve.ScalarField(), frontend.PublicOnly())
		if err != nil {
			return 0, err
		}
		return 0, groth16.Verify(proof, vk, witness)
	}
	return 0, errors.New("invalid rule command")
}
