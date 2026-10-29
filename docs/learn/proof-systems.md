# Circle STARK for LLMs and classifiers

Hallmark proves with Circle STARKs: SASH for the quantized LLM and direct STWO
for classifiers. The two paths share the proof family but prove different
computations with different provers.

## The current division

| | LLM path | Classifier path |
|---|---|---|
| Backend | SASH Circle STARK | Direct STWO 2.2.0 Circle STARK |
| Workload | Complete fixed quantized TinyLlama response | Rule, trained MLP and contextual byte CNN; 96-byte demo semantics |
| Proof structure | 23 linked segments | One fixed-gate proof per classifier/request |
| Verification | SASH; Linux and adapted Mac variants | Fresh native STWO processes; shared engine/AIR implementation |
| Setup/enrollment | Expected model, shape and calibration roots | Public preprocessing, program/model mapping and concrete parameters |
| Recorded proof files | 738 MB across 23 proofs | 1.91–2.16 MB canonical JSON per proof |

LLM/classifier artifact sizes cover different computations. A proof-size ratio
between them is not a meaningful comparison.

## Circle STARKs: a small-field route

Circle STARKs organize polynomial work over points on the circle
\(x^2 + y^2 = 1\), enabling efficient domains for suitable fields, including
the Mersenne prime \(2^{31}-1\). The construction changes how polynomial
evaluation and interpolation domains are organized.

SASH turns its specialized quantized inference relation into constraints
checked by its Circle STARK stack. Hallmark uses hash-pinned upstream source
and command-line adapters, with changes for preparation, native Mac verification
and CUDA proving. The constraints describe inference directly, without a
general-purpose VM.

Read the original [Circle STARKs paper](https://eprint.iacr.org/2024/278)
by Haböck, Levit and Papini, then
[Hallmark's SASH integration](../ARCHITECTURE.md#how-sash-is-integrated).
The construction's mathematical properties do not replace a security review
of this implementation, parameters and composition.

## A fair comparison needs the same claim

Before comparing prover backends, freeze:

- the same model, weights, input bytes, coverage and arithmetic;
- the same public inputs and caller binding;
- honest verification and mutation/rejection gates;
- hardware, threads, preprocessing and timing boundaries;
- proof, key, enrollment and transfer sizes.

## The same-host GPU comparison {#what-the-gpu-result-does-show}

The H200 experiment compares SIMD and CUDA **inside the same SASH relation**
with the same inputs, parameters and four Rayon threads. Generated constraint
kernels eliminate CPU constraint fallback. All 69 files match byte for byte.

CUDA took 53.94 s versus SIMD's 547.75 s for summed proving, a 10.15× ratio.
Complete segment commands took 155.89 s versus 679.49 s, a 4.36× ratio.
Witness/interaction generation stays on CPU. Only one matched pair was measured,
so these timings do not describe run-to-run variation.
[The benchmark guide](../GPU-BENCHMARK.md#generated-constraint-result) preserves
the raw evidence and the earlier slower fallback configuration.

Continue with [verify one request](one-request.md).
