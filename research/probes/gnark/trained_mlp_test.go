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

func testTrainedModel(t *testing.T) *trainedMlpData {
	t.Helper()
	encoder, err := loadEncoderData()
	if err != nil {
		t.Fatal(err)
	}
	d := &trainedMlpData{Schema: "hallmark.trained-mlp-graph/1", Profile: encoder.Profile,
		Program: strings.Repeat("01", 32), Arithmetic: strings.Repeat("02", 32), WeightsSHA256: strings.Repeat("03", 32),
		FirstFraction: 1, LastFraction: 1, HiddenBias: []int64{-1, 1, -3, 0},
		OutputWeights: []int64{3, -3, 1, 0}, OutputBias: -1}
	for range 4 {
		d.HiddenWeights = append(d.HiddenWeights, make([]int64, 256))
	}
	d.HiddenWeights[0][0], d.HiddenWeights[0]['A'], d.HiddenWeights[0]['x'] = 1, 3, -3
	d.HiddenWeights[1][0], d.HiddenWeights[1]['A'], d.HiddenWeights[1]['x'] = -1, -3, 3
	d.HiddenWeights[2]['B'] = 1
	return d
}

func TestTrainedRounding(t *testing.T) {
	for shift := 0; shift <= 30; shift++ {
		for _, n := range []int64{-(1 << 31), -1073741825, -257, -7, -5, -3, -1, 0, 1, 3, 5, 7, 257, 1073741825, (1 << 31) - 1} {
			want := int64(math.RoundToEven(float64(n) / math.Exp2(float64(shift))))
			if got := roundInteger(n, shift); got != want {
				t.Fatalf("round %d/%d: %d != %d", n, shift, got, want)
			}
		}
	}
}

func TestTrainedModelAdmission(t *testing.T) {
	d := testTrainedModel(t)
	if err := d.validate(); err != nil {
		t.Fatal(err)
	}
	for _, mutate := range []func(*trainedMlpData){
		func(d *trainedMlpData) { d.FirstFraction = 31 }, func(d *trainedMlpData) { d.LastFraction = -1 },
		func(d *trainedMlpData) { d.HiddenWeights[0][0] = 128 }, func(d *trainedMlpData) { d.HiddenBias[0] = 1<<31 - 1 },
		func(d *trainedMlpData) { d.OutputBias = 1<<31 - 1 }, func(d *trainedMlpData) { d.Profile = "bad" },
		func(d *trainedMlpData) { d.HiddenWeights[0] = d.HiddenWeights[0][:255] },
	} {
		d := testTrainedModel(t)
		mutate(d)
		if d.validate() == nil {
			t.Fatal("invalid model accepted")
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
		_, err := loadTrainedMlp()
		if (err == nil) != (i == 0) {
			t.Fatalf("model input %d: %v", i, err)
		}
	}
}

func TestTrainedLookupCircuitAndMutations(t *testing.T) {
	d := testTrainedModel(t)
	field := ecc.BLS12_381.ScalarField()
	ccs, err := frontend.Compile(field, r1cs.NewBuilder, newTrainedMlp(8, d))
	if err != nil {
		t.Fatal(err)
	}
	if ccs.GetNbPublicVariables() != 101 {
		t.Fatal("public layout changed")
	}
	for _, old := range encoderTestAssignments(t, "encoder-fixture.json", 15) {
		c := newTrainedMlp(8, d)
		c.Public, c.Salt = old.Public, old.Salt
		c.Units, c.Encoded, c.Positions, c.UnitActive, c.EncodedActive = old.Units, old.Encoded, old.Positions, old.UnitActive, old.EncodedActive
		var output int64 = d.OutputBias
		for i, row := range d.HiddenWeights {
			acc := d.HiddenBias[i]
			for j := 0; j < int(c.Public[96].(int64)); j++ {
				acc += row[c.Units[j].(int64)]
			}
			hidden := int64(math.RoundToEven(float64(acc) / 2))
			activated := max(0, hidden)
			c.Trace[i], c.Trace[4+i], c.Trace[8+i] = acc, hidden, activated
			output += activated * d.OutputWeights[i]
		}
		score := int64(math.RoundToEven(float64(output) / 2))
		c.Trace[12], c.Trace[13] = output, score
		c.Public[97] = int64(1)
		threshold := c.Public[98].(int64) - (1 << 31)
		c.Public[99] = int64(0)
		if score < threshold {
			c.Public[99] = int64(1)
		}
		solve := func(want bool) {
			t.Helper()
			w, err := frontend.NewWitness(c, field)
			if err != nil {
				t.Fatal(err)
			}
			if !expectedProverOutcome(want, ccs.IsSolved(w)) {
				t.Fatal("unexpected trained circuit outcome")
			}
		}
		solve(true)
		for _, item := range []struct {
			field []frontend.Variable
			index int
			value int64
		}{
			{c.Units, 7, c.Units[7].(int64) ^ 1}, {c.Trace, 4, c.Trace[4].(int64) ^ 1},
			{c.Public[:], 97, 2}, {c.Public[:], 32, 256}, {c.Public[:], 99, 1 - c.Public[99].(int64)},
		} {
			saved := item.field[item.index]
			item.field[item.index] = item.value
			solve(false)
			item.field[item.index] = saved
		}
		// Equality blocks; one above passes, including negative scores.
		for _, offset := range []int64{0, 1} {
			c.Public[98], c.Public[99] = int64(1<<31)+score+offset, offset
			solve(true)
			c.Public[99] = 1 - offset
			solve(false)
		}
	}
}
