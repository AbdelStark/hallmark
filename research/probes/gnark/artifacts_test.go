package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"testing"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/backend/groth16"
)

func TestArtifactExplicitLimit(t *testing.T) {
	name := filepath.Join(t.TempDir(), "artifact")
	if err := os.WriteFile(name, []byte("data"), 0600); err != nil {
		t.Fatal(err)
	}
	for _, limit := range []int64{
		-1, 0, 3, 4,
		24 * 1024 * 1024 * 1024, 24*1024*1024*1024 + 1,
		48 * 1024 * 1024 * 1024, 48*1024*1024*1024 + 1,
	} {
		called := false
		decoder := artifactReader(func(r io.Reader) (int64, error) {
			called = true
			return io.Copy(io.Discard, r)
		})
		err := readBounded(name, decoder, limit)
		accepted := limit >= 4 && limit <= 48*1024*1024*1024
		if (err == nil) != accepted || called != accepted {
			t.Fatalf("limit %d: called=%v, error=%v", limit, called, err)
		}
	}
}

func TestCompiledSetupRoundTrip(t *testing.T) {
	for _, test := range []struct {
		name  string
		limit int64
	}{
		{"default", 256 * 1024 * 1024},
		{"maximum-encoder", 48 * 1024 * 1024 * 1024},
	} {
		t.Run(test.name, func(t *testing.T) {
			directory := t.TempDir()
			t.Chdir(directory)
			for _, action := range []string{"export", "inspect", "setup-compiled"} {
				if action == "inspect" {
					if err := os.Rename("capacity.json", "export-capacity.json"); err != nil {
						t.Fatal(err)
					}
				}
				count, err := runRelation(action, &circuit{}, nil, test.limit)
				if err != nil || count != 45 {
					t.Fatalf("%s: count=%d, error=%v", action, count, err)
				}
			}
			exported, err := os.ReadFile("export-capacity.json")
			if err != nil {
				t.Fatal(err)
			}
			inspected, err := os.ReadFile("capacity.json")
			if err != nil || !bytes.Equal(exported, inspected) {
				t.Fatalf("round-trip capacity changed: %v", err)
			}
			var report map[string]any
			if err := json.Unmarshal(exported, &report); err != nil || report["public_variables"] != float64(2) || report["secret_variables"] != float64(1) {
				t.Fatalf("invalid variable counts: %s", exported)
			}
			if report["commitments"] != float64(0) || report["private_committed_variables"] != float64(0) {
				t.Fatalf("unexpected commitments: %s", exported)
			}
			for _, args := range [][]string{{"prove", "3", "35"}, {"verify", "35"}} {
				if _, err := run(args); err != nil {
					t.Fatalf("%v: %v", args, err)
				}
			}
			if _, err := runRelation("export", &circuit{}, nil, test.limit); err == nil {
				t.Fatal("overwrote existing circuit")
			}
			if err := os.WriteFile("circuit.r1cs", []byte("invalid"), 0600); err != nil {
				t.Fatal(err)
			}
			if _, err := runRelation("setup-compiled", &circuit{}, nil, test.limit); err == nil {
				t.Fatal("accepted malformed compiled circuit")
			}
		})
	}
}

type artifactReader func(io.Reader) (int64, error)

func (f artifactReader) ReadFrom(r io.Reader) (int64, error) { return f(r) }

type artifactWriter func(io.Writer) (int64, error)

func (f artifactWriter) WriteTo(w io.Writer) (int64, error) { return f(w) }

func TestArtifactWriterBytesAndFailures(t *testing.T) {
	for _, size := range []int{0, 1, 65535, 65536, 65537, 131073} {
		for _, fail := range []bool{false, true} {
			name := filepath.Join(t.TempDir(), "artifact")
			raw := bytes.Repeat([]byte{0, 1, 255}, (size+2)/3)[:size]
			serializationErr := errors.New("serialization failed")
			encoder := artifactWriter(func(w io.Writer) (int64, error) {
				var n int64
				for start := 0; start < len(raw); start += 48 {
					written, err := w.Write(raw[start:min(start+48, len(raw))])
					n += int64(written)
					if err != nil {
						return n, err
					}
				}
				if fail {
					return n, serializationErr
				}
				return n, nil
			})
			err := write(name, encoder)
			if (err == nil) == fail || (fail && !errors.Is(err, serializationErr)) {
				t.Fatalf("size=%d fail=%v: %v", size, fail, err)
			}
			actual, err := os.ReadFile(name)
			if err != nil || !bytes.Equal(actual, raw) {
				t.Fatalf("lost serialized bytes: %v", err)
			}
			if err := write(name, bytes.NewReader([]byte("overwrite"))); err == nil {
				t.Fatal("overwrote existing artifact")
			}
			actual, err = os.ReadFile(name)
			if err != nil || !bytes.Equal(actual, raw) {
				t.Fatal("changed existing artifact")
			}
		}
	}
}

func TestArtifactWriterFlushFailure(t *testing.T) {
	if os.Getenv("HALLMARK_FLUSH_FAILURE_CHILD") != "1" {
		cmd := exec.Command(os.Args[0], "-test.run=^TestArtifactWriterFlushFailure$")
		cmd.Env = append(os.Environ(), "HALLMARK_FLUSH_FAILURE_CHILD=1")
		if output, err := cmd.CombinedOutput(); err != nil {
			t.Fatalf("flush failure fixture: %v\n%s", err, output)
		}
		return
	}
	// Isolate the real file-size limit from the parent test process.
	var limit syscall.Rlimit
	if err := syscall.Getrlimit(syscall.RLIMIT_FSIZE, &limit); err != nil {
		t.Fatal(err)
	}
	limit.Cur = 256
	if err := syscall.Setrlimit(syscall.RLIMIT_FSIZE, &limit); err != nil {
		t.Fatal(err)
	}
	name := filepath.Join(t.TempDir(), "artifact")
	if err := write(name, bytes.NewReader(make([]byte, 512))); err == nil {
		t.Fatal("accepted failed flush")
	}
}

func TestArtifactReaderBoundaries(t *testing.T) {
	for _, kind := range []string{"valid", "truncated", "trailing", "decoder-error", "wrong-count", "underread", "symlink", "hardlink", "directory", "fifo", "oversize", "changed"} {
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
				if kind == "underread" {
					_, err := r.Read(buf[:1])
					return 4, err
				}
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
		value func() io.ReaderFrom
	}{
		{"circuit.r1cs", func() io.ReaderFrom { return groth16.NewCS(ecc.BLS12_381) }},
		{"pk.bin", func() io.ReaderFrom { return groth16.NewProvingKey(ecc.BLS12_381) }},
		{"vk.bin", func() io.ReaderFrom { return groth16.NewVerifyingKey(ecc.BLS12_381) }},
		{"proof.bin", func() io.ReaderFrom { return groth16.NewProof(ecc.BLS12_381) }},
	} {
		raw, err := os.ReadFile(artifact.name)
		if err != nil {
			t.Fatal(err)
		}
		decoded := artifact.value()
		if err := read(artifact.name, decoded); err != nil {
			t.Fatal(err)
		}
		var reference bytes.Buffer
		if _, err := decoded.(io.WriterTo).WriteTo(&reference); err != nil || !bytes.Equal(raw, reference.Bytes()) {
			t.Fatalf("serialized %s differs from reference: %v", artifact.name, err)
		}
		if err := os.WriteFile(artifact.name, append(raw, '!'), 0600); err != nil {
			t.Fatal(err)
		}
		if err := read(artifact.name, artifact.value()); err == nil {
			t.Fatalf("accepted trailing %s", artifact.name)
		}
	}
}
