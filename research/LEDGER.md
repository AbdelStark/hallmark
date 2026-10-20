# Evidence ledger

Entries distinguish local software results, statistical conclusions, literature reports and proposed work. Never replace a failed entry with a favorable rerun.

## 2026-10-20: bootstrap software checks and negative classifier result

Purpose: exercise the research and integer-execution contracts on harmless amber/violet marker data. Dataset SHA-256: `a7b2c3f3b978623273b72fa3853344b4059725a5b147540c5a1e906a11977ae7`. Fixed config: [fixture](../configs/fixture.json). There are 24 training, 12 calibration and 16 test records, balanced within splits.

Local software evidence: `make check` passes lock validation, Ruff lint/format, strict mypy, 29 tests and local Markdown file-link checks. `make package-check` builds wheel/sdist, checks required contents and installs the wheel with locked core dependencies in a fresh environment, then runs the installed CLI. Host: macOS arm64, Python 3.12.12, uv 0.9.18. Training used one BLAS/OpenMP thread. CI definitions are present; these local results do not establish hosted CI status.

Repeat experiment commands, each with `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1`:

```
uv run --locked --extra train hallmark run configs/fixture.json --output runs/bootstrap-003
uv run --locked --extra train hallmark run configs/fixture.json --output runs/bootstrap-004
uv run --locked hallmark audit-run runs/bootstrap-003 --dataset fixtures/smoke.jsonl --expected-manifest 4326f9b8987b6e465ab2bc32d15d2a94eef76d3c21c1ff8b79bc6f36a8fe9088
diff -qr runs/bootstrap-003 runs/bootstrap-004
```

Both complete run directories were byte-identical, with manifest SHA-256 `4326f9b8987b6e465ab2bc32d15d2a94eef76d3c21c1ff8b79bc6f36a8fe9088`. Replay returned `research-replay-matched`. Source snapshots identify the exact pre-publication code; the later CLI type annotation changes no arithmetic. Runs remain local and gitignored, not hosted evidence.

Negative result: threshold `-273`; calibration TP=6, FP=0, TN=6, FN=0; test TP=8, FP=8, TN=0, FN=0. Test FPR is 1.0. The report correctly says `insufficient-evidence`; this is not a useful classifier result. The fixture includes split names in its text, a visible distribution shift/confound for the weak byte baseline. That is a candidate explanation, not an experimentally isolated cause. We did not tune the threshold or change the fixture after seeing test outcomes. Even a perfect result on eight benign examples would lack power for a 1% FPR claim.

Earlier bootstrap-001/002 were also retained; repeated model/prediction/result files matched. Tamper tests reject changed reports under the original hash and mathematically inconsistent reports even after rehashing a bundle. Those checks exercise software integrity/replay only. No real safety-policy, hardware or proof result is claimed.

Hosted execution: the first private GitHub run could not start any steps because of an account payment/spending-limit block. This is not a hosted pass or a code-test failure. Billing settings were not changed.

The local Python 3.13 core-only check caught a mypy configuration gap: the optional NumPy import was not exempted when NumPy was absent. Adding it to the existing missing-optional-import override fixes that environment without installing training dependencies into core. The train-enabled environment still checks against installed NumPy types. This is a tooling fix, not a model, data or evaluation change.

Final local matrix: Python 3.12.12 with the train extra, `make check`, 29 passed; fresh Python 3.13.11 core-only environment, `make check`, 28 passed and the optional train test skipped. Both passed strict typing, lint/format and docs checks. Fresh installed-wheel/CLI checks passed on both interpreter versions. Linux/hosted CI remains unexecuted because of the account block; these are local macOS results, not substituted hosted passes.

## 2026-10-20: v1 specification corpus and implementation decomposition

Hypothesis: the historical hybrid POC can be expressed as one coherent, typed v1 contract with every implementation deliverable mapped to a bounded work item, while preserving the existing research evidence. Baseline: commit `1024ae9a0598ae842e86eaf98c479c5d11ea1f23`, no issues or PRs, software foundation only. Mutable paths: root specification/navigation, `docs/spec/`, `docs/rfcs/`, `docs/roadmap/`, decision 0002, state/ledger/evidence and source-distribution inclusion. Runtime, evaluator, dataset, fixture config and old results were not changed. The existing `.gitignore` edit is unrelated and was preserved.

Raw identities/counts and commands were saved first in [spec bootstrap evidence](evidence/spec-bootstrap-2026-10-20.json). Local validation: smallest contract/reference/docs fixture, 18 passed; `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 make check`, 29 passed; `make package-check`, passed including isolated installed CLI. The initial formatting gate failed on Python signatures inside a documentation code block; formatting was corrected and the full gate rerun successfully. The structural audit checked 23 index/section/RFC files, all 10 exact RFC templates, local anchors, 40 unique work items and an acyclic dependency graph. Archive inspection found every corpus/work-map path and no harness, runs, data, checkpoints or environment-secret paths.

The corpus preserves genuine hardware, rule/MLP/encoder proofs, B1/B2, complete-input binding, independent verification and private reviewer reproduction. Open questions have owners and resolution checkpoints. Drafting a requirement or filing its issue does not perform the experiment or authorize its resources. No statistical, hardware, proof, performance or security result was produced.

Privacy correction: live repository metadata showed public visibility and disabled issues. Before publishing this corpus, visibility was changed to private and verified; issues were enabled under the explicit specification/backlog request. This does not establish whether older public material was copied. No collaborators or billing settings were changed.

Acceptance requires both the pushed corpus/PR and the complete live issue set with tracker and dependency links. Publication receipts are recorded in the follow-up entry after filing; the local checks alone do not complete that gate.

### Private publication and live backlog audit

Phase 1 was committed in four logical commits and pushed as `spec/bootstrap-2026-10-20`; corpus commit `ad058ad74a6dc23ae95cc523d7bf468a06d4c4ce` is the immutable reference used by the issues. [PR #1](https://github.com/AbdelStark/hallmark/pull/1) remains open for owner review.

Phase 2 used `gh label list/create`, `gh api` for milestones, `gh issue create --body-file`, `gh issue edit --body-file` and `gh issue comment --body-file`. Initial `gh issue list --state all --limit 200` found no issues. Created 40 implementation issues (#2–#41) and ten RFC trackers (#42–#51), with exactly one type/area/priority/effort label per issue, applicable RFC labels, and milestones v0.2/v0.3/v1.0. The total milestone counts, including trackers, are 16/19/15. No issue was closed or represented as implemented.

The [live publication audit](evidence/spec-publication-2026-10-20.json) was saved before this summary. It fetched all 50 live issues and compared their complete bodies with the work map, checked metadata and pinned references, validated all 102 implementation dependency edges and all 50 dependency comments, and compared each tracker checklist with its exact child set. Missing labels, unmapped items and missing children: zero. The [tracker](../docs/roadmap/IMPLEMENTATION.md) and [work map](../docs/roadmap/work-items.json) carry all returned issue URLs and owner/date resolution gates.

Final local checks after adding the tracker: `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 make check`, 29 passed; `make package-check`, passed. The source distribution includes the tracker and complete corpus; forbidden harness/run/data/checkpoint/secret paths were absent. Runtime, evaluation code, fixture/config, tests and lock remained unchanged from the baseline. Documentation structure/anchor checks passed.

Hosted spec run [39393331644](https://github.com/AbdelStark/hallmark/actions/runs/39393331644) on `ad058ad` completed without starting any job steps. Its check annotation reports an account payment/spending-limit block. This is unavailable hosted execution, not a test failure or pass; final-head delivery/check state is reported on the PR. Billing was not changed.

The deliverable is the proposed corpus plus filed backlog, not a completed v1 system. Next bounded research work is the admission proposal in issue #14. Hardware/proof/data campaigns, independent implementer access, policy adoption and reviewer sharing remain gated. Prior public exposure is unassessed.

## 2026-10-20: owner-authorized merge and public visibility

At the owner's request, PR #1 was merged as `f0f117285d2ccf82b122d1155b8a1fb56a2a2217`; local and remote `main` matched. Its tree matches the previously validated PR head `3951d1f49c9e5f91c0ef4c592c973d95dfa0828a`. Hosted run [39396000433](https://github.com/AbdelStark/hallmark/actions/runs/39396000433) started no job steps because of the same account billing/spending-limit block.

The owner then explicitly requested public visibility and instructed agents to keep it public unless explicitly asked otherwise. Executed `gh repo edit AbdelStark/hallmark --visibility public --accept-visibility-change-consequences`. Verification with `gh api repos/AbdelStark/hallmark` returned `private: false` and `visibility: public`; an unauthenticated HTTP request to the repository returned 200. AGENTS.md records the standing instruction, superseding the earlier private-repository instruction. The unrelated `.gitignore` edit was preserved. No research execution authority was expanded.

Documentation validation: `uv run --locked python scripts/check_docs.py` passed; `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 make check` passed all gates with 29 tests. Package checks were not repeated for these instruction/state/ledger edits.

## 2026-10-20: W01 strict v1 primitive encoding

Hypothesis: a bounded RFC-0001 codec can give each supported value one canonical
representation while preserving the existing research identities. Baseline:
`48f2d7066b62a42f971cd10dbbc2cdbae720b82e`; the legacy contract fixture passed
14 tests and the new fixture failed because `hallmark.wire` was absent. Mutable
paths: new wire module/tests, package smoke, schema/API documentation, decision
0003, changelog and this state/evidence record. No data, evaluation, training or
legacy identity code changed.

Saved [source/environment hashes and numeric results](evidence/w01-wire-2026-10-20.json)
before this entry. The codec accepts only the restricted primitive types and 22
domains, rejects duplicate/unsorted keys, overlong forms, trailing data, tags,
invalid Unicode, integer overflow and resource excess. Fixed vectors, seeded
differential checks against cbor2 and truncation tests passed: 108 codec tests.
An initial mypy gate caught a redundant cast; it was removed. Final `make check`
passed 137 tests plus lint, format, typing and documentation checks;
`make package-check` passed including an isolated installed codec smoke.

The separate v1 module preserves both recorded legacy digest fixtures. No artifact
schema, signature, attestation, proof or security-review result is claimed.
[Decision 0003](../docs/decisions/0003-v1-codec.md) records limits and the raw
codec/schema boundary; owner review before enrollment remains outstanding.

Delivery: [PR #52](https://github.com/AbdelStark/hallmark/pull/52) merged W01 as
`516143e0fb7ae696ab76a1a6d8a314496a60f6a3`; issue #2 closed. Hosted checks passed
on both the PR head and the [merge commit](https://github.com/AbdelStark/hallmark/actions/runs/39401155509),
including both core interpreter jobs and the train fixture.

## 2026-10-20: W30 typed errors and CLI privacy

Hypothesis: one allowlisted diagnostic boundary can prevent private input/path
and external exception text from reaching CLI output, while preserving success
output and research arithmetic. Baseline: `516143e0fb7ae696ab76a1a6d8a314496a60f6a3`.
A missing-file fixture reproduced a path-sentinel leak with exit 2.
Mutable paths: error module, CLI boundary, wire error inheritance, privacy tests,
package smoke, error/API docs, decision 0004 and state/evidence records.

Saved [source/environment hashes and raw results](evidence/w30-errors-2026-10-20.json)
before this entry. All 19 codes are exercised through the CLI, including exception
notes/causes. Additional tests cover argument parsing, malformed JSON/UTF-8,
private paths, timeout/OOM, child-process stderr, failed result serialization,
stage precedence and retained failed-run artifacts. The 52 privacy tests pass;
`make check` passes 189 total tests plus lint, format, typing and docs.
`make package-check` passes with an installed invalid-argument diagnostic smoke.
Initial mypy attribute annotations and Ruff zip strictness failures were fixed
and retained in the evidence record.

Input errors retain exit 2; execution/storage/resource failures now exit 3.
Unexpected exceptions get random local diagnostic IDs. No error returns success.
No arithmetic, dataset, evaluator or historical bundle was changed. Event
persistence, process isolation and real provider integrations remain separate
gates; this does not establish hardware/proof evidence or sanitize old snapshots.

Delivery: [PR #53](https://github.com/AbdelStark/hallmark/pull/53) merged W30 as
`ad664aa16f591c6c9fef08fa6b309faa0b69c1b6`; issue #31 closed. Exact-head PR and
[merge-commit checks](https://github.com/AbdelStark/hallmark/actions/runs/39402274960)
passed. The repository remained public.

## 2026-10-20: W36 required training and interpreter matrix

Hypothesis: the train CI job can reject missing execution without changing the
core-only environment's legitimate optional skip. Baseline:
`ad664aa16f591c6c9fef08fa6b309faa0b69c1b6`. A forced-skip fixture run with
`pytest -m train` returned exit 0 with one skipped test, confirming the false-green
case. Mutable paths: pytest guard/tests, Makefile, workflow, contributor/operations
docs and state/evidence records. Runtime, data, training and evaluation code
were unchanged.

Saved [source/config/environment hashes and raw numeric results](evidence/w36-ci-2026-10-20.json)
before this entry. The guard's 16 subprocess tests cover real execution,
optional core skipping, missing extras, call/setup/teardown skips, partial
execution, xfail/xpass and collection/setup-only runs. `make check-train` sets
one BLAS/OpenMP thread and requires successful setup/call/teardown for every
selected training test, with at least one training test selected.

Fresh macOS arm64 environments used CPython 3.12.12, 3.13.11 and 3.14.6 with
`uv sync --locked --python VERSION`. On each: `make check` passed 204 tests and
skipped the absent optional training dependency; `make package-check` passed;
then `make check-train` installed the locked extra and executed one training test
successfully with 204 other tests deselected. These are six local core/train
configurations, not classifier-quality measurements. An initial Ruff E501 test
literal failure was fixed; its output was preserved before fresh attempts.

The workflow runs core/package and training separately on all three versions.
Inspection confirms read-only contents permission, disabled checkout credential
persistence, no secrets, no self-hosted runners and no artifact uploads.
Workflow dispatch runs the same fixtures; it is not authority for a privileged
integration job. Real proof/hardware execution still requires its separate
protocol, host and budget. Hosted delivery must be checked on this PR's exact
commit before integration.

Delivery: [PR #54](https://github.com/AbdelStark/hallmark/pull/54) merged W36 as
`6b2a6acda5813ddcdf9d14554a99ada8ad2e6245`; issue #37 closed. Exact-head PR
checks and all six [merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39404113385)
passed. The repository remained public.

## 2026-10-20: W03 immutable model manifests

Hypothesis: a strict frozen manifest can bind every execution-relevant field
while rejecting malformed references before explicit file inspection. Baseline:
`6b2a6acda5813ddcdf9d14554a99ada8ad2e6245`, with 108 passing existing wire tests.
Mutable paths: the new manifests module/tests/vector/schema, installed-package
check, API/decision docs and state/evidence/tracker records. The existing research
hashes, dataset, evaluator and training protocol are unchanged.

Saved [source/config/environment hashes and numeric results](evidence/w03-model-manifests-2026-10-20.json)
before this entry. The selected gate passes locally: 128 manifest tests,
333 total tests under `make check`, and `make package-check`, including the
351-byte fixed CBOR vector, typed model identity and bounded rooted-file check
from an isolated installed wheel. Python 3.12.12/macOS arm64 used the locked
environment, one training thread and harmless local files only.

Negative cases cover path traversal/absolute paths, Unicode byte bounds,
unsorted/duplicate/oversized lists, integer/boolean confusion, invalid greedy
configuration, missing/extra fields, unknown versions, malformed wire values,
unsafe unchecked model copies, symbolic/hard links, filesystem aliases, FIFOs,
file size/hash mismatches, directory swaps and files changing during reading.
Parsing performs no I/O. Every valid file/digest/generation/numerical-mode mutation
tested changes identity; unsupported generation changes are rejected.

The initial vector setup found a JSON decoding problem caused by manually
converting a file list before Pydantic validated nested strict bytes. The manual
conversion was removed; JSON projection round trips and wire byte/text rejection
now pass. Two focused lint findings were also fixed. These failures remain in
the evidence record rather than being counted as successful checks.

The schema interpretation and path/inspection limits are recorded in
[decision 0005](../docs/decisions/0005-model-manifests.md). Wire-profile enrollment
still needs owner/independent review. The file checker describes opened files,
not a protected later load, genuine attestation, classifier quality or proof.
No real model was loaded or downloaded. Hosted checks must pass on the exact PR
commit before merging.

The live #3/#6 dependency correction is now mirrored in the work map and tracker:
W02 requires W05 for typed request expectation/context binding. The current graph
has 103 edges; the original publication audit remains an immutable 102-edge record.
Next implementation order after W03: #5, #6, then #3.

Delivery: [PR #55](https://github.com/AbdelStark/hallmark/pull/55) merged W03 as
`f844342c18af85d8cb0b1160521c58938f9d87ea`; issue #4 closed. All six exact-head
PR and [merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39406784978)
passed. The repository remained public.

## 2026-10-20: W04 classifier and arithmetic contracts

Hypothesis: immutable classifier/profile identities plus exact parameter-file
binding can reject malformed topology, shapes, masks and integer range
declarations without loading a model or executing a graph. Baseline:
`f844342c18af85d8cb0b1160521c58938f9d87ea`, with 128 passing model-manifest tests.
Mutable paths: v1 contracts/shared serializer, tests, schema/vector fixtures,
package checks, the mypy TypeForm option and specification/evidence/tracker docs.
The legacy dataset, evaluator, training protocol and research hashes are unchanged.

Saved [source/config/environment hashes and numeric results](evidence/w04-classifier-manifests-2026-10-20.json)
before this entry. The selected gate passes locally: 133 classifier contract tests,
all 128 model regressions, 466 total tests under `make check`, and
`make package-check` with an isolated installed-wheel classifier/profile/parameter
check. The locked Python 3.12.12/macOS arm64 environment used one training thread
and synthetic local metadata. No model, dataset or proof backend was downloaded.

Each allowed operator family has positive and negative shape/range cases.
Further cases cover duplicate producers, forward references/cycles, unused
declarations, boolean/integer confusion, capacity boundaries, parameter
hash/schema mismatches, masking, lookup bounds, overflow, negative ties-to-even,
mixed scales, immutable nested records and unvalidated copies. Large tensor
dimensions are checked as bounded-rank metadata without allocating their data.
The initial identity-mutation test accidentally left unused roots; correcting
the test preserved the validator's rejection. Its failed output hash is retained.

The checked parameter union uses Pydantic's TypeForm annotation. Enabling the
locked mypy implementation's TypeForm support resolved its typing error without
suppressing checks. The shared serializer preserves all prior model golden bytes,
identity and schema projection.

[Decision 0006](../docs/decisions/0006-classifier-contracts.md) records the exact
operator files, scale/rounding rules, graph bounds and separate parsing/parameter
validation phases. Static interval bounds are conservative and do not validate
actual external tensors, program semantics, classifier quality, backend behavior,
hardware, proofs or independent verification. WIRE-REVIEW/INTEGER-GRAPH owner gates
remain. Exact-head hosted checks must pass before integration.

The work map now records W04's actual dependency on W03's file references (104
edges total); historical audits are untouched. After W04, #6 policy/request
expectations is the next contract gate, then #3 transcript/input binding.

Delivery: [PR #56](https://github.com/AbdelStark/hallmark/pull/56) merged W04 as
`f456b4a749d795f2f22f19e5d2ae5fd90b099539`; issue #5 closed. All six exact-head
PR and [merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39409355612)
passed. The repository remained public.

## 2026-10-20: W05 policies and caller request expectations

Hypothesis: strict policy/request records plus explicit resolved manifests and
caller expectations can reject classifier substitution, expectation mismatches
and byte-limit violations before later binding or verification. Baseline:
`f456b4a749d795f2f22f19e5d2ae5fd90b099539`, with 261 passing model/classifier tests.
Mutable paths: the new policy module, tests, schema/vector fixtures, package check
and specification/evidence/tracker docs. Legacy datasets, evaluators, training
protocols, research hashes and the existing model/classifier modules are unchanged.
Pass criterion: all #6 schema/mutation/continuity/byte-limit cases, `make check`
and isolated distribution checks pass with no fallback to sender-supplied trust.

Saved [source/config/environment hashes and numeric results](evidence/w05-policy-requests-2026-10-20.json)
before this entry. The selected local gate passes: 95 policy/request tests and all
261 manifest regressions, 561 total tests under `make check`, and
`make package-check` including installed-wheel decoding and explicit expectation
comparison. Runs used the locked Python 3.12.12/macOS arm64 environment, one training
thread and harmless synthetic fixtures. All commands completed below 60 seconds.

Negative cases include coordinated digest/manifest reordering, duplicate kinds
with distinct identities, changed audience/nonce/interaction/model/policy,
required nullable continuity, malformed sequences/predecessors, oversize
multibyte prompts, invalid Unicode, unchecked copies and sanitized errors.
Exact UTF-8 is preserved, and repeated checks perform no I/O or nonce consumption.
The fixed vector's nonce and interaction bytes are public test values.

[Decision 0007](../docs/decisions/0007-policy-request-contracts.md) records the
versioned external expectation, classifier resolution and comparison boundaries.
`inj.direct/1` remains a proposal until owner/relying-party admission. These checks
do not authenticate enrollment, prove freshness or history, execute classifiers,
or verify hardware/proofs. No data/model download or policy adoption occurred.
Exact-head hosted checks must pass before integration; W02 / #3 is next.

Delivery: [PR #57](https://github.com/AbdelStark/hallmark/pull/57) merged W05 as
`1d344d55b44efae9b0232c46d4553dfe59f49288`; issue #6 closed. All six exact-head
PR and [merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39411367808)
passed. #3, #7 and #9 were unblocked after checking their live prerequisites.
The repository remained public.

## 2026-10-20: W02 exact transcript and input openings

Hypothesis: the specified transcript/context/input preimages bind exact roles,
caller expectations and every original input unit, reproducibly across two
language implementations without hardware. Baseline:
`1d344d55b44efae9b0232c46d4553dfe59f49288`, with 203 passing wire/policy tests.
Mutable paths: a separate opening module, tests, schema/vector fixtures,
JavaScript vector checker, package checks and specification/evidence/tracker docs.
Pass criterion: all field, Unicode, salt, nonce and late-unit mutations change
the corresponding identity or fail, both encoders match fixed vectors, and
`make check`/`make package-check` pass. Legacy hashes and experiments stay unchanged.

The first empty-opening fixture matched a literal CBOR preimage. Saved
[source/config/environment hashes and numeric results](evidence/w02-openings-2026-10-20.json)
before this entry. All 69 opening tests and 203 wire/policy regressions pass;
`make check` passes 630 tests and static/doc checks. `make package-check` passes
isolated installed-wheel transcript/context/byte-input reconstruction.
Commands completed below 60 seconds in the locked Python 3.12.12/macOS arm64
environment with one training thread; no data/model/backend was downloaded.

Node v24.18.0, already installed, ran the separate JavaScript CBOR/hash checker
using standard libraries only. It agrees on seven transcript/context and 13 input
vectors, including U64 IDs stored as decimal strings to preserve exactness.
Changing the final token without updating its committed preimage correctly
causes an assertion failure; its output hash is retained as an expected negative
result. This is a separately written implementation by the same contributor,
not independent reviewer or full verifier acceptance. Node is optional developer
tooling and was not added to package dependencies or mandatory CI.

[Decision 0008](../docs/decisions/0008-transcript-input-openings.md) specifies raw
UTF-8 role preimages, caller-bound context, per-classifier salts, limits, opening
privacy and the incompatible v0/v1 formats. Byte input is derived from the whole
prompt; token input requires independently computed original units and an explicit
vocabulary bound. The helper validates integer ranges and hashes all supplied
units, but cannot authenticate a tokenizer or prove text-to-token correspondence.
Chunk execution, complete circuit coverage, enrollment, real proofs/hardware and
independent verification remain separate gates. Synthetic salts are public test
values. Exact-head hosted checks are next, then #7 receipt contracts.

Delivery: [PR #58](https://github.com/AbdelStark/hallmark/pull/58) merged W02 as
`fbd6c90f65e5e535f8dfb839012f1bd3bd544097`; issue #3 closed. All six exact-head
PR and [merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39412814966)
passed. #12 was unblocked after checking its live prerequisites; #11 still needs
#14 policy/data/resource admission. The repository remained public.

## 2026-10-20: W06 receipt, epoch and proof-container contracts

Hypothesis: strict immutable containers and explicit declared-binding checks can
reject malformed layouts, classifier substitutions, interval mismatches and field
aliases without pretending to verify their evidence. Baseline:
`fbd6c90f65e5e535f8dfb839012f1bd3bd544097`, with 164 passing policy/opening tests.
Mutable paths: a separate receipt module, tests, schema/layout/vector fixtures,
package checks and specification/evidence/tracker docs. Pass criterion: #7's
structural, time, identity, packing and size failures are rejected, golden fields
round-trip, and `make check`/`make package-check` pass without an acceptance stub.
Legacy identities, evaluators and experiment protocols stay unchanged.

The smallest fixture matched the exact 100-element layout and minimum signed
threshold offset. Saved
[source/config/environment hashes and numeric results](evidence/w06-receipt-contracts-2026-10-20.json)
before this entry. All 145 receipt-contract tests and 164 policy/opening regressions
pass; `make check` passes 775 tests and static/doc gates. `make package-check`
passes installed-wheel record decoding, declared reference/time checks, signature
message reconstruction and signed-threshold unpacking. Runs used locked
Python 3.12.12/macOS arm64, one training thread and commands below 60 seconds.
No model, dataset, hardware host or cryptographic/proof library was downloaded.

Cases cover missing/extra/reordered classifiers, duplicate identities, exact
profile chunk counts, every public-input position, negative/overflow/boolean field
aliases, signed int32 extrema, external expectation mutations, continuity,
one-hour epochs, issuance/future/expiry boundaries, signature/key sizes, opaque
payload caps, immutable copies and sanitized failures. Five schema snapshots plus
the field-layout file are shipped. Synthetic proof/signature/quote payloads are
labeled unverified and there is no verifier or accepted/verified result.

[Decision 0009](../docs/decisions/0009-receipt-evidence-contracts.md) fixes the
record IDs, complete epoch identity versus quote challenge, exact signature
message, 16 MiB per-payload caps and explicit caller-clock/reference boundaries.
Actual Ed25519 encoding/signature checks, attestation/collateral validity,
independently enrolled proof verification, complete circuit coverage and policy/data
admission remain required. Structural success does not establish any of them.
Exact-head hosted checks are next, then #9 external enrollment; reassess #8 and #12
against their actual dependencies.

## 2026-10-20: W08 external registry enrollment and atomic checkpoints

Hypothesis: mandatory external trust and a retained checkpoint, complete signed
successor links and a transactional compare-and-swap update can reject rollback
and substituted identities without losing the prior trusted state on failure.
Baseline: `774887d0e40b82459d4f7ca8657400d9905577ad`, with 240 passing receipt/policy
tests. Mutable paths: enrollment and checkpoint-store modules, signature dependency
pin/lock, focused tests, schema/signed fixtures, package checks and relevant
specification/evidence/tracker docs. Pass criterion: #9's trust, history, freshness,
rollback and write-failure cases reject; offline local and package gates pass.

The smallest signed fixture round-tripped under cryptography 50.0.2 / OpenSSL 4.0.3.
The [dependency review](evidence/w08-dependency-review-2026-10-20.json) recorded exact
versions, distributions/hashes, published licence metadata and primary security
sources before installation; the final lock's new hashes match that inventory.
No operational roots were created. Ed25519 verification is necessary for W08's
history gate; W09 retains authoring, retained snapshot contents and key transitions.

Saved [source/config/environment hashes and numeric results](evidence/w08-enrollment-2026-10-20.json)
before this entry. All 88 enrollment tests and 240 receipt/policy regressions pass.
`make check` passes 863 tests and static/doc gates; `make package-check` passes
isolated installed-wheel signature verification, external-state provisioning and
committed-state readback. The first full check failed on one overlong package-check
source string; its failed result is preserved and the final gate passed after
splitting that literal. Commands used one training thread and stayed below 60 s.

Tests include equal-sequence different-digest rejection, skipped/reordered history,
invalid intermediate signatures, threshold/duplicate/unknown signers, signature
malleation and domain substitution, strict clocks, age/expiry boundaries, retirement,
external allowlist intersection, history byte/nesting/deadline bounds, stale writers,
concurrent locks, rejected writes, deferred-constraint commit failure, silent update
suppression and process exit before commit. Stored checkpoints remain unchanged
in the tested failure cases. Four schemas and a fixed signed corpus are shipped.

[Decision 0010](../docs/decisions/0010-external-enrollment.md) documents caller-controlled
provisioning, trust identity, chain semantics, process-local enrollment, retirement
and SQLite/POSIX assumptions. Physical power loss, whole-store rollback, malicious
OS-account changes and global equivocation prevention are not established. Process
termination/RSS enforcement, operational root custody, receipt/hardware/proof
verification and policy/data admission remain separate gates. No model/data
retrieval, external inference, GPU or paid compute occurred.

W06's final head `2fb4bf170503bc7bc4bea4b1c155bdc5fd0e51da` was merged in
[PR #59](https://github.com/AbdelStark/hallmark/pull/59). All six
[merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39414504221)
passed on this turn's baseline. W08 exact-head hosted checks are next, then #8,
#10 and #12 according to actual prerequisites. The work map now mirrors #8's
necessary #9 dependency, for 105 edges; the original publication audit is unchanged.

## 2026-10-20: W07 offline bundle, response and reported-result contracts

Hypothesis: strict bounded containers can reject malformed embedded files,
incomplete or inconsistent declarations, private protocol records and contradictory
collection/claim reports without turning parsing into evidence verification.
Baseline: `866d36a69762104847f1ded8253829a4e11dd786`, with 233 passing receipt and
enrollment tests. Mutable paths: one bundle-contract module, focused tests,
schemas/vectors, package checks and relevant spec/evidence/tracker docs.
Pass criterion: #8's path/file/proof/privacy and status cases reject, total/caller
limits hold, and `make check`/`make package-check` pass. Existing identities,
evaluators and research protocols remain unchanged.

The smallest fixture round-tripped a 3,998-byte structural bundle; its receipt,
hardware and proof bytes remained unverified. Saved
[source/config/environment hashes and numeric results](evidence/w07-bundle-contracts-2026-10-20.json)
before this entry. All 91 bundle/result tests and 233 receipt/enrollment regressions
pass. `make check` passes 954 tests and static/doc gates. `make package-check`
passes decoding/re-encoding all 17 structural/report examples and bounded bundle
parsing from the installed wheel. Four schema snapshots are frozen. Targeted lint
initially found an unused test import and an overlong package-check literal;
both were fixed before the recorded final gates. Commands used one training
thread and stayed below 60 seconds.

Cases include traversal/locators, duplicate or unsorted paths, exact sizes/hashes,
missing/mismatched collateral, three ordered proof declarations, receipt/epoch
links, caller depth/byte/per-proof caps, total container overhead, missing/extra
fields, canonical private records disguised as files, response/opening binding,
UTF-8 boundaries, blocked/failed/expired payload omission, collection status/error
coherence, claim strengths, residuals/assumptions, pending versus rejected proofs,
policy block and external required-claim checks. A parsing test replaces file
opening, socket creation and registry verification with failure guards. Malformed
copies are revalidated before use; private payloads are omitted from repr/errors.

[Decision 0011](../docs/decisions/0011-offline-bundle-contracts.md) records canonical
wire limits, separate opening exchange and the boundary between reported claims
and an actual verifier. Canonical embedded opening/response records are rejected;
arbitrary opaque or differently encoded bytes still need an admitted artifact
inventory. No signatures, hardware or proofs become accepted through parsing.
Full artifact closure, release persistence/recovery, worker time/RSS enforcement,
operational enrollment and independent verification remain downstream gates.
No new dependency, data/model retrieval, external inference, hardware host, GPU
job or paid compute was used.

W08 was merged in [PR #60](https://github.com/AbdelStark/hallmark/pull/60) at
`866d36a69762104847f1ded8253829a4e11dd786`, with all six
[merge-commit jobs](https://github.com/AbdelStark/hallmark/actions/runs/39416596651)
passing. W07 now explicitly depends on completed W02 for its private opening type;
source and live #8/#3 dependency records agree. The 106-edge work graph is acyclic;
the original 102-edge publication audit is unchanged. W07 exact-head hosted checks
are next, followed by #10 and #12 according to actual prerequisites.

## 2026-10-20: W09 registry authoring, rotation and offline checking

Hypothesis: explicit dual-threshold transitions, immutable complete authoring
history and atomic checkpoint/trust updates can reject one-sided rotation,
retirement reversal and retired-policy reuse while preserving prior state on
write failures. Baseline: `302a861043636094295c4dc06832e4a8c06afe87`, with 140
passing enrollment/privacy tests. Mutable paths: registry authoring/history/CLI,
the shared signature checker and checkpoint store, focused tests, schemas/vectors,
package checks and relevant spec/evidence/tracker docs. Pass criterion: #10's
signer, transition, retirement and persistence cases reject; offline local and
installed-package gates pass. Prior protocols/evaluators and results are unchanged.

The smallest fixture passed one-key-per-side rotation at sequence 1 with a
664-byte signed transition. The committed corpus exercises two-key thresholds
with one shared key and separate old/new role messages. Stored
[source/config/environment hashes and numeric results](evidence/w09-registry-rotation-2026-10-20.json)
before this entry: 97 new tests, 237 focused tests, 1,051 total tests through
`make check`, and a passing `make package-check`. The installed-wheel check retains
old/new snapshots and transition bytes, invokes the actual registry-check CLI,
reads back the committed state and rejects a replay. All commands used one
training thread and stayed below 60 seconds.

Tests cover duplicate/unknown/insufficient signers; old-only/new-only, swapped and
wrong-domain signatures; shared-key role reuse; complete trust/activation/reason/
review binding; immutable prior metadata; missing/expired/retired entries;
retirement reversal; stale policy reuse; malformed records and constructor
bypasses; byte/time limits; unsafe paths/FIFOs; private CLI failures; stale writers,
locks, suppressed/failed writes, failed commits and process exit before commit.
The two stores preserve their prior records and trust binding in tested failures.
Two schemas and one exact signed rotation corpus are committed.

Review found that sequence/digest-only checkpoints could permit later reuse of
the old policy. The store now records external trust on first successful
enrollment and changes that binding only with a dual-authorized rotation, in the
same transaction as checkpoint state. An unrelated policy change requires owner
re-enrollment. Early lint/type checks found line lengths, import order and one
digest annotation; these were fixed before the recorded final gates.
Final migration review added an atomic HMR1-to-HMR2 application-ID upgrade so
older readers cannot ignore the trust binding. Executing the actual W08 reader
confirmed it accepts the unbound checkpoint and rejects the upgraded checkpoint;
the current reader accepts the committed result. Missing trust in HMR2 fails closed.
The full local and installed-package gates were rerun on the corrected source.

[Decision 0012](../docs/decisions/0012-registry-authoring-rotation.md) fixes signature
role tags, activation, irreversible retirement, append-only local history, lazy
checkpoint-format extension and the CLI boundary. No operational key was created,
enrolled or rotated. The pinned signature implementation and its pre-install
review are unchanged; private custody approval remains absent and required before
operational roots are enrolled. The local log does not prevent split views or
whole-store rollback by the OS account. Physical power loss, independent review,
worker RSS/process isolation, genuine hardware/proofs and policy quality remain
unverified. No data/model download, external inference, GPU or paid compute occurred.

W07 was merged in [PR #61](https://github.com/AbdelStark/hallmark/pull/61) at this
turn's baseline, with all six [main jobs](https://github.com/AbdelStark/hallmark/actions/runs/39419869358)
passing. W09 exact-head hosted delivery is next. Its completion makes #34's
software corpus dependencies available; reassess that gate before #12, then
#32/#38/#39. The full MVP still requires admitted data, real classifiers, proof
and hardware integration, and independent verification.

## 2026-10-20 — W33 frozen component conformance

Hypothesis: a caller-pinned corpus can compare exact component outcomes and
detect wrong expectations while preserving every unavailable genuine-evidence
obligation. Baseline: `9357288387bfbcdf0ad28ae34f54b37fe70a1333`, with 205 parser/
registry tests passing. Mutable paths were the corpus contracts/adapters, builder,
runner, schema snapshots, tests/vectors, package/Make checks and their documentation.
Pass criterion: every executable vector matches, a deliberately wrong expectation
fails, full scope rejects required unavailable evidence, and local/package gates
pass without treating the primary implementation as independent.

Saved [source/config/environment hashes and numeric results](evidence/w33-conformance-2026-10-20.json)
before this entry. The frozen identity is
`febda826f0d2cb8c195c8637014f8ca1f5f017cfea709030ca5fbe76d5a9093e`.
There are 188 cases: 156 component matches, zero mismatches and 32 unavailable
real-proof/hardware/hybrid obligations. All 15 original PRD cheats and all 19
error codes remain mapped. The builder reproduces every frozen byte using the
frozen source snapshots and refuses an existing destination.

The first builder candidate failed on an incorrect fixture key. The second
expected a profile's inclusive 32,768-byte limit to reject; the implementation
correctly accepted it, producing one mismatch and exit 1. Preserved both failed
directories. A new candidate added separate exact-limit, max-plus-one and complete
tail cases. Expected values were not copied from runner output.

All 46 harness tests and 205 parser/registry regressions passed. `make check`
passed 1,097 tests, lint, format, typing, documentation links and the software
conformance self-tests. `make package-check` passed with all pinned corpus files
in the sdist and both runner scopes against the installed wheel. Software scope
exits 0; full-evidence scope exits 3 with all 32 unavailable cases retained. The
wrong-expectation self-test requires exactly one mismatch/exit 1. Tests reject
wrong pins, changed files, unsafe paths, invalid ancestry, missing contexts and
falsified report counts. Unexpected implementation exceptions abort the run.

[Decision 0013](../docs/decisions/0013-frozen-conformance-corpus.md) defines the
source snapshots, raw request hash, typed corpus identity, component-only accepted
flag, bounds and immutable migration. Every executed case reports both claims
not accepted. Full graph arithmetic, actual evidence, independent implementation/
review, operational trust and policy quality remain absent. No private transcript,
operational key, data/model download, external inference or paid run was introduced.

W09 was merged in [PR #62](https://github.com/AbdelStark/hallmark/pull/62), with all
six [main jobs](https://github.com/AbdelStark/hallmark/actions/runs/39422275382) passing.
W33 exact-head hosted delivery is next. #35/#36 still require the complete verifier
and genuine evidence work. After delivery, reassess #12 before #32/#38/#39.

## 2026-10-20 — W11 exact native integer MLP

Hypothesis: a bounded byte-count MLP can bind complete exports, agree with a
separate formula at every layer and reject int32 overflow before rescaling while
preserving complete prompt coverage. Baseline:
`89de51b49cfbf10040384967b289a32b9709cb02`, with 248 classifier/opening/conformance
tests passing. Mutable paths were the new runtime/export records, fixed vectors,
builder/checker, schemas, tests, package check and associated documentation.
The pass criterion was exact layer agreement plus negative identity, shape,
range, padding, overflow and resource tests, followed by full local/package gates.

Saved [source/config/environment hashes and raw numeric results](evidence/w11-integer-mlp-2026-10-20.json)
before this entry. All nine fixed vectors matched. Sixty cases with seed 20261020
compare every count, accumulator, rescaled hidden value, ReLU value and score
against direct per-byte sums and signed quotient/remainder rounding. The primary
runtime uses count-vector dot products and the existing exact Fraction rescaler.
This is a separate formula check with shared repository provenance, not W34
independence or a proof of execution.

All 75 runtime tests and 248 regressions passed. Coverage includes both int8
extrema, int32 endpoints, positive/negative halfway ties, threshold equality,
empty input, actual NUL versus padding, split UTF-8, a late positive chunk,
complete 32,768-byte input, raw accumulator overflow/underflow hidden by rescaling,
cancelling-prefix overflow and execution caps. The smallest empty-input case
returned one zero-count chunk with native score zero and no evidence claim.

A new negative test reproduced acceptance of a weight path colliding with an
operator path. Preserved the failed output and source hash; added a pre-execution
rejection. No file was read through that path, but accepting an ambiguous export
would have left its file inventory inconsistent. The final full gate passed
1,172 tests, lint, format, typing, documentation links and unchanged W33 software
conformance. Isolated installed-wheel validation matched all nine MLP vectors.
The three schema snapshots and the deterministic fixture rebuild also passed.

[Decision 0014](../docs/decisions/0014-integer-mlp-runtime.md) fixes export identity,
raw weight-file hashing, the three-node numerical profile, bias-first int32
accumulation and exact rescaling. It caps weights at 65,536 bytes, execution at
1,024 chunks and 2,097,152 products. Over-budget input is rejected without a
partial result; these caps are not worker isolation or measured performance.
Diagnostic traces disclose counts/activations on serialization and belong on
private authorized channels. Native verdicts establish neither policy quality nor
hardware/proof acceptance. No training, calibration, model/data download, external
inference, GPU or paid run occurred. Prior identities and the frozen W33 corpus
remain unchanged, including its 32 unavailable genuine-evidence obligations.

W33 was merged in [PR #63](https://github.com/AbdelStark/hallmark/pull/63), with all
six [main jobs](https://github.com/AbdelStark/hallmark/actions/runs/39425868492) passing.
W11 exact-head hosted delivery is next; its dependents still need admitted data,
qualified proving or the other native/hardware components. Reassess #32, then
#38/#39. The full MVP remains incomplete.

## 2026-10-20 — W31 bounded private event attempts

Hypothesis: a private bounded event log can retain failures and reject invalid
metadata, duplicate ordinals, concurrent writers and uncertain writes without
promoting a completed stage into a completed attempt. Baseline:
`e8c9d0be603d477e3861b6843538477974b97354`; all 55 error-privacy/pipeline tests
passed. Mutable paths were the new writer/reader, schemas, event tests, installed
fixture/package checks and their documentation. The pass criterion was the
smallest complete stage fixture plus negative privacy, sequence, concurrency,
resource and durable-write tests, followed by `make check` and `make package-check`.

Saved [source/config/environment hashes and raw numeric results](evidence/w31-private-events-2026-10-20.json)
before this entry. The first privacy test exposed unsuppressed Python exception
chaining in generator context managers: nine sentinel cases failed. The output
and source hashes were retained; final exceptions suppress external chains and
the tests check both serialized files and formatted exception output. An
intermediate fixture test also failed because `scripts` was not importable as
a package. It now executes the actual fixture with a bounded subprocess.

All 101 new tests and 55 regressions passed. The complete local gate passed
1,273 tests, lint, formatting, typing, documentation links and the unchanged
156-case W33 software conformance scope. The isolated installed wheel retained
one failed attempt and one explicit successful retry across six events. Three
schema snapshots matched their runtime definitions. No training, model/data
retrieval, external inference, GPU or paid execution occurred.

Failure tests cover all nine sync points, failed/short/zero writes, publication
failure, byte/event caps, malformed metadata, duplicate/gap ordinals and mismatched
receipt hashes. Four subprocess exits preserve incomplete attempts, including a
retry interrupted before its first stage. Separate processes, a thread and a
fork cannot reuse a live writer. Unsafe modes, symlinks, hardlinks, FIFOs and
unexpected directory entries reject. Durations use a controlled monotonic clock;
negative or out-of-U64 values fail. This is correctness testing, not timing data
for a full-path performance claim.

[Decision 0015](../docs/decisions/0015-private-event-storage.md) fixes the private
storage protocol and bounds. Failures remain local and metadata has the run's
access/retention policy; there is no hosted telemetry or automatic cleanup. The
reader cannot authenticate history or prove that a supplied UUID was random.
Physical power loss, network filesystems and compound storage failures preventing
both failure-marker retention and receipt removal remain unqualified. Quarantine
ambiguous archives. Legacy manifests/results and the frozen W33 corpus are unchanged.

W11 was merged in [PR #64](https://github.com/AbdelStark/hallmark/pull/64), with all
six [main jobs](https://github.com/AbdelStark/hallmark/actions/runs/39428839904) passing.
W31 exact-head hosted delivery is next. W32 still requires #14 policy/resource
admission and #19 proof qualification, in addition to this storage foundation.
Reassess #38 packaging and #39 traceability next; the full MVP remains incomplete.

## 2026-10-20 — W37 reproducible packages and installed inventories

Hypothesis: a reviewed source snapshot and fully pinned build environment can
produce identical wheel/sdist bytes, rebuild the same wheel from the sdist and
execute installed core/train contracts while rejecting inventory defects.
Baseline: `5e23f44ca51a58760ff1c139c114b7db52c5c1c5`. A fresh baseline build
passed and reported Hatchling 1.32.4, but the backend constraint and transitive
build selections were not all exact. The existing package gate installed core
only and checked selected archive filenames. Mutable paths were packaging
configuration/scripts, CI, tests, inventory/licence evidence and related docs.
The criterion was repeated byte equality under fixed inputs, exact safe archive
inventories, real installed core/train checks, negative fixtures and full gates.

Saved [source/environment hashes and raw numeric results](evidence/w37-reproducible-packages-2026-10-20.json)
before this prose. All 58 new packaging tests and 16 training-gate regressions
passed; the full gate passed 1,331 tests, lint, formatting, typing, docs and the
unchanged 156-case W33 software conformance scope. `make package-check` passed
in 5.036 seconds and `make package-check-train` in 23.968 seconds on the recorded
local environment. These are command validation durations, not system performance
measurements. Each gate compares two builds and a wheel rebuilt from the sdist.

The two gates used source snapshot
`73bbb8673857df59505fa944e0108f1505971204b2d1aec301d70c4fb445039b`,
with the same wheel SHA-256
`72c410bd17cc6075b6732b3f4399f10d0501c47430bef6e43abc9e04ba18ab3b`
and sdist SHA-256
`cf843cf16470b5baf2f07b9eff939324d87f86e519eb77e1adc0c8de6571bd19`.
This is the captured candidate before this evidence/ledger entry; final-commit
CI rebuilds and records its own source/artifact identities. It is not a release
manifest. The six-package build environment and installed 10-package core and
17-package train environments include exact selected archive and notice hashes.
Core confirms scikit-learn is absent; train has no skip path and checks fit,
caller-pinned replay and altered-result rejection from the extracted sdist.

The first stricter archive check failed because Hatch included a parent
`.gitignore` in the sdist. That directory and its hashes/logs remain retained.
Empty VCS boundaries now stop ancestor exclusion discovery. A separate first
installed-train attempt exceeded 20 seconds and remains retained; an unchanged
diagnostic rerun passed. The final 45-second fixture timeout is within the existing
60-second per-command budget. Negative tests cover malformed/duplicate/traversal
members, links/nonregular files, size caps, source aliases, credentials, wheel
RECORDs, missing/extra files, unequal hashes and stale build/dependency review pins.

The [dependency metadata review](evidence/w37-dependencies-2026-10-20.json)
matched all 518 locked artifact hashes for 32 packages against version-specific
PyPI metadata. `mypy-extensions` lacked licence fields; its locked universal wheel
was hash-verified and its MIT notice recorded. This is provenance and licence
inventory, not a legal opinion, vulnerability audit or release approval. Full
binary-wheel and bundled-component notices remain required for redistribution.

[Decision 0016](../docs/decisions/0016-reproducible-packaging.md) fixes the gate;
[PACKAGING](../docs/PACKAGING.md) gives commands and limits. Each invocation retains
fresh private local outputs, including failures. Recognizable credential patterns
are not a universal confidentiality detector. Build equality is scoped to recorded
environments, not arbitrary OS/Python combinations or an immutable OS image.
The repository stays public; `LicenseRef-Proprietary` and unpublished package
status remain. Legacy runtimes, fixture identities and the frozen corpus are unchanged.

W31 was merged in [PR #65](https://github.com/AbdelStark/hallmark/pull/65), with all
six [main jobs](https://github.com/AbdelStark/hallmark/actions/runs/39432180583) passing.
W37 exact-head hosted delivery on the expanded Linux/macOS matrix is next, then
#39 spec traceability. Admission, real proof/hardware evidence, independent review
and the complete MVP remain outstanding.

### W37 hosted portability correction

Initial [push CI](https://github.com/AbdelStark/hallmark/actions/runs/39436507423)
and [PR CI](https://github.com/AbdelStark/hallmark/actions/runs/39436633372) failed
on `e36e70f89a7b8827b9795c957eda0b02286b2ba5`; the matrix cancelled remaining
jobs after failures. Linux rejected valid source reads because complete stat-record
comparison included access time. This is a failed hosted result, not a passed
platform qualification.

A local regression reproduced the problem: one access-time-only case failed while
seven identity/modification cases correctly rejected. Saved the failure/source/log
hashes and [corrected validation](evidence/w37-source-snapshot-fix-2026-10-20.json)
before this entry. The guard now ignores access time and still compares device,
inode, mode, links, uid/gid, size, mtime and ctime. All eight cases pass.

The corrected local gate passed 66 packaging tests, 82 focused tests and 1,339
total tests, plus unchanged lint/type/docs/conformance checks. Both package gates
passed again with identical repeated artifacts and sdist wheel rebuilds. The
corrected candidate source is
`7a0ed2baa6c932cfd45668459dbd35793f99bd5df64a7a83d9e79246f1121743`;
its wheel hash is unchanged and its sdist hash is
`c2dce2adb0810d81ab3ab86349cecaad55d35a02a81172cea1778f0d0a07a6d1`.
These candidate IDs precede this follow-up record/prose. The original evidence
and failed runs are preserved. Corrected exact-head Linux/macOS checks remain
the next delivery gate; no platform success is inferred from local validation.


## 2026-10-20 — W38 specification traceability

Selected #39 after W37 delivery. Hypothesis: a bounded offline gate can reject
missing requirements, broken anchors and orphan issue mappings while preserving
the historical packet; an explicit live query can establish current work/issue
metadata agreement without giving normal CI network access. Mutable paths were
scripts, focused tests, Makefile, the coverage register and maintainer docs.
No runtime, fixture, model/data, conformance or old-evidence files changed.

The [raw evidence](evidence/w38-spec-traceability-2026-10-20.json) was saved before
this entry. Against base `56b53f42cdc25f7690b6e8d1ed95a4e87b1e0bfb`,
`make check-spec` exited 2 because the target was absent; the old doc checker
accepted a fixture with a missing same-file fragment. The new isolated tests
reject that fragment and missing/orphan requirement rows, issue mappings, cycles,
tracker drift, unknown coverage owners, malformed RFC sections/questions and
historical source changes. Fake API failures retain a failed result without raw
provider output, and a pre-existing result is preserved before any network call.

Focused validation passed 54 tests (53 new); `make check` passed 1,392 tests,
lock/lint/format/type checks, all local links and the frozen software corpus.
The spec gate covers 51 sections, 18 invariants, 40 work IDs, 10 RFCs and 106 edges.
Both `make package-check` and `make package-check-train` passed, including spec
validation from the extracted sdist and the existing installed contracts. The
candidate source ID is `a0041cb17d54d01f6062520e372f3ecb65464a1681560da09d5cca5a4b2f5d41`;
wheel SHA-256 is `da20dbc02441fd0746687ff627669298ae8fb252f0b87302e9ab34b71384b2e1`,
sdist SHA-256 is `4721e28e46276f1e8c0733678982bdcd50c933c646270a7f83ad3572a761456d`.
The hashes identify the candidate before evidence/prose; final-commit CI rebuilds it.

The [live audit](evidence/w38-live-issues-2026-10-20.json), produced by
`uv run --locked python scripts/check_spec.py --live --output research/evidence/w38-live-issues-2026-10-20.json`,
matched all 50 work/tracker issues: actual titles, scopes, acceptance criteria,
labels, milestones, forward dependency edges and tracker children. It records
observation time, source/response/body hashes and issue states. It is a dated
observation, not a permanent GitHub guarantee. The earlier successful live audit
remains local; no failed scientific or hosted outcome is hidden by these checks.

[Decision 0017](../docs/decisions/0017-spec-traceability.md) defines the limits.
The checker supports the documented repository Markdown forms; structural coverage
cannot establish that an implementation satisfies the requirement's meaning.
Owner questions remain open and all RFCs remain Draft. Public visibility persists;
licensing, data/policy admission, hardware/proofs and independent review remain separate.

W37's [main CI](https://github.com/AbdelStark/hallmark/actions/runs/39437824044)
passed all 12 jobs after [PR #66](https://github.com/AbdelStark/hallmark/pull/66).
W38 exact-head hosted delivery is next. Afterward reassess the full remaining
backlog; the broader MVP is not complete merely because its local foundation is green.


### W38 parser review correction and final local candidate

Review found nested repetition in the new Markdown target regex. An isolated
10,014-byte unfinished-link probe exceeded a one-second limit and was terminated;
the probe and candidate source hashes remain retained. Removing the nested
quantifier makes that input plain text without exponential backtracking. Added
a regression; [final validation](evidence/w38-final-validation-2026-10-20.json)
records 55 focused tests (54 new), 1,393 total tests and both package gates passing.
The prior candidate evidence above is preserved.

The final candidate source is
`f29c9340099fa787e7f8380888f33d0e738b3e54f9af1a392ab524040188a458`;
its wheel hash is unchanged and its sdist hash is
`0f141689018b583aa8487cfc2b508f61955e1f65285a24432e920c3f614ca46b`.
These identities precede this follow-up record/prose. A fresh explicit live audit
matched exactly the original 50-issue metadata inventory and response hash;
the follow-up records its own time and source hashes. Hosted final-head validation
is still required before merge. No historical packet, corpus or prior run changed.

### W38 delivered

[PR #67](https://github.com/AbdelStark/hallmark/pull/67) merged as
`1da52da9c5f45b481d031ab3dd1ec5b4601c7a6d`. Push run `39440344222`,
PR run `39440355607` and [main run `39440839286`](https://github.com/AbdelStark/hallmark/actions/runs/39440839286)
each passed all 12 jobs. Issue #39 is closed; the release tracker remains open.

## 2026-10-20 — W13 admission preparation, approval outstanding

Selected the explicitly permitted proposal portion of #14. Hypothesis: strict
study terms and a caller-pinned review dossier can reject missing/changed
declarations while a separate concrete proposal preserves every unresolved owner
decision. Baseline is W38's 1,393 passing tests. Mutable paths are the new admission
module, fixtures/schemas/tests, package/check entry points, proposal and related
maintainer documentation. No data/model asset, historical experiment or frozen
conformance corpus changed.

The [raw validation record](evidence/w13-admission-preparation-2026-10-20.json)
was saved before this entry. `uv run --locked pytest tests/test_admission.py -q`
passed 81 tests; `make check` passed 1,474 tests plus lock/lint/format/types,
spec traceability, the existing software corpus and the new admission fixture.
The builder reproduced the fixture and three schemas byte for byte in a fresh
directory. Negatives cover absent/wrong external pins, mutated nested terms,
missing role/source/code/config documents, exact file inventories, invalid caps,
ambiguous decimals, unsafe constructed records and the actual unapproved proposal.

The initial `make package-check` failed: its tracked-only source snapshot omitted
new unstaged files, and extracted-sdist link validation rejected the missing
proposal/decision. Diagnostics remain in `dist/package-check-tfkme4t0`; the evidence
retains the failed command and output hash. Staging the reviewed new paths fixed
the candidate inventory without changing the gate. Both `make package-check` and
`make package-check-train` then passed, including repeated build equality, fresh
installed core admission checks and installed synthetic training/replay negatives.
Their source ID is `9518789db603e79363316833eadcbe686201b65ffd535e65ffa453568dc20392`;
wheel hash `d8d481d1eacefeb8d6f9ee92eb3134d92ac2e5265874638aae95d2be76876cde`,
sdist hash `ad5fa5b0da0785892da8df7ebeecca57af040e64120be568074391aab4ac1fe7`.
These identify the candidate before this evidence/prose; final-commit CI rebuilds.

The [public metadata record](evidence/w13-public-metadata-2026-10-20.json) retains
exact metadata/card/config/notice hashes and advertised asset inventories. No
dataset, checkpoint or tokenizer asset was downloaded. Public dataset previews
were exposed during page inspection, so the proposed source is exploratory,
not blind confirmatory evidence. Licence metadata conflicts, provenance, source
overlap and all access approvals remain holds. No upstream performance claim was
adopted. The [power calculation](evidence/w13-power-scenarios-2026-10-20.json)
records source/environment and conditional binomial results, including 299-group
zero-event power; it is not an approved sampling or quality plan.

[Decision 0018](../docs/decisions/0018-admission-proposal.md) proposes a pre-training
StudyPolicy and acyclic review terms. The check compares exact declarations;
it does not authenticate reviewers, verify actual assets, enforce resource limits
or establish scientific/legal adequacy. The marker fixture explicitly grants no
measurement authority. [The actual proposal](proposals/inj-direct-v1/README.md)
retains null quality/power/budget and reviewer choices. W13 remains open and
blocked for owner/relying-party review; a draft PR is the next delivery step.
No prior research result is reused and no full MVP, hardware or proof claim is made.

### W13 preparation delivered

[PR #68](https://github.com/AbdelStark/hallmark/pull/68) merged as
`346f9bcc1940985c90053a719eb2ed4fea4671b6`. Push run `39444024829`, PR run
`39444100293` and [main run `39452888007`](https://github.com/AbdelStark/hallmark/actions/runs/39452888007)
each passed all 12 jobs. This delivery did not itself adopt the study.

## 2026-10-20 — W13 owner approval and delegated study design

The owner approved the English single-turn study and its quality targets, acting
as prototype decision owner; delegated evaluation design and licence-reviewed
public source/software selection; approved the local four-thread/16-GiB/20-GiB,
two-hour/job, six-hour/$0 envelope; and authorized conditional HF GPU Jobs,
preferring the Mac. The owner requested hardware/reviewer options only.
[Decision 0019](../docs/decisions/0019-approved-study-scope.md) normalizes this
authority without publishing a private transcript or credential.

Hypothesis: the current authority and proposal can agree on the approved scope
without admitting unresolved sources or an incomplete measurement dossier.
Baseline: 1,474 tests at the PR #68 merge. Mutable paths: authority, proposal,
agent workflow, study/resource docs, the power calculation and admission tests.
No runtime contract, marker fixture, historical experiment, dataset or model
changed. Pass criterion: coherent authority/budget/roles, reproducible power
calculation, continued refusal of the incomplete protocol, and local/package gates.

The [raw validation record](evidence/w13-study-approval-2026-10-20.json) precedes
this entry. `make check` passed 1,476 tests plus lock/lint/format/types, spec,
software conformance and admission gates. The first focused lint check caught
one overlong assertion; formatting fixed it before the passing gate.
The two new tests compare approval/budget/role records and reproduce the fixed
power script with independent exact-tail/confidence-bound cross-checks.
`make check-train` required and passed both training-marked tests.
`make package-check` passed repeated build equality, installed-wheel checks and
extracted-sdist validation. Its source ID is
`5d6697994c9f7fc4ab1c6ac43d6c88eed6caa54900bf04a14ccfe42d1c38dd26`,
wheel SHA-256 `d8d481d1eacefeb8d6f9ee92eb3134d92ac2e5265874638aae95d2be76876cde`,
sdist SHA-256 `77478a534c5dc8dc83916c0b2fb941410931168919b6789de71fb43914e92ea7`.
The wheel is unchanged; these identities precede this evidence/ledger addition.
Final-commit CI rebuilds the final source.

The [power evidence](evidence/w13-design-power-2026-10-20.json) records code and
lock hashes, environment, exact cutoffs and conditional probabilities. With 15
Bonferroni-controlled one-sided bounds and family power at least 0.90 under the
specified alternatives, the design requires 7,831 independent benign groups and
1,375 positive groups. Those are planning quantities, not measured model quality.
Unknown lineage, label audit, actual asset/split/candidate/evaluator identities
and the final enrolled review pin remain concrete measurement dependencies.

The [options evidence](evidence/w13-compute-options-2026-10-20.json) records local
hardware and unauthenticated public provider metadata, including the HF price
inventory. Reviewer-site direct HTTP attempts failed; the browser reader supplied
the cited public pages. The [options brief](proposals/inj-direct-v1/compute-and-review-options.md)
compares local/HF research, Azure/GCP genuine hardware and independent review.
No account pricing/quota/credit state was checked, no paid job launched, and no
reviewer contacted. Existing source licence holds are preserved. The old
fixture-only authority is superseded; W10 implementation can proceed.

### W13 approval delivered

[PR #69](https://github.com/AbdelStark/hallmark/pull/69) merged as
`7f547356a7f91e8d331a6963d0cf40603dd49b44`. Final head
`af14a223c1060bdbc8c21d703291478c58e5dccb` passed all 12 jobs in each of push
`39456548720` and PR `39456559150`; [main run `39457001526`](https://github.com/AbdelStark/hallmark/actions/runs/39457001526)
passed all 12 jobs on the merge. Issue #14 is closed and its approval blocker
removed. The repository remains public.

## 2026-10-20 — W10 complete-byte literal rule

Hypothesis: bounded suffix state can reproduce an independent complete-byte
literal oracle at every chunk, while exact manifests and file hashes reject
substitution. Baseline: 1,476 tests at the PR #69 merge. Mutable paths: native
rule records/runtime, fixture builder/checker, schemas, tests, package checks and
related API/decision/research documentation. Existing contracts, historical
experiments and the frozen conformance corpus are unchanged.

The [raw evidence](evidence/w10-complete-byte-rule-2026-10-20.json) precedes this
entry. `uv run --locked pytest tests/test_rule.py -q` passed 96 tests; `make check`
passed 1,572 tests plus lock/lint/format/types, spec, software conformance and
admission checks. The initial 95-test pass was extended with a regression for
short matches retained inside a longer pattern's suffix and partial UTF-8 byte
patterns; the complete gate was rerun successfully.

The independent oracle enumerates complete-input byte slices and match-ending
positions. One thousand fixed-seed generated cases compare every chunk; the
maximum-size test places a 4,096-byte pattern at the end of a 32,768-byte prompt,
using one-byte chunks. Eleven fixed vectors reproduced byte for byte in a fresh
directory. No pattern is inferred from private data or a downloaded source.
The fixture's hashed provenance identifies hand-authored harmless markers under
the repository licence; it is not an operational injection-policy approval.

[Decision 0020](../docs/decisions/0020-complete-byte-rule.md) fixes native matching,
aggregation and bounds. Provenance and parameters are byte-exact, input coverage
is complete, equality blocks and invalid/unsafe constructed records reject.
The scalar ReLU graph only projects the match feature. A proof of that graph
alone would omit the literal extractor and cross-chunk state, and cannot satisfy
W19. No learned quality, external enrollment, hardware or proof claim is made.

Both `make package-check` and `make package-check-train` passed repeated builds,
fresh installed rule vectors and the existing core/train checks. Their common
source identity is `d55ca53816123a94a81aaf92583e6c3b7831cbabcbd07937bc5b54f060800c7a`;
wheel SHA-256 `650b58c23b14374caddaa9cf8fa85d8155efd58f1c9ba5243d6f3ee854a4ce5b`,
sdist SHA-256 `e7b114c57fc297d5518fc0fe6a12df0f9674298ecdc4859cb2a13bfe3da1d75d`.
These identify the candidate before this final evidence/prose addition;
final-head hosted CI rebuilds it. The unrelated `.gitignore` edit is preserved.

Review then caught a JSON schema mismatch: the default bytes schema described
binary strings using byte lengths, but the actual JSON encoding is hex. The
pattern schema now admits exactly even-length hex through 8,192 characters.
A maximum-pattern JSON roundtrip and odd-hex rejection test bring the final
focused count to 97 and total to 1,573. The evidence preserves the earlier passes
and the new full check and both package passes. Final pre-prose source identity:
`1f4d4e8913de56fca3c3911c6322574fce372e75165618ad6edfa6110d004013`;
wheel `c71824e2fc237e9851bbbe299fe30fde5ccb3909123b80f66947ed5ad5fad402`,
sdist `78383daf2085efb9cc7d11d9238a871a2ec141f6aac40e2a2fff5f50a8c9a50d`.
Runtime/fixture wire identities remain unchanged by this schema correction.

### W10 delivered

[PR #70](https://github.com/AbdelStark/hallmark/pull/70) merged as
`fa310ea2a4d1d484f1ef325eb7bfbf5f86a280ed`. Final head
`19541ba307b456ce295545bd2740debbee69f6a1` passed all 24 push/PR jobs;
[main run 39459269341](https://github.com/AbdelStark/hallmark/actions/runs/39459269341)
passed all 12 jobs. Local, tracking and remote main matched the merge commit.
Issue #11 is closed; #15 and #19 had stale dependency blockers removed.

## 2026-10-20 — W14 source admission and lineage-first split

Hypothesis: externally pinned source/review bytes and complete connected groups
can produce reproducible frozen splits while rejecting substitutions and
cross-split descendants. Baseline: 1,573 tests at the W10 merge above.
Mutable paths: the additive import API, fixtures/checker, schemas/tests,
package inventories and related decision/API/research documentation. The
unrelated `.gitignore` edit remains unstaged.

The [raw evidence](evidence/w14-lineage-data-admission-2026-10-20.json) precedes
this entry. Initial validation passed 55 focused tests, 1,628 total tests and
both package gates. Final review removed repeated held-out-set construction
from the per-group loop and added UTF-8 byte-boundary and policy-mismatch cases.
The final focused command passed 59 tests; `make check` passed 1,632 tests plus
lock/lint/format/types, spec, software conformance and admission checks.
All recorded initial/final runs passed. Development lint/type corrections
preceded these retained runs.

Twenty-five fixed-seed parent graphs match an independently computed reachability
oracle. Split boundaries/group representatives match independent arithmetic,
and changing labels/input ordering leaves assignments unchanged. The 26-row
fixture has 21 groups: 11 train, five calibration and five test. Parents,
cross-source descendants, shared histories and identical/ASCII-equivalent prompts
stay together; contrasting labels remain separate records. Held-out source/family
members move their complete component into the separate held-out cohort.
The fixture reproduced byte for byte in a fresh directory; all seven schemas
match their generated definitions.

Source/licence/review changes, malformed JSON/UTF-8, missing parents, cycles,
unknown labels, policy mismatches, stale near-review inventories and rehashed
split/lineage mutations reject. Four injected sync failures retain partial
output without a final manifest; existing/symlink targets cannot be overwritten.
These checks do not establish physical power-loss or hostile-parent-path safety.

Final `make package-check` and `make package-check-train` both passed repeated
distributions, sdist rebuild and installed import fixtures. Their common source
identity is `8f8a6b09485619d95ff7ad5de62b98a464c8c441b483566464de6bd67e42f4c2`;
wheel SHA-256 `f7b93027de33840ce2d0ff3e2a6eb3574053d5557ccd1abf684a4a2b2c7c14e0`,
sdist `dd608f800f8f426c033c1ae0fd92a1cd9d083a182e21c3b6e6df59816fb1f718`.
These identify the candidate before this final evidence/prose addition;
final-head hosted CI rebuilds the complete commit.

[Decision 0021](../docs/decisions/0021-lineage-data-admission.md) records limits,
exact identities, review/source-card gaps and trust boundaries. Every source
and review is synthetic; mock public-mode tests bind declarations without
authenticating a human. No real dataset, checkpoint, external inference or paid
job was used. Lexical candidates cover ASCII case/whitespace only; reviewed
semantic lineage and final measurement admission remain necessary. Historical
results and the legacy 8 MiB loader are unchanged.
