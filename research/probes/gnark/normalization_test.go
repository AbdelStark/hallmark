package main

import (
	"encoding/json"
	"os"
	"testing"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/backend/groth16"
	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/frontend/cs/r1cs"
)

func TestNormalizationFrozenDomainAndRealProof(t *testing.T) {
	raw, err := os.ReadFile("normalization-fixture.json")
	if err != nil {
		t.Fatal(err)
	}
	var fixture struct {
		Cases []struct {
			Public []int64
			Trace  []int64
		}
	}
	if err := json.Unmarshal(raw, &fixture); err != nil {
		t.Fatal(err)
	}
	if len(fixture.Cases) != 289 {
		t.Fatal("incomplete normalization domain")
	}
	curve := ecc.BLS12_381
	ccs, err := frontend.Compile(curve.ScalarField(), r1cs.NewBuilder, &normalizationCircuit{})
	if err != nil {
		t.Fatal(err)
	}
	var last normalizationCircuit
	for _, row := range fixture.Cases {
		if len(row.Public) != 4 || len(row.Trace) != 11 {
			t.Fatal("invalid fixture shape")
		}
		for i, value := range row.Public {
			last.Public[i] = value
		}
		for i, value := range row.Trace {
			last.Trace[i] = value
		}
		witness, err := frontend.NewWitness(&last, curve.ScalarField())
		if err != nil {
			t.Fatal(err)
		}
		if err := ccs.IsSolved(witness); err != nil {
			t.Fatal(err)
		}
	}
	pk, vk, err := groth16.Setup(ccs)
	if err != nil {
		t.Fatal(err)
	}
	witness, err := frontend.NewWitness(&last, curve.ScalarField())
	if err != nil {
		t.Fatal(err)
	}
	proof, err := groth16.Prove(ccs, pk, witness)
	if err != nil {
		t.Fatal(err)
	}
	public, err := witness.Public()
	if err != nil {
		t.Fatal(err)
	}
	if err := groth16.Verify(proof, vk, public); err != nil {
		t.Fatal(err)
	}
	for i := range last.Trace {
		changed := last
		changed.Trace[i] = last.Trace[i].(int64) ^ 1
		witness, err := frontend.NewWitness(&changed, curve.ScalarField())
		if err != nil {
			t.Fatal(err)
		}
		if err := ccs.IsSolved(witness); err == nil {
			t.Fatalf("accepted changed trace %d", i)
		}
	}
	for i := range last.Public {
		changed := last
		changed.Public[i] = last.Public[i].(int64) ^ 1
		witness, err := frontend.NewWitness(&changed, curve.ScalarField(), frontend.PublicOnly())
		if err != nil {
			t.Fatal(err)
		}
		if err := groth16.Verify(proof, vk, witness); err == nil {
			t.Fatalf("accepted changed public %d", i)
		}
	}
}
