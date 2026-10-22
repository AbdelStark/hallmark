package main

import (
	"bytes"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"os"
	"syscall"

	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/std/lookup/logderivlookup"
)

// Constants are enrolled with the native export and setup key before proving.
type trainedMlpData struct {
	Schema        string    `json:"schema_id"`
	Program       string    `json:"program"`
	Profile       string    `json:"input_profile"`
	Arithmetic    string    `json:"arithmetic"`
	WeightsSHA256 string    `json:"weights_sha256"`
	FirstFraction int       `json:"first_fraction"`
	LastFraction  int       `json:"last_fraction"`
	HiddenWeights [][]int64 `json:"hidden_weights"`
	HiddenBias    []int64   `json:"hidden_bias"`
	OutputWeights []int64   `json:"output_weights"`
	OutputBias    int64     `json:"output_bias"`
}

func roundInteger(value int64, shift int) int64 {
	negative := value < 0
	if negative {
		value = -value
	}
	divisor := int64(1) << shift
	q, r := value/divisor, value%divisor
	if 2*r > divisor || (2*r == divisor && q&1 == 1) {
		q++
	}
	if negative {
		return -q
	}
	return q
}

func int32Range(low, high int64) bool { return low >= -(1<<31) && high < 1<<31 }

func (d *trainedMlpData) validate() error {
	if d.Schema != "hallmark.trained-mlp-graph/1" || d.FirstFraction < 0 || d.FirstFraction > 30 || d.LastFraction < 0 || d.LastFraction > 30 || len(d.HiddenWeights) != 4 || len(d.HiddenBias) != 4 || len(d.OutputWeights) != 4 {
		return errors.New("unsupported trained MLP profile")
	}
	for _, pin := range []string{d.Program, d.Profile, d.Arithmetic, d.WeightsSHA256} {
		raw, err := hex.DecodeString(pin)
		if err != nil || len(raw) != 32 || hex.EncodeToString(raw) != pin {
			return errors.New("invalid native export pin")
		}
	}
	lo, hi := d.OutputBias, d.OutputBias
	if !int32Range(lo, hi) {
		return errors.New("output bias overflow")
	}
	for i, row := range d.HiddenWeights {
		low, high := d.HiddenBias[i], d.HiddenBias[i]
		if len(row) != 256 || !int32Range(low, high) || d.OutputWeights[i] < -128 || d.OutputWeights[i] > 127 {
			return errors.New("invalid affine parameters")
		}
		for _, weight := range row {
			if weight < -128 || weight > 127 {
				return errors.New("weight outside int8")
			}
			// Independent counts in [0,512] overapproximate every ordered partial sum.
			low += min(weight*512, 0)
			high += max(weight*512, 0)
			if !int32Range(low, high) {
				return errors.New("hidden accumulator overflow")
			}
		}
		a := max(0, roundInteger(low, d.FirstFraction)) * d.OutputWeights[i]
		b := max(0, roundInteger(high, d.FirstFraction)) * d.OutputWeights[i]
		lo += min(a, b)
		hi += max(a, b)
		if !int32Range(lo, hi) {
			return errors.New("output accumulator overflow")
		}
	}
	return nil
}

func loadTrainedMlp() (*trainedMlpData, error) {
	f, err := os.OpenFile("model.json", os.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_NONBLOCK, 0)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	stat, err := f.Stat()
	if err != nil || !stat.Mode().IsRegular() || stat.Size() > 65536 || stat.Sys().(*syscall.Stat_t).Nlink != 1 {
		return nil, errors.New("invalid model file")
	}
	raw, err := io.ReadAll(io.LimitReader(f, 65537))
	if err != nil || len(raw) > 65536 || int64(len(raw)) != stat.Size() {
		return nil, errors.New("invalid model bytes")
	}
	var d trainedMlpData
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&d); err != nil {
		return nil, err
	}
	if decoder.Decode(new(any)) != io.EOF {
		return nil, errors.New("trailing model bytes")
	}
	// Require the complete canonical object; duplicate and omitted fields cannot survive.
	canonical, _ := json.Marshal(d)
	var object map[string]any
	if err := json.Unmarshal(canonical, &object); err != nil {
		return nil, err
	}
	canonical, _ = json.Marshal(object)
	if !bytes.Equal(bytes.TrimSpace(raw), canonical) {
		return nil, errors.New("noncanonical model")
	}
	return &d, d.validate()
}

type trainedMlpCircuit struct {
	Public        [100]frontend.Variable `gnark:",public"`
	Salt          [32]frontend.Variable
	Units         []frontend.Variable
	Encoded       []frontend.Variable
	Positions     []frontend.Variable
	UnitActive    []frontend.Variable
	EncodedActive []frontend.Variable
	Trace         []frontend.Variable
	Model         *trainedMlpData `gnark:"-"`
}

func newTrainedMlp(size int, d *trainedMlpData) *trainedMlpCircuit {
	input := newInputScale(size)
	return &trainedMlpCircuit{Salt: input.Salt, Units: input.Units, Encoded: input.Encoded,
		Positions: input.Positions, UnitActive: input.UnitActive, EncodedActive: input.EncodedActive,
		Trace: make([]frontend.Variable, ((size+511)/512)*14), Model: d}
}

func (c *trainedMlpCircuit) Define(api frontend.API) error {
	if err := c.Model.validate(); err != nil {
		return err
	}
	profile, _ := hex.DecodeString(c.Model.Profile)
	input := &inputScaleCircuit{Salt: c.Salt, Units: c.Units, Encoded: c.Encoded,
		Positions: c.Positions, UnitActive: c.UnitActive, EncodedActive: c.EncodedActive}
	input.Public[0] = c.Public[96]
	copy(input.Public[1:], c.Public[64:96])
	if err := input.defineProfile(api, profile); err != nil {
		return err
	}
	for _, value := range c.Public[:64] {
		api.ToBinary(value, 8)
	}
	api.ToBinary(c.Public[97], 15)
	api.ToBinary(c.Public[98], 32)
	api.AssertIsBoolean(c.Public[99])
	tables := make([]logderivlookup.Table, 4)
	for i, row := range c.Model.HiddenWeights {
		tables[i] = logderivlookup.New(api)
		for _, weight := range row {
			tables[i].Insert(weight)
		}
	}
	round := func(value frontend.Variable, shift int) frontend.Variable {
		signed32(api, value)
		if shift == 0 {
			return value
		}
		if shift == 1 {
			return roundHalf(api, value)
		}
		result := encoderRound(api, value, shift)
		signed32(api, result)
		return result
	}
	var maximum, count frontend.Variable = 0, 1
	for start, chunk := 0, 0; start < len(c.Units); start, chunk = start+512, chunk+1 {
		end := min(start+512, len(c.Units))
		trace := c.Trace[chunk*14 : (chunk+1)*14]
		var output frontend.Variable = c.Model.OutputBias
		for i, table := range tables {
			values := table.Lookup(c.Units[start:end]...)
			var accumulator frontend.Variable = c.Model.HiddenBias[i]
			for j, weight := range values {
				accumulator = api.Add(accumulator, api.Mul(c.UnitActive[start+j], weight))
			}
			hidden := round(accumulator, c.Model.FirstFraction)
			activated := api.Select(signed32(api, hidden)[31], hidden, 0)
			api.AssertIsEqual(trace[i], accumulator)
			api.AssertIsEqual(trace[4+i], hidden)
			api.AssertIsEqual(trace[8+i], activated)
			output = api.Add(output, api.Mul(activated, c.Model.OutputWeights[i]))
		}
		score := round(output, c.Model.LastFraction)
		api.AssertIsEqual(trace[12], output)
		api.AssertIsEqual(trace[13], score)
		if start == 0 {
			maximum = score
		} else {
			active := c.UnitActive[start]
			count = api.Add(count, active)
			atLeast := api.ToBinary(api.Add(api.Sub(score, maximum), uint64(1<<32)), 33)[32]
			maximum = api.Select(active, api.Select(atLeast, score, maximum), maximum)
		}
	}
	api.AssertIsEqual(c.Public[97], count)
	difference := api.Sub(c.Public[98], api.Add(maximum, uint64(1<<31)))
	positive := api.ToBinary(api.Add(difference, uint64(1<<32)), 33)[32]
	api.AssertIsEqual(c.Public[99], api.Mul(positive, api.Sub(1, api.IsZero(difference))))
	return nil
}

func trainedMlpAssignment(size int, d *trainedMlpData, name string, private bool) (frontend.Circuit, error) {
	c := newTrainedMlp(size, d)
	fields := [][]frontend.Variable{c.Public[:]}
	if private {
		fields = append(fields, c.Salt[:], c.Units, c.Encoded, c.Positions, c.UnitActive, c.EncodedActive, c.Trace)
	}
	count := 0
	for _, field := range fields {
		count += len(field)
	}
	values, err := readAssignmentFile(name, count)
	if err != nil {
		return nil, err
	}
	next := 0
	for j, field := range fields {
		for i := range field {
			if private && j == len(fields)-1 {
				field[i] = int64(values[next]) - int64(1<<31)
			} else {
				field[i] = values[next]
			}
			next++
		}
	}
	return c, nil
}

func runTrainedMlp(action, rawSize string) (int, error) {
	size, err := number(rawSize, 16)
	if err != nil || (size != 8 && size != 96 && size != 1024) {
		return 0, errors.New("unsupported trained MLP capacity")
	}
	d, err := loadTrainedMlp()
	if err != nil {
		return 0, err
	}
	if action == "batch" {
		return relationBatch(func(name string) (frontend.Circuit, error) {
			return trainedMlpAssignment(int(size), d, name, true)
		}, 2*1024*1024*1024, 12, 4096)
	}
	return runRelation(action, newTrainedMlp(int(size), d), func(private bool) (frontend.Circuit, error) {
		return trainedMlpAssignment(int(size), d, "assignment.txt", private)
	}, 2*1024*1024*1024)
}
