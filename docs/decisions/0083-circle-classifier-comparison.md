# 0083: Exact classifier relations and a matched Circle STARK comparison

Date: 2026-10-27. Status: frozen protocol executed; retain both research paths with gnark default.
Implementation/evidence for epic #112 and #113–#117 are recorded below.

## Gate and frozen baseline

Hypothesis: a fixed classifier circuit over a pinned Circle STARK engine can prove
the exact existing rule, integer MLP and contextual CNN relations, including their
canonical salted SHA-256 input commitments, and support a complete matched cost
comparison. No speed advantage is assumed. Baseline is main
`0b7fcf256e2b1da7f89578014bcc86e6737fc3f5`.

The first acceptance gate is #113: executable frozen model/caller/corpus admission,
native and actual gnark replay with fresh py-ecc verification, and the complete
benchmark protocol. The full epic remains open until all three real STARK paths,
nine-proof workflows, common-request LLM composition and repeated measurements
pass. An infeasible candidate is a preserved result, not completion.

Mutable paths are new comparison scripts/tests/configuration, the new
`research/probes/circle/` backend, its adapter and workflow integration, and the
associated guides/STATE/LEDGER/evidence. Existing proof implementations, native
arithmetic, model exports, datasets, thresholds and historical numeric records
remain unchanged. Backend-specific enrollment does not change model semantics.

## Relation and caller boundary

The existing [classifier statement](../PROOFS.md) is authoritative: complete
0–96-byte input, no truncation, exact padding/masks, literal BAD across chunks,
integer rounding and threshold equality blocking. The SHA-256 preimage is
`u32be(len(tag)) || tag || CBOR([salt32, profile32, count, byte_values])`, with
`tag = hallmark/v1/input`. It is distinct from the transcript-opening commitment.
The input digest must be constrained inside each proof.

The 100 logical public fields remain context digest, classifier identity, input
digest, unit count, chunk count, biased signed threshold and verdict. The caller
constructs context/classifier identities and salt derivation, admits exact models
and inputs, and checks complete unique classifier coverage. Those host semantics
must not be presented as in-circuit context reconstruction.

Classifier manifests include backend/key/setup identities. Their full IDs,
policy/context hashes and derived salts can therefore differ across backends.
Match the unchanged model/program/profile/arithmetic/threshold and caller
opening contents; record each complete backend-specific identity chain. Do not
claim byte-identical public statements across distinct backend enrollments.
The new proof envelope enrolls the backend program/preprocessing and proof
parameters before proving. It must identify the
exact compiled relation selected before proving. Public 32-bit values need
bounded limbs over M31; reduction modulo M31 is not a transport decoder. SHA words,
integer signs, carries, ranges and rounding branches require constrained, unique
interpretations. A field equality alone does not establish an integer equality.

## Backend and security

The [engine review](../../research/circle-classifier-engine-review.md) selects
pinned direct STWO 2.2.0, separately from SASH's Llama application. The experimental
candidate passes complete rule/MLP/CNN acceptance; it is not an adopted backend
and is not production-qualified. The [completed comparison](../CLASSIFIER-BENCHMARK.md)
records repeated matched results and the retain-both recommendation. Reuse the Circle
FFT/FRI/Merkle/constraint framework, with specialized classifier and exact SHA-256
constraints. There is no general-purpose VM.

Preprocessing wiring, constants, copy multiplicities, model/program identities,
column shapes and PCS parameters are caller-enrolled. A fresh verifier accepts
proof plus caller-owned expectations/enrollment, without the witness/checkpoint,
prover invocation, native-inference fallback or trusted success flag. SHA-256
input binding is separate from the engine's Blake2s transcript/Merkle hashes.

Concrete FRI/lookup parameters and their soundness assumptions must accompany
the results. M31/QM31 statistical bounds and implementation assumptions do not
establish equal security to BLS12-381 Groth16. Neither path gains witness hiding,
hardware provenance, an audited setup ceremony or production qualification here.

## Measurements and resource bounds

[The versioned plan](../../configs/circle-classifiers/plan.json) freezes all three
cases, at least three fresh and five warm repetitions per case/backend, ordering,
cache definitions, stages, numeric schema, failure handling and Mac resource caps
before candidate measurement. Fresh means a fresh workspace including setup and
preprocessing, with OS caches explicitly uncontrolled. Warm means new proof and
fresh verifier, reusing admitted preparation only. Preserve failed samples and
report successful counts plus median, range and IQR.

The formal campaign identity is `circle-classifiers-matched-v1`, with sample IDs
`fresh-00-gnark` through `fresh-02-circle` and `warm-00-gnark` through
`warm-04-circle`, alternating backend order by repetition. The plan specifies the
raw workflow/case/proof record fields, unavailable-value representation, shared
costs and native timing scope. Each fresh workflow compiles from an empty object
cache; installed toolchains, downloaded dependency sources and OS caches are
reused and disclosed. Only successful derived object caches may be removed after
their binary, byte counts and source/build records are retained. Failed builds
stay intact. APFS clones preserve independently hashed regular input files while
sharing physical blocks; materialization time remains measured.

The gnark timing overlay applies only to an isolated source copy and adds
observations around the existing compile, setup, witness, prove and serialization
calls. It cannot alter the canonical source or enrolled circuit. Match its R1CS
hashes against the frozen gnark baseline before admitting samples.

The earlier acceptance/conformance trials had protocol files written before
execution, but precede publication of this decision commit. They are exploratory,
retained under their original identities, and excluded from the formal matched
sample set. Commit this decision and the frozen plan before starting that campaign.

Report compilation, setup/preprocessing, model commitments, witness generation,
proving, serialization, proof-only verification, caller binding and total wall
separately. Measure native-only and native plus binding; include the current
caller's native recomputation. Measure proof/key/parameter/disk sizes, encoding,
compression, sampled process-tree RSS and exact source/environment/input hashes.
Account for reusable cost at a declared amortization denominator. Match host and
threads or separate the results; LLM measurements are a different workload.

The initial build/API fixture is capped at 600 seconds, four threads, 16 GiB RSS
and 4 GiB new storage. Classifier experiments use the frozen plan's bounds, one
foreground command at a time. Review licences/dependencies before execution.
Prefer the Mac. A cloud fallback needs a separate frozen plan with live balance,
prices, source and public inputs checked under standing authority. No automatic
paid retry, top-up, private upload, outreach or scheduler is introduced.

## Review and historical evidence

This is a new experiment over unchanged semantics. Historical benchmarks are
preserved and are not relabelled as matched measurements. If semantics, arithmetic,
commitments, datasets or evaluation change, start a new identity and obtain owner
review before reusing previous results under that changed protocol. The owner's
request authorizes implementation of the full epic; it does not make an untested
candidate pass, silently adopt a backend or waive any acceptance criterion.

## Measured outcome

The [HF campaign and raw evidence](../CLASSIFIER-BENCHMARK.md) pass all 144
measured proofs, fresh Mac postflight and the retained-LLM join. Keep gnark
default and retain Circle experimentally. Lower complete-workflow time in this
stateless harness trades against higher memory and larger proof files; gnark's
instrumented proving stage is shorter on the representative control, while its
combined assignment/R1CS/key parsing dominates its command. Concrete security
profiles remain unequal/unqualified. No original classifier arithmetic, weights,
thresholds or historical measurements are changed.
