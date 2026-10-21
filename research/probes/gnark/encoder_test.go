package main

import (
	"encoding/json"
	"os"
	"testing"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/frontend/cs/r1cs"
)

func encoderTestAssignments(t *testing.T, filename string, count int) []*encoderCircuit {
	t.Helper()
	raw, err := os.ReadFile(filename)
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
	if f.Capacity != 8 || len(f.Cases) != count {
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
	assignments := encoderTestAssignments(t, "encoder-fixture.json", 15)
	for i, assignment := range assignments {
		witness, err := frontend.NewWitness(assignment, ecc.BLS12_381.ScalarField())
		if err != nil {
			t.Fatal(err)
		}
		if err := ccs.IsSolved(witness); err != nil {
			t.Fatalf("native case %d failed: %v", i, err)
		}
	}
	maximum, empty := assignments[9], assignments[0]
	for _, test := range []struct {
		name       string
		assignment *encoderCircuit
		field      []frontend.Variable
		index      int
		value      int64
	}{
		{"last-unit", maximum, maximum.Units, 7, maximum.Units[7].(int64) ^ 1},
		{"last-encoding", maximum, maximum.Encoded, int(maximum.Positions[8].(int64)) - 1, 64},
		{"last-position", maximum, maximum.Positions, 8, 1},
		{"wrong-count", maximum, maximum.Public[:], 96, 7},
		{"unit-range", maximum, maximum.Units, 0, 256},
		{"prefix-hole", maximum, maximum.UnitActive, 4, 0},
		{"empty-padding", empty, empty.Encoded, 21, 1},
		{"empty-unit-padding", empty, empty.Units, 7, 1},
		{"salt-range", maximum, maximum.Salt[:], 0, 256},
		{"trace-first", maximum, maximum.Trace, 0, maximum.Trace[0].(int64) ^ 1},
		{"trace-middle", maximum, maximum.Trace, 242, maximum.Trace[242].(int64) ^ 1},
		{"trace-last", maximum, maximum.Trace, 483, maximum.Trace[483].(int64) ^ 1},
	} {
		saved := test.field[test.index]
		test.field[test.index] = test.value
		witness, err := frontend.NewWitness(test.assignment, ecc.BLS12_381.ScalarField())
		test.field[test.index] = saved
		if err != nil {
			t.Fatal(err)
		}
		if !expectedProverOutcome(false, ccs.IsSolved(witness)) {
			t.Fatalf("%s did not yield an unsatisfied constraint", test.name)
		}
	}
	t.Logf("full eight-unit encoder constraints: %d", ccs.GetNbConstraints())
}

func TestEncoderNumericalChunkClasses(t *testing.T) {
	ccs, err := frontend.Compile(ecc.BLS12_381.ScalarField(), r1cs.NewBuilder, newEncoder(8))
	if err != nil {
		t.Fatal(err)
	}
	for i, assignment := range encoderTestAssignments(t, "encoder-classes-fixture.json", 21) {
		witness, err := frontend.NewWitness(assignment, ecc.BLS12_381.ScalarField())
		if err != nil {
			t.Fatal(err)
		}
		if err := ccs.IsSolved(witness); err != nil {
			t.Fatalf("numerical class %d failed: %v", i, err)
		}
		assignment.Trace[0] = assignment.Trace[0].(int64) ^ 1
		witness, err = frontend.NewWitness(assignment, ecc.BLS12_381.ScalarField())
		if err != nil {
			t.Fatal(err)
		}
		if !expectedProverOutcome(false, ccs.IsSolved(witness)) {
			t.Fatalf("changed numerical class %d did not yield an unsatisfied constraint", i)
		}
	}
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
