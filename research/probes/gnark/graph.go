package main

import (
	"errors"
	"io"
	"os"
	"strings"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/backend/groth16"
	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/frontend/cs/r1cs"
)

func graph(kind string) (frontend.Circuit, *inputCircuit, []frontend.Variable) {
	if kind == "rule" {
		c := &ruleCircuit{}
		return c, &c.Input, nil
	}
	c := &mlpCircuit{}
	return c, &c.Input, c.Trace[:]
}

func graphAssignment(kind string, private bool) (frontend.Circuit, error) {
	c, input, trace := graph(kind)
	count := 100
	if private {
		count += 40 + len(trace)
	}
	handle, err := os.Open("assignment.txt")
	if err != nil {
		return nil, err
	}
	defer handle.Close()
	raw, err := io.ReadAll(io.LimitReader(handle, 8193))
	if err != nil || len(raw) > 8192 {
		return nil, errors.New("invalid assignment")
	}
	lines := strings.Split(string(raw), "\n")
	if len(lines) != count+1 || lines[count] != "" {
		return nil, errors.New("invalid assignment shape")
	}
	for i, line := range lines[:count] {
		n, err := number(line, 32)
		if err != nil {
			return nil, err
		}
		switch {
		case i < 100:
			input.Public[i] = n
		case i < 132:
			input.Salt[i-100] = n
		case i < 140:
			input.Units[i-132] = n
		default:
			trace[i-140] = int64(n) - int64(1<<31)
		}
	}
	return c, nil
}

func runGraph(command string) (int, error) {
	kind, action, found := strings.Cut(command, "-")
	if !found || (kind != "rule" && kind != "mlp") {
		return 0, errors.New("invalid graph kind")
	}
	curve := ecc.BLS12_381
	switch action {
	case "setup":
		prototype, _, _ := graph(kind)
		ccs, err := frontend.Compile(curve.ScalarField(), r1cs.NewBuilder, prototype)
		if err != nil {
			return 0, err
		}
		pk, vk, err := groth16.Setup(ccs)
		if err != nil {
			return ccs.GetNbConstraints(), err
		}
		for _, artifact := range []struct {
			name string
			data io.WriterTo
		}{{"circuit.r1cs", ccs}, {"pk.bin", pk}, {"vk.bin", vk}} {
			if err := write(artifact.name, artifact.data); err != nil {
				return ccs.GetNbConstraints(), err
			}
		}
		return ccs.GetNbConstraints(), nil
	case "prove":
		assignment, err := graphAssignment(kind, true)
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
		witness, err := frontend.NewWitness(assignment, curve.ScalarField())
		if err != nil {
			return 0, err
		}
		proof, err := groth16.Prove(ccs, pk, witness)
		if err != nil {
			return ccs.GetNbConstraints(), err
		}
		return ccs.GetNbConstraints(), write("proof.bin", proof)
	case "verify":
		assignment, err := graphAssignment(kind, false)
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
		witness, err := frontend.NewWitness(assignment, curve.ScalarField(), frontend.PublicOnly())
		if err != nil {
			return 0, err
		}
		return 0, groth16.Verify(proof, vk, witness)
	}
	return 0, errors.New("invalid graph command")
}
