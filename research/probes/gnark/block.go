package main

import "github.com/consensys/gnark/frontend"

const blockTraceSize = 89

type blockCircuit struct {
	Public [5]frontend.Variable `gnark:",public"`
	Trace  [blockTraceSize]frontend.Variable
}

func blockAssignment(private bool) (frontend.Circuit, error) {
	count := 5
	if private {
		count += blockTraceSize
	}
	values, err := readAssignment(count)
	if err != nil {
		return nil, err
	}
	c := &blockCircuit{}
	for i, n := range values {
		if i < 5 {
			c.Public[i] = n
		} else {
			c.Trace[i-5] = int64(n) - int64(1<<31)
		}
	}
	return c, nil
}

// Exact finite selection avoids an unconstrained lookup hint.
func blockLookup(api frontend.API, index frontend.Variable, table []int, offset int) frontend.Variable {
	var total, value frontend.Variable = 0, 0
	for i, entry := range table {
		selected := api.IsZero(api.Sub(api.Add(index, offset), i))
		total = api.Add(total, selected)
		value = api.Add(value, api.Mul(selected, entry))
	}
	api.AssertIsEqual(total, 1)
	return value
}

// shortcut: this block's attention uses eight fractional bits; other profiles need separate qualification.
func roundAttention(api frontend.API, value frontend.Variable) frontend.Variable {
	negative := api.Sub(1, signed32(api, value)[31])
	magnitude := api.Select(negative, api.Neg(value), value)
	bits := api.ToBinary(magnitude, 32)
	lowerZero := api.IsZero(api.FromBinary(bits[:7]...))
	increment := api.Mul(bits[7], api.Sub(1, api.Mul(lowerZero, api.Sub(1, bits[8]))))
	rounded := api.Add(api.FromBinary(bits[8:]...), increment)
	result := api.Select(negative, api.Neg(rounded), rounded)
	signed32(api, result)
	return result
}

func blockAffine(api frontend.API, rows [][]frontend.Variable, weights [][]int, bias []int) [][]frontend.Variable {
	out := make([][]frontend.Variable, len(rows))
	for i, row := range rows {
		out[i] = make([]frontend.Variable, len(weights))
		for j, column := range weights {
			var value frontend.Variable = bias[j]
			for k, weight := range column {
				value = api.Add(value, api.Mul(row[k], weight))
			}
			out[i][j] = value
		}
	}
	return out
}

func blockMatmul(api frontend.API, a, b [][]frontend.Variable) [][]frontend.Variable {
	out := make([][]frontend.Variable, len(a))
	for i := range a {
		out[i] = make([]frontend.Variable, len(b[0]))
		for j := range b[0] {
			var value frontend.Variable = 0
			for k := range b {
				value = api.Add(value, api.Mul(a[i][k], b[k][j]))
			}
			out[i][j] = value
		}
	}
	return out
}

func (c *blockCircuit) Define(api frontend.API) error {
	for i := 0; i < 2; i++ {
		api.ToBinary(c.Public[i], 2)
		api.AssertIsBoolean(c.Public[2+i])
	}
	api.ToBinary(c.Public[4], 32)
	next := 0
	record := func(rows [][]frontend.Variable) [][]frontend.Variable {
		for _, row := range rows {
			for _, value := range row {
				api.AssertIsEqual(c.Trace[next], value)
				signed32(api, c.Trace[next])
				next++
			}
		}
		return rows
	}
	embedding := make([][]frontend.Variable, 2)
	for i := range embedding {
		embedding[i] = []frontend.Variable{
			blockLookup(api, c.Public[i], []int{0, 1, -1, 1}, 0),
			blockLookup(api, c.Public[i], []int{0, -1, 1, 1}, 0),
		}
	}
	record(embedding)
	query := record(blockAffine(api, embedding, [][]int{{1, 0}, {0, 1}}, []int{0, 0}))
	key := record(blockAffine(api, embedding, [][]int{{0, 1}, {1, 0}}, []int{0, 0}))
	value := record(blockAffine(api, embedding, [][]int{{1, 0}, {0, -1}}, []int{0, 0}))
	transposed := record([][]frontend.Variable{{key[0][0], key[1][0]}, {key[0][1], key[1][1]}})
	scores := record(blockMatmul(api, query, transposed))
	exponential, masked := make([][]frontend.Variable, 2), make([][]frontend.Variable, 2)
	denominator, inverse := make([][]frontend.Variable, 2), make([][]frontend.Variable, 2)
	normalized := make([][]frontend.Variable, 2)
	for i := 0; i < 2; i++ {
		exponential[i], masked[i], normalized[i] = make([]frontend.Variable, 2), make([]frontend.Variable, 2), make([]frontend.Variable, 2)
		for j := 0; j < 2; j++ {
			exponential[i][j] = blockLookup(api, scores[i][j], []int{1, 2, 4, 8, 16}, 2)
			masked[i][j] = api.Mul(exponential[i][j], c.Public[2+j])
		}
		denominator[i] = []frontend.Variable{api.Add(masked[i][0], masked[i][1])}
		inverse[i] = []frontend.Variable{blockLookup(api, denominator[i][0],
			[]int{0, 256, 128, 85, 64, 51, 43, 37, 32, 28, 26, 23, 21, 20, 18, 17, 16, 15, 14, 13, 13, 12, 12, 11, 11, 10, 10, 9, 9, 9, 9, 8, 8}, 0)}
		for j := 0; j < 2; j++ {
			normalized[i][j] = api.Mul(masked[i][j], inverse[i][0])
		}
	}
	record(exponential)
	record(masked)
	record(denominator)
	record(inverse)
	record(normalized)
	attention := blockMatmul(api, normalized, value)
	residual := make([][]frontend.Variable, 2)
	for i := 0; i < 2; i++ {
		residual[i] = make([]frontend.Variable, 2)
		for j := 0; j < 2; j++ {
			attention[i][j] = roundAttention(api, attention[i][j])
			residual[i][j] = api.Add(attention[i][j], embedding[i][j])
		}
	}
	record(attention)
	record(residual)
	hiddenAcc := record(blockAffine(api, residual, [][]int{{1, 1}, {1, -1}, {-1, 0}}, []int{1, -1, 0}))
	hidden, activated := make([][]frontend.Variable, 2), make([][]frontend.Variable, 2)
	for i := 0; i < 2; i++ {
		hidden[i], activated[i] = make([]frontend.Variable, 3), make([]frontend.Variable, 3)
		for j := 0; j < 3; j++ {
			hidden[i][j] = roundHalf(api, hiddenAcc[i][j])
			activated[i][j] = api.Select(signed32(api, hidden[i][j])[31], hidden[i][j], 0)
		}
	}
	record(hidden)
	record(activated)
	outputAcc := record(blockAffine(api, activated, [][]int{{1, -1, 2}, {-1, 1, 1}}, []int{-1, 1}))
	output, block := make([][]frontend.Variable, 2), make([][]frontend.Variable, 2)
	for i := 0; i < 2; i++ {
		output[i], block[i] = make([]frontend.Variable, 2), make([]frontend.Variable, 2)
		for j := 0; j < 2; j++ {
			output[i][j] = roundHalf(api, outputAcc[i][j])
			block[i][j] = api.Add(output[i][j], residual[i][j])
		}
	}
	record(output)
	record(block)
	sums, maxima, pooled := make([]frontend.Variable, 2), make([]frontend.Variable, 2), make([]frontend.Variable, 2)
	for j := 0; j < 2; j++ {
		a, b := block[0][j], block[1][j]
		sums[j] = api.Add(api.Mul(c.Public[2], a), api.Mul(c.Public[3], b))
		atLeast := api.ToBinary(api.Add(api.Sub(a, b), uint64(1<<32)), 33)[32]
		both := api.Select(atLeast, a, b)
		maxima[j] = api.Select(c.Public[2], api.Select(c.Public[3], both, a), api.Select(c.Public[3], b, 0))
		pooled[j] = api.Add(sums[j], maxima[j])
	}
	record([][]frontend.Variable{sums})
	record([][]frontend.Variable{maxima})
	record([][]frontend.Variable{pooled})
	logitAcc := record(blockAffine(api, [][]frontend.Variable{pooled}, [][]int{{2, -1}, {-1, 2}}, []int{1, -1}))
	logits := record([][]frontend.Variable{{roundHalf(api, logitAcc[0][0]), roundHalf(api, logitAcc[0][1])}})
	score := api.Sub(logits[0][1], logits[0][0])
	record([][]frontend.Variable{{score}})
	api.AssertIsEqual(c.Public[4], api.Add(score, uint64(1<<31)))
	if next != blockTraceSize {
		panic("incorrect frozen block trace size")
	}
	return nil
}
