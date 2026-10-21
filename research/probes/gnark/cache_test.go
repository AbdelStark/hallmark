package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"testing"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/frontend/cs/r1cs"
	"github.com/consensys/gnark/logger"
)

type booleanCacheFixture struct {
	Public [2]frontend.Variable `gnark:",public"`
	Flags  [130]frontend.Variable
}

func (c *booleanCacheFixture) Define(api frontend.API) error {
	compiler := api.Compiler()
	for _, v := range append(c.Public[:], c.Flags[:]...) {
		if compiler.IsBoolean(v) {
			return fmt.Errorf("unconstrained wire already marked")
		}
		api.AssertIsBoolean(v)
		api.AssertIsBoolean(v)
		if !compiler.IsBoolean(api.Add(v, 0)) || compiler.IsBoolean(api.Mul(2, v)) || compiler.IsBoolean(api.Neg(v)) {
			return fmt.Errorf("wire or coefficient cache alias")
		}
	}
	mixed := api.Add(c.Flags[0], c.Flags[64])
	if compiler.IsBoolean(mixed) {
		return fmt.Errorf("unmarked expression cached")
	}
	// MarkBoolean records metadata only; this expression is not claimed constrained.
	compiler.MarkBoolean(mixed)
	compiler.MarkBoolean(mixed)
	if !compiler.IsBoolean(api.Add(c.Flags[64], c.Flags[0])) || compiler.IsBoolean(api.Sub(c.Flags[0], c.Flags[64])) {
		return fmt.Errorf("general expression cache mismatch")
	}
	internal := api.Mul(c.Flags[0], c.Flags[1])
	if compiler.IsBoolean(internal) {
		return fmt.Errorf("internal wire aliases an input")
	}
	api.AssertIsBoolean(internal)
	return nil
}

func TestBooleanCacheWireBoundariesAndAliases(t *testing.T) {
	logger.Disable()
	field := ecc.BLS12_381.ScalarField()
	ccs, err := frontend.Compile(field, r1cs.NewBuilder, &booleanCacheFixture{})
	if err != nil {
		t.Fatal(err)
	}
	for changed := -1; changed < 132; changed++ {
		value := booleanCacheFixture{}
		for i := range value.Public {
			value.Public[i] = 0
		}
		for i := range value.Flags {
			value.Flags[i] = 0
		}
		if changed >= 0 && changed < 2 {
			value.Public[changed] = 2
		} else if changed >= 2 {
			value.Flags[changed-2] = 2
		}
		witness, err := frontend.NewWitness(&value, field)
		if err != nil {
			t.Fatal(err)
		}
		if (ccs.IsSolved(witness) == nil) != (changed == -1) {
			t.Fatalf("incorrect Boolean range result for wire %d", changed)
		}
	}
}

type booleanConstantFixture struct {
	Value int `gnark:"-"`
}

func (c *booleanConstantFixture) Define(api frontend.API) error {
	if api.Compiler().IsBoolean(c.Value) != (c.Value == 0 || c.Value == 1) {
		return fmt.Errorf("incorrect Boolean constant")
	}
	api.Compiler().MarkBoolean(c.Value)
	return nil
}

func TestBooleanCacheConstants(t *testing.T) {
	for _, value := range []int{0, 1, 2, -1} {
		_, err := frontend.Compile(ecc.BLS12_381.ScalarField(), r1cs.NewBuilder, &booleanConstantFixture{Value: value})
		if (err == nil) != (value == 0 || value == 1) {
			t.Fatalf("incorrect constant result for %d", value)
		}
	}
}

// Compare these bytes across pinned builds; matching counts alone is insufficient.
func TestCircuitFingerprints(t *testing.T) {
	logger.Disable()
	for _, test := range []struct {
		name    string
		circuit frontend.Circuit
	}{
		{"installation", &circuit{}}, {"rule", &ruleCircuit{}}, {"mlp", &mlpCircuit{}},
		{"block", &blockCircuit{}}, {"input-8", newInputScale(8)},
		{"input-32", newInputScale(32)}, {"input-256", newInputScale(256)},
		{"encoder-8", newEncoder(8)},
	} {
		ccs, err := frontend.Compile(ecc.BLS12_381.ScalarField(), r1cs.NewBuilder, test.circuit)
		if err != nil {
			t.Fatal(err)
		}
		var data bytes.Buffer
		if _, err := ccs.WriteTo(&data); err != nil {
			t.Fatal(err)
		}
		record := map[string]any{"name": test.name, "constraints": ccs.GetNbConstraints(), "bytes": data.Len(), "sha256": fmt.Sprintf("%x", sha256.Sum256(data.Bytes()))}
		raw, err := json.Marshal(record)
		if err != nil {
			t.Fatal(err)
		}
		fmt.Println("CIRCUIT", string(raw))
	}
}
