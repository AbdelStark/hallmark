package main

import "github.com/consensys/gnark/frontend"

// Pins reproduce from build_gnark_mlp_fixture.py; weights and enrollment are synthetic.
const mlpClassifier = "2200b23766fbbfa152856353a5fef5b7f7e72daaf4554a1adecd78bd7439a110"
const mlpProfile = "1c90a8bd4419e53b0284c1d37684705c6bc695f6fd261d57d259011d84cab953"

type mlpCircuit struct {
	Input inputCircuit
	Trace [22]frontend.Variable
}

func signed32(api frontend.API, value frontend.Variable) []frontend.Variable {
	return api.ToBinary(api.Add(value, uint64(1<<31)), 32)
}

// The frozen graph rescales by exactly two, nearest with ties to an even integer.
func roundHalf(api frontend.API, value frontend.Variable) frontend.Variable {
	bits := signed32(api, value)
	negative := api.Sub(1, bits[31])
	magnitude := api.Select(negative, api.Neg(value), value)
	magnitudeBits := api.ToBinary(magnitude, 32)
	quotient := api.FromBinary(magnitudeBits[1:]...)
	rounded := api.Add(quotient, api.Mul(magnitudeBits[0], magnitudeBits[1]))
	result := api.Select(negative, api.Neg(rounded), rounded)
	signed32(api, result)
	return result
}

func (c *mlpCircuit) Define(api frontend.API) error {
	active, err := c.Input.bind(api, mlpClassifier, mlpProfile, 2)
	if err != nil {
		return err
	}
	var scores [2]frontend.Variable
	for chunk := 0; chunk < 2; chunk++ {
		// All other entries of the fixed 3x256 weight matrix are zero.
		var counts [4]frontend.Variable
		for j, b := range []byte{0, 'A', 'B', 'x'} {
			counts[j] = 0
			for i := chunk * 4; i < (chunk+1)*4; i++ {
				counts[j] = api.Add(
					counts[j],
					api.Mul(active[i], api.IsZero(api.Sub(c.Input.Units[i], b))),
				)
			}
			api.ToBinary(counts[j], 3)
		}
		accumulators := []frontend.Variable{
			api.Add(-1, counts[0], api.Mul(3, counts[1]), api.Mul(-3, counts[3])),
			api.Add(1, api.Neg(counts[0]), api.Mul(-3, counts[1]), api.Mul(3, counts[3])),
			api.Sub(counts[2], 3),
		}
		var activated [3]frontend.Variable
		for i, accumulator := range accumulators {
			hidden := roundHalf(api, accumulator)
			nonnegative := signed32(api, hidden)[31]
			activated[i] = api.Select(nonnegative, hidden, 0)
			api.AssertIsEqual(c.Trace[chunk*11+i], accumulator)
			api.AssertIsEqual(c.Trace[chunk*11+3+i], hidden)
			api.AssertIsEqual(c.Trace[chunk*11+6+i], activated[i])
		}
		output := api.Add(-1, api.Mul(3, activated[0]), api.Mul(-3, activated[1]), activated[2])
		scores[chunk] = roundHalf(api, output)
		api.AssertIsEqual(c.Trace[chunk*11+9], output)
		api.AssertIsEqual(c.Trace[chunk*11+10], scores[chunk])
	}
	for _, value := range c.Trace {
		signed32(api, value)
	}
	// Offset by 2^32 so subtracting any two int32 scores cannot overflow this comparison.
	atLeast := api.ToBinary(api.Add(api.Sub(scores[0], scores[1]), uint64(1<<32)), 33)[32]
	maximum := api.Select(atLeast, scores[0], scores[1])
	score := api.Select(active[4], maximum, scores[0])
	blocks := api.ToBinary(api.Add(api.Sub(score, 2), uint64(1<<32)), 33)[32]
	api.AssertIsEqual(c.Input.Public[99], api.Sub(1, blocks))
	return nil
}
