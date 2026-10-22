package main

import (
	"encoding/hex"
	"errors"
	"github.com/consensys/gnark/frontend"
)

const scaledRuleProfile = "793a7a11ef3a2f0e9e556fb5ada8b4b8e40ed27a576e43c1af4f332a9a733f88"

type scaledRuleCircuit struct {
	Public                                               [100]frontend.Variable `gnark:",public"`
	Salt                                                 [32]frontend.Variable
	Units, Encoded, Positions, UnitActive, EncodedActive []frontend.Variable
}

func newScaledRule(size int) *scaledRuleCircuit {
	x := newInputScale(size)
	return &scaledRuleCircuit{Salt: x.Salt, Units: x.Units, Encoded: x.Encoded,
		Positions: x.Positions, UnitActive: x.UnitActive, EncodedActive: x.EncodedActive}
}

func (c *scaledRuleCircuit) Define(api frontend.API) error {
	profile, _ := hex.DecodeString(scaledRuleProfile)
	x := &inputScaleCircuit{Salt: c.Salt, Units: c.Units, Encoded: c.Encoded,
		Positions: c.Positions, UnitActive: c.UnitActive, EncodedActive: c.EncodedActive}
	x.Public[0] = c.Public[96]
	copy(x.Public[1:], c.Public[64:96])
	if err := x.defineProfile(api, profile); err != nil {
		return err
	}
	for _, v := range c.Public[:64] {
		api.ToBinary(v, 8)
	}
	api.AssertIsEqual(c.Public[98], uint64(1<<31)+1)
	api.AssertIsBoolean(c.Public[99])
	var count, noMatch frontend.Variable = 1, 1
	for start := 4; start < len(c.Units); start += 4 {
		count = api.Add(count, c.UnitActive[start])
	}
	api.AssertIsEqual(c.Public[97], count)
	for start := 0; start+2 < len(c.Units); start++ {
		matched := c.UnitActive[start+2]
		for j, b := range []byte("BAD") {
			matched = api.Mul(matched, api.IsZero(api.Sub(c.Units[start+j], b)))
		}
		noMatch = api.Mul(noMatch, api.Sub(1, matched))
	}
	api.AssertIsEqual(c.Public[99], noMatch)
	return nil
}

func scaledRuleAssignment(size int, name string, private bool) (frontend.Circuit, error) {
	c := newScaledRule(size)
	fields := [][]frontend.Variable{c.Public[:]}
	if private {
		fields = append(fields, c.Salt[:], c.Units, c.Encoded, c.Positions, c.UnitActive, c.EncodedActive)
	}
	count := 0
	for _, field := range fields {
		count += len(field)
	}
	values, err := readAssignmentFile(name, count)
	if err != nil {
		return nil, err
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

func runScaledRule(action, rawSize string) (int, error) {
	size, err := number(rawSize, 16)
	if err != nil || (size != 8 && size != 96) {
		return 0, errors.New("unsupported scaled rule capacity")
	}
	if action == "batch" {
		return relationBatch(func(name string) (frontend.Circuit, error) {
			return scaledRuleAssignment(int(size), name, true)
		}, 2*1024*1024*1024, 12, 4096)
	}
	return runRelation(action, newScaledRule(int(size)), func(private bool) (frontend.Circuit, error) {
		return scaledRuleAssignment(int(size), "assignment.txt", private)
	}, 2*1024*1024*1024)
}
