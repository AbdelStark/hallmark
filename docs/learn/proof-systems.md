# Why two proof systems?

Hallmark uses a specialized Circle STARK path for the quantized LLM and dedicated
Groth16 circuits for the classifiers. These were built separately; Hallmark has
not benchmarked both systems on the same classifier computation.

## The current division

| | LLM path | Classifier path |
|---|---|---|
| Backend | SASH Circle STARK | gnark Groth16 / BLS12-381 |
| Workload | Complete fixed quantized TinyLlama response | Rule, trained MLP and contextual byte CNN |
| Proof structure | 23 linked segments | One dedicated proof per classifier/request |
| Verification | SASH cryptographic implementation; Linux and adapted Mac variants | Separate py-ecc decoder and pairing arithmetic |
| Setup/enrollment | Expected model, shape and calibration roots; caller admission required | Circuit-specific research setup plus caller-enrolled circuit/key/model mapping |
| Recorded artifact size | 738 MB across all 23 proof files | 292 bytes per proof in this research encoding |
| Matched classifier comparison | Not implemented | Existing baseline for the planned comparison |

The artifact sizes cover different computations and encodings, so their ratio
says little about the relative cost of the two proof systems.

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

## Groth16: a circuit-specific route

Groth16 is a pairing-based proof system for arithmetic circuit satisfiability.
Its construction uses a circuit-specific reference string. The verifier checks
a small collection of group elements using a pairing equation.

Hallmark compiles dedicated classifier circuits with gnark. A separate py-ecc
verifier decodes the proofs and checks the Groth16 equations. Each local demo
creates a fresh setup; that setup has not had an independently reviewed ceremony.

Read [Groth's original paper](https://eprint.iacr.org/2016/260) and
[the classifier relation](../PROOFS.md). Groth16 supports zero knowledge, but
Hallmark has not qualified witness privacy across its data handling, parameters,
proofs and host composition.

## A fair comparison needs the same claim

Before comparing prover backends, freeze:

- the same model, weights, input bytes, coverage and arithmetic;
- the same public inputs and caller binding;
- honest verification and mutation/rejection gates;
- hardware, threads, preprocessing and timing boundaries;
- proof, key, enrollment and transfer sizes.

[Classifier epic #112](https://github.com/AbdelStark/hallmark/issues/112) tracks
the planned Circle STARK classifier implementation and matched comparison with
gnark and native execution. That backend is not yet implemented.

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
