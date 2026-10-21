package main

import (
	"crypto/sha256"
	"encoding/binary"
	"fmt"
	"testing"

	curve "github.com/consensys/gnark-crypto/ecc/bls12-381"
	"github.com/consensys/gnark-crypto/ecc/bls12-381/fr"
)

// One diagnostic sample measures allocated bytes, not the maximum setup's peak.
func BenchmarkG1Batch262145(b *testing.B) {
	scalars := make([]fr.Element, 262145)
	for i := range scalars {
		var input [8]byte
		binary.BigEndian.PutUint64(input[:], uint64(i))
		digest := sha256.Sum256(input[:])
		scalars[i].SetBytes(digest[:])
	}
	_, _, generator, _ := curve.Generators()
	var points []curve.G1Affine
	b.ReportAllocs()
	b.ResetTimer()
	for range b.N {
		points = curve.BatchScalarMultiplicationG1(&generator, scalars)
	}
	b.StopTimer()
	if len(points) != len(scalars) {
		b.Fatal("point count mismatch")
	}
	digest := sha256.New()
	for i := range points {
		raw := points[i].Bytes()
		digest.Write(raw[:])
	}
	fmt.Printf("G1ALLOCATION {\"points\":%d,\"compressed_sha256\":\"%x\"}\n", len(points), digest.Sum(nil))
}
