package main

import "github.com/consensys/gnark/frontend"

type normalizationCircuit struct {
	Public [4]frontend.Variable `gnark:",public"`
	Trace  [11]frontend.Variable
}

func normalizationAssignment(private bool) (frontend.Circuit, error) {
	count := 4
	if private {
		count += 11
	}
	values, err := readAssignment(count)
	if err != nil {
		return nil, err
	}
	c := &normalizationCircuit{}
	for i, value := range values {
		if i < 4 {
			c.Public[i] = value
		} else {
			c.Trace[i-4] = int64(value) - int64(1<<31)
		}
	}
	return c, nil
}

func (c *normalizationCircuit) Define(api frontend.API) error {
	for _, value := range c.Public {
		api.ToBinary(value, 32)
	}
	x := [2]frontend.Variable{}
	for i := range x {
		x[i] = blockLookup(api, api.Sub(c.Public[i], uint64(1<<31)),
			[]int{-8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8}, 8)
	}
	mean := roundHalf(api, api.Add(x[0], x[1]))
	a, b := api.Sub(x[0], mean), api.Sub(x[1], mean)
	aa, bb := api.Mul(a, a), api.Mul(b, b)
	variance := roundHalf(api, api.Add(aa, bb))
	scale := blockLookup(api, variance, normalizationInverse, 0)
	na, nb := api.Mul(a, scale), api.Mul(b, scale)
	left, right := api.Add(na, 256), api.Sub(api.Mul(-2, nb), 256)
	values := []frontend.Variable{mean, a, b, aa, bb, variance, scale, na, nb, left, right}
	for i, value := range values {
		api.AssertIsEqual(c.Trace[i], value)
		signed32(api, c.Trace[i])
	}
	api.AssertIsEqual(c.Public[2], api.Add(left, uint64(1<<31)))
	api.AssertIsEqual(c.Public[3], api.Add(right, uint64(1<<31)))
	return nil
}

// The exact table is frozen before proof execution; see decision 0050.
var normalizationInverse = []int{256, 181, 148, 128, 114, 105, 97, 91, 85, 81, 77, 74, 71, 68, 66, 64, 62, 60, 59, 57, 56, 55, 53, 52, 51, 50, 49, 48, 48, 47, 46, 45, 45, 44, 43, 43, 42, 42, 41, 40, 40, 40, 39, 39, 38, 38, 37, 37, 37, 36, 36, 36, 35, 35, 35, 34, 34, 34, 33, 33, 33, 33, 32, 32, 32}
