# Circle STARK by default, gnark for comparison

Hallmark defaults to Circle STARKs: SASH for the quantized LLM and direct STWO
for classifiers. Gnark/Groth16 remains an explicit comparison backend. The classifier paths now
have a [matched CPU comparison](../CLASSIFIER-BENCHMARK.md) of the same computation.

## The current division

| | LLM path | Default classifier path | Comparison classifier path |
|---|---|---|---|
| Backend | SASH Circle STARK | Direct STWO 2.2.0 Circle STARK | gnark Groth16 / BLS12-381 |
| Workload | Complete fixed quantized TinyLlama response | Same complete classifiers and 96-byte semantics | Rule, trained MLP and contextual byte CNN |
| Proof structure | 23 linked segments | One fixed-gate proof per classifier/request | One dedicated proof per classifier/request |
| Verification | SASH; Linux and adapted Mac variants | Fresh native STWO processes; shared engine/AIR implementation | Separate py-ecc decoder and pairing arithmetic |
| Setup/enrollment | Expected model, shape and calibration roots | Public preprocessing, program/model mapping and concrete parameters | Research setup plus circuit/key/model mapping |
| Recorded proof files | 738 MB across 23 proofs | 1.91–2.16 MB canonical JSON per proof | 292 bytes per proof |
| Matched classifier comparison | Separate workload | Same cases, host and thread budget | Three fresh/five warm workflows |

LLM/classifier artifact sizes cover different computations. The classifier
comparison fixes the computation, but encodings, soundness parameters and
implementation costs still differ. A proof-size ratio alone is insufficient.

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

The [completed classifier report](../CLASSIFIER-BENCHMARK.md) follows this plan
and retains every sample and failed provisioning fixture. Circle's complete
workflow is faster in that stateless harness, while using more memory and much
larger proofs. Gnark's combined parsing stage dominates its command; its
instrumented proving stage is shorter on the representative control. The report
keeps the internal timing boundaries and security assumptions explicit, and
originally recommended retaining both with gnark default. The owner subsequently
selected Circle for all default workflows in [decision 0085](../decisions/0085-circle-default.md);
the experiment and its measurements remain unchanged.

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
