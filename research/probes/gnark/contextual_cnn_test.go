package main

import (
	"encoding/json"
	"math"
	"os"
	"strings"
	"testing"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/frontend/cs/r1cs"
)

func testContextualModel(t *testing.T) *contextualData {
	t.Helper()
	encoder, err := loadEncoderData()
	if err != nil {
		t.Fatal(err)
	}
	d := &contextualData{Schema: "hallmark.contextual-cnn-graph/1", Profile: encoder.Profile, Program: strings.Repeat("01", 32), Arithmetic: strings.Repeat("02", 32), WeightsSHA256: strings.Repeat("03", 32), EmbeddingFraction: 1, KernelFraction: 8, HeadFraction: 1, Embedding: make([][]int64, 256), Kernel: make([][]int64, cnnChannels), Bias: make([]int64, cnnChannels), Head: make([]int64, cnnChannels), OutputBias: -1}
	for i := range d.Embedding {
		d.Embedding[i] = make([]int64, cnnEmbedding)
	}
	for i := range d.Kernel {
		d.Kernel[i] = make([]int64, cnnKernel*cnnEmbedding)
	}
	d.Embedding['A'][0] = 3
	d.Embedding['B'][0] = -3
	d.Embedding[0][0] = 1
	d.Kernel[0][92] = 3
	d.Kernel[0][88] = -1
	d.Kernel[1][92] = -3
	d.Bias[0] = -1
	d.Bias[1] = 1
	d.Head[0] = 3
	d.Head[1] = -3
	return d
}

func TestContextualAdmission(t *testing.T) {
	d := testContextualModel(t)
	if err := d.validate(); err != nil {
		t.Fatal(err)
	}
	for _, mutate := range []func(*contextualData){
		func(d *contextualData) { d.Embedding = d.Embedding[:255] },
		func(d *contextualData) { d.Kernel[0] = d.Kernel[0][:95] },
		func(d *contextualData) { d.Embedding[0][0] = 128 },
		func(d *contextualData) { d.Kernel[0][0] = -129 },
		func(d *contextualData) { d.Head[0] = 128 },
		func(d *contextualData) { d.EmbeddingFraction = 16; d.KernelFraction = 16 },
		func(d *contextualData) { d.Bias[0] = 1<<31 - 1 },
		func(d *contextualData) { d.OutputBias = 1<<31 - 1 },
		func(d *contextualData) { d.OutputBias = 1 << 62 },
		func(d *contextualData) { d.Profile = "bad" },
	} {
		v := testContextualModel(t)
		mutate(v)
		if v.validate() == nil {
			t.Fatal("invalid CNN accepted")
		}
	}
	raw, _ := json.Marshal(d)
	var obj map[string]any
	json.Unmarshal(raw, &obj)
	raw, _ = json.Marshal(obj)
	t.Chdir(t.TempDir())
	for i, value := range [][]byte{raw, append([]byte(`{"schema_id":"duplicate",`), raw[1:]...), append(raw, []byte(" 0")...), []byte("{}"), []byte(strings.Repeat(" ", 65537))} {
		if err := os.WriteFile("model.json", value, 0600); err != nil {
			t.Fatal(err)
		}
		_, err := loadContextual()
		if (err == nil) != (i == 0) {
			t.Fatalf("CNN input %d: %v", i, err)
		}
	}
}

func contextualTestTrace(c *contextualCircuit) {
	d := c.Model
	count := int(c.Public[96].(int64))
	var pooled [cnnChannels]int64
	for pos := range cnnCapacity {
		for h := range cnnChannels {
			acc := d.Bias[h]
			for k := range cnnKernel {
				at := pos - (cnnKernel - 1 - k)
				if at < 0 || at >= count {
					continue
				}
				token := c.Units[at].(int64)
				for j := range cnnEmbedding {
					acc += d.Embedding[token][j] * d.Kernel[h][k*cnnEmbedding+j]
				}
			}
			z := int64(math.RoundToEven(float64(acc) / math.Exp2(float64(d.EmbeddingFraction+d.KernelFraction-8))))
			a := max(0, z)
			i := (pos*cnnChannels + h) * 3
			c.Trace[i], c.Trace[i+1], c.Trace[i+2] = acc, z, a
			if pos < count {
				pooled[h] = max(pooled[h], a)
			}
		}
	}
	output := d.OutputBias
	for h, v := range pooled {
		c.Trace[cnnCapacity*cnnChannels*3+h] = v
		output += v * d.Head[h]
	}
	score := int64(math.RoundToEven(float64(output) / math.Exp2(float64(d.HeadFraction))))
	c.Trace[cnnTraceSize-2], c.Trace[cnnTraceSize-1] = output, score
	c.Public[97] = int64(1)
	c.Public[98] = int64(1<<31) + score
	c.Public[99] = int64(0)
}

func TestContextualCircuitAndMutations(t *testing.T) {
	d := testContextualModel(t)
	field := ecc.BLS12_381.ScalarField()
	ccs, err := frontend.Compile(field, r1cs.NewBuilder, newContextual(8, d))
	if err != nil {
		t.Fatal(err)
	}
	if ccs.GetNbPublicVariables() != 101 {
		t.Fatal("public layout changed")
	}
	for _, old := range encoderTestAssignments(t, "encoder-fixture.json", 15) {
		c := newContextual(8, d)
		c.Public, c.Salt = old.Public, old.Salt
		c.Units, c.Encoded, c.Positions, c.UnitActive, c.EncodedActive = old.Units, old.Encoded, old.Positions, old.UnitActive, old.EncodedActive
		contextualTestTrace(c)
		check := func(valid bool) {
			t.Helper()
			w, err := frontend.NewWitness(c, field)
			if err != nil {
				t.Fatal(err)
			}
			err = ccs.IsSolved(w)
			if (err == nil) != valid {
				t.Fatalf("CNN constraint result: %v", err)
			}
		}
		check(true)
		for _, index := range []int{0, 1, 2, cnnCapacity * cnnChannels * 3, cnnTraceSize - 2, cnnTraceSize - 1} {
			v := c.Trace[index].(int64)
			c.Trace[index] = v + 1
			check(false)
			c.Trace[index] = v
		}
		threshold := c.Public[98].(int64)
		c.Public[98] = threshold + 1
		check(false)
		c.Public[99] = int64(1)
		check(true)
		c.Public[98], c.Public[99] = threshold, int64(0)
		v := c.UnitActive[7].(int64)
		c.UnitActive[7] = 1 - v
		check(false)
		c.UnitActive[7] = v
	}
}
