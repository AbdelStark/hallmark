# Research state

Updated: 2026-10-21. Phase: research software foundation in a public repository, not a deployed or cryptographically verified system. AI-assisted code and research initialization.

## Implemented

Strict dataset/config/integer-model/run contracts; exact group/transcript split checks; canonical typed research hashes and salted byte-exact transcript commitment; optional synthetic-data logistic training/PTQ; full-coverage integer inference; separate calibration; metrics and uncertainty; fresh run bundles; caller-pinned replay; offline conformance/tamper tests; locked distribution and CI definitions. See [ledger](LEDGER.md) for actual commands and results.

W01 / issue #2 adds a separate bounded v1 primitive codec and 22 typed hash domains.
The [evidence](evidence/w01-wire-2026-10-20.json) records 108 codec tests, 137 total
local tests and an isolated installed-wheel codec check. Legacy fixed hashes are
unchanged. This validates value encoding only; artifact schemas and trust remain
separate gates.

W30 / issue #31 adds typed errors and sanitized CLI failures, including argparse,
filesystem/Unicode and child-process errors. Its
[evidence](evidence/w30-errors-2026-10-20.json) records the reproduced path leak,
52 privacy tests, 189 total local tests and an installed CLI error check.
Historical run artifacts remain unchanged; new versioned events are described below.

W36 / issue #37 adds `make check-train` and a required-execution pytest guard.
The [evidence](evidence/w36-ci-2026-10-20.json) records 16 guard tests and fresh
CPython 3.12/3.13/3.14 environments: each core gate passed 204 tests with one
legitimate optional-training skip, each package gate passed, and each guarded
train gate executed and passed its training test. CI now covers all three
versions for both core/package and training, with no privileged integration job.

W03 / issue #4 adds frozen model/file/generation contracts, a canonical model
identity, a JSON schema snapshot and explicit rooted file inspection. Its
[evidence](evidence/w03-model-manifests-2026-10-20.json) records 128 manifest tests,
333 total local tests and an installed-wheel vector/file check. Filesystem
inspection is bounded and rejects links, aliases, nonregular files and detected
mismatches or concurrent changes; it does not load or attest to a model.

W04 / issue #5 adds frozen input/classifier/arithmetic contracts and typed operator
parameter files. Its [evidence](evidence/w04-classifier-manifests-2026-10-20.json)
records 133 classifier tests, all 128 model regressions, 466 total local tests and
installed-wheel profile/parameter validation. Checks cover topology and, against
exact hashed parameters, operation shapes, masks, scales and conservative integer
range envelopes. These are static contracts, not an executed or qualified graph.

W05 / issue #6 adds frozen policy, request and caller-expectation contracts.
Its [evidence](evidence/w05-policy-requests-2026-10-20.json) records 95 new tests,
all 261 model/classifier regressions, 561 total local tests and installed-wheel
validation. Checks resolve exactly rule/MLP/encoder in order, compare independently
supplied expectations and enforce continuity shape and UTF-8 byte limits. They do
not admit policy/data, authenticate enrollment or consume nonces.

W02 / issue #3 adds exact v1 transcript openings, caller-bound context and salted
complete-input hashes. Its [evidence](evidence/w02-openings-2026-10-20.json) records
69 new tests, 630 total tests, installed-wheel reconstruction and separate Python/
JavaScript agreement on seven transcript/context and 13 input vectors. The
JavaScript checker rejects a late-token mutation. Bytes are reconstructed from
the full prompt; encoder tokens still require an independently pinned local
tokenizer. This is hash reconstruction, not a proof or independent verifier.

W06 / issue #7 adds strict receipt, epoch, public-input and proof-container records.
Its [evidence](evidence/w06-receipt-contracts-2026-10-20.json) records 145 new tests,
775 total tests and installed-wheel declared-binding/packing checks. It checks
ordered identities, exact profile count relations, caller expectations, intervals,
opaque payload caps and the 100-element public-input layout. Synthetic signature,
quote and proof bytes remain unverified; these contracts expose no acceptance result.

W08 / issue #9 adds external trust, real Ed25519 threshold verification, bounded
complete successor history and an atomic SQLite checkpoint store. Its
[evidence](evidence/w08-enrollment-2026-10-20.json) records 88 new tests, 863 total
local tests and installed-wheel enrollment/persistence. Rejections cover rollback,
equivocation, skipped or incorrectly signed history, unknown/duplicate signers,
freshness, retirement, stale writers and unsafe state files. Update/commit failures
and process exit before commit preserve the prior checkpoint in the tested cases.
The [dependency review](evidence/w08-dependency-review-2026-10-20.json) preceded
installation. Fixture keys are public; operational root custody remains unenrolled.

W07 / issue #8 adds bounded offline bundle, private response, collection-state and
reported-result contracts. Its [evidence](evidence/w07-bundle-contracts-2026-10-20.json)
records 91 new tests, 954 total local tests, four schemas and 17 structural/report
vectors. It checks exact embedded files, declared evidence links, three ordered
proofs, caller limits and status/claim consistency. Openings remain separate,
including rejection of canonical private records embedded as files. These are
container/report checks; a decoded accepted flag is not verified evidence.

W09 / issue #10 adds caller-owned snapshot signing, immutable local history,
irreversible retirement, dual-authorized key transitions and `registry-check`.
Its [evidence](evidence/w09-registry-rotation-2026-10-20.json) records 97 new tests,
1,051 total local tests, two schemas and an installed-wheel rotation/CLI fixture.
The checkpoint now retains the external trust digest atomically, rejecting old
policy reuse after rotation. Failure and process-exit tests preserve prior state
and history. All keys are public fixtures; operational custody remains unapproved.

W33 / issue #34 adds a frozen corpus with 156 executable component cases and 32
unavailable genuine-evidence obligations. Its
[evidence](evidence/w33-conformance-2026-10-20.json) records 46 harness tests,
1,097 total local tests, byte-identical corpus reproduction and installed-wheel
checks. Software scope matches every executable outcome and catches a deliberately
wrong expectation. Default full-evidence scope exits 3; neither hardware/proofs nor
independent verification passed. All original PRD cheats remain in the required map.

W11 / issue #12 adds bound byte-count affine/ReLU/affine execution, with exact
ties-to-even rescaling, int32 partial-sum checks and full prompt coverage.
Its [evidence](evidence/w11-integer-mlp-2026-10-20.json) records 75 native-runtime
tests, nine fixed vectors, 60 seeded intermediate-layer comparisons, 1,172 total
local tests and installed-wheel validation. Weight/profile identities and file
paths are checked before execution; resource limits reject rather than truncate.
The exported weights are synthetic markers. Private traces are not proof evidence,
and no policy training, quality evaluation or backend qualification occurred.

W31 / issue #32 adds bounded private POSIX event storage, allowlisted schemas,
random run IDs, exclusive writers and immutable attempt/failure records. Its
[evidence](evidence/w31-private-events-2026-10-20.json) records 101 event tests,
156 focused regressions, 1,273 total tests and installed-wheel persistence.
Nine sync-failure points and four process-exit cases never produced an accepted
complete attempt. Failed attempts survive an explicit permitted retry; unknown
metadata, duplicate ordinals and unsafe files reject. Metadata remains private;
this does not authenticate execution, qualify physical power-loss behavior or
implement W32 full-path cost measurement.

W10 / issue #11 adds a bounded literal byte-rule program and complete-input native
execution with suffix state across chunk boundaries. The
[evidence](evidence/w10-complete-byte-rule-2026-10-20.json) records 97 new tests,
1,000 seeded oracle comparisons, 11 reproduced fixed vectors and 1,573 total
local tests, with both installed-package gates passing. Invalid bindings,
parameter/provenance changes, padding-dependent
matches, resource excess and inconsistent results reject. The scalar arithmetic
DAG projects the Boolean match feature; it does not encode the matcher.
The full extractor/state must be constrained by a future W19 proof.
Patterns are authored harmless markers, not a measured injection detector.
[PR #70](https://github.com/AbdelStark/hallmark/pull/70) merged as
`fa310ea2a4d1d484f1ef325eb7bfbf5f86a280ed`; all 12
[main jobs](https://github.com/AbdelStark/hallmark/actions/runs/39459269341) passed.
Issue #11 is closed.

W14 / issue #15 adds externally pinned source import, exact raw-row lineage,
complete parent/history/prompt grouping and the frozen study split recipe.
The [evidence](evidence/w14-lineage-data-admission-2026-10-20.json) records 59 new
tests, 25 independent graph-oracle cases, seven reproduced schema snapshots and
1,632 passing local tests, with both installed-package gates passing. The
26-row synthetic fixture retains all contrastive examples in 21 groups.
Changed source/review bytes, missing provenance, cycles, policy mismatches,
rehashed cross-split descendants and resource excess reject.
Four injected sync failures preserve partial directories without publishing
the final manifest. Automatic near-candidate discovery covers ASCII
case/whitespace equivalence only; broader semantic lineage, actual rights and
human label review remain external obligations. See
[decision 0021](../docs/decisions/0021-lineage-data-admission.md).
No real source was downloaded/admitted or task quality measured.
[PR #71](https://github.com/AbdelStark/hallmark/pull/71) merged as
`c4586a7107c59fb7ba4665247e73ff7e0146cf7d`; all 12
[main jobs](https://github.com/AbdelStark/hallmark/actions/runs/39466963984) passed.
Issue #15 is closed.

W18 / issue #19 now has actual local Groth16/BLS12-381 proof probes using
pinned, licence-reviewed gnark and an isolated Go toolchain. The
[raw evidence](evidence/w18-proof-probes-2026-10-20.json) records an 18-case
cubic installation probe and a 134-case complete eight-byte marker/hash probe.
Nine native rule vectors produced real proofs checked in fresh processes;
mutating each of the 100 public fields, witness/padding/counts, proof bytes and
the setup key rejected. The rule circuit has 206,801 constraints and a 292-byte
proof. Its diagnostic run took 321.90 seconds with 709,033,984-byte peak process
RSS and zero spend. These are small-program observations, not full-encoder costs.

The first rule candidate failed because its hash-domain length was wrong;
its source hashes, setup, numeric costs and failure remain intact. Earlier
toolchain/module/sandbox failures are also retained. The corrected runner denies
forks/network, checks expected artifacts and measured resource limits, and has
31 offline boundary/fixture tests. `make check` passes 1,663 tests; both
installed-package gates pass. The published synthetic proof/key example also
reverifies from its encoded evidence under separately pinned key/fixture inputs.
See [decision 0022](../docs/decisions/0022-local-proof-probes.md) and the
[source review](proposals/backend-v1/candidate-review.md) for licence/setup/gadget
limits. Classifier enrollment tags are synthetic, setup is local, and verification
shares the proving library. Neither hiding nor independent security review is
established. `qualified_backend` is always false; W18 remains open.

W18 now also implements the RFC-0005 `BackendQualification` declaration and
caller-pinned file/program/claimed-hiding checks. These are structural bindings,
not a qualification result; see
[decision 0023](../docs/decisions/0023-backend-declaration-contract.md).
The bounded synthetic integer MLP produced nine actual proofs and passed
156 cases, including all 100 public-field mutations and all 22 private layer
mutations. Its circuit has 208,717 constraints and a 292-byte proof.
The diagnostic run took 654.92 seconds with 704,036,864-byte peak process RSS
and zero spend. Some offline software/package checks ran concurrently on the
host, so these are not isolated latency measurements. `make check` passes
1,747 tests; both installed-package gates pass.
The [new raw evidence](evidence/w18-backend-contract-and-mlp-2026-10-20.json)
also records all 134 rule regression cases under the changed circuit, all
18 cubic cases under the final binary, and fresh verification of the published
MLP proof/key example against separately retained key and fixture pins.
[Decision 0024](../docs/decisions/0024-bounded-mlp-proof-probe.md) preserves the
eight-byte/synthetic-graph, setup, shared-library and security limitations.
At that stage, the general qualification runner, encoder operator block and
complete admitted encoder remained open; no backend was selected.

W18's fixed integer attention/feed-forward block now passes all 233 real-worker
checks. Its 64 proofs exhaust the four-token, two-position Boolean-mask domain;
all five public-field mutations and all 89 private intermediate mutations
reject. The 5,250-constraint circuit uses a 244-byte proof. The diagnostic roster
took 62.70 seconds, peaked at 39,223,296-byte process RSS and cost zero.
The [raw evidence](evidence/w18-integer-attention-block-2026-10-20.json) also
records exact reproduction of the earlier rule/MLP circuit hashes, all 18
retained proofs verified under the rebuilt worker, fresh proof/rejection cases,
18 cubic regression cases and fresh verification of the published block example.
`make check` passes 1,764 tests; both installed-package gates pass.
See [decision 0025](../docs/decisions/0025-integer-attention-block-probe.md).
This is a five-field standalone block, not the complete Hallmark proof statement.
At that stage, tokenizer, layer normalization, full encoder/input binding, the
qualification runner and independent setup/security review remained open.

W18 now exposes `hallmark qualify` with a caller-pinned protocol, safe input
snapshots and shared execution/storage limits. The
[raw evidence](evidence/w18-staged-qualification-2026-10-20.json) records all
541 actual worker cases passing in order: installation 18, rule 134, MLP 156
and attention block 233. Fresh setups reproduce the prior graph circuit hashes.
The command reports `incomplete` with exit 3 and `qualified_backend: false`.
Its diagnostic run took 1059.29 seconds, peaked at 677,314,560-byte worker
RSS and retained 5,926,016,680 bytes. Initial package validation overlapped
by 8.59 seconds; these are not isolated latency measurements. All 1,807 local
tests and both installed-package gates pass. See
[decision 0026](../docs/decisions/0026-staged-qualification-command.md).
The full admitted encoder, operational program/key enrollment, independent
verifier/security/hiding evidence and accepted setup lineage remain missing.
Review-file hashes bind documents without authenticating their approval or
adjudicating their claims. No backend is selected; W18 remains open.

W18's separate [input-scaling evidence](evidence/w18-input-scaling-2026-10-21.json)
now covers indexed canonical CBOR packing with 33 public commitment fields.
Eight actual proofs verify at capacities 8 and 256, including count boundaries
23/24 and 255/256. Twelve corrupted witnesses, all 33 public-field mutations,
an alias, altered proof and wrong setup key reject. Constraints are 206,049 /
244,924 / 525,403 at capacities 8 / 32 / 256. The 32,768-byte compile times out
after 90.335 seconds and peaks at 17,181,917,184 bytes RSS: 2,048,000 bytes above
the 16 GiB measured limit. No maximum-input circuit or proof is produced.
The corrected run takes 318.353 seconds; its predecessor's 118.892-second failure
is retained. Direct `IsSolved` lacked the actual commitment hint; those earlier
solver-negative outcomes are discarded as evidence. Real prover batches replace
that path without dummy hints. See [decision 0035](../docs/decisions/0035-input-commitment-scaling.md).
All 2,004 repository tests and both installed-package gates pass, with training
and guard checks executed. This isolates a full-input resource obstacle before adding encoder layers.
That run's post-exit memory checks did not prevent the small overage. This is a component with a
synthetic profile pin, not the 100-field classifier statement or a full encoder.

The new [live-memory evidence](evidence/w18-live-memory-2026-10-21.json) records a
shared native macOS RSS sampler and seven-eighths cutoff, plus retained signal
race and non-triggering test failures. Final maximum-capacity compilation attempts
stop twice below a deliberately lowered 2 GiB ceiling, at 1,891,549,184 and
1,963,802,624 bytes RSS. Small compilation passes. These are worker-boundary tests,
not full-input proofs or hard memory isolation. The historical receipt audit
charges 5,540 seconds, retaining failed runs and the original unattributed allowance;
this increment reserves 300 seconds, leaving 1,360 unreserved in the existing
7,200-second proving allocation. All 2,033 tests and both installed-package gates pass,
including required train/guard execution. See [decision 0036](../docs/decisions/0036-live-proof-worker-memory.md).

The [prefix-coverage candidate](evidence/w18-prefix-coverage-2026-10-21.json)
replaces per-position comparisons with exact Boolean prefix masks. All eight
small proofs verify, including five separately pinned proofs recovered after
a false monitor failure; all 18 malformed witnesses and the existing public/key/
proof mutations reject. Constraints fall to 205,547 / 243,222 / 512,502 at capacities
8 / 32 / 256. The maximum compile still fails: the live cutoff stops it after
60.889 seconds at 15,033,548,800 bytes peak RSS, below the 16 GiB ceiling.
There is no complete maximum circuit or proof. The failed original controller
run remains intact; a fresh recovery freezes corrected native-errno handling.
An early diagnostic heap guided the optimization but does not establish full-run
memory or speed improvements. See [decision 0037](../docs/decisions/0037-prefix-coverage-commitments.md).
The diagnostic and candidate reserve another 180 and 600 seconds respectively,
leaving 580 unreserved in the existing local proving allocation. All 2,042 tests
and both installed-package gates pass, including required train/guard execution.

An opt-in [compiler-cache candidate](evidence/w18-boolean-cache-2026-10-21.json)
changes one of 1,264 inventoried gnark source files in a separate copy. The original
cache and default dependency stay unchanged. Seven small fixtures have identical
serialized R1CS bytes across builds, and cache boundary/alias/constant tests pass.
A fresh 304.056-second campaign verifies eight proofs and rejects all 18 malformed
witnesses plus the public/key/proof mutations. The maximum compile still fails,
this time at the wall limit: 90.307 seconds and 14,839,169,024-byte peak RSS,
below the live cutoff and approved ceiling. No maximum circuit or proof exists.
Fixture equivalence and different stop conditions do not establish general compiler
correctness, an overall performance improvement or full-encoder qualification.
See [decision 0038](../docs/decisions/0038-boolean-wire-cache-candidate.md).
Its 550-second reservation leaves 30 unreserved; retain all reservations until a
receipt audit. All 2,042 Python tests and both installed-package gates pass,
including required train/guard execution; the new Go checks pass on both builds.

A [late compile diagnosis](evidence/w18-late-compile-2026-10-21.json) retains the
same compiler/circuit and adds a local-only profiling hook. All six Go tests and
seven serialized fingerprints pass. The maximum compile hits the live memory
cutoff after 56.651 seconds at 15,037,972,480-byte peak RSS, below the 16 GiB ceiling.
It produces a complete 40-second snapshot but no 80-second snapshot or circuit;
the conditional unchanged-binary confirmation is skipped. The saved main stack
is in deferred range-check recomposition. Instruction storage and hint construction
account for about 63% of sampled live heap at their allocation sites. Sampling
does not identify retaining paths, and instrumentation can perturb the run;
these observations do not establish a performance regression or improvement.
[Decision 0039](../docs/decisions/0039-late-compile-diagnosis.md) adopts a rechecked
receipt audit, conservatively charging 6,660 prior seconds within the unchanged
7,200-second allocation. A 500-second reservation leaves 40 unreserved; keep it
charged until a later receipt audit. Full-input proving remains unavailable.
All 2,042 Python tests and both installed-package gates pass, including required
train/guard execution. Exact-head hosted verification remains separate.

The [Linux fallback evidence](evidence/w18-hf-compile-2026-10-21.json) now records
two successful maximum-capacity (32,768-unit) commitment compilations under
[decision 0040](../docs/decisions/0040-bounded-hf-compile.md). Both report
40,015,721 constraints. They take 250.655/244.997 seconds, with kernel peak RSS
21,509,857,280/21,476,012,032 bytes, within the frozen limits. The one approved
L4 job completes in 557 provider-reported seconds. Compilation uses CPU; the GPU
is unused. A rounded-total-duration cost estimate is USD 0.133330, not an invoice.
Six Go tests and seven small serialized circuit fingerprints pass before the
large attempts. Maximum reproduction checks equal counts; no serialized maximum
circuit, setup, witness or proof is retained. The synthetic profile pin and this
commitment component do not qualify an enrolled classifier or complete encoder.

The pinned public bootstrap keeps the HF token on the Mac. Its separate worker
passes actual socket-denial smoke and bounded time/memory checks; this is not a
general sandbox. All 30 new tests, including four actual kernel cases, pass in
Linux CI. Local validation passes 2,068 tests with four Linux-only skips; both
package gates pass with installed train/guard execution. All 28 exact-runtime-head
jobs pass on `de05e111e92d356a1c472abe7ceb934660a4ccc1`. A prior push attempt's
macOS package failure and fail-fast cancellation remain retained; their cause is
unestablished and the failed jobs passed on same-head rerun. The increment charges
294.110 local seconds, including control commands and the full ancillary allowance,
within its 330-second reservation. Keep that reservation charged: zero unreserved
within the 7,200-second proving allocation. The one-job HF allowance is consumed.

The [streamed-artifact preparation](evidence/w18-stream-artifacts-2026-10-21.json)
removes the Go adapter's whole-file buffer and carries commitment-scaling setup
files through pinned, exclusive streaming copies. Existing size caps stay fixed.
The baseline accepts a symbolic link; new file-boundary tests reject it, malformed
sizes, trailing bytes and detected changes. Thirteen focused Python tests and
seven Go tests pass, including a tiny real-proof unit fixture. A retained
eight-unit commitment proof verifies with the new binary; an appended proof byte
rejects. The Python copy fixture asserts less than 3 MiB traced allocation for an
8 MiB file. This is adapter behavior, not whole-decoder or full-prover memory.
Lint, formatting and type checks pass, but the initial full local gate reaches its
39-second cap at 94% of tests, with no test failure reported before termination.
The package gate was unrun at that point; the approved validation below closes
both local gaps while preserving the timeout. The receipt audit
retains all actual commands and allowances, rounds prior usage to 7,136 seconds
and reserves the remaining 64 under [decision 0041](../docs/decisions/0041-streamed-proof-artifacts.md).

Streaming commit `d03f9d1` passes all 28 hosted jobs: push `39589743317` and PR
`39589749300`. Its retained local timeout and unrun local package gate remain
separate. The [setup capacity review](evidence/w18-setup-capacity-2026-10-21.json)
now derives a 3,221,225,428-byte minimum for the maximum key's Z vector alone,
above the unchanged 256 MiB cap. Default FFT precomputation and simultaneously
live G1 Jacobian/affine arrays require at least 24,696,063,552 bytes of slice
backing storage before other allocations; this is not measured RSS. The
[next candidate](proposals/backend-v1/setup-capacity-options.md) bounds G1
Jacobian temporaries. G2 already converts directly to affine. Neither a patch
nor a new setup run is executed by this source review; total memory/time and
L4 fit remain unestablished.

The [approved validation](evidence/w18-approved-validation-2026-10-21.json) passes
`make check` with 2,081 tests, four platform skips and one warning, and the core
`make package-check`. The corrected optional G1 patch builds from a fresh full
module copy. All 16 point cases agree with separate scalar multiplication and
across builds, including an actual per-worker chunk boundary. Seven serialized
circuit fingerprints match. Both variants pass the existing tiny cubic real-proof
unit fixture and changed-input/trailing-byte rejections; its temporary proof/key
bytes are not retained as published proof evidence.

One 262,145-point allocation sample per variant produces identical ordered-output
digests. Allocated bytes are 80,061,592 / 76,999,144; allocation counts increase
from 250 to 2,622; observed worker RSS is 96,813,056 / 79,331,328 bytes. This is
neither a statistical speedup nor maximum setup memory evidence. The first failed
build, local timeout and previous resource charges remain intact. The additional
120-second allowance costs zero and launches no HF job. At that stage, a fresh
small commitment proof/negative campaign and maximum setup resource plan remained open.

The [fresh G1 proof campaign](evidence/w18-g1-small-proofs-2026-10-21.json) now
passes twice under the owner's additional 600-second Mac-only approval. Each
fresh run passes 50 worker cases: eight proofs at capacities 8 and 256 verify;
18 malformed witnesses, all 33 public-field changes, an alias, changed proof and
wrong key reject. All 16 proofs also verify in fresh replay workers against
key/proof/native-input pins stored outside the run outputs. Circuit and native
input identities agree across runs; independently generated setup keys differ.
The diagnostic rosters take 213.851 / 212.832 seconds and peak at 1,264,451,584 /
1,248,935,936 bytes process RSS. No maximum compile/setup/proof is attempted.
These are small commitment proofs with local setup and a shared verifier library,
not full-encoder qualification or independent security evidence. See
[decision 0044](../docs/decisions/0044-approved-small-g1-proof-campaign.md).
`make check` passes 2,081 tests and the core package gate passes. Total command
time plus ancillary allowance is 514.800 of 600 approved seconds, at zero spend.
Final retained checkout allocation is 33,955,835,904 bytes, below 40 GiB.

The [maximum artifact evidence](evidence/w18-maximum-artifacts-2026-10-21.json)
now retains the complete 32,768-unit circuit on the Mac. Export takes 79.600 seconds,
peaks at 17,674,289,152 bytes RSS and writes 2,566,643,378 circuit bytes. A fresh
reload takes 2.678 seconds and matches the hash and all original counts. A separate
inventory reload adds commitment sizes: 48,477,333 total wires, one commitment and
22,366,059 private committed wires. These are serialization/inspection results,
not setup or proof results. The new adapter supports bounded large artifacts and
setup from a pinned compiled circuit. Tiny actual proofs and seven small circuit
fingerprints pass; a missed test-call argument and a pre-worker Python filename
collision are retained as failures. [Decision 0045](../docs/decisions/0045-standing-approval-and-maximum-artifacts.md)
records standing owner approval and replaces repeated micro-budget permission
barriers. [Decision 0046](../docs/decisions/0046-bounded-maximum-hf-proof.md) prepares
one bounded larger-memory L4 fallback; no new cloud job has launched at this point.

W15 / issue #16 now has the record-level MLP component: train-only complete-input
max-logit fitting, pinned same-environment optimizer resume and explicit native
integer export. The [evidence](evidence/w15-record-mlp-training-2026-10-20.json)
records 33 new tests, 1,665 total tests, 17 required train tests and both installed
package gates. Two fresh three-seed fixture runs produced 27 identical artifacts
each, including checkpoint/history/export results. All seeds hit the 80-epoch
limit without convergence; maximum observed score error was 0.016157 against the
fixed 0.1 engineering bound. These are authored markers, not policy-quality data.
The historical logistic baseline and native fixture identities remain unchanged.
See [decision 0027](../docs/decisions/0027-record-level-mlp-training.md).
The follow-up [comparison evidence](evidence/w15-grouped-comparisons-2026-10-20.json)
adds exact-text character n-grams, fixed controls, five grouped train-internal
rotations and separately pinned native calibration/evaluation. It records 44 more
tests, 1,709 total tests, 35 required train tests and both installed-package gates.
Two new runs reproduce all 31 artifacts: 75 rotations, 15 deliberate nonconvergence
cases, and nine final evaluations each. The toy MLP detects none of the five
positive representatives; its false-positive counts are 0/1/2 across the seeds.
These failures remain visible; the pipeline pass is not a task-quality pass.
[Decision 0028](../docs/decisions/0028-grouped-baseline-selection.md) fixes the
selection rule, source bounds and remaining admission obligations.

[Merged PR #73](https://github.com/AbdelStark/hallmark/pull/73) contains this work.
The [guard source review](evidence/w15-guard-source-selection-2026-10-20.json) and
[decision 0029](../docs/decisions/0029-guard-source-selection.md) select the pinned
published guard for bounded asset/runtime qualification under the reviewed model
grants. The [CPU evidence](evidence/w15-guard-cpu-2026-10-20.json) now verifies
all five acquired asset digests and executes the real ONNX graph locally. Two
fresh processes reproduce all 11 output artifacts: seven authored probes, 50
chunks per run, including 32,768-byte ASCII and Unicode prompts. Elapsed times
are 7.253/7.008 seconds, with 4.372/4.371 GB peak RSS. The optional adapter joins
the pinned calibration/evaluation API; its tiny installed-runtime fixture needs
no research assets. The tokenizer remains lossy, and both maximum-length harmless
repetitive probes have positive uncalibrated margins. These are software results,
not measured task quality. Contamination/label review and admitted real-data
commands remain required for confirmatory task-quality claims; decision 0033
permits completion of the synthetic software stage. The compact encoder belongs
to W16. See [decision 0030](../docs/decisions/0030-complete-input-guard.md).

The [comparison command evidence](evidence/w15-comparison-command-2026-10-20.json)
adds one caller-enrolled execution path from reproduced source import through
train-only selection, final fitting and calibration to test scoring. Every fit
and threshold is retained before any test-scoring call. Two fresh authored-fixture
processes reproduce all 38 output artifacts, each in about 2.9 seconds and below
273 MB peak RSS. All 75 rotations and 15 nonconverged attempts remain visible.
The toy MLP misses all 20 positive test representatives in every seed; the
character baseline has 2/20 benign false positives. This is plumbing evidence,
not a detector-quality result. Validation passes 31 new tests, 1,772 total tests,
35 required training tests, 32 guard tests and the core installed-package gate.
The larger local combined-package check is deferred under the nearly exhausted
20 GiB storage limit; Linux/macOS CI requires that installed comparison fixture.
The [command template](../docs/OPERATIONS.md#caller-enrolled-baseline-comparisons)
is implemented, but no genuine reviewed real-data dossier has been enrolled.
PR #73 remained draft at that point. See [decision 0031](../docs/decisions/0031-admitted-comparison-command.md).

The [source review](evidence/w15-source-review-2026-10-20.json) now retains 1,000
Gandalf viewer rows at an exact reported revision and Dolly's SHA-256-verified
15,011-row JSONL. The fixed empty-context filter leaves 10,544 Dolly instruction
candidates and excludes 4,467 rows. Two fresh builds reproduce a 64-item blank
human label packet. These are review candidates, not admitted labels or data.
The 114 exact-duplicate groups and a separate 563-pair lexical screen are retained;
one candidate component crosses Gandalf's original splits. Missing historical
parents and semantic lineage remain unresolved. A separately acquired 5,441-row
public synthetic source cannot replace natural traffic or the study's power
requirements. No detector was fitted/scored or HF token used. See the
[human-review handoff](proposals/inj-direct-v1/source-review.md) and
[decision 0032](../docs/decisions/0032-public-source-review-pilot.md).

The [authorized synthetic pipeline evidence](evidence/w15-synthetic-pipeline-2026-10-21.json)
now joins the complete comparison command to the real pinned guard weights.
Two fresh Mac processes reproduce all 38 artifacts in 4.674/4.665 seconds, with
4.374 GB peak RSS. The agent checked all 200 authored control labels; no human
review occurred. The guard produces 3/20 negative-control false positives, the
character model 2/20, and each MLP misses all 20 positive controls. These are
software-control outcomes, not injection-policy quality estimates. W15's execution
criterion passes; full-study/quality/independence flags remain false and the
compact encoder stays explicitly unavailable. The owner's decision supersedes
the earlier human-review/storage merge blockers for this pipeline stage.
All 1,772 local tests, 35 required training tests, core/combined package checks
and the live specification audit pass.

W37 / issue #38 adds a fully pinned build environment, reviewed source snapshots,
byte-identical repeated distributions and exact archive/dependency inventories.
Its [initial evidence](evidence/w37-reproducible-packages-2026-10-20.json) and
[access-time correction](evidence/w37-source-snapshot-fix-2026-10-20.json) record
66 new tests, 82 focused tests and 1,339 total local tests. The correction permits
access-time updates while retaining identity/modification-change rejection. Both package gates build twice,
rebuild the same wheel from the sdist and exercise fresh installed core contracts;
the train gate additionally executes synthetic fit/replay and tamper rejection.
The [dependency review](evidence/w37-dependencies-2026-10-20.json) matches 518
locked artifact hashes for 32 packages and records actual licence metadata/notices.
Linux/macOS CI now covers core/package and required-train/package on CPython
3.12–3.14. This is engineering reproducibility within a recorded environment, not
package publication, an open-source licence, scientific validity or a release packet.

W38 / issue #39 adds the offline `make check-spec` gate and an explicit read-only
live issue audit. Its [initial evidence](evidence/w38-spec-traceability-2026-10-20.json) and
[final validation](evidence/w38-final-validation-2026-10-20.json) record
54 new tests, 55 focused tests and 1,393 total local tests; both package
gates also execute the spec check from the extracted sdist. The
[live observation](evidence/w38-live-issues-2026-10-20.json) matches 40 work issues,
10 trackers, 106 dependency edges, labels, milestones, scope and acceptance.
Local coverage names 51 sections and 18 invariants. Missing requirements, anchors,
orphan mappings, cycles, unowned questions and metadata drift reject. Historical
source/corpus/legacy results are unchanged. Structural agreement and issue state
are not semantic completeness, approval or scientific/security evidence.

W13 / issue #14 now has a [concrete admission proposal](proposals/inj-direct-v1/README.md)
and strict study/protocol/review records with caller-pinned document checks.
The [evidence](evidence/w13-admission-preparation-2026-10-20.json) records
81 new tests, 1,474 total local tests, byte-identical marker/schema reproduction
and both installed-package gates. The first package attempt rejected unstaged
files missing from its tracked-only snapshot; the complete staged candidate passed.
At that stage, source/model/host holds and unapproved quality/power/cost terms
remained explicit. [PR #68](https://github.com/AbdelStark/hallmark/pull/68) merged
as `346f9bcc1940985c90053a719eb2ed4fea4671b6`; all 12
[main jobs](https://github.com/AbdelStark/hallmark/actions/runs/39452888007) passed.

The owner subsequently approved the prototype study, targets, delegated evaluation
design/public source selection, bounded local budget and conditional HF Jobs.
[Decision 0019](../docs/decisions/0019-approved-study-scope.md) and
[AUTHORITY](AUTHORITY.json) record that authority. The
[frozen design](proposals/inj-direct-v1/design.md) fills quality/power/cost and
retention terms, including an exact conditional power plan. The
[approval-update evidence](evidence/w13-study-approval-2026-10-20.json) records
1,476 passing local tests. Existing source holds remain; actual file/split,
candidate/evaluator and independently enrolled final review identities are still
missing, so the proposal correctly rejects as a measurement admission.
The source-selection and engineering work is authorized now. No dataset/model
asset, paid job, private upload, hardware evidence or independent review occurred.
[PR #69](https://github.com/AbdelStark/hallmark/pull/69) delivered this update as
`7f547356a7f91e8d331a6963d0cf40603dd49b44`; all 12
[main jobs](https://github.com/AbdelStark/hallmark/actions/runs/39457001526) passed.
Issue #14 is closed as admission preparation, not completed measurement.

W17 / issue #18 now adds caller-pinned versioned slice and paired group reports.
The [evidence](evidence/w17-group-evaluation-2026-10-21.json) records 40 new tests,
1,812 total tests and both installed-package gates. The authored correlated
fixture keeps 36 records in 12 resampling groups, all three seeds and deliberate
float/integer regressions. The report never fits, scores or calibrates a model.
Two fresh report commands over retained W15 controls reproduce identical bytes
in 0.292/0.283 seconds, with less than 42 MB peak RSS. They retain ten available
models, nine 10,000-resample comparisons, twelve unavailable members and nine
unavailable quantization pairs. Original fixed controls remain in the pinned
provenance. Shared marker templates are not independent policy samples; this is
software evidence. Synthetic/exploratory reports do not evaluate a confirmatory
decision, and confirmatory requests remain inconclusive. The initial package
check rejected global uv 0.13.4; an isolated required uv 0.9.18 made both gates
pass without changing the global tool. See [decision 0034](../docs/decisions/0034-frozen-group-reports.md).

## Not implemented or established

TEE evidence, operational registry enrollment/authoring/rotation, proofs for enrolled operational Hallmark classifiers, full bundle assembly and combined verification, independent verifier implementation, real safety-policy dataset/evaluation, encoder/teacher/student training, full proof/compiler qualification, public release licence, production service, deployment, partner approval or any safety guarantee. CI definitions alone are not hosted green checks. CODEOWNERS and agent rules are not enforced sandboxing or branch protection.

## Next bounded task

The [proposed v1 corpus](../SPEC.md) defines the full hybrid POC, with 10 draft RFCs and explicit owner-review gates. Merged [PR #1](https://github.com/AbdelStark/hallmark/pull/1) contains the corpus and [implementation tracker](../docs/roadmap/IMPLEMENTATION.md): 40 work issues, 10 RFC trackers and 102 implementation dependency edges. The [live audit](evidence/spec-publication-2026-10-20.json) checked all issue bodies, labels, milestones, comments and child checklists. This is specification/backlog delivery, not implementation or new scientific evidence; see [decision 0002](../docs/decisions/0002-v1-specification-scope.md). The owner explicitly authorized public repository visibility on 2026-10-20; the standing visibility instruction is in [AGENTS.md](../AGENTS.md).

Local Python 3.12 train-enabled and Python 3.13 core-only baseline gates pass, including isolated wheel checks. Earlier private hosted runs could not start because of an account billing/spending-limit block. After the owner made the repository public, hosted [run 39398412605](https://github.com/AbdelStark/hallmark/actions/runs/39398412605) passed on `48f2d7066b62a42f971cd10dbbc2cdbae720b82e`. Each implementation PR still needs checks on its own commit. Billing settings were not changed.

The owner requested autonomous implementation through `.agents/harness/goal.md`,
sequentially with one issue per PR. #2 is merged in [PR #52](https://github.com/AbdelStark/hallmark/pull/52)
and #31 in [PR #53](https://github.com/AbdelStark/hallmark/pull/53).
#37 is merged in [PR #54](https://github.com/AbdelStark/hallmark/pull/54), with
[merge-commit CI](https://github.com/AbdelStark/hallmark/actions/runs/39404113385)
passing on `6b2a6acda5813ddcdf9d14554a99ada8ad2e6245`. All three merge-commit CI
runs passed. W03 / #4 is merged in [PR #55](https://github.com/AbdelStark/hallmark/pull/55);
[merge-commit CI](https://github.com/AbdelStark/hallmark/actions/runs/39406784978)
passed on `f844342c18af85d8cb0b1160521c58938f9d87ea`. W04 / #5 is merged in
[PR #56](https://github.com/AbdelStark/hallmark/pull/56), with all six
[merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39409355612)
passing on `f456b4a749d795f2f22f19e5d2ae5fd90b099539`.
W05 / #6 is merged in [PR #57](https://github.com/AbdelStark/hallmark/pull/57), with
all six [merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39411367808)
passing on `1d344d55b44efae9b0232c46d4553dfe59f49288`.
W02 / #3 is merged in [PR #58](https://github.com/AbdelStark/hallmark/pull/58), with
all six [merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39412814966)
passing on `fbd6c90f65e5e535f8dfb839012f1bd3bd544097`.
W06 / #7 is merged in [PR #59](https://github.com/AbdelStark/hallmark/pull/59), with
all six [merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39414504221)
passing on `774887d0e40b82459d4f7ca8657400d9905577ad`.
W08 / #9 is merged in [PR #60](https://github.com/AbdelStark/hallmark/pull/60), with
all six [merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39416596651)
passing on `866d36a69762104847f1ded8253829a4e11dd786`.
W07 / #8 is merged in [PR #61](https://github.com/AbdelStark/hallmark/pull/61), with
all six [merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39419869358)
passing on `302a861043636094295c4dc06832e4a8c06afe87`.
W09 / #10 is merged in [PR #62](https://github.com/AbdelStark/hallmark/pull/62), with
all six [merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39422275382)
passing on `9357288387bfbcdf0ad28ae34f54b37fe70a1333`.
W33 / #34 is merged in [PR #63](https://github.com/AbdelStark/hallmark/pull/63), with
all six [merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39425868492)
passing on `89de51b49cfbf10040384967b289a32b9709cb02`.
W11 / #12 is merged in [PR #64](https://github.com/AbdelStark/hallmark/pull/64), with
all six [merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39428839904)
passing on `e8c9d0be603d477e3861b6843538477974b97354`.
W31 / #32 is merged in [PR #65](https://github.com/AbdelStark/hallmark/pull/65), with
all six [merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39432180583)
passing on `5e23f44ca51a58760ff1c139c114b7db52c5c1c5`.
W37 / #38 is merged in [PR #66](https://github.com/AbdelStark/hallmark/pull/66),
with all 12 [main jobs](https://github.com/AbdelStark/hallmark/actions/runs/39437824044)
passing on `56b53f42cdc25f7690b6e8d1ed95a4e87b1e0bfb`.
W38 / #39 is merged in [PR #67](https://github.com/AbdelStark/hallmark/pull/67),
with all 12 [main jobs](https://github.com/AbdelStark/hallmark/actions/runs/39440839286)
passing on `1da52da9c5f45b481d031ab3dd1ec5b4601c7a6d`. The current work map has 106 dependency edges, including W04's reuse
of W03 file references and W07's opening/signed-registry dependencies on W02/W08;
the historical 102-edge publication audit is unchanged. Re-evaluate dependencies
before #39 spec traceability and the remaining admission/integration work. Research,
real proofs, genuine hardware and independent verification remain required for
the full MVP.

W14 / #15 is merged in [PR #71](https://github.com/AbdelStark/hallmark/pull/71).
W15 / #16 is merged in [PR #73](https://github.com/AbdelStark/hallmark/pull/73)
as `de29271d21196202fc951ebe5f5fc3348fbf9a63`; all 28 candidate jobs and all 14
[merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39562563658) passed.
The owner's [synthetic-stage approval](../docs/decisions/0033-approved-synthetic-pipeline.md)
permits agent review without human labels for pipeline development, 40 GiB
retained storage, Mac-first execution and HF T4/L4 fallback. The earlier label
packet and all failures remain retained. Confirmatory task quality is separate.

W17 / #18 is merged in [PR #74](https://github.com/AbdelStark/hallmark/pull/74)
as `5312460d8a48a4771d502592a05fb3ba362bdc03`; all 28 candidate jobs and all 14
[main jobs](https://github.com/AbdelStark/hallmark/actions/runs/39565926086) passed.

W18 / #19's staged implementation is merged in [PR #72](https://github.com/AbdelStark/hallmark/pull/72)
as `89c2585619d4404d702439a46c825c8f8241cef9`. All 28 final candidate jobs and
all 14 [merged-main jobs](https://github.com/AbdelStark/hallmark/actions/runs/39604077378)
pass. Issue #19 stays open; no backend is selected.
The small proof, artifact-reader and G1 gates pass. The maximum circuit now
exports and reloads on the Mac with an independently retained circuit hash.
Continue the frozen maximum setup/proof campaign in decisions 0046 and
[0047](../docs/decisions/0047-cpu-maximum-proof-fallback.md) under the
owner's standing approval; do not ask for another small-run permission or reuse
old exhausted reservations. The source-derived setup/key bounds justify a larger
host; they do not establish actual setup RSS or latency. The queued L4 job was
cancelled without observed execution, its empty bucket was removed, and a cheaper
256 GB CPU attempt exports the identical maximum circuit but stops on the mounted
bucket file-integrity guard. All 37 files are downloaded and checked, and the bucket
is removed. [Failure evidence](evidence/w18-hf-storage-failure-2026-10-21.json)
retains the missing maximum cost receipt and unavailable setup/proof. The
[local-disk correction](../docs/decisions/0048-local-disk-proof-execution.md)
keeps file checks strict and copies complete/failed outputs only after execution.
All historical failures
and budgets remain preserved. Current preparation has not produced a maximum
proof, complete encoder, independent verifier/security review or genuine hardware
evidence. Continue the admitted encoder graph, including layer normalization,
after resolving the resource gate; the commitment component does not qualify it.
Under [AUTHORITY](AUTHORITY.json), review public source rights
and complete exact inventories; exclude ambiguous/gated assets. Freeze actual
data, candidate and evaluator identities before measurement. Use
[PROGRAM](PROGRAM.md), [ML-PLAN](../docs/ML-PLAN.md) and [EVALUATION](../docs/EVALUATION.md).
The [hardware/reviewer options](proposals/inj-direct-v1/compute-and-review-options.md)
are prepared; procurement and contact remain owner choices when those gates are
ready. Neither blocks ordinary local implementation.

Keep further proof work sequential within each recorded bounded campaign. The tiny graphs already have real proof evidence; they do not qualify a larger encoder. Preserve the hybrid hardware/ZK split and the B1/B2 trust distinction in [SPEC](../docs/SPEC.md).

## Resume

Inspect git state and actual installed environment, read the latest ledger entry, then take one falsifiable gate. Run the smallest relevant negative test. Update this state and the ledger with evidence, limits and a concrete next step. Use the current [approved research authority](AUTHORITY.json); repository visibility follows [AGENTS.md](../AGENTS.md).
