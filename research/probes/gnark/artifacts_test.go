package main

import (
	"bytes"
	"errors"
	"io"
	"os"
	"path/filepath"
	"syscall"
	"testing"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/backend/groth16"
)

type artifactReader func(io.Reader) (int64, error)

func (f artifactReader) ReadFrom(r io.Reader) (int64, error) { return f(r) }

func TestArtifactReaderBoundaries(t *testing.T) {
	for _, kind := range []string{"valid", "truncated", "trailing", "decoder-error", "wrong-count", "symlink", "hardlink", "directory", "fifo", "oversize", "changed"} {
		t.Run(kind, func(t *testing.T) {
			name := filepath.Join(t.TempDir(), "artifact")
			raw := []byte("data")
			if kind == "truncated" {
				raw = raw[:3]
			}
			if kind == "trailing" {
				raw = append(raw, '!')
			}
			if err := os.WriteFile(name, raw, 0600); err != nil {
				t.Fatal(err)
			}
			switch kind {
			case "symlink", "hardlink":
				alias := name + ".alias"
				var err error
				if kind == "symlink" {
					err = os.Symlink(name, alias)
				} else {
					err = os.Link(name, alias)
				}
				if err != nil {
					t.Fatal(err)
				}
				name = alias
			case "directory":
				name = t.TempDir()
			case "fifo":
				if err := os.Remove(name); err != nil {
					t.Fatal(err)
				}
				if err := syscall.Mkfifo(name, 0600); err != nil {
					t.Fatal(err)
				}
			case "oversize":
				if err := os.Truncate(name, 256*1024*1024+1); err != nil {
					t.Fatal(err)
				}
			}
			called := false
			decoder := artifactReader(func(r io.Reader) (int64, error) {
				called = true
				if kind == "decoder-error" {
					return 0, errors.New("decoder failed")
				}
				var buf [4]byte
				n, err := io.ReadFull(r, buf[:])
				if err == nil && !bytes.Equal(buf[:], []byte("data")) {
					return int64(n), errors.New("wrong data")
				}
				if kind == "changed" {
					if err := os.Rename(name, name+".old"); err != nil {
						t.Fatal(err)
					}
					if err := os.WriteFile(name, raw, 0600); err != nil {
						t.Fatal(err)
					}
				}
				if kind == "wrong-count" {
					return 0, err
				}
				return int64(n), err
			})
			err := read(name, decoder)
			if (err == nil) != (kind == "valid") {
				t.Fatalf("unexpected result: %v", err)
			}
			if (kind == "symlink" || kind == "hardlink" || kind == "directory" || kind == "fifo" || kind == "oversize") && called {
				t.Fatal("unsafe file reached decoder")
			}
		})
	}
}

func TestArtifactReaderRealProof(t *testing.T) {
	t.Chdir(t.TempDir())
	for _, args := range [][]string{{"setup"}, {"prove", "3", "35"}, {"verify", "35"}} {
		if _, err := run(args); err != nil {
			t.Fatalf("%v: %v", args, err)
		}
	}
	if _, err := run([]string{"verify", "36"}); err == nil {
		t.Fatal("accepted changed public input")
	}
	for _, artifact := range []struct {
		name  string
		value io.ReaderFrom
	}{
		{"circuit.r1cs", groth16.NewCS(ecc.BLS12_381)},
		{"pk.bin", groth16.NewProvingKey(ecc.BLS12_381)},
		{"vk.bin", groth16.NewVerifyingKey(ecc.BLS12_381)},
		{"proof.bin", groth16.NewProof(ecc.BLS12_381)},
	} {
		raw, err := os.ReadFile(artifact.name)
		if err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(artifact.name, append(raw, '!'), 0600); err != nil {
			t.Fatal(err)
		}
		if err := read(artifact.name, artifact.value); err == nil {
			t.Fatalf("accepted trailing %s", artifact.name)
		}
	}
}
