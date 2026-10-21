package main

import (
	"bytes"
	_ "embed"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"math/bits"

	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/std/lookup/logderivlookup"
)

//go:embed encoder-graph.json
var encoderGraph []byte

const encoderTraceSize = 121
const encoderNativePin = "8d0551ac2e9c9e2527004bc4a33392844963ffcb17b9589139448db3f068ee7d"

type encoderData struct {
	Schema     string           `json:"schema_id"`
	Native     string           `json:"native_fixture_sha256"`
	Program    string           `json:"program"`
	Profile    string           `json:"input_profile"`
	Arithmetic string           `json:"arithmetic"`
	Weights    string           `json:"weights_sha256"`
	Constants  map[string][]int `json:"constants"`
	Trace      []struct {
		Name    string `json:"name"`
		Count   int    `json:"count"`
		Minimum int64  `json:"minimum"`
		Maximum int64  `json:"maximum"`
	} `json:"trace"`
}

func loadEncoderData() (*encoderData, error) {
	var d encoderData
	decoder := json.NewDecoder(bytes.NewReader(encoderGraph))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&d); err != nil {
		return nil, err
	}
	if decoder.Decode(new(any)) != io.EOF || d.Schema != "hallmark.gnark-encoder-graph/1" || d.Native != encoderNativePin || len(d.Trace) != 39 {
		return nil, errors.New("invalid frozen encoder data")
	}
	count := 0
	for _, t := range d.Trace {
		if t.Count < 1 || t.Minimum < -(1<<31) || t.Maximum >= 1<<31 || t.Minimum > t.Maximum {
			return nil, errors.New("invalid encoder range")
		}
		count += t.Count
	}
	if count != encoderTraceSize {
		return nil, errors.New("invalid encoder trace shape")
	}
	return &d, nil
}

type encoderCircuit struct {
	Public        [100]frontend.Variable `gnark:",public"`
	Salt          [32]frontend.Variable
	Units         []frontend.Variable
	Encoded       []frontend.Variable
	Positions     []frontend.Variable
	UnitActive    []frontend.Variable
	EncodedActive []frontend.Variable
	Trace         []frontend.Variable
}

func newEncoder(size int) *encoderCircuit {
	input := newInputScale(size)
	return &encoderCircuit{Units: input.Units, Encoded: input.Encoded, Positions: input.Positions,
		UnitActive: input.UnitActive, EncodedActive: input.EncodedActive,
		Trace: make([]frontend.Variable, size/2*encoderTraceSize)}
}

func encoderAssignment(size int, name string, private bool) (frontend.Circuit, error) {
	c := newEncoder(size)
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
	for fieldIndex, field := range fields {
		for i := range field {
			if private && fieldIndex == len(fields)-1 {
				field[i] = int64(values[next]) - int64(1<<31)
			} else {
				field[i] = values[next]
			}
			next++
		}
	}
	return c, nil
}

func encoderRange(api frontend.API, value frontend.Variable, low, high int64) {
	if low == high {
		api.AssertIsEqual(value, low)
		return
	}
	width := bits.Len64(uint64(high - low))
	api.ToBinary(api.Sub(value, low), width)
	api.ToBinary(api.Sub(high, value), width)
}

func encoderRound(api frontend.API, value frontend.Variable, shift int) frontend.Variable {
	negative := api.Sub(1, signed32(api, value)[31])
	magnitude := api.Select(negative, api.Neg(value), value)
	digits := api.ToBinary(magnitude, 32)
	lowerZero := api.IsZero(api.FromBinary(digits[:shift-1]...))
	increment := api.Mul(digits[shift-1], api.Sub(1, api.Mul(lowerZero, api.Sub(1, digits[shift]))))
	rounded := api.Add(api.FromBinary(digits[shift:]...), increment)
	return api.Select(negative, api.Neg(rounded), rounded)
}

func (c *encoderCircuit) Define(api frontend.API) error {
	d, err := loadEncoderData()
	if err != nil {
		return err
	}
	profile, err := hex.DecodeString(d.Profile)
	if err != nil {
		return err
	}
	input := &inputScaleCircuit{Salt: c.Salt, Units: c.Units, Encoded: c.Encoded, Positions: c.Positions, UnitActive: c.UnitActive, EncodedActive: c.EncodedActive}
	input.Public[0] = c.Public[96]
	copy(input.Public[1:], c.Public[64:96])
	if err := input.defineProfile(api, profile); err != nil {
		return err
	}
	// Program/key enrollment validates the classifier binder without a key/hash cycle.
	for i := 0; i < 64; i++ {
		api.ToBinary(c.Public[i], 8)
	}
	api.ToBinary(c.Public[97], 15)
	api.ToBinary(c.Public[98], 32)
	api.AssertIsBoolean(c.Public[99])
	tables := map[string]logderivlookup.Table{}
	for _, name := range []string{"embedding-table", "exponential-table", "inverse-table", "norm1-table", "norm2-table"} {
		table := logderivlookup.New(api)
		for _, value := range d.Constants[name] {
			table.Insert(value)
		}
		tables[name] = table
	}
	var maximum, chunkCount frontend.Variable = 0, 1
	for i := 0; i < len(c.Units)/2; i++ {
		score := encoderBlock(api, d, tables, c.Units[2*i:2*i+2], c.UnitActive[2*i:2*i+2], c.Trace[i*encoderTraceSize:(i+1)*encoderTraceSize])
		if i == 0 {
			maximum = score
			continue
		}
		chunkCount = api.Add(chunkCount, c.UnitActive[2*i])
		atLeast := api.ToBinary(api.Add(api.Sub(score, maximum), uint64(1<<32)), 33)[32]
		maximum = api.Select(c.UnitActive[2*i], api.Select(atLeast, score, maximum), maximum)
	}
	api.AssertIsEqual(c.Public[97], chunkCount)
	difference := api.Sub(c.Public[98], api.Add(maximum, uint64(1<<31)))
	atLeast := api.ToBinary(api.Add(difference, uint64(1<<32)), 33)[32]
	api.AssertIsEqual(c.Public[99], api.Mul(atLeast, api.Sub(1, api.IsZero(difference))))
	return nil
}

// shortcut: fixed decision-0051 graph; a different graph requires fresh lowering and qualification.
func encoderBlock(api frontend.API, d *encoderData, tables map[string]logderivlookup.Table, tokens, masks, trace []frontend.Variable) frontend.Variable {
	cursor, next := 0, 0
	record := func(name string, rows [][]frontend.Variable) [][]frontend.Variable {
		spec := d.Trace[cursor]
		if spec.Name != name {
			panic("encoder tensor order mismatch")
		}
		count := 0
		for _, row := range rows {
			for _, value := range row {
				api.AssertIsEqual(trace[next], value)
				encoderRange(api, trace[next], spec.Minimum, spec.Maximum)
				next++
				count++
			}
		}
		if count != spec.Count {
			panic("encoder tensor shape mismatch")
		}
		cursor++
		return rows
	}
	affine := func(name string, rows [][]frontend.Variable) [][]frontend.Variable {
		bias := d.Constants[name+"-bias"]
		flat := d.Constants[name+"-weights"]
		weights := make([][]int, len(bias))
		if len(flat) != len(bias)*len(rows[0]) {
			panic("invalid frozen affine shape")
		}
		for i := range weights {
			weights[i] = flat[i*len(rows[0]) : (i+1)*len(rows[0])]
		}
		return blockAffine(api, rows, weights, bias)
	}
	norm := func(name string, rows [][]frontend.Variable) [][]frontend.Variable {
		left, right := make([][]frontend.Variable, 2), make([][]frontend.Variable, 2)
		for i := range rows {
			left[i] = []frontend.Variable{rows[i][0]}
			right[i] = []frontend.Variable{rows[i][1]}
		}
		record(name+"-left", left)
		record(name+"-right", right)
		scaled, pair, index, indices, out := make([][]frontend.Variable, 2), make([][]frontend.Variable, 2), make([][]frontend.Variable, 2), make([][]frontend.Variable, 2), make([][]frontend.Variable, 2)
		for i := range rows {
			scaled[i] = []frontend.Variable{api.Mul(left[i][0], d.Constants[name+"-width"][0])}
			pair[i] = []frontend.Variable{api.Add(scaled[i][0], right[i][0])}
			index[i] = []frontend.Variable{api.Add(pair[i][0], d.Constants[name+"-offset"][0])}
			indices[i] = []frontend.Variable{index[i][0], api.Add(index[i][0], d.Constants[name+"-feature-offset"][1])}
			out[i] = tables[name+"-table"].Lookup(indices[i]...)
		}
		record(name+"-scaled-left", scaled)
		record(name+"-pair", pair)
		record(name+"-index", index)
		record(name+"-indices", indices)
		return record(name, out)
	}
	embedding := make([][]frontend.Variable, 2)
	for i := range tokens {
		embedding[i] = tables["embedding-table"].Lookup(api.Mul(tokens[i], 2), api.Add(api.Mul(tokens[i], 2), 1))
	}
	record("token-embedding", embedding)
	positioned := make([][]frontend.Variable, 2)
	for i := range embedding {
		positioned[i] = []frontend.Variable{api.Add(embedding[i][0], d.Constants["positions"][2*i]), api.Add(embedding[i][1], d.Constants["positions"][2*i+1])}
	}
	record("embedding", positioned)
	query := record("query", affine("query", positioned))
	key := record("key", affine("key", positioned))
	value := record("value", affine("value", positioned))
	transposed := record("key-transpose", [][]frontend.Variable{{key[0][0], key[1][0]}, {key[0][1], key[1][1]}})
	scores := record("scores", blockMatmul(api, query, transposed))
	exponential, masked, denominator, inverse, normalized := make([][]frontend.Variable, 2), make([][]frontend.Variable, 2), make([][]frontend.Variable, 2), make([][]frontend.Variable, 2), make([][]frontend.Variable, 2)
	for i := range scores {
		exponential[i] = tables["exponential-table"].Lookup(api.Add(scores[i][0], 16), api.Add(scores[i][1], 16))
		masked[i] = []frontend.Variable{api.Mul(exponential[i][0], masks[0]), api.Mul(exponential[i][1], masks[1])}
		denominator[i] = []frontend.Variable{api.Add(masked[i][0], masked[i][1])}
		inverse[i] = tables["inverse-table"].Lookup(denominator[i][0])
		normalized[i] = []frontend.Variable{api.Mul(masked[i][0], inverse[i][0]), api.Mul(masked[i][1], inverse[i][0])}
	}
	record("exponential", exponential)
	record("key-mask", [][]frontend.Variable{masks})
	record("masked", masked)
	record("denominator", denominator)
	record("inverse", inverse)
	record("normalized", normalized)
	attention := blockMatmul(api, normalized, value)
	residual := make([][]frontend.Variable, 2)
	for i := range attention {
		residual[i] = make([]frontend.Variable, 2)
		for j := range attention[i] {
			attention[i][j] = roundAttention(api, attention[i][j])
			residual[i][j] = api.Add(attention[i][j], positioned[i][j])
		}
	}
	record("attention", attention)
	record("residual", residual)
	n1 := norm("norm1", residual)
	hidden := affine("hidden", n1)
	activated := make([][]frontend.Variable, 2)
	for i := range hidden {
		activated[i] = make([]frontend.Variable, 3)
		for j := range hidden[i] {
			hidden[i][j] = encoderRound(api, hidden[i][j], 9)
			activated[i][j] = api.Select(signed32(api, hidden[i][j])[31], hidden[i][j], 0)
		}
	}
	record("hidden", hidden)
	record("activated", activated)
	output := affine("output", activated)
	residual2 := make([][]frontend.Variable, 2)
	for i := range output {
		residual2[i] = make([]frontend.Variable, 2)
		for j := range output[i] {
			output[i][j] = roundHalf(api, output[i][j])
			residual2[i][j] = roundAttention(api, api.Add(n1[i][j], api.Mul(output[i][j], 256)))
		}
	}
	record("output", output)
	record("residual2", residual2)
	n2 := norm("norm2", residual2)
	record("pool-mask", [][]frontend.Variable{{masks[0]}, {masks[1]}})
	sums, maxima, pooled := make([]frontend.Variable, 2), make([]frontend.Variable, 2), make([]frontend.Variable, 2)
	for j := range sums {
		a, b := n2[0][j], n2[1][j]
		sums[j] = api.Add(api.Mul(masks[0], a), api.Mul(masks[1], b))
		atLeast := api.ToBinary(api.Add(api.Sub(a, b), uint64(1<<32)), 33)[32]
		both := api.Select(atLeast, a, b)
		maxima[j] = api.Select(masks[0], api.Select(masks[1], both, a), api.Select(masks[1], b, 0))
		pooled[j] = api.Add(sums[j], maxima[j])
	}
	record("pool-sum", [][]frontend.Variable{sums})
	record("pool-max", [][]frontend.Variable{maxima})
	record("pooled", [][]frontend.Variable{pooled})
	logits := affine("logits", [][]frontend.Variable{pooled})
	for j := range logits[0] {
		logits[0][j] = encoderRound(api, logits[0][j], 9)
	}
	record("logits", logits)
	score := affine("score", logits)[0][0]
	record("score", [][]frontend.Variable{{score}})
	if cursor != len(d.Trace) || next != encoderTraceSize {
		panic("invalid encoder trace length")
	}
	return score
}

func runEncoder(action, rawSize string) (int, error) {
	size, err := number(rawSize, 16)
	if err != nil || (size != 8 && size != 32 && size != 256 && size != 32768) {
		return 0, errors.New("invalid encoder capacity")
	}
	limit := int64(2 * 1024 * 1024 * 1024)
	if size == 32768 {
		limit = 48 * 1024 * 1024 * 1024
	}
	if action == "batch" {
		return relationBatch(func(name string) (frontend.Circuit, error) { return encoderAssignment(int(size), name, true) }, limit, 1024, 128*1024)
	}
	return runRelation(action, newEncoder(int(size)), func(private bool) (frontend.Circuit, error) {
		return encoderAssignment(int(size), "assignment.txt", private)
	}, limit)
}
