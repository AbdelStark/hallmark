package main

import (
	"crypto/sha256"
	"fmt"
	"math/big"
	"runtime"
	"slices"
	"testing"

	curve "github.com/consensys/gnark-crypto/ecc/bls12-381"
	"github.com/consensys/gnark-crypto/ecc/bls12-381/fr"
	"github.com/consensys/gnark-crypto/parallel"
)

// Invoke this file explicitly with both pinned module variants; it performs no setup.
func TestG1BatchEquivalence(t *testing.T) {
	var values [8]fr.Element
	values[1].SetOne()
	values[2].Neg(&values[1])
	values[3].SetUint64(2)
	for i := 4; i < len(values); i++ {
		digest := sha256.Sum256([]byte(fmt.Sprintf("hallmark/g1-batch-fixture/1/%d", i)))
		values[i].SetBytes(digest[:])
	}
	_, _, generator, _ := curve.Generators()
	lengths := []int{0, 1, 3, 4095, 4096, 4097, 8193, runtime.NumCPU()*4096 + 1}
	for _, base := range []struct {
		name  string
		point curve.G1Affine
	}{{"generator", generator}, {"infinity", curve.G1Affine{}}} {
		t.Run(base.name, func(t *testing.T) {
			var expected [8]curve.G1Affine
			for i := range values {
				var scalar big.Int
				values[i].BigInt(&scalar)
				expected[i].ScalarMultiplication(&base.point, &scalar)
			}
			for _, length := range lengths {
				t.Run(fmt.Sprintf("n%d", length), func(t *testing.T) {
					if length == lengths[len(lengths)-1] {
						crosses := false
						for _, span := range parallel.Chunks(length) {
							crosses = crosses || span[1]-span[0] > 4096
						}
						if !crosses {
							t.Fatal("fixture misses a per-worker chunk boundary")
						}
					}
					scalars := make([]fr.Element, length)
					for i := range scalars {
						scalars[i] = values[i%len(values)]
					}
					before := slices.Clone(scalars)
					point := base.point
					got := curve.BatchScalarMultiplicationG1(&point, scalars)
					if len(got) != length || point != base.point || !slices.Equal(before, scalars) {
						t.Fatal("length mismatch or mutated input")
					}
					coordinates, compressed := sha256.New(), sha256.New()
					for i := range got {
						want := expected[i%len(expected)]
						if !got[i].Equal(&want) || got[i].Bytes() != want.Bytes() || got[i].RawBytes() != want.RawBytes() {
							t.Fatalf("point %d differs from scalar multiplication", i)
						}
						raw, encoded := got[i].RawBytes(), got[i].Bytes()
						coordinates.Write(raw[:])
						compressed.Write(encoded[:])
					}
					fmt.Printf("G1CASE {\"base\":%q,\"length\":%d,\"coordinates_sha256\":\"%x\",\"compressed_sha256\":\"%x\"}\n", base.name, length, coordinates.Sum(nil), compressed.Sum(nil))
				})
			}
		})
	}
}
