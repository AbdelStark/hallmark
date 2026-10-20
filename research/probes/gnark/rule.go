package main

import "github.com/consensys/gnark/frontend"

// Pins reproduce from build_gnark_rule_fixture.py; enrollment remains synthetic.
const ruleClassifier = "45bab258e0553c47399246e3c9aedb3ac7bb321969f09b03d96220d7aa1b7a4b"
const ruleProfile = "1c90a8bd4419e53b0284c1d37684705c6bc695f6fd261d57d259011d84cab953"

type ruleCircuit struct{ Input inputCircuit }

func (c *ruleCircuit) Define(api frontend.API) error {
	active, err := c.Input.bind(api, ruleClassifier, ruleProfile, 1)
	if err != nil {
		return err
	}

	var noMatch frontend.Variable = 1
	for start := 0; start <= 5; start++ {
		matched := active[start+2]
		for j, b := range []byte("BAD") {
			matched = api.Mul(matched, api.IsZero(api.Sub(c.Input.Units[start+j], b)))
		}
		noMatch = api.Mul(noMatch, api.Sub(1, matched))
	}
	api.AssertIsEqual(c.Input.Public[99], noMatch)

	return nil
}
