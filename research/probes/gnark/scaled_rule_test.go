package main

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/frontend/cs/r1cs"
	"strings"
	"testing"
)

func scaledRuleWitness(size int, prompt string) *scaledRuleCircuit {
	c := newScaledRule(size)
	for _, a := range [][]frontend.Variable{c.Public[:], c.Salt[:], c.Units, c.Encoded, c.Positions, c.UnitActive, c.EncodedActive} {
		for i := range a {
			a[i] = int64(0)
		}
	}
	n := len(prompt)
	head := func(n int, major byte) []byte {
		if n < 24 {
			return []byte{major + byte(n)}
		}
		return []byte{major + 24, byte(n)}
	}
	enc := append(head(n, 0), head(n, 0x80)...)
	for i := 0; i < size; i++ {
		c.Positions[i] = int64(len(enc))
		if i < n {
			c.Units[i], c.UnitActive[i] = int64(prompt[i]), int64(1)
			enc = append(enc, head(int(prompt[i]), 0)...)
		}
	}
	c.Positions[size] = int64(len(enc))
	for i, b := range enc {
		c.Encoded[i], c.EncodedActive[i] = int64(b), int64(1)
	}
	tag := []byte("hallmark/v1/input")
	prefix := make([]byte, 4)
	binary.BigEndian.PutUint32(prefix, uint32(len(tag)))
	preimage := append(prefix, tag...)
	preimage = append(preimage, 0x84, 0x58, 0x20)
	preimage = append(preimage, make([]byte, 32)...)
	preimage = append(preimage, 0x58, 0x20)
	profile, _ := hex.DecodeString(scaledRuleProfile)
	preimage = append(preimage, profile...)
	h := sha256.Sum256(append(preimage, enc...))
	for i, b := range h {
		c.Public[64+i] = int64(b)
	}
	c.Public[96], c.Public[97], c.Public[98] = int64(n), int64(max(1, (n+3)/4)), int64(1<<31)+1
	if !strings.Contains(prompt, "BAD") {
		c.Public[99] = int64(1)
	}
	return c
}

func TestScaledRuleCompleteInput(t *testing.T) {
	field := ecc.BLS12_381.ScalarField()
	for _, size := range []int{8, 96} {
		ccs, err := frontend.Compile(field, r1cs.NewBuilder, newScaledRule(size))
		if err != nil {
			t.Fatal(err)
		}
		if ccs.GetNbPublicVariables() != 101 {
			t.Fatal("public layout")
		}
		for _, prompt := range []string{"", "é", "xBAD", strings.Repeat("x", size-3) + "BAD", strings.Repeat("x", size)} {
			c := scaledRuleWitness(size, prompt)
			solve := func(want bool) {
				t.Helper()
				w, err := frontend.NewWitness(c, field)
				if err != nil {
					t.Fatal(err)
				}
				if !expectedProverOutcome(want, ccs.IsSolved(w)) {
					t.Fatal("unexpected rule outcome")
				}
			}
			solve(true)
			for _, change := range []struct {
				a []frontend.Variable
				i int
			}{
				{c.Public[:], 97}, {c.Public[:], 98}, {c.Public[:], 99}, {c.Units, size - 1}, {c.UnitActive, size - 1},
			} {
				v := change.a[change.i].(int64)
				change.a[change.i] = v ^ 1
				solve(false)
				change.a[change.i] = v
			}
		}
	}
}
