package main

import (
	"encoding/json"
	"os"
	"testing"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/frontend/cs/r1cs"
)

func TestProgramEnrollmentBindings(t *testing.T) {
	for _, kind := range []string{"rule", "mlp"} {
		raw, err := os.ReadFile(kind + "-fixture.json")
		if err != nil {
			t.Fatal(err)
		}
		var fixture struct {
			Cases []struct{ Public, Salt, Units, Trace []int64 }
		}
		if err := json.Unmarshal(raw, &fixture); err != nil {
			t.Fatal(err)
		}
		if len(fixture.Cases) != 9 {
			t.Fatal("unexpected fixture roster")
		}
		for _, mode := range []string{kind, kind + "-program"} {
			prototype, _, _ := graph(mode)
			ccs, err := frontend.Compile(ecc.BLS12_381.ScalarField(), r1cs.NewBuilder, prototype)
			if err != nil {
				t.Fatal(err)
			}
			for _, row := range fixture.Cases {
				assignment, input, trace := graph(mode)
				for i, v := range row.Public {
					input.Public[i] = v
				}
				for i, v := range row.Salt {
					input.Salt[i] = v
				}
				for i, v := range row.Units {
					input.Units[i] = v
				}
				for i, v := range row.Trace {
					trace[i] = v
				}
				solve := func(want bool) {
					t.Helper()
					witness, err := frontend.NewWitness(assignment, ecc.BLS12_381.ScalarField())
					if err != nil {
						t.Fatal(err)
					}
					if !expectedProverOutcome(want, ccs.IsSolved(witness)) {
						t.Fatalf("unexpected %s constraint result", mode)
					}
				}
				solve(true)
				input.Public[32] = row.Public[32] ^ 1
				solve(mode == kind+"-program")
				input.Public[32] = 256
				solve(false)
				input.Public[32] = row.Public[32]
				input.Public[98] = row.Public[98] + 1
				solve(false)
				input.Public[98] = row.Public[98]
				input.Units[7] = row.Units[7] ^ 1
				solve(false)
			}
		}
	}
}
