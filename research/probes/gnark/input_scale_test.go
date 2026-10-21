package main

import (
	"os"
	"strings"
	"testing"
)

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
			_, err := inputScaleBatch(8)
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
