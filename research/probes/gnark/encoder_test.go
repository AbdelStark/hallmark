package main

import (
	"encoding/json"
	"os"
	"testing"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/frontend/cs/r1cs"
)

func encoderTestAssignments(t *testing.T) []*encoderCircuit {
	t.Helper()
	raw, err := os.ReadFile("encoder-fixture.json")
	if err != nil {
		t.Fatal(err)
	}
	var f struct {
		Capacity int `json:"capacity"`
		Cases    []struct {
			Public        []int64 `json:"public"`
			Salt          []int64 `json:"salt"`
			Units         []int64 `json:"units"`
			Encoded       []int64 `json:"encoded"`
			Positions     []int64 `json:"positions"`
			UnitActive    []int64 `json:"unit_active"`
			EncodedActive []int64 `json:"encoded_active"`
			Trace         []int64 `json:"trace"`
		} `json:"cases"`
	}
	if err := json.Unmarshal(raw, &f); err != nil {
		t.Fatal(err)
	}
	if f.Capacity != 8 || len(f.Cases) != 15 {
		t.Fatal("invalid encoder fixture roster")
	}
	assignments := make([]*encoderCircuit, len(f.Cases))
	for i, row := range f.Cases {
		c := newEncoder(8)
		fields := [][]frontend.Variable{c.Public[:], c.Salt[:], c.Units, c.Encoded, c.Positions, c.UnitActive, c.EncodedActive, c.Trace}
		values := [][]int64{row.Public, row.Salt, row.Units, row.Encoded, row.Positions, row.UnitActive, row.EncodedActive, row.Trace}
		for j, field := range fields {
			if len(field) != len(values[j]) {
				t.Fatal("invalid encoder assignment shape")
			}
			for k, value := range values[j] {
				field[k] = value
			}
		}
		assignments[i] = c
	}
	return assignments
}

func TestEncoderFrozenNativeTrace(t *testing.T) {
	ccs, err := frontend.Compile(ecc.BLS12_381.ScalarField(), r1cs.NewBuilder, newEncoder(8))
	if err != nil {
		t.Fatal(err)
	}
	assignments := encoderTestAssignments(t)
	for i, assignment := range assignments {
		witness, err := frontend.NewWitness(assignment, ecc.BLS12_381.ScalarField())
		if err != nil {
			t.Fatal(err)
		}
		if err := ccs.IsSolved(witness); err != nil {
			t.Fatalf("native case %d failed: %v", i, err)
		}
	}
	changed := assignments[9]
	changed.Trace[len(changed.Trace)-1] = changed.Trace[len(changed.Trace)-1].(int64) ^ 1
	witness, err := frontend.NewWitness(changed, ecc.BLS12_381.ScalarField())
	if err != nil {
		t.Fatal(err)
	}
	if err := ccs.IsSolved(witness); err == nil {
		t.Fatal("accepted altered final tensor")
	}
	t.Logf("full eight-unit encoder constraints: %d", ccs.GetNbConstraints())
}

func TestProverRejectionRequiresUnsatisfiedConstraint(t *testing.T) {
	ccs, err := frontend.Compile(ecc.BLS12_381.ScalarField(), r1cs.NewBuilder, &circuit{})
	if err != nil {
		t.Fatal(err)
	}
	witness, err := frontend.NewWitness(&circuit{X: 0, Y: 6}, ecc.BLS12_381.ScalarField())
	if err != nil {
		t.Fatal(err)
	}
	invalid := ccs.IsSolved(witness)
	if !expectedProverOutcome(false, invalid) || expectedProverOutcome(true, invalid) || expectedProverOutcome(false, nil) || !expectedProverOutcome(true, nil) {
		t.Fatal("incorrect constraint outcome classification")
	}
	if expectedProverOutcome(false, os.ErrPermission) || expectedProverOutcome(true, os.ErrPermission) {
		t.Fatal("accepted an infrastructure error")
	}
}
