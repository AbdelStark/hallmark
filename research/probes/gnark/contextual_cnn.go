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

const cnnCapacity, cnnKernel, cnnEmbedding, cnnChannels = 96, 24, 4, 32
const cnnTraceSize = cnnCapacity*cnnChannels*3 + cnnChannels + 2

type contextualData struct {
	Schema            string    `json:"schema_id"`
	Program           string    `json:"program"`
	Profile           string    `json:"input_profile"`
	Arithmetic        string    `json:"arithmetic"`
	WeightsSHA256     string    `json:"weights_sha256"`
	EmbeddingFraction int       `json:"embedding_fraction"`
	KernelFraction    int       `json:"kernel_fraction"`
	HeadFraction      int       `json:"head_fraction"`
	Embedding         [][]int64 `json:"embedding"`
	Kernel            [][]int64 `json:"kernel"`
	Bias              []int64   `json:"bias"`
	Head              []int64   `json:"head"`
	OutputBias        int64     `json:"output_bias"`
}

func cnnRound(value int64, shift int) int64 {
	if shift < 0 {
		return value << -shift
	}
	return roundInteger(value, shift)
}

func (d *contextualData) validate() error {
	if d.Schema != "hallmark.contextual-cnn-graph/1" || len(d.Embedding) != 256 || len(d.Kernel) != cnnChannels || len(d.Bias) != cnnChannels || len(d.Head) != cnnChannels {
		return errors.New("unsupported contextual CNN shape")
	}
	for _, f := range []int{d.EmbeddingFraction, d.KernelFraction, d.HeadFraction} {
		if f < 0 || f > 16 {
			return errors.New("invalid CNN fraction")
		}
	}
	if d.EmbeddingFraction+d.KernelFraction > 30 {
		return errors.New("unsupported product scale")
	}
	for _, pin := range []string{d.Program, d.Profile, d.Arithmetic, d.WeightsSHA256} {
		raw, err := hex.DecodeString(pin)
		if err != nil || len(raw) != 32 || hex.EncodeToString(raw) != pin {
			return errors.New("invalid CNN pin")
		}
	}
	var low, high [cnnEmbedding]int64
	for _, row := range d.Embedding {
		if len(row) != cnnEmbedding {
			return errors.New("invalid embedding shape")
		}
		for j, v := range row {
			if v < -128 || v > 127 {
				return errors.New("embedding outside int8")
			}
			low[j], high[j] = min(low[j], v), max(high[j], v)
		}
	}
	lo, hi := d.OutputBias, d.OutputBias
	if !int32Range(lo*256, hi*256) || !int32Range(lo, hi) {
		return errors.New("output bias overflow")
	}
	for h, row := range d.Kernel {
		if len(row) != cnnKernel*cnnEmbedding || d.Head[h] < -128 || d.Head[h] > 127 || !int32Range(d.Bias[h], d.Bias[h]) {
			return errors.New("invalid CNN affine")
		}
		a, b := d.Bias[h], d.Bias[h]
		for j, w := range row {
			if w < -128 || w > 127 {
				return errors.New("kernel outside int8")
			}
			x, y := low[j%cnnEmbedding]*w, high[j%cnnEmbedding]*w
			a += min(x, y)
			b += max(x, y)
			if !int32Range(a, b) {
				return errors.New("convolution overflow")
			}
		}
		a, b = cnnRound(a, d.EmbeddingFraction+d.KernelFraction-8), cnnRound(b, d.EmbeddingFraction+d.KernelFraction-8)
		if !int32Range(a, b) {
			return errors.New("hidden rescale overflow")
		}
		// Pooling can be zero even when every affine is positive (empty input).
		radius := max(0, b) * d.Head[h]
		lo += min(0, radius)
		hi += max(0, radius)
		// The native DAG exposes integer score units with 256-scaled head constants.
		if !int32Range(lo, hi) || !int32Range(lo*256, hi*256) {
			return errors.New("head overflow")
		}
	}
	return nil
}

func loadContextual() (*contextualData, error) {
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
	var d contextualData
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err = decoder.Decode(&d); err != nil {
		return nil, err
	}
	if decoder.Decode(new(any)) != io.EOF {
		return nil, errors.New("trailing model bytes")
	}
	canonical, _ := json.Marshal(d)
	var object map[string]any
	if err = json.Unmarshal(canonical, &object); err != nil {
		return nil, err
	}
	canonical, _ = json.Marshal(object)
	if !bytes.Equal(bytes.TrimSpace(raw), canonical) {
		return nil, errors.New("noncanonical model")
	}
	return &d, d.validate()
}

type contextualCircuit struct {
	Public                                               [100]frontend.Variable `gnark:",public"`
	Salt                                                 [32]frontend.Variable
	Units, Encoded, Positions, UnitActive, EncodedActive []frontend.Variable
	Trace                                                []frontend.Variable
	Model                                                *contextualData `gnark:"-"`
}

func newContextual(size int, d *contextualData) *contextualCircuit {
	i := newInputScale(size)
	return &contextualCircuit{Units: i.Units, Encoded: i.Encoded, Positions: i.Positions, UnitActive: i.UnitActive, EncodedActive: i.EncodedActive, Trace: make([]frontend.Variable, cnnTraceSize), Model: d}
}

func (c *contextualCircuit) Define(api frontend.API) error {
	d := c.Model
	if err := d.validate(); err != nil {
		return err
	}
	profile, _ := hex.DecodeString(d.Profile)
	input := &inputScaleCircuit{Salt: c.Salt, Units: c.Units, Encoded: c.Encoded, Positions: c.Positions, UnitActive: c.UnitActive, EncodedActive: c.EncodedActive}
	input.Public[0] = c.Public[96]
	copy(input.Public[1:], c.Public[64:96])
	if err := input.defineProfile(api, profile); err != nil {
		return err
	}
	for _, v := range c.Public[:64] {
		api.ToBinary(v, 8)
	}
	api.AssertIsEqual(c.Public[97], 1)
	api.ToBinary(c.Public[98], 32)
	api.AssertIsBoolean(c.Public[99])
	var embedded [cnnCapacity][cnnEmbedding]frontend.Variable
	for j := range cnnEmbedding {
		table := logderivlookup.New(api)
		for _, row := range d.Embedding {
			table.Insert(row[j])
		}
		values := table.Lookup(c.Units...)
		for t := range cnnCapacity {
			embedded[t][j] = 0
			if t < len(c.Units) {
				embedded[t][j] = api.Mul(values[t], c.UnitActive[t])
			}
		}
	}
	round := func(v frontend.Variable, shift int) frontend.Variable {
		signed32(api, v)
		var result frontend.Variable
		switch {
		case shift < 0:
			result = api.Mul(v, int64(1)<<-shift)
		case shift == 0:
			return v
		case shift == 1:
			result = roundHalf(api, v)
		default:
			result = encoderRound(api, v, shift)
		}
		signed32(api, result)
		return result
	}
	var pooled [cnnChannels]frontend.Variable
	for h := range cnnChannels {
		pooled[h] = 0
	}
	for t := range cnnCapacity {
		for h := range cnnChannels {
			var acc frontend.Variable = d.Bias[h]
			for k := range cnnKernel {
				pos := t - (cnnKernel - 1 - k)
				if pos < 0 {
					continue
				}
				for j := range cnnEmbedding {
					acc = api.Add(acc, api.Mul(embedded[pos][j], d.Kernel[h][k*cnnEmbedding+j]))
				}
			}
			z := round(acc, d.EmbeddingFraction+d.KernelFraction-8)
			a := api.Select(signed32(api, z)[31], z, 0)
			index := (t*cnnChannels + h) * 3
			api.AssertIsEqual(c.Trace[index], acc)
			api.AssertIsEqual(c.Trace[index+1], z)
			api.AssertIsEqual(c.Trace[index+2], a)
			if t < len(c.Units) {
				atLeast := api.ToBinary(api.Add(api.Sub(a, pooled[h]), uint64(1<<32)), 33)[32]
				pooled[h] = api.Select(c.UnitActive[t], api.Select(atLeast, a, pooled[h]), pooled[h])
			}
		}
	}
	var output frontend.Variable = d.OutputBias
	for h, v := range pooled {
		api.AssertIsEqual(c.Trace[cnnCapacity*cnnChannels*3+h], v)
		output = api.Add(output, api.Mul(v, d.Head[h]))
	}
	score := round(output, d.HeadFraction)
	api.AssertIsEqual(c.Trace[cnnTraceSize-2], output)
	api.AssertIsEqual(c.Trace[cnnTraceSize-1], score)
	difference := api.Sub(c.Public[98], api.Add(score, uint64(1<<31)))
	positive := api.ToBinary(api.Add(difference, uint64(1<<32)), 33)[32]
	api.AssertIsEqual(c.Public[99], api.Mul(positive, api.Sub(1, api.IsZero(difference))))
	return nil
}

func contextualAssignment(size int, d *contextualData, name string, private bool) (frontend.Circuit, error) {
	c := newContextual(size, d)
	fields := [][]frontend.Variable{c.Public[:]}
	if private {
		fields = append(fields, c.Salt[:], c.Units, c.Encoded, c.Positions, c.UnitActive, c.EncodedActive, c.Trace)
	}
	count := 0
	for _, f := range fields {
		count += len(f)
	}
	values, err := readAssignmentFile(name, count)
	if err != nil {
		return nil, err
	}
	next := 0
	for j, f := range fields {
		for i := range f {
			if private && j == len(fields)-1 {
				f[i] = int64(values[next]) - int64(1<<31)
			} else {
				f[i] = values[next]
			}
			next++
		}
	}
	return c, nil
}

func runContextual(action, rawSize string) (int, error) {
	size, err := number(rawSize, 16)
	if err != nil || (size != 8 && size != 96) {
		return 0, errors.New("unsupported CNN proof capacity")
	}
	d, err := loadContextual()
	if err != nil {
		return 0, err
	}
	if action == "batch" {
		return relationBatch(func(name string) (frontend.Circuit, error) { return contextualAssignment(int(size), d, name, true) }, 2*1024*1024*1024, 16, 4096)
	}
	return runRelation(action, newContextual(int(size), d), func(private bool) (frontend.Circuit, error) {
		return contextualAssignment(int(size), d, "assignment.txt", private)
	}, 2*1024*1024*1024)
}
