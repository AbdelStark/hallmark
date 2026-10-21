// A bounded real-proof installation probe, not a Hallmark classifier relation.
package main

import (
	"encoding/json"
	"errors"
	"io"
	"os"
	"strconv"
	"syscall"
	"time"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/backend/groth16"
	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/frontend/cs/r1cs"
	"github.com/consensys/gnark/logger"
)

// The private byte x satisfies y=x³+x+5; both ranges are constrained.
type circuit struct {
	X frontend.Variable
	Y frontend.Variable `gnark:",public"`
}

func (c *circuit) Define(api frontend.API) error {
	api.ToBinary(c.X, 8)
	api.ToBinary(c.Y, 32)
	api.AssertIsEqual(c.Y, api.Add(api.Mul(c.X, c.X, c.X), c.X, 5))
	return nil
}

func number(text string, bits int) (uint64, error) {
	n, err := strconv.ParseUint(text, 10, bits)
	if err != nil || strconv.FormatUint(n, 10) != text {
		return 0, errors.New("noncanonical integer")
	}
	return n, nil
}

func write(name string, value io.WriterTo) error {
	handle, err := os.OpenFile(name, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		return err
	}
	defer handle.Close()
	if _, err := value.WriteTo(handle); err != nil {
		return err
	}
	return handle.Sync()
}

func read(name string, value io.ReaderFrom) error {
	handle, err := os.OpenFile(name, os.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_NONBLOCK, 0)
	if err != nil {
		return err
	}
	defer handle.Close()
	before, err := handle.Stat()
	if err != nil || !before.Mode().IsRegular() || before.Size() > 256*1024*1024 || before.Sys().(*syscall.Stat_t).Nlink != 1 {
		return errors.New("invalid artifact size")
	}
	reader := &io.LimitedReader{R: handle, N: before.Size() + 1}
	n, err := value.ReadFrom(reader)
	if err != nil {
		return err
	}
	if n != before.Size() || reader.N != 1 {
		return errors.New("trailing bytes")
	}
	after, err := handle.Stat()
	if err != nil || before.Size() != after.Size() || !before.ModTime().Equal(after.ModTime()) || after.Sys().(*syscall.Stat_t).Nlink != 1 {
		return errors.New("changed artifact")
	}
	path, err := os.Lstat(name)
	if err != nil || !os.SameFile(before, path) || !path.Mode().IsRegular() {
		return errors.New("changed artifact")
	}
	return nil
}

func run(args []string) (int, error) {
	if len(args) == 2 {
		switch args[0] {
		case "input-compile", "input-setup", "input-prove", "input-batch", "input-verify":
			return runInputScale(args[0][6:], args[1])
		}
	}
	if len(args) == 1 {
		switch args[0] {
		case "rule-setup", "rule-prove", "rule-verify", "mlp-setup", "mlp-prove", "mlp-verify",
			"block-setup", "block-prove", "block-verify":
			return runGraph(args[0])
		}
	}
	curve := ecc.BLS12_381
	if len(args) == 1 && args[0] == "setup" {
		ccs, err := frontend.Compile(curve.ScalarField(), r1cs.NewBuilder, &circuit{})
		if err != nil {
			return 0, err
		}
		pk, vk, err := groth16.Setup(ccs)
		if err != nil {
			return 0, err
		}
		for _, artifact := range []struct {
			name string
			data io.WriterTo
		}{{"circuit.r1cs", ccs}, {"pk.bin", pk}, {"vk.bin", vk}} {
			if err := write(artifact.name, artifact.data); err != nil {
				return 0, err
			}
		}
		return ccs.GetNbConstraints(), nil
	}
	if len(args) == 3 && args[0] == "prove" {
		x, err := number(args[1], 8)
		if err != nil {
			return 0, err
		}
		y, err := number(args[2], 32)
		if err != nil {
			return 0, err
		}
		ccs := groth16.NewCS(curve)
		pk := groth16.NewProvingKey(curve)
		if err := read("circuit.r1cs", ccs); err != nil {
			return 0, err
		}
		if err := read("pk.bin", pk); err != nil {
			return 0, err
		}
		witness, err := frontend.NewWitness(&circuit{X: x, Y: y}, curve.ScalarField())
		if err != nil {
			return 0, err
		}
		proof, err := groth16.Prove(ccs, pk, witness)
		if err != nil {
			return 0, err
		}
		return ccs.GetNbConstraints(), write("proof.bin", proof)
	}
	if len(args) == 2 && args[0] == "verify" {
		y, err := number(args[1], 32)
		if err != nil {
			return 0, err
		}
		vk, proof := groth16.NewVerifyingKey(curve), groth16.NewProof(curve)
		if err := read("vk.bin", vk); err != nil {
			return 0, err
		}
		if err := read("proof.bin", proof); err != nil {
			return 0, err
		}
		witness, err := frontend.NewWitness(
			&circuit{Y: y}, curve.ScalarField(), frontend.PublicOnly(),
		)
		if err != nil {
			return 0, err
		}
		return 0, groth16.Verify(proof, vk, witness)
	}
	return 0, errors.New("invalid command")
}

func main() {
	logger.Disable()
	start := time.Now()
	constraints, err := run(os.Args[1:])
	status := "passed"
	if err != nil {
		status = "failed"
	}
	result := struct {
		Schema      string `json:"schema_id"`
		Status      string `json:"status"`
		Constraints int    `json:"constraints"`
		ElapsedNS   int64  `json:"elapsed_ns"`
	}{
		"hallmark.gnark-installation-probe/1", status, constraints, time.Since(start).Nanoseconds(),
	}
	if json.NewEncoder(os.Stdout).Encode(result) != nil || err != nil {
		os.Exit(1)
	}
}
