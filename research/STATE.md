# Research state

Updated: 2026-10-29. Phase: MIT-licensed research software in a public repository, with dedicated classifier and quantized LLM proofs, not a deployed or fully verified hybrid system. AI-assisted code and research initialization.

## Single classifier backend — removal of the pairing backend

2026-10-29. At the owner's request, [decision 0087](../docs/decisions/0087-remove-pairing-backend.md)
removes the former classifier proof backend, its comparison benchmark,
`hallmark qualify`, the `proof-artifacts` CI job and the two app workflows that
depended on it. Circle STARK (STWO) is the only classifier proof backend;
`make e2e` and `make e2e-composed` run the Circle drivers. The last commit
containing the removed sources is `b7b8376b584836f29066708b663006c2cae7328e`;
history remains in git, and this file no longer describes the removed work.

Circle circuit/compiler sources and engine identity, model exports, thresholds,
rule program records (now `fixtures/rule-program.json`) and the caller enrollment
pin are unchanged. Numeric evidence receipts stay byte-identical. The native LLM
verifier inventory now lists only the 17 files it loads, so its identity changes;
statements below that the 55 LLM source pins were unchanged describe their own
changes, not this one. Signed LLM enrollments bound to the earlier identity need
a new owner signature, and the `circle-reference-2026-10-28` release verifies at
its own tag. The shared worker sandbox is `hallmark._worker`. Acceptance is
recorded in the decision and its PR. No security, hiding, hardware or
qualification claim changes.

## Public Circle reference collection — local acceptance and publication passed

The owner requested complete Circle headline numbers with actual proof/log and
machine resources. [Decision 0086](../docs/decisions/0086-public-circle-reference.md)
fixes baseline, scope and acceptance. The [reference guide](../docs/REFERENCE-RUN.md)
and [numeric receipt](evidence/circle-reference-2026-10-28.json) distinguish L1
(H200 matched pair), C1 (fresh Mac classifier controller) and J1 (retained-input
composition). They are not one measured fresh end-to-end GPU invocation.

[Discussion #133](https://github.com/AbdelStark/hallmark/discussions/133) indexes
all stage tables, machine/job details and source-pinned verification commands.
The [artifact release](https://github.com/AbdelStark/hallmark/releases/tag/circle-reference-2026-10-28)
contains actual 23 LLM proof files plus 46 statements/claims, nine fresh classifier
controls, three composed classifier proofs and 988 exact supporting files. All four
assets were downloaded without authentication and matched their byte counts and
SHA-256. The external manifest pin is recorded in the guide and Discussion.

The fresh C1 controller takes 302.96 s: MLP 1.95 s, CNN 172.94 s, Rust builds
24.82/9.57 s and proof campaign 93.50 s. Nine final STWO proving calls total
24.061 s; complete prover commands total 50.028 s; proof-only verifier processes
total 0.807 s; actual proof files total 18,063,779 bytes. Peak sampled worker-tree
RSS is 23.45 GB. These are one local observation, not timing distributions.
The retained L1 CUDA session timer is 53.94 s, including interaction work;
complete commands are 155.89 s and separate CPU grid verification 84.32 s.
The raw 23-proof payload is 737,858,641 bytes. Reused/unrecorded stages remain
explicit; SASH and classifier internal proving timers use different boundaries.

Fresh archive-based cryptographic verification takes 219.25 s including native
compilation: all 23 LLM proofs twice, all 36 LLM mutations rejected, and all 12
classifier proofs checked in fresh proof-only processes with caller reconstruction.
The first helper attempt passed LLM checks but incorrectly charged input archives
to its work quota, failing before classifier checks. Failure is retained; generated
Circle work now has its own 128-MiB budget. The 55-file LLM and Circle backend
identities, models and thresholds are unchanged. No new paid job, hiding, hardware,
independent qualification or policy-quality claim. Final repo/CI/Pages delivery is
tracked on this change's PR.

## Circle-first defaults — local acceptance passed

Circle STARK is the owner-selected default for `make e2e`, `make e2e-composed`,
the web/TUI workbench, README, current guides and both published model cards.
[Decision 0085](../docs/decisions/0085-circle-default.md) records the scope;
[numeric acceptance](evidence/circle-default-2026-10-28.json) pins exact sources,
commands, outputs and failures.

Bare `make e2e` freshly trains/exports, generates and freshly verifies nine
Circle proofs; 63 public-input mutations, 18 substitutions and three invalid
rosters reject. It takes 320.68 s including local training/build checks. Default
retained LLM composition takes 266.29 s including native verifier compilation:
23 SASH proofs, 22 links, two honest checks, 36 LLM mutations, three new Circle
classifier proofs, three fresh outer-join verifications and 16 binding rejections.
Verdicts `[1,1,0]` give integrity pass and policy release false. These are single
Mac acceptance observations.

A browser-launched retained-model run makes nine new proofs with the same
rejections in 97.94 s. Both interfaces select Circle first; 56 app tests pass,
and actual desktop/mobile results were inspected. Core validation passes 2,588
tests with 50 optional/platform skips; strict docs and core distribution gates
pass. Exact-head hosted/merge/Pages receipts are tracked with this change.
No new cloud jobs or compute spend were needed. Both HF card-only updates leave
weights and original release tags unchanged. All 55 LLM source pins and the
Circle engine/compiler identity remain unchanged. No hiding, hardware,
independent qualification or useful-policy claim is added.

## Circle classifiers — verified implementation

Epic [#112](https://github.com/AbdelStark/hallmark/issues/112) has a complete
experimental direct-STWO path for the unchanged rule, four-unit integer MLP and
contextual CNN. It preserves complete 0–96-byte inputs, salted canonical SHA-256,
strict integer decisions and caller-owned context/model/enrollment checks.
The completed experiment exposed the nine-proof Circle control workflow; the
later default change is tracked above. No core inference arithmetic, model, threshold or historical
result is changed. [Implementation and commands](../docs/CIRCLE-CLASSIFIERS.md).
The [actual Make reproduction](evidence/circle-make-e2e-2026-10-27.json) freshly
builds both locked targets and passes all nine proofs and rejection checks;
driver wall time is 97.81 s excluding compilation.

Three additional Circle proofs join the retained TinyLlama request. Fresh Mac
verification checks those, 23 SASH proofs and 22 links, and rejects 16 changed
bindings/rosters. Host composition takes 11.13 s including hashes and host work.
Verdicts `[1,1,0]` give valid integrity with policy release false. No new LLM
proving, recursion, hiding or hardware evidence is claimed. All 55 native LLM
verifier source pins and their identity remain unchanged.

The [acceptance record](evidence/circle-classifiers-acceptance-2026-10-27.json)
retains two nine-proof Mac runs, 63 direct public-input rejections, 18 request
swaps and three roster rejections per run. Full-length conformance adds three
proofs and 21 real constraint failures plus an omitted-edge program-pin failure.
Six arithmetic fixtures cover both strict thresholds below/equal/above the
boundary; local `make check` passes 2,580 tests with 51 optional skips. Final
packaging, exact-head CI, merge and deployment receipts are tracked on
[PR #130](https://github.com/AbdelStark/hallmark/pull/130).

The frozen MLP always allows in this 96-byte domain: its exact-rational interval
score bound is [−5600,−2338] at threshold 0. The README and
[published card clarification](evidence/mlp-model-card-clarification-2026-10-27.json)
disclose this quality limitation. Weights and original release tags are unchanged. Independent follow-up #131 remains outside this epic.

## Terminal and web workbench — complete

`make demo-tui` and `make demo-web` launch shared local-first demo apps. One
catalog, persistent controller and result adapter expose six existing workflows,
observed stages, logs, local process-tree samples, HF jobs, retained artifacts
and receipts. The [guide](../docs/WORKBENCH.md) includes actual rendered results;
[decision 0082](../docs/decisions/0082-demo-workbench.md) records the boundary.

The [acceptance record](evidence/demo-workbench-2026-10-27.json) pins the inputs,
source and result hashes. The real TUI-launched classifier run verifies 9 proofs,
rejects 18 substitutions and checks 405 arithmetic cases. Browser-launched native
LLM verification checks 23 proofs and rejects 36 mutations. A fresh complete
browser-launched TinyLlama run produces 23 proofs, checks 22 residual links,
accepts two honest verifications and rejects all 14 mutations. All three HF jobs
are completed, outputs retained and buckets deleted. The $0.31 running-compute
estimate is not an invoice; the startup-inclusive admission ceiling was $2.50.

There are 52 passing app tests, including both interfaces, cancellation,
request/artifact boundaries and recovery without duplicate work. Desktop/mobile
and 120×42/80×24 terminal views were inspected. Core validation passes 2,398
tests with 123 optional skips. Distribution, app build and strict docs checks
pass; exact-head hosted/deployment receipts are recorded on
[PR #129](https://github.com/AbdelStark/hallmark/pull/129). All 55 native verifier
source pins, its identity and the inference lock remain unchanged. No fresh GPU
benchmark or composed campaign is claimed for this app work. Monitoring and
completion-report checks add no backend qualification, privacy or hardware claim.

## Public documentation site and badges

The README also reuses the homepage's proof-flow SVG below its introduction,
linked to the detailed LLM statement. No duplicate asset is added.

The [site](https://abdelstark.github.io/hallmark/) is deployed. A copy-edit pass
under the owner's `no-ai-slop` request replaces homepage slogans and repetitive
learning-page framing with specific computations, commands and checks. Existing
section anchors remain available. Proof relations, measurements, model files and
historical evidence are unchanged; validation and delivery receipts follow on PR.

The owner requested a GitHub Pages documentation site and `for-the-badge` header
badges, including both published Hugging Face models. The candidate site adds
an editorial homepage, four educational chapters, a workflow chooser, searchable
canonical guides, model cards and a research evidence map. Existing Markdown
and numeric evidence stay canonical; staged link/anchor adaptation produces the
website without publishing untracked notes or ignored runs.

[Decision 0081](../docs/decisions/0081-public-documentation-site.md) records the
publication scope. The [QA record](evidence/documentation-site-2026-10-27.json)
pins source files and observed desktop/mobile, math, diagram, search, theme and
proof-explorer checks; the final clipboard check was interrupted by a browser
connection reset. Ten staging/link-boundary tests pass. Strict builds and local
link/asset checks pass; exact final counts and hosted delivery are recorded on PR.

The docs toolchain is isolated in `website/`, with its own lock and dependency
review. All 55 native verifier source pins, the inference lockfile and verifier
identity remain unchanged. No training, proof benchmark, evaluator or numeric
evidence is modified. Pages is enabled for the standard main-only Actions
deployment with HTTPS; the repository remains public. [Build and maintenance](../docs/DOCUMENTATION.md).

## Published classifier models — complete

The owner subsequently requested publication of trained models. The exact
seed-17 [MLP and CNN are public on Hugging Face](../docs/MODELS.md), under
[decision 0080](../docs/decisions/0080-public-classifier-models.md), with model
cards, original JSON checkpoints, unchanged quantizations, native exports,
evaluation and hash manifests. The [publication receipt](evidence/hub-model-publication-2026-10-27.json)
records immutable Hub revisions and anonymous verification of all 41 released
files. Full/resumed checkpoints and requantizations match; exported model bytes
match the proved models; all 100 retained CNN test scores/decisions replay.
Native examples run from anonymous downloads. This adds a hash-pinned inference
command, not new training, held-out evaluation or proof qualification. The
synthetic task and 96-byte demo scope remain explicit. TinyLlama is upstream,
not a Hallmark-trained release. Local/distribution/hosted receipts follow on PR.

## README benchmark and onboarding refresh

The README now leads with the recorded generated-kernel result: 53.94 s CUDA
proving, 10.15× over same-host SIMD, and 155.89 s complete commands (4.36×).
Timing boundaries, memory, proof size, fresh verification checks and raw evidence
are adjacent to the headline. Quickstarts distinguish local classifiers, paid
CPU inference proofs, paid GPU measurements and retained proof verification.
The proof statement/diagram and source-ownership guides distinguish unchanged
CPU Rust from generated/patched CUDA. This is documentation of the existing
fixed-case evidence; runtime, protocol and numeric records remain unchanged.
Local/distribution and delivery receipts are recorded in the ledger and PR.

## Generated CUDA constraint kernels — complete fixed-case trial

The owner-requested [generated-constraint pipeline](../docs/GPU-BENCHMARK.md#generated-constraint-result)
passes its complete gate under [decision 0079](../docs/decisions/0079-generated-cuda-constraints.md).
The [numeric evidence](evidence/llm-gpu-generated-constraints-2026-10-26.json)
pins the measured source, admitted generated build, 77 kernel shapes across
16 families, all source/binary/input hashes and the retained failed attempt.

One matched H200 pair takes **547.75 s SIMD / 53.94 s CUDA** summed proving
(10.15×), and 679.49 / 155.89 s complete segment commands (4.36×). CUDA executes
1,710 device constraint evaluations, with **zero CPU fallback**, in 0.47 seconds
total constraint evaluation. Both backends prove all 23 segments and pass full
grid/token checks. All 69 files match each other and the historical CPU case.
Fresh CPU verification accepts two honest checks and rejects all 14 mutations;
Mac verification accepts two and rejects all 36. Witness/interaction generation
remains on the CPU; hiding, hardware and backend qualification remain unclaimed.

The passing cached-build command takes 2,086.78 seconds. Its running-compute
estimate is $1.76; the complete kernel campaign totals $3.37 including the build
and telemetry-failure attempt, not invoices. All four jobs are terminal, outputs
retained and buckets deleted. The earlier failed run's 23 valid individual
proofs stay a failed pipeline record; the complete CSV-framing regression fix
precedes the clean rerun. All 51 focused tests and 2,454 local tests pass (50
skipped). Distribution and hosted receipts are recorded on the delivery PR for
[issue #122](https://github.com/AbdelStark/hallmark/issues/122). The historical
fallback baseline below remains unchanged. One pair establishes no distribution.

## GPU prover measurements — complete fixed-case trial

The [GPU pipeline](../docs/GPU-BENCHMARK.md) passes its complete research gate:
same TinyLlama relation, reviewed witness archive, 23 SIMD and 23 CUDA segments
on one H200, identical 69-file inventories and fresh CPU/Mac verification.
[Decisions 0077](../docs/decisions/0077-gpu-prover-measurement.md) and
[0078](../docs/decisions/0078-native-gpu-build-and-window.md) freeze the profile.
The [numeric evidence](evidence/llm-gpu-benchmark-2026-10-26.json) retains all
four attempts, source/input/binary hashes, profiler counters and mutation results.

One CPU-then-CUDA pair takes 537.20/583.87 seconds summed proving and
669.25/687.34 seconds complete segment commands. CUDA is slower in this initial
host-generation profile; its 1,710 CPU constraint fallback calls take 532.75
seconds. Peak host RSS is 104.69/11.78 GB, with CUDA using 67.08 GiB VRAM.
Both grids pass; the separate CPU suite accepts two honest checks and rejects
14 mutations, and the native Mac suite accepts two and rejects 36. No hiding,
hardware provenance or backend qualification is claimed. At this baseline,
generated CUDA constraint kernels were an unimplemented optimization candidate;
the later completed trial is recorded above.

The full retained-preparation benchmark takes 3,372.34 seconds. Running-compute
estimates are $2.52 for the successful run and $5.37 across all attempts, not
invoices. All six jobs are terminal, outputs retained and buckets deleted.
Earlier source-freeze, fixture-enrollment and incomplete-head failures remain
failed records. The measured snapshot passes 38 focused tests and 2,441 local
tests. Four additional controller tests reject unsupported hosts or missing Rust
before paid work. At that baseline's delivery, the local gate passes 2,445 tests (50 skipped), with
42 focused tests; publication/distribution gates are recorded on the PR.
This is separate from the Circle
STARK classifier implementation below; [issue #120](https://github.com/AbdelStark/hallmark/issues/120)
tracks the GPU measurement delivery.

## Circle classifier tracker and architecture guide

The owner requested clearer proof architecture documentation and a Circle STARK
classifier implementation tracker. The [architecture guide](../docs/ARCHITECTURE.md)
maps each Make target, the three flows, exact statements and SASH source/patch
ownership. [Epic #112](https://github.com/AbdelStark/hallmark/issues/112) tracks five
ordered tasks (#113–#117): freeze/replay, rule, MLP, CNN and benchmarks. At that
tracker-creation baseline no Circle STARK classifier adapter existed; the
implementation update is near the top of this file.
This is new integrity research, not a remaining gate for the completed MVP or a
substitute for original private/hardware v1 qualification. Runtime, model,
evaluation and historical evidence remain unchanged; no proving/cloud run is
needed for this documentation/tracker change.

The README now surfaces [recorded headline results](../README.md#recorded-results-at-a-glance):
model/response size, proving and verification times, serialized proof size and
fresh workflow costs. These summarize existing evidence, with hardware and
preprocessing caveats; they introduce no new benchmark or backend comparison.

## Current MVP — complete

The owner explicitly selected completion of the **LLM integrity MVP without
hardware or hiding requirements** on 2026-10-25. [Decision 0076](../docs/decisions/0076-integrity-mvp-scope.md)
records that scope; [acceptance and limits](../docs/MVP.md) map it to evidence.
The completion audit rehashes
all 207 runtime files at that recorded source, 55 native verifier files, 20 fresh-proving pipeline
files, all eight model files and all 69 proof/statement/claim files. The complete
short TinyLlama response, caller expectations, current signed composition and
proof-only verification pass. No runtime or historical evidence is changed.

No further implementation gate is required for this selected research MVP.
The original private/hardware v1 roadmap stays open as `post-mvp` work; its
requirements have not been implemented or adopted by this completion decision.
Operational custody/revocation, independent security/hiding qualification,
general prompts/models and hardware provenance remain limitations/future work.
The code retains `qualified_backend: false`, `hiding_claim: false` and
`hardware_claim: "not-accepted"`. The repository remains public and MIT licensed.

## Supporting proof and workflow evidence

The owner's complete short pretrained LLM response now has a passing composed
proof: **23 segments, 22 residual links and eight answer tokens through EOS**.
The model is pinned TinyLlama-1.1B-Chat-v1.0 with the disclosed `y-attnout-w12`
quantization. [The proof explanation](../docs/LLM-PROOF.md) states the exact claim;
[raw evidence](evidence/llm-response-composition-2026-10-23.json) retains the failures.

The first non-delayed composition passed every individual proof but rejected the
last link. [Decision 0068](../docs/decisions/0068-prove-the-output-head-final-norm.md)
corrects the head extraction's family selection. Only that head is reproved;
the 22 transformer proofs remain byte-identical. The original Rust binary is
unchanged. Full verification takes 92.10 seconds on the smaller CPU worker.

A fresh proof-only worker passes: two honest verification processes and all
14 changed-claim rejections, with no model weights or witness mounted. The honest
runs take 83.99 and 79.16 seconds.
The caller checks pinned shape digests, exact tokens, complete coverage and the
final-norm head. **`make e2e-llm` now reproduces this result from fresh preparation,
build and proofs.** Its [recorded run](evidence/llm-e2e-reproduction-2026-10-23.json)
took 31 minutes 15 seconds, with a $0.31 compute bound rather than an invoice.
All 69 proof/statement/claim files match the earlier accepted bundle byte for
byte. Two fresh verifications took 80.11 and 78.45 seconds; all 14 mutations reject.
All outputs are retained and the three temporary buckets are deleted. The first
local patching failure remains recorded in [decision 0069](../docs/decisions/0069-reproduce-the-llm-response-workflow.md).
`make e2e` still runs the classifier demo. The remaining operational gates are
root provisioning and independent security/hiding qualification; hardware provenance is
a separate extension, not part of this LLM demo.

An optional native Mac verifier now specializes the same proof relation to the
frozen public case using compiled caller-enrolled shape roots. `make verify-llm
LLM_RUN=runs/llm-e2e-...` rebuilds that verifier and checks retained proofs without
weights, witnesses or paid jobs. The [native experiment](evidence/native-llm-verification-2026-10-23.json)
requires two honest checks, all 14 original mutations and two direct native
unknown-shape/calibration rejections. [Decision 0070](../docs/decisions/0070-native-enrolled-llm-verifier.md)
explains the preprocessing change and retained linker/sandbox failures. This
variant does not rederive shape trees; operational root qualification remains separate.
`make e2e-llm` retains the original Linux verifier's runtime derivation.

The native suite now includes 20 additional boundary mutations. The expanded
probe found an output-token field alias accepted only when the caller was
bypassed, plus four malformed shapes that crashed. The native verifier now
checks vocabulary ranges, tree/column dimensions and redundant configuration;
the complete suite requires two honest checks and 36 explicit rejections.
[Decision 0071](../docs/decisions/0071-native-proof-input-boundaries.md) and
[numeric evidence](evidence/native-proof-boundaries-2026-10-23.json) preserve the
baseline and candidate outcomes. Operational root custody and independent
security review remain open.

The native verifier now supports detached Ed25519 authorization of the exact
case and verifier source inventory, using a public key supplied separately by
the caller. It checks authorization before build, before the proof worker and
after verification, and reports whether it used signed enrollment or the
checkout case. [Decision 0072](../docs/decisions/0072-signed-llm-parameter-enrollment.md)
defines the format; [evidence](evidence/llm-signed-enrollment-2026-10-23.json)
retains wrong-key, tampering, expiry and changed-source rejections. The integration
issuer is a disposable research key. This implements parameter authentication;
operational key custody, revocation/rollback policy and independent security
qualification remain separate obligations.

Earlier failures are documented in decisions [0065](../docs/decisions/0065-exact-llm-witness-accumulators.md),
[0066](../docs/decisions/0066-llm-shape-reconstruction.md) and
[0067](../docs/decisions/0067-bind-the-value-activation-scale.md).
The delayed-value profile remains ineligible because its activation-scale binding
is open; its constructor repair is not used in the complete-response result.

The owner-requested code cleanup consolidates four proof controllers onto one
checked worker runner and replaces global sandbox overrides with per-call read
paths. [Validation](evidence/worker-cleanup-2026-10-22.json) covers retained failure
costs, artifact tampering, sandbox isolation and real proof/verification execution.
This maintenance gate changes no model, proof relation or qualification status.

The owner-requested usability gate now has a one-command entrypoint: `make e2e`.
The [fresh reproduction](evidence/e2e-entrypoint-2026-10-22.json) completed pinned
preparation, both training/export runs, nine proofs, all 18 cross-request
rejections and all 405 expected arithmetic outcomes. Both model identities and
all three circuit identities match the earlier walkthrough; the executable
pipeline stayed frozen. The [proof explainer](../docs/PROOFS.md) distinguishes
in-circuit input hashing/arithmetic from caller-owned context/program/key binding,
and a valid proof from a passing classifier verdict. Native verdict recomputation
remains part of the caller helper. This usability gate does not close the
qualification gates below.


Reader entry points: [end-to-end demo](../docs/DEMO.md),
[results and limits](../docs/RESULTS.md), [documentation index](../docs/README.md).
The walkthrough now has [fresh reproduction evidence](evidence/docs-demo-reproduction-2026-10-22.json):
both exports match, nine real proofs verify, all three decisions match, all 18
cross-request substitutions reject and all 405 arithmetic cases match their
expected outcomes. The owner explicitly adopted [MIT](../docs/decisions/0063-mit-license.md);
historical experiment records remain byte-identical. This closes the documentation
reproduction gate, not the qualification gates below.

The [second synthetic screen](evidence/w16-contextual-screen-v2-2026-10-22.json)
and [failed first screen](evidence/w16-contextual-screen-v1-2026-10-22.json) retain
their original evidence boundaries; the reused test pair is an engineering case.

For the broader v1 roadmap, the remaining qualification gates are explicit: authenticated compiler/program
and key enrollment, setup custody, independent security/hiding review and an
admitted B1 verifier adapter. B2 and the full hybrid path additionally need genuine
hardware provenance and protected inference/output evidence. Issues #19/#29
remain open; research proofs do not satisfy those operational dependencies.
Mac first; approved Modal/Vast/HF credits remain bounded fallbacks, and GCP is
not a classifier-proof dependency. Historical entries below preserve prior results.

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

## Broader v1 work not implemented or established

TEE evidence, operational registry enrollment/authoring/rotation, proofs for enrolled operational Hallmark classifiers, full bundle assembly and combined verification, separate verifier for complete hybrid bundles, real safety-policy dataset/evaluation, encoder/teacher/student training, full proof/compiler qualification, production service, deployment, partner approval or any safety guarantee. CI definitions alone are not hosted green checks. CODEOWNERS and agent rules are not enforced sandboxing or branch protection.

## Implementation history

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
