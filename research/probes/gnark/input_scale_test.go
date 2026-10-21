package main

import (
	"os"
	"strings"
	"testing"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/frontend/cs/r1cs"
)

type prefixFixture struct {
	Flags [4]frontend.Variable
	Count frontend.Variable
}

func (c *prefixFixture) Define(api frontend.API) error {
	constrainPrefix(api, c.Flags[:], c.Count)
	return nil
}

func TestPrefixCoverageAcceptsOnlyExactBooleanPrefixes(t *testing.T) {
	field := ecc.BLS12_381.ScalarField()
	ccs, err := frontend.Compile(field, r1cs.NewBuilder, &prefixFixture{})
	if err != nil {
		t.Fatal(err)
	}
	for mask := 0; mask < 16; mask++ {
		for count := 0; count <= 4; count++ {
			value := prefixFixture{Count: count}
			for i := range value.Flags {
				value.Flags[i] = (mask >> i) & 1
			}
			witness, err := frontend.NewWitness(&value, field)
			if err != nil {
				t.Fatal(err)
			}
			// This isolated Boolean relation has no commitment hint; this is not proof evidence.
			if (ccs.IsSolved(witness) == nil) != (mask == (1<<count)-1) {
				t.Fatalf("incorrect acceptance for mask %d count %d", mask, count)
			}
		}
	}
	for _, flags := range [][4]frontend.Variable{{2, 0, 0, 0}, {1, 2, -1, 0}, {-1, 1, 1, 1}} {
		witness, err := frontend.NewWitness(&prefixFixture{Flags: flags, Count: 2}, field)
		if err != nil {
			t.Fatal(err)
		}
		if ccs.IsSolved(witness) == nil {
			t.Fatal("accepted non-Boolean prefix")
		}
	}
}

func TestInputBatchRejectsMalformedManifestBeforeLoadingKeys(t *testing.T) {
	for _, test := range []struct{ name, raw, message string }{
		{"empty", `[]`, "invalid batch"},
		{"unknown-field", `[{"name":"valid","valid":true,"extra":0}]`, "invalid batch"},
		{"trailing", `[{"name":"valid","valid":true}] 0`, "trailing batch data"},
		{"path", `[{"name":"../escape","valid":true}]`, "invalid batch case"},
		{"missing-expectation", `[{"name":"valid"}]`, "invalid batch case"},
		{"duplicate", `[{"name":"valid","valid":true},{"name":"valid","valid":true}]`, "invalid batch case"},
		{"oversize", `[]` + strings.Repeat(" ", 8192), "invalid batch size"},
	} {
		t.Run(test.name, func(t *testing.T) {
			t.Chdir(t.TempDir())
			if err := os.WriteFile("cases.json", []byte(test.raw), 0600); err != nil {
				t.Fatal(err)
			}
			_, err := inputScaleBatch(8, 256*1024*1024)
			if err == nil || err.Error() != test.message {
				t.Fatalf("expected %q, got %v", test.message, err)
			}
		})
	}
}

func TestAssignmentReaderRejectsNoncanonicalOrOversizedNumbers(t *testing.T) {
	for _, raw := range []string{"", "1", "01\n", "-1\n", "4294967296\n", "0\n0\n", strings.Repeat("0", 12)} {
		name := t.TempDir() + "/assignment.txt"
		if err := os.WriteFile(name, []byte(raw), 0600); err != nil {
			t.Fatal(err)
		}
		if _, err := readAssignmentFile(name, 1); err == nil {
			t.Fatalf("accepted noncanonical assignment %q", raw)
		}
	}
}
