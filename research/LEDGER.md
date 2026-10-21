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

### W14 delivered

[PR #71](https://github.com/AbdelStark/hallmark/pull/71) merged as
`c4586a7107c59fb7ba4665247e73ff7e0146cf7d`. Final head
`0bc7f3c8cf4c13b11f6633ee6193a832a2f2628b` passed all 24 push/PR jobs;
[main run 39466963984](https://github.com/AbdelStark/hallmark/actions/runs/39466963984)
passed all 12 jobs. Local, tracking and remote main matched the merge commit.
Issue #15 is closed. The repository remains public.

## 2026-10-20 — W18 real local proof probes, backend still unqualified

Hypothesis: a reviewed local backend can produce genuine proofs of the exact
salted complete-input commitment and a tiny native rule while rejecting changed
public bindings and invalid witnesses. Baseline: 1,632 tests and no real proof
backend execution at the W14 merge. Mutable paths: optional Go probes, their
Python controllers, frozen harmless fixture, tests, source reviews and research
documentation. The unrelated `.gitignore` edit remains unstaged.

The [raw evidence](evidence/w18-proof-probes-2026-10-20.json), including source/
environment pins, numeric costs, failures and one public proof/key example,
precedes this entry. The
[source review](proposals/backend-v1/candidate-review.md) holds EZKL on unresolved
licence admission and chooses gnark v0.16.4 only for experiments. Fourteen
compiled modules match the reviewed licence/version/checksum inventory.
The isolated Go 1.26.8 archive was checked against its official SHA-256;
system tools were not replaced.

Preserved preparation failures: the archive extractor initially rejected the
ordinary `go` root directory before extraction; the full upstream module graph
failed on an unavailable optional Solidity checker; two initial sandbox attempts
aborted in Apple's loader before Go ran. The corrected profile imports the OS
`dyld-support.sb`. The selected compilation closure is verified; the optional
full module graph is not. No failure was relabeled as a pass.

The original 18-case cubic probe produced a 244-byte real Groth16 proof and
verified it in fresh processes. The final binary and tightened worker profile
repeated all 18 cases successfully in a new directory. Wrong inputs/keys,
field aliases, malformed proof bytes and invalid witnesses reject.
Randomized repeated proofs differ, which alone does not demonstrate privacy.

The first rule experiment's setup completed, but the real prover rejected the
empty input. The circuit encoded 16 for a 17-byte domain tag. Its source was
retained with every reconstructed file verified against the original pre-build
hash; setup and failure artifacts were not overwritten. It also exposed a
platform limitation: `RLIMIT_CPU=40` was requested, but setup used 97.43 CPU
seconds and the failed proof process used 58.81. The new experiment computes
the tag length, requests a documented 120-second case budget and rejects
measured CPU overages after exit. This fits the approved owner envelope;
the OS request is not claimed to be a hard aggregate CPU boundary.

The corrected experiment passed 134 cases in 321.904 seconds. Nine vectors
cover empty input, canonical CBOR's small/wide byte representations, UTF-8,
four-byte and near/maximum boundaries, cross-chunk matching and a final-byte
match. Each produced an actual proof checked in a fresh verifier process.
All 100 public-field mutations, out-of-range/alias values, changed private
inputs, nonzero padding, omitted last byte, wrong count/verdict, corrupted or
trailing proof bytes and a second setup's key reject.

The circuit has 206,801 constraints, an 18,147,793-byte R1CS, 77,729,235-byte
proving key, 5,536-byte verifier key and 292-byte proof. Valid proof processes
took 15.856–16.208 seconds and verifier processes 0.031–0.062 seconds, including
startup and artifact loading. Peak process RSS was 709,033,984 bytes; cumulative
worker CPU was 1,173.542 seconds and measured output was 1,739,947,438 bytes.
This is one diagnostic roster, not a repeated latency study, pure prover
timing, p95 estimate or full-encoder extrapolation.

Thirty-one offline tests cover file and identity boundaries, fixture reproduction,
failed-result handling, sanitized CLI failures and the Mac sandbox. The live
loopback control succeeds outside the worker and is denied inside; unrelated
file reads, inherited sentinel variables and child-process creation reject,
and a timed-out process is reaped. An initial curl control could not read its
TLS configuration; the final test uses a local TCP utility without expanding
permissions. `make check` passes 1,663 tests plus lock/lint/format/types, spec,
software conformance and admission gates.

The [decision](../docs/decisions/0022-local-proof-probes.md) bounds the claim:
synthetic classifier tags, local research setup, shared verifier library,
upstream gadget soundness warning, unqualified hiding/security, soft memory
limit and post-run aggregate resource checks. No `BackendQualification` artifact,
`hallmark qualify`, bounded MLP or complete encoder is implemented or qualified.
W18 stays open. No real dataset/model, HF token, paid job or hardware evidence
was used; local experimental assets have a 2026-11-19 retention limit without
an ongoing scheduler.

Both `make package-check` and `make package-check-train` passed repeated
distributions, sdist rebuild and installed core/train checks. Their common
pre-prose source identity is
`539d4bff99a59f56265e42b568b30a6ac55df8042708e99be24ebb87b448d36d`;
wheel SHA-256 `f7b93027de33840ce2d0ff3e2a6eb3574053d5557ccd1abf684a4a2b2c7c14e0`,
sdist `0a7e21a490fe86cf8a1745b8ce98ea8a90b4e66465d034e19e21cc210a5aff63`.
Final-head CI must rebuild the complete evidence/prose candidate. The public
synthetic key/proof example was decoded from the evidence file and verified
again in a fresh sandbox, with the key and expected fixture independently
pinned from the preceding experiment records. This checks the published
example transport; it does not establish independent implementation or enrollment.

## 2026-10-20 — W18 backend declarations and bounded MLP proof

Hypothesis: the same reviewed backend can prove the exact frozen integer MLP,
including signed ties-to-even arithmetic, all intermediate values, complete
chunk aggregation and salted input binding. Baseline: the prior tiny rule proof
and 1,663 local tests. Mutable paths: the optional Go graph probes, shared input
constraints/controller, MLP fixture, additive backend record/file validator,
distribution checks and documentation. No historical experiment is overwritten.

The [raw evidence](evidence/w18-backend-contract-and-mlp-2026-10-20.json)
retains the protocol, source/build/dependency pins, every case's costs and
artifact hashes, validation logs' hashes and a public synthetic proof/key
example. Executed helper commands and source copies remain in the ignored
run's `commands/`; portable controller invocations are documented in the
[probe README](probes/gnark/README.md).

[Decision 0023](../docs/decisions/0023-backend-declaration-contract.md) implements
the RFC-0005 `BackendQualification` record and caller-pinned dependency/metadata
file checks. The record binds opaque evidence identities, declared program
coverage and a claimed hiding flag. It does not resolve reviews, authenticate
setup, execute a verifier or establish qualification. Tests explicitly permit
a separately enrolled true declaration to pass structural binding without
mistaking it for evidence of hiding.

The new protocol and complete source snapshot were written to
`runs/w18-graphs-1792520823690561000` before compilation. The selected 14 module
versions match the previous reviewed inventory, with `GOPROXY=off` and the
unchanged isolated Go 1.26.8 toolchain. The build succeeded as
`15c749c564acd18e56870c7412f9c6fbc6c713679f34bf2fec63641c32f9e107`.
The nine-vector MLP fixture SHA-256 is
`db1e5792c87d8e66617ba39a9ecb588dcb637e885211d5f241bdaf632b51f1fd`.
The native implementation and separate arithmetic formula agree on all layers
when reproducing that fixture.

The actual MLP run passed all 156 cases in 654.918 seconds. Nine proofs verified
in fresh processes. All 100 public-field mutations, 22 private layer mutations,
invalid private inputs/padding/counts, proof corruption/trailing bytes and a
second setup's key rejected. The 208,717-constraint circuit has an
18,170,074-byte R1CS, 78,166,557-byte proving key, 5,536-byte verifier key and
292-byte proof. Peak process RSS was 704,036,864 bytes, cumulative worker CPU
2,477.395 seconds, and measured artifacts 3,867,731,554 bytes. No case exceeded
the requested measured CPU budget; the largest used 98.541 CPU seconds.

Valid proof processes took 15.824–16.092 seconds, including startup and artifact
loading; verifier processes took 0.029–0.294 seconds. Offline software/package
validation also ran on the host during part of this experiment. These costs
are a single diagnostic roster, not an isolated latency study or p95 estimate.
The shared input refactor changes circuit/key identity, so the rule regression
uses a separate fresh setup rather than reusing the earlier proof.

That regression passed all 134 cases in 320.919 seconds, with 692,666,368-byte
peak process RSS and 1,739,957,340 measured artifact bytes. The final binary
also passed all 18 cubic installation cases. The published MLP example was
decoded from the evidence and verified in another fresh process, using the
key and fixture pins retained from the original run. The confirmation took
2.005 seconds in total. Fresh processes still share the same gnark verifier;
this does not establish independent implementation or operational enrollment.

`make check` passed 1,747 tests, including 77 backend tests and 38 probe
boundary/fixture tests. Both package gates passed, including installed backend
fixture checks and the required training extra. Their common source identity
before final evidence/prose was
`7a455d4a696b47978a3fb95eaa2bb111ae140696377fd90af86632c382066831`;
wheel SHA-256 `4c79ab355f919c4bb4dd9a54bc2aebf233a06597275d68c184ae851273344d5b`,
sdist `e1855343b8b09154dd4386b713d1ce7795434bc094c9de1e20de67c5f589e014`.

[Decision 0024](../docs/decisions/0024-bounded-mlp-proof-probe.md) retains the
limits: one fixed synthetic MLP with an eight-byte input bound, local setup,
shared verifier library, upstream gadget warning and no security/hiding
qualification. No `hallmark qualify`, encoder operator block or complete
admitted encoder is supplied. The backend record and small proofs cannot
replace those remaining gates. No HF token, paid job, private input or genuine
hardware evidence was used. Repository visibility remains public.

## 2026-10-20 — W18 exhaustive integer attention block

Hypothesis: a fixed integer attention/feed-forward block can produce real proofs
that match every arithmetic-oracle tensor for every admitted input/mask pair,
while rejecting changed intermediate values. Baseline: rule/MLP proofs and
1,747 local tests, with no attention-block evidence. Mutable paths: the optional
Go block and shared process code, frozen oracle/controller, boundary tests and
research documentation. No Python runtime acceptance path or dependency changes.

The [raw evidence](evidence/w18-integer-attention-block-2026-10-20.json) precedes
this entry. [Decision 0025](../docs/decisions/0025-integer-attention-block-probe.md)
fixes the four-entry embedding vocabulary, two token positions, exact tables,
signed rounding, residual/MLP weights, masked pooling and five public fields.
The independent Python arithmetic implementation exhausts all 64 token/mask
combinations and checks masked-token invariance before proving. Two hand-derived
single-token results cover negative max pooling and signed half ties.

The pre-build protocol/source snapshot is
`runs/w18-block-1792522883989554000`. It records the prior measured intervals
(retaining nested duplication), an additional conservative preflight allowance,
fresh-run limits and actual storage. The same 14 reviewed modules, `go.mod`,
`go.sum` and isolated Go executable hashes match the earlier reviewed pins.
The offline-cache build produced
`3befb4b0075de7415e4f91a50ece56cf97e3649201dc677c66581f2bd46ccdc3`.
Fixture SHA-256:
`4526e21b5fe001d81611c5ccd5bb23f7347cdcc79c5ed75a56776944f581c7bb`.
Build, run and regression helper sources and commands are retained locally;
portable controller commands are in the [probe README](probes/gnark/README.md).

The block passed all 233 checks in 62.698 seconds. Every one of the 64 valid
inputs produced an actual proof verified in a fresh process. All five public
mutations and all 89 private intermediate mutations rejected, as did invalid
tokens/masks/scores, field aliases, signed overflow in assignment transport,
noncanonical decimal input, changed/trailing proof bytes and a second setup key.
The circuit has 5,250 constraints, a 133,167-byte R1CS, 1,599,991-byte proving
key, 732-byte verifier key and 244-byte proof. Peak process RSS was
39,223,296 bytes and cumulative worker CPU 203.779 seconds. Proof processes
took 0.363–0.403 seconds; verifier processes took 0.025–0.284 seconds.
These include startup and artifact loading and are one finite-domain diagnostic
roster, not pure prover timing, p95 or a full-encoder feasibility measurement.

The shared worker refactor passed 30 rule/MLP regression cases and 18 cubic
cases in 131.824 seconds.
Fresh setups reproduced both previous R1CS hashes byte-for-byte. Fresh empty-input
proofs verified, invalid padding/public fields and a wrong key rejected, and
all 18 retained proofs verified under their separately pinned original keys.
The published block proof/key example was decoded
from the evidence and verified again in a new process with independently retained
key/fixture pins. Verification still shares gnark with the prover.

The recorded case-file sum for the block is 289,708,535 bytes; a complete
post-run inventory including metadata is 290,309,998 bytes. The regression's
full inventory including its nested cubic run is 603,653,502 bytes.
Both meet their recorded limits. The protocol/source/command/result files stay
in the ignored fresh directory, with the same 2026-11-19 retention limit and
no scheduler. No failure or earlier result was overwritten.

`make check` passed 1,764 tests, including 17 new exhaustive-fixture, malformed
input, stale-pin, failure-retention and sanitized-path checks. Both package gates
passed; the required training extra executed. The common pre-evidence/prose
source identity is
`ef439b2cdc190d52d8bf0884eff90f59d161adf7ef2954a536bac98d12db06b9`;
sdist SHA-256 `814046250fba3371d3dbc778e8b553656cf84418061d2acea616ae760fb08a4c`.
The unchanged runtime wheel is
`4c79ab355f919c4bb4dd9a54bc2aebf233a06597275d68c184ae851273344d5b`.
Final-head CI must rebuild the complete documentation/evidence candidate.

This proves the stated tiny block only. It has no tokenizer, complete input
commitment, layer normalization, trained model or full encoder. The power-of-two
and reciprocal tables define its arithmetic; no float-parent equivalence is
claimed. Local setup, shared verifier, independent review and complete graph
qualification remain unresolved. `qualified_backend` stays false; W18 remains
open. No HF token, GPU job, paid compute or private input was used.


## 2026-10-20 — W18 staged qualification command

Hypothesis: the existing real-proof controllers retain their correctness and
failure behavior under one externally pinned protocol and shared budget.
Baseline: standalone installation/rule/MLP/block controllers, 1,764 local tests
and no installed qualification command. Mutable paths: packaged controllers,
CLI, shared rooted file reader, tests, protocol schema/marker and documentation.
The Go source/binary, arithmetic and frozen graph inputs remain unchanged.
[Decision 0026](../docs/decisions/0026-staged-qualification-command.md) fixes the
scope and criterion before execution. The [raw numeric evidence](evidence/w18-staged-qualification-2026-10-20.json)
precedes this prose.

The frozen plan/source snapshot is `runs/w18-qualification-1792524845681991000`.
Protocol identity: `713f73c35a0fd80543c00dc1f8c8ff16205d8a20f28b89be33a2233c017ea766`.
Controller identity: `004a15d94fbc6f271c27319d76b8855cbbb3c5aa422a45cfee5496f23dcb1b06`.
Binary SHA-256: `3befb4b0075de7415e4f91a50ece56cf97e3649201dc677c66581f2bd46ccdc3`.
The protocol pins the reviewed source/licence, dependency, build and authority
records alongside all fixtures. The run retained them before execution; it does
not authenticate approval or adjudicate those documents' claims.

The exact command is retained in `command.json`; its portable form is:

```text
uv run --locked hallmark qualify APPROVED_PROTOCOL.json \
  --expected-protocol 713f73c35a0fd80543c00dc1f8c8ff16205d8a20f28b89be33a2233c017ea766 \
  --output FRESH_DIRECTORY
```

All 541 real cases pass in the prescribed order: installation 18, rule 134,
MLP 156 and block 233. Fresh setups reproduce the earlier rule, MLP and block
R1CS hashes exactly. Actual proofs verify in fresh processes; mutations to all
100 public fields for rule/MLP, all 22/89 MLP/block intermediate values, aliases,
proof bytes and setup keys reject. Complete raw case inventories and costs are
retained. The evidence generator rehashes every stored file against the case
records; no earlier experiment or failure is overwritten.

The command correctly exits 3 with `status: incomplete`, not a qualification.
Elapsed time is 1059.285s; worker peak RSS is 677,314,560 bytes;
summed worker CPU is 3852.295s. The output contains
4,424 files totaling 5,926,016,680 bytes, below its 6 GiB cap.
The shared deadline was 1,200 seconds, four threads, one research worker at a
time and zero spend. Prior recorded intervals plus a conservative preflight
allowance were 4955.640s; the new 1,500-second reservation
fit the study's 7,200-second proving envelope. The actual combined runs/dist
allocation stayed below the owner's 20 GiB cap. Retention is through 2026-11-19;
no scheduler was started. Installed-package validation overlapped the first
8.59 seconds. These timings include startup, artifact I/O and checks, and are
not isolated prover latency, p95 or an encoder-feasibility measurement.

`make check` passes 1,807 tests, including 43 new protocol/controller cases.
Tests cover wrong pins, duplicate JSON keys, incorrect fixture kinds, unsafe
paths, hardlinks/FIFOs, source changes after snapshotting, resource limits,
failure retention, interruption, private CLI errors and a live deadline that
kills/reaps the worker while retaining timeout costs. Marker-worker tests never
count as proof evidence. The common rooted reader retains all 128 model-file
regressions. A transient import-order lint failure is retained in `check-02`;
the final `check-03` passes without weakening checks.

Both installed-package gates pass, including the actual training extra. Their
common pre-evidence/prose source identity is
`4aa11d2a4bd163f3a9889f64ef835067826b9dc97bd916f8bbe790d44e9b7d0e`;
wheel SHA-256 is
`2bb327c94c931195eb6ea7de4f1dc20dc95789b9e9b6de7060744379277fc4dd`.
Final-head hosted CI must rebuild the completed documentation/evidence candidate.
The standalone script paths remain compatibility commands for the packaged
controllers; an additional 18-case real cubic run passed through the legacy
script entry point in 1.41 seconds. No dependency or Go rebuild was required.

Whole-encoder proofs at empty/near-boundary/maximum length, operational key/
program enrollment, an independent verifier/security/hiding review and accepted
setup lineage remain open. RSS/aggregate storage checks are postconditions,
not hard OS quotas. Local setup and shared gnark verification remain research
limitations. `qualified_backend` stays false and PR #72 stays draft. No HF token,
GPU job, paid compute, private upload or operational acceptance occurred.

## 2026-10-20 — W15 record-level MLP component

Hypothesis and boundary are recorded in
[decision 0027](../docs/decisions/0027-record-level-mlp-training.md): complete-input
record-max fitting can resume exactly and export the existing native integer
runtime without exposing calibration/test labels to fitting. Baseline: 1,632 tests
at the W14 merge above, synthetic native MLP weights, and the unchanged logistic
trainer's multi-chunk rejection. Mutable paths are the additive training/export
API, shared fixture assembly, schemas/tests, package checks and documentation.
No dataset, evaluator, policy threshold or historical result was retuned.

The [machine-readable evidence](evidence/w15-record-mlp-training-2026-10-20.json)
was saved before this prose. Raw local artifacts are retained at
`runs/w15-mlp-training-1792527541853491000` with the protocol, source snapshots,
environment, command logs, optimizer checkpoints, epoch traces and exports.
Protocol SHA-256:
`406c6d18fd70796b17246460acff8986d7e9c4fb8470411f88720211489a1d58`;
receipt SHA-256:
`5bdeb8c5a3428235fec47fd0c177ff79b890dae59fab6848b49b56de645df5cd`.
The pre-run source inventory identity is
`fca0528fd4eab344ed62315d7df070f9d76dc542407c695881e805a79546ed1e`.

Two new directories reproduced all 27 substantive artifacts byte for byte.
Each run fits the frozen 12 authored marker records for seeds 17/29/43, compares
fresh fitting with a JSON checkpoint resumed after epoch 31, and executes seven
native/float probes per seed. Probes include empty, Unicode, chunk boundaries,
last-byte markers and the full 32,768-byte limit. Maximum absolute score errors
were 0.0064575824, 0.0081562375 and 0.0161565061, below the predeclared 0.1
engineering tolerance. Final losses were 0.3366060358, 0.4234531054 and
0.3295476184. All three reached epoch 80 without convergence; none is reported
as converged or as a successful policy detector.

The two sequential one-thread commands took 0.671 and 0.371 seconds, with measured
peak RSS 57,458,688 and 58,474,496 bytes. Source and raw evidence occupied
3,262,607 bytes before the receipt. Cost was $0. NumPy 2.5.4 / CPython 3.12.12
ran on the owner Mac; exact CPU features, extension and trainer hashes are in the
environment record. No dataset/checkpoint download, external inference, GPU job,
HF token access or private upload occurred. Timings are single fixture observations,
not a performance distribution or proof-cost claim.

The 108 focused tests passed, including 75 existing native-MLP cases and 33 new
training/export checks. Numerical finite differences check the record-max
subgradient away from ties; a separate tie case verifies first-max routing.
Pre-import rejection covers nontraining rows, changed identities, invalid
profiles, malformed shapes and resource limits. Checkpoint substitution, changed
configuration/data/runtime/loss, CLI path disclosure and failed output retention
are checked. The historical MLP fixture still reproduces unchanged.

`make check` passed all 1,665 tests plus lock/lint/format/types, spec, software
conformance and admission. `make check-train` executed all 17 selected tests.
Both package gates passed, including core-only contract checks and actual
installed-wheel three-seed training. Their shared pre-evidence source identity is
`d12a88046b5cc57d36db75c1c04831bc6c87daaf166e92b6753d86f11b6eb6eb`;
wheel `1fa14f03212f2154143e3963d1969b2017b890a11034b8025dd88e1db68c4627`,
sdist `a2c789a76539e27868ddb0887d491387b945a9ee55cbef6f2a4bbd345495cc89`.
Gate commands consumed another 42.942 seconds. Final-head hosted CI rebuilds the
complete commit including this evidence and prose.

All recorded runs passed; earlier development checks rejected a fractional native
output. The correction preserves the integral-score contract through explicit
score units instead of relaxing validation. Epoch-limit nonconvergence is retained.
These are shared-implementation software checks, not independent authentication,
policy quality, hardware provenance or a proof. The complete W15 roster, grouped
selection, MLP calibration/evaluation and admitted real-data commands remain open.
W18's staged proof work stays separate in draft PR #72. The unrelated `.gitignore`
edit remains unstaged, and repository visibility remains public.

## 2026-10-20 — W15 grouped comparisons and native calibration

Hypothesis: finite, train-only grouped selection can preserve split isolation and
every candidate failure, followed by separately pinned native calibration and
evaluation. Baseline: `865691f0fe455045f24543f0f5de333a5a2dae5f` in draft PR #73,
with 1,665 tests and MLP fitting/resume but no grouped comparison pipeline.
Mutable paths: additive baseline/selection/calibration APIs, fixture/checker,
schemas/tests, package checks and documentation. The historical logistic trainer,
evaluator, datasets and previous MLP experiment remain unchanged.
[Decision 0028](../docs/decisions/0028-grouped-baseline-selection.md) preceded the run.

The [numeric evidence](evidence/w15-grouped-comparisons-2026-10-20.json) was saved
before this prose. Raw snapshots/logs/fit states are retained under
`runs/w15-grouped-selection-1792528940558781000`. Protocol SHA-256:
`7974d63824ad53ee0137f9f163a365e3c8b12baebccd71f5eab2b7f287a09285`;
receipt `8240caf7da59550237723e2f6c5ce747cce5e5108fbd4cf3973747df430e16a2`;
pre-run source inventory
`56f5a904f868dae836b73cf2be8f7a849d550a035e29a725cc14cb41e082c97d`.

The frozen fixture has 100 train rows in 50 groups, plus 20 calibration and 20
test rows in disjoint groups. Five declared candidates and three seeds produce
75 rotations: three folds fit, one selects an internal threshold, and one
validates. Only fitting rows supply vocabulary or optimizer inputs. Group and
representative assignment are label-independent. Exact rational ranking selects
per family and seed, with lexical candidate ties. Controls never fit/calibrate.
Every nonconverged or failed candidate remains in the report.

Two fresh one-thread runs reproduced all 31 substantive artifacts byte for byte.
Each retains 15 deliberately nonconverged MLP rotations and refits/calibrates/
evaluates nine selected models. All nine primary test reports contain ten group
representatives; all-row reports contain 20 descendants. The authored-marker
logistic and character models each have TP=5, FP=0, TN=5, FN=0. The deliberately
loose-tolerance MLP has TP=0 and FN=5 for every seed; FP counts are 0/1/2 and TN
counts 5/4/3. These are unacceptable as task-quality results, not hidden by the
software pipeline's pass. Neither MLP fixture configuration is a real study
candidate, and no result is an injection-policy estimate.

Recorded command times were 2.282 and 2.165 seconds; macOS `time -l` peak RSS was
142,442,496 and 141,213,696 bytes. Source/raw files occupied 8,016,420 bytes before
the receipt. Cost was $0; no model/dataset download, private upload, HF token or
paid job was used. These two fixture observations do not establish latency
percentiles or production throughput.

All 44 focused tests pass. They check outer-label rejection before serialization
or optional imports, group/representative invariance, fitting-only vocabularies,
exact decimal allowances and blocking ties, resource limits, malformed numeric
types, preserved long-input floor rejection, explicit liblinear nonconvergence,
candidate ties, wrong fit/calibration pins and overlapping groups/prompts. A
development check found that numeric literals accepted float-valued seeds/folds;
strict integer fields and regression cases corrected that before this protocol.
The final fixture/schema snapshots reproduce, and injected controller failure
retains an incomplete directory without a final result.

`make check` passed 1,709 tests plus lock/lint/format/types, spec, software
conformance and admission. `make check-train` executed all 35 selected tests.
Both package gates passed, including the core-only contract path and actual
installed three-seed grouped comparisons. Their common pre-prose source identity
is `d9b7a89726fb7b24624c778438c713197ef0b8b1049e5ad5ea0bfad39bafa2b8`;
wheel `5754530a3759c13a35653480bc599d4c63e1be27a5f2434565aac769d3896326`,
sdist `5dea06cf58fa65aeff0f8c2be01e88a50c97cd0990e3269d69ed0fc9db501b7c`.
These gates consumed another 58.399 seconds; final-head hosted checks rebuild the
complete source including this evidence and prose.

The separate [guard source review](evidence/w15-guard-source-selection-2026-10-20.json)
retains current public metadata and base-model notices. Under delegated selection,
[decision 0029](../docs/decisions/0029-guard-source-selection.md) chooses the pinned
published guard for bounded qualification using its explicit model grants. It
does not approve acquiring unnamed unlicensed upstream training data, endorse
the archived project's metrics, or resolve contamination. The local raw metadata
is in `runs/w15-guard-metadata-1792528650785139000`; no weights/tokenizer or runtime
packages were acquired. Exact runtime review, asset hashes, complete-input guard
execution and final real-data admission remain the next W15 gates. This PR stays
draft; W18's proof work stays separate. The unrelated `.gitignore` edit is preserved.

## 2026-10-20: W15 complete-input CPU guard and optional runtime

Hypothesis: the selected pinned guard can score every content-token block of a
32,768-byte prompt on the Mac and reproduce its numeric outputs in a fresh
process. Baseline: metadata selection only; the publisher's example truncates.
[Decision 0030](../docs/decisions/0030-complete-input-guard.md) freezes the
complete-input max-margin adaptation before real inference. Mutable paths are
the optional adapter, its comparison binding, tiny runtime fixture, packaging,
tests and documentation. The previous learned baselines and evaluator are unchanged.

The [dependency review](evidence/w15-guard-dependencies-2026-10-20.json) matches
684 locked artifacts for 52 packages. Existing versions are unchanged. It records
selected-wheel notice hashes and exact upstream Apache notices for the two wheels
missing licence files. Acquisition verifies all five advertised model/tokenizer
digests, including the 738,563,188-byte ONNX graph. Model/base notices accompany
the ignored assets. No remote model code, pickle, HF token or paid job was used.

The [CPU evidence](evidence/w15-guard-cpu-2026-10-20.json) retains raw scores,
source/runtime/binary hashes, exact asset/spec/input identities and receipts.
Raw model acquisition is `runs/w15-guard-assets-1792529768485391000`; execution is
`runs/w15-guard-cpu-1792530020726182000`. Its protocol hash is
`30e2e46c066c526ad4abf9a71278cee6445bfcc1afee486471a517205ca1bce1`, receipt
`5113ada479ae8fa5267d64d5c0a09f6e6b4864376cc38c2f3b80f84aacd8e809`.
Two four-thread CPU processes each score seven fixed harmless probes through 50
chunks and reproduce all 11 substantive JSON files byte for byte. Times are
7.253/7.008 seconds; peak RSS is 4,372,217,856/4,371,480,576 bytes. The maximum
ASCII prompt has 5,463 tokens/11 chunks; the maximum Unicode prompt has 16,384
tokens/33 chunks. Both are exactly 32,768 bytes. The late instruction is scored
in its second chunk. Costs remain $0, with no external inference.

Negative evidence remains explicit: the two maximum-length repetitive benign
probes have margins +8.170272/+6.674934. Zero is not an admitted threshold, and
these seven authored prompts cannot estimate a false-positive rate. The published
tokenizer strips/normalizes text; full token coverage is not byte preservation.
Upstream contamination, human label review, task-quality targets and independent
verification remain unresolved. `bind_guard` adds the fixed pretrained model to
the separate calibration/evaluation API without local fitting or test selection.

Validation: 32 new guard tests; `make check` passes 1,741 tests; `make check-train`
executes all 35 required tests; `make check-guard` executes the real tiny ONNX
fixture and all 32 tests. Core packaging and a combined train/guard package gate
pass through separate installed environments and reproduce identical distributions.
Their pre-prose source identity is
`76fb4bbbc68ec8b7217d494d5800a2cff9135cf1b792068a5d2095b8b30e1cf6`;
wheel `2d5a12bb022de94eeeb5f2a8e8498887ebb2f76bffa0c9e9d4f3ffdc657c69ef`,
sdist `3f72ce130a180ff8a749e233d49d1250feb949255bad98ed8c8b4ca4025dd52d`.
The five passing gates consume 67.287 seconds. Raw logs/receipts are in
`runs/w15-guard-gates-1792530308409104000`. The earlier failed full gate is kept:
its only failure was the old statistical calculation's lock pin. A separately
retained calculation reproduces every field except the new lock SHA; the original
W13 record is untouched. Runtime tests also reject changed files/pins, links,
external tensors, custom domains, oversized/invalid Unicode inputs, bad outputs,
held-out rows, overlapping groups/prompts and existing output directories.

PR #73 remains draft until admitted real-data commands satisfy the rest of W15.
The compact encoder and full proof/hardware obligations remain separate work.
The repository remains public and the unrelated `.gitignore` edit is preserved.

## 2026-10-20 — W15 caller-enrolled comparison command (partial issue #16)

[Decision 0031](../docs/decisions/0031-admitted-comparison-command.md) fixes a fresh
engineering experiment joining admission, reproduced source import, grouped
selection, final fits and calibration before test. Existing evaluator, grouping,
study targets and historical results remain unchanged. The command checks an
externally supplied review identity, exact source/config/runtime pins and dataset
reproduction; it does not authenticate a human approval. Fixture-only mode cannot
relabel authored data as real study evidence.

The [raw numeric evidence](evidence/w15-comparison-command-2026-10-20.json) points
to `runs/w15-comparison-command-1792531617672623000`. Protocol
`c912d278451562cc2f15abc1b7191e2bc31dbdc7b9dc7c7ef931fb0c4a1dd6f2`
was written before measurement with exact source/input identities, two commands,
55 seconds per command, one thread, 2 GiB memory and 16 MiB new storage. Two fresh
processes took 2.931/2.892 seconds and peaked at 272,400,384/270,286,848 bytes RSS.
All 38 output artifacts match byte for byte. The full 200-row authored source,
invented review dossier and tiny ONNX graph remain local. No downloaded data,
HF token, GPU, paid compute or external inference was used in this experiment.

The runner retains 75 train-internal rotations, including 15 deliberate
nonconvergences, then nine selected final fits plus the fixed marker guard.
Every fit/calibration identity is saved before scoring test. Negative results
remain: each MLP seed misses all 20 positives; each character baseline has 2/20
benign false positives. Logistic/marker-guard fixture results are not scientific
quality evidence. Controls report their full errors; compact encoder is explicitly
unavailable. `full_study_complete` and `quality_claim` remain false.

Validation: `make check` passes 1,772 tests, `make check-train` executes 35 tests,
`make check-guard` executes its graph plus 32 tests, `make check-comparison`
executes the real CLI plus 31 binding/order/failure tests, and `make package-check`
passes. The five gates total 63.908 seconds. The existing fork-rejection test
emits Python's multithreaded-fork deprecation warning and passes. Raw logs are in
the experiment's `gates/` directory. Core package source identity is
`49bd4b6098c32ec95579924492abc3b442f40054245c3817147678fb10286ac5`, wheel
`a8929702d6cb278097b1c62e7cf93b60c1af6ff081af0d18d178da0efa942b3f`, sdist
`ded0fad4b12738742daa23a9d9c0bd66398299424fa359f55db011b67f3ec733`.
These distributions precede this evidence prose. Another local combined-package
environment would exceed the remaining 20 GiB allowance, so it was not run;
Linux/macOS hosted jobs now require the installed combined comparison fixture.
The storage-choice request remains pending and old evidence was not removed.

PR #73 stays draft: the real-data command is implemented, but an actual reviewed
source/label/contamination dossier is still missing. `docs/OPERATIONS.md` provides
the exact invocation template, required layout, external-pin and resource
obligations. No real-data or final study claim is made by this increment.

The first hosted Linux comparison check on `5027e50` failed one test after 30
passed: ONNX Runtime emitted a native device-discovery warning while the command
correctly returned partial-result exit 3. The test had incorrectly required an
empty diagnostic stream. The correction checks the exact stdout status and
absence of private input paths, retaining exit-code, missing-family, convergence
and sanitized-exception checks. Execution code and measured source/input/output
identities are unchanged. The failed
[job](https://github.com/AbdelStark/hallmark/actions/runs/39500956450/job/118898010242)
log is retained in the raw experiment directory; its failure is not reported as
a passing package check. All 31 corrected comparison tests pass locally in
10.54 seconds (`portability-tests.log`); hosted jobs must pass on the corrected
commit.

## 2026-10-20 — W15 public-source review and human audit handoff

[Decision 0032](../docs/decisions/0032-public-source-review-pilot.md) bounds source
preparation under the existing delegation. The
[evidence](evidence/w15-source-review-2026-10-20.json) retains exact metadata,
licence notices, acquisition plans/receipts and local raw pointers in
`runs/w15-source-review-1792532338623341000`. No source is admitted for measurement.

Gandalf revision `04737b65e90a6794ec227012e4a255a7def6344b` yields all 1,000 rows
through the public viewer API. Every page reports that exact `x-revision`, the
expected row count/indices and no truncation. This checks retrieved snapshots,
not local Parquet decoding. Dolly revision
`bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a` verifies the 13,085,339-byte JSONL against
`2df9083338b4abd6bceb5635764dab5d833b393b55759dffb0959b6fcbf794ec`.
The predeclared empty-context filter retains 10,544 exact instructions and excludes
4,467 context-dependent records. Acquisition totals 13,248,844 bytes in 4.555
seconds. Source grants are MIT and CC BY-SA 3.0; copyright, attribution, licence
and change notices accompany the local review adaptation. No raw rows are added
to Git.

The separate Mirza Akhi source at `011a9ae25b31feb48d23f837fdcbc3a6a4ee3b4e`
has an explicit CC BY 4.0 grant. Its acquired CSV matches
`eb748eb8104f0a736934bf4f3c96335801010b09e17467fd4aadc1c1ae7bbced`:
5,441 unique prompts, 5,425 marked English, maximum 223 bytes. The generation
recipe was inspected as text, never executed. Template ancestry and the original
holdout need review; it is a possible supplemental stress set, not real-world
validation. The Qualifire successor is auto-gated and was excluded without token
access. PINT's full corpus remains held for task/provenance/rights review. A direct
Creative Commons text download returned HTTP 403; the official browser-reader
responses and repository notices are retained, without claiming raw HTTP-byte
equivalence for those browser snapshots.

Two fresh review builds reproduce all six files byte for byte. The 64-item packet
SHA-256 is `0ec4a6951b1939474aa70eb89b7b0228890ef71dec93846bbd63d6de51e2a57e`.
It hides proposed labels/source class per item and includes complete prompts,
the frozen rubric, attribution and blank human response fields. A separate
editable `human-response/labels.json` preserves the two original templates.
No human identity, labels or agreement rate were invented. The owner was asked
who will perform the review; no reviewer was contacted.

Preflight finds 114 exact-duplicate groups. A fixed, non-fitted character-hashing
screen retains all 563 pairs at cosine at least 0.90 and 172 multirow components;
the largest has 33 rows. One two-row component crosses Gandalf's original splits.
The tiny equality/unrelated-text fixture passes first. The full screen takes
1.022 seconds in-script (1.80 seconds process wall time), with 216,514,560 bytes
peak RSS. Pair/component files, code/dependency pins and the cross-split review
example are retained. The screen proposes links; it cannot establish semantic
or historical lineage, and no links are represented as human-approved.

The complete study remains unmet: source identity is confounded with provisional
class, language/label decisions and parent identities need review, and 1,000 total
Gandalf rows cannot supply 1,375 independent positive test groups. These exposed
public sources are exploratory. No acquired row was used for classifier fitting,
guard inference or test scoring. No paid job or HF token access occurred. Frozen
targets and old results are unchanged. PR #73 stays draft pending genuine review
and final admission.

Storage accounting was corrected to include the whole checkout, Git and caches;
the earlier three-directory total omitted those bytes and the checkout was about
0.9 MiB above the recorded 20 GiB cap. Only mypy's tagged, rebuildable SQLite cache
was removed, restoring headroom. `storage-correction.json` records exact before/
after bytes; no research run, failure, environment, asset or review artifact was
removed or archived. Subsequent local validation disables mypy cache writes.
The request for a larger retained-storage envelope remains pending.

Validation with `MYPY_CACHE_DIR=/dev/null make check` passes all 1,772 existing
tests, strict type/style checks and the spec/admission/conformance gates in
32.696 seconds. The existing multithreaded-fork deprecation warning remains.
Source-card Git blob checks, all acquisition file hashes, canonical candidate
pairs/components and both blank packet builds also pass. Classifier source and
dependency locks are unchanged. Distribution checks run in hosted CI; another
retained local package environment does not fit the remaining storage allowance.


## 2026-10-21 — Owner-approved synthetic W15 pipeline and storage

The owner approved the requested 40 GiB retained-storage envelope, agent review
and wholly synthetic data without human review for pipeline development, with
the Mac preferred and HF T4/L4 allowed fallbacks. [Decision 0033](../docs/decisions/0033-approved-synthetic-pipeline.md)
records this change. Historical natural-source packets, failures and evidence
remain unchanged. The W15 work-map/issue criterion now explicitly permits the
authorized synthetic pipeline, retaining confirmatory real-data admission as a
separate quality gate. No human review identity or agreement rate is fabricated.

Hypothesis: the existing comparison command runs unchanged with the real pinned
published guard and the 200 authored controls. Baseline: its tiny-marker guard
fixture and the earlier standalone real-guard execution. Mutable paths are the
new local dossier/protocol, approval records, documentation and authority checks.
No classifier, evaluator, dependency or runtime source changed. Pass criterion:
complete W15 execution with every baseline/control retained, exact reproduction,
package gates and truthful unavailable/quality status.

[Numeric evidence](evidence/w15-synthetic-pipeline-2026-10-21.json) retains
`runs/w15-synthetic-pipeline-1792567226626052000`: frozen outer protocol, both
controller sources/pins, agent review, complete dossier inventory, caller pin,
commands, results, resource receipts and validation logs. The agent checked all
200 control labels against the recipe (`hello`=0, `ALERT`=1). Shared templates
make these unsuitable independent statistical groups or injection-policy labels.
The internal fixture source markers remain mechanical binding inputs; actual
run authority is this owner's decision, not invented fixture approvals.

The externally retained review pin is
`bcc2f807bc7bf6849d9cf04c30c7b41b2bacc3ac6fcfd28243b4896fecab079b`.
Both actual CLI invocations use `--fixture-only`, the frozen dossier and existing
pinned guard assets; exact argv records are in the evidence. Each fresh process
exits 0 with all W15 baseline families and fixed controls executed. All 38 files
reproduce byte for byte. Elapsed times are 4.674/4.665 seconds; peak RSS is
4,373,692,416/4,373,921,792 bytes. Preparation itself was not separately RSS-timed.
The outer watchdog limits execution to 300 seconds; resource observations are
not an OS memory/storage sandbox.

Negative results remain visible: the real guard marks 3/20 negative controls,
character n-grams 2/20 per seed, and each MLP misses all 20 positive controls.
These are fixture-control outcomes, not FPR/TPR estimates for injection policy.
The full study, quality and independent-verification flags remain false; compact
encoder is explicitly W16-not-executed. This completes W15 software execution
under the owner's revised stage, not the entire MVP or confirmatory study.

Validation: 114 focused admission/comparison tests; `make check` passes 1,772
with the existing fork warning, strict typing/style, 156 software conformance
cases and specification/admission checks. `make check-train` executes all 35
training tests. Core and combined train/guard package gates both pass; the latter
runs the installed comparison command. Their pre-evidence-update source identity
is `45e564fabc36a7f0256a45fee9213b235d399767e81bdc2b840190bbbebf4d4c`.
The live spec audit matches all 40 work items and 106 dependency edges after the
owner-approved W15 acceptance update. Final-head hosted CI remains required
before merge. No HF token, GPU job, paid compute or reviewer contact occurred.


## 2026-10-21 — Integrate the merged comparison pipeline into W18

W15 / #16 merged through [PR #73](https://github.com/AbdelStark/hallmark/pull/73)
as `de29271d21196202fc951ebe5f5fc3348fbf9a63`. All 28 candidate jobs and all 14
[main jobs](https://github.com/AbdelStark/hallmark/actions/runs/39562563658) pass;
local/tracking/remote main match. The owner-approved synthetic stage is delivered.

Hypothesis: the existing qualification and comparison commands coexist with both
sets of installed-package checks. Baselines: W18 at
`32aecdbed4869cdff6bd28d7e0725763ef1c5c85` and the W15 merge above. Mutable paths
are the five conflicting changelog/ML-plan/ledger/state/package-check files and
current status/evidence documentation. Both implementations and historical proof
records remain intact. The bounded gate is combined software/package validation,
not a new cryptographic qualification experiment.

[Evidence](evidence/w18-main-integration-2026-10-21.json) retains
`runs/w18-main-integration-1792567953903508000`. The package-check conflict now
runs qualification/backend fixtures as well as MLP/selection/guard/comparison
checks. The ledger retains both branches' historical entries; state reflects
W15's merged delivery and W18's remaining whole-encoder gate. The owner-approved
40 GiB envelope and synthetic/no-human-review pipeline stage are inherited from
main. The unrelated `.gitignore` bytes are unchanged.

All 140 focused integration tests and all 1,947 local tests pass. Both core and
combined train/guard package gates pass, including installed protocol/selection
and comparison commands. The proof source, Go circuits and packaged controllers
are byte-unchanged from the W18 parent. No new proof run, setup, token use or
paid compute occurred; existing proof time accounting is unchanged.
Final-head hosted checks are required before publishing this integration as
verified. PR #72 remains draft: full encoder/input qualification, independent
verification, security/hiding review, accepted setup and operational enrollment
remain incomplete. W17 / #18 is now dependency-ready for synthetic reporting.

## 2026-10-21 — W17 frozen group-aware reporting

Hypothesis: existing frozen test predictions can support versioned slice and
paired root-group reports without training, scoring or threshold selection.
Baseline: W15 has separate per-model counts but no shared reporting adapter.
Decision [0034](../docs/decisions/0034-frozen-group-reports.md) freezes the report
semantics; mutable paths are report API/command, fixture/tests, package checks
and documentation. Prior evaluator/data/threshold identities remain unchanged.

[Raw numeric evidence](evidence/w17-group-evaluation-2026-10-21.json) retains
`runs/w17-group-report-1792568480677539000`: predeclared implementation/execution
plans, the preparation controller and pin, verified prior artifact inventories,
source/provenance/observation inputs, separately retained plan pin, exact commands,
resource receipts and byte-equal reports. The new synthetic experiment explicitly
records prior exposure to W15 test outputs. It does not reuse them as unseen
confirmatory evidence. All 38 original run artifacts and the entire source dossier
were checked against their existing inventories before preparing report inputs.

The correlated software fixture has 36 authored-score rows in 12 declared groups,
three seeds, three paired 10,000-resample comparisons, one positive quantization
regression and one benign false positive per seed. Existing calibrator tests check
ties and no benign calibration; new checks reject changed labels/thresholds,
missing seeds/rows, split overlap, pin changes and adaptive confirmatory requests.
Counts for correlated descendants have no binomial intervals. Empty denominators
and absent bootstrap denominators remain null. Missing attempts remain explicit.

Two new CLI processes report the retained W15 outputs in 0.292/0.283 seconds,
peaking at 41,697,280/41,779,200 bytes RSS. Both report files are byte-identical.
Ten available members and nine paired comparisons execute; twelve absent
float/encoder members and nine quantization comparisons remain unavailable.
Original pass/block control counts are retained in the pinned provenance.
The guard's three negative-control positives, character models' two and MLPs'
twenty missed positive controls remain unchanged. Shared templates are not
independent statistical units or policy labels, so these intervals only check
software. No human review, task-quality claim or independent verification occurred.

Validation: 40 new tests, 47 focused checks and all 1,812 tests pass. Both core
and combined train/guard package gates pass, including the installed report
fixture and comparison pipeline. The first package attempt rejected uv 0.13.4
before building; `dist/package-check-go3nqolb` retains that failure. Restoring
required uv 0.9.18 in a private tool directory (published wheel SHA-256 checked,
MIT/Apache notices retained) resolved it without modifying global tools or source.
The package snapshot before this evidence/documentation update is
`e21d8170269b46ab75c2702576326e47705ffbf290af71d7cc0667ce1d4ec51f`.
No proof run, HF token, paid compute, model download or private-data upload occurred.
Exact-head hosted checks remain required before merge.

## 2026-10-21 — W18 complete-input commitment scaling

Hypothesis: indexed lookup removes quadratic CBOR packing and makes the admitted
maximum-input component measurable. Baseline: eight-byte rule/MLP input binding.
Decision [0035](../docs/decisions/0035-input-commitment-scaling.md) fixes the new
component, byte/header boundaries, negative cases and resource envelope. Mutable
paths are the optional Go component/worker dispatch, its research runner, tests
and evidence. Rule, MLP, attention-block and original input circuit bytes are
unchanged. W17 / PR #74 was integrated as `132c65e`, preserving both implementations;
83 focused reporting/qualification tests passed before the new experiment.

[Numeric evidence](evidence/w18-input-scaling-2026-10-21.json) retains
`runs/w18-input-scale-1792570054284510000`: predeclared plans, exact source snapshots,
reviewed cached dependency pins, offline builds, both candidate identities, every
attempt/cost and synthetic proof/key bytes. No transcript, model checkpoint,
token, HF job, fee or scheduler is involved. The native fixture cross-checks a
hand-assembled encoding/hash against the existing canonical codec at lengths
0/1/8/23/24/255/256/32767/32768. The 33-field relation binds count and salted input
digest under a synthetic fixed profile; it is not a classifier statement.

The first 118.892-second run produced three small proofs, then failed on a valid
empty 256-byte solver assignment. Inspection of the pinned gnark commitment
placeholder established that standalone `IsSolved` lacks the real prover's hint.
Its negative solver outcomes are inadmissible and remain marked as such. The
corrected source uses only actual Groth16 proving, with one key load per batch,
and fresh verifier processes. No placeholder/dummy hint was introduced. Source
snapshots of the failed Go candidate reproduce its pre-run hashes exactly.

The corrected 318.353-second command records 51 worker processes, including
two proving batches: eight valid proofs
(empty/near/max at capacity 8 and lengths 0/23/24/255/256 at capacity 256), twelve
invalid prover witnesses, eight successful fresh verifications, 33 changed
public-field rejections, field alias/proof corruption/wrong-key rejections,
setups and compilation probes. Padding, byte range, salt range, header/array
encoding and prefix gaps reject. The small circuits contain 206,049, 244,924 and
525,403 constraints for capacities 8, 32 and 256. Capacity 32 is compile-only.

Maximum capacity 32,768 fails compilation: the watchdog kills it after 90.335
seconds, with measured peak RSS 17,181,917,184 bytes, 2,048,000 above the approved
16 GiB postcondition. The late supplemental memory observer found no matching
live process and sent no signal. No complete constraint count or maximum-input
proof exists; this is not a throughput estimate or whole-encoder result. Future
large attempts need a conservative live cutoff and an accounting audit first.
Old conservative consumption 4,955.640 seconds and the prior 1,500-second
reservation remain intact; this increment reserves 700 of the remaining 744.360
seconds, including failures, builds and checks. No time refund is assumed.

Validation so far: 16 new Python tests, all 2,003 repository tests and two Go
boundary tests pass. Seven Go manifest cases cover unsafe names, duplicates,
unknown/missing fields, trailing/oversized input and empty batches; seven numeric
transport cases reject malformed or excessive assignments. The first package
attempt retained in `dist/package-check-jssm2d0r` correctly rejected missing linked
documentation because new files had not yet entered the Git-index source snapshot.
Stage exact intended files before repeating the package gate. No unrelated
`.gitignore` change is staged. Backend selection and issue #19 remain open.

Final validation passes all 2,004 Python tests and both package gates, including
required installed training and guard/comparison/report/qualification checks.
The package source identity is `c8d57b9251622d2c3a14305c60ce025754e3a4da7f9ff7b6f0cd9e1a43db3b29`.
Seventeen new Python tests include sanitized CLI argument errors; that post-run
CLI hardening does not relabel the frozen cryptographic experiment. The timed new
commands total 648.176 seconds; a further ten-second preflight/test allowance
keeps consumption inside the 700-second reservation. Final-head hosted verification
is separate from these local results.

## 2026-10-21 — W18 live memory cutoff and receipt audit

Hypothesis: native RSS sampling can stop the existing proof worker below its
approved ceiling. Baseline `2ac8fe5` checked memory only after exit and retained
an over-limit maximum compile. [Decision 0036](../docs/decisions/0036-live-proof-worker-memory.md)
freezes the circuits and changes only resource handling, failure classification,
tests and evidence. The shared worker now samples macOS `proc_pidinfo` every
10 ms, stops at seven eighths of the ceiling and retains post-exit peak checks.
Sampling remains fallible and is not a hard OS memory quota.

Raw records: `runs/w18-memory-budget-1792571904712696000`. The receipt audit
selects outer commands/rosters rather than double-counting nested workers; it
keeps failures, the original unattributed 1,800 seconds and conservative software
allowances. Measured selected time is 3,429.129 seconds; total prior charge rounds
to 5,540 seconds. Reserve 300 of the existing 7,200 seconds for this increment,
leaving 1,360 unreserved. No budget increase, concurrency refund or paid compute.
The [evidence](evidence/w18-live-memory-2026-10-21.json) pins the full raw audit,
source, ABI header, commands and costs.

The initial native stop exposed macOS group-signal `EPERM` on a completed child;
that attempt has no cutoff cost receipt and retains an explicit failure record.
An intermediate correction stopped two compiles below 384 MiB, but an existing
short-lived network-denial test exposed an exit-transition race. The final worker
allows one 10 ms exit grace and, on group `EPERM`, signals only its unreaped child
PID. Genuine signal permission failures still propagate. Another attempted
confirmation completed below its cutoff, so it failed the planned stop criterion;
its measured peak is 340,852,736 bytes. These failures are not deleted or relabeled.

Final command: `uv run --locked python runs/w18-memory-budget-1792571904712696000/experiment-04/run.py`
with the recorded isolated uv 0.9.18 tool. The unchanged pinned gnark binary first
compiles the eight-byte fixture in 0.760 seconds at 281,444,352 bytes peak RSS.
Two maximum-capacity cutoff tests exit -9 after 11.212 / 11.797 seconds at
1,891,549,184 / 1,963,802,624 bytes, both below their deliberately lowered 2 GiB
ceiling. Both report a live memory cutoff, no monitor failure and no wall timeout.
This validates stopping, not a complete maximum-input circuit or proof.

New tests cover the native ABI, cutoff boundaries, lost samples, sampling and
signal exit races, peak-only overshoots, standalone/staged callers and genuine
signal denial. Maximum-compilation accounting now distinguishes monitor failure
from resource failure, including a cutoff racing a normal exit. Final repository
and installed-package checks are recorded in the evidence after execution.

Final validation passes all 2,033 Python tests (29 new), `make check`, core
`make package-check` and combined `make package-check-comparison`, with installed
training and guard checks required and executed. Both packages use source identity
`d16500bf7fb47a7fce783dff1297b62ecf079b66c20371896ddaeb3c50eabc31`
before this final evidence update. A first lint failure is retained; its only
worker edit shortens a limitation string. The measured worker source remains
frozen and separately pinned. New scaling-controller failure classification is
validated offline; historical cryptographic runs keep their original identities.
The increment's timed commands plus conservative unrecorded-attempt/software
allowances consume 177.419 seconds inside the 300-second reservation. Keep the
entire reservation charged until a later audit. Exact-head hosted CI is separate.

## 2026-10-21 — W18 prefix coverage and exit-transition recovery

Hypothesis: exact Boolean prefix masks reduce complete-input compilation cost
without changing canonical bytes, public fields or the relation. Baseline
`7163ff1` retains failed 32,768-byte compilation. The diagnostic root is
`runs/w18-compile-profile-1792573233952310000`; the candidate root is
`runs/w18-prefix-coverage-1792573572212248000`. The
[evidence](evidence/w18-prefix-coverage-2026-10-21.json) pins source, environment,
heap sample, plans, proofs, costs and the retained failure before this prose.

The unchanged circuit's four-second heap sample attributes approximately 83% of
sampled live allocation to the per-encoded-byte padding comparison. Compilation
is stopped below a deliberately lowered 2 GiB ceiling after retaining the sample.
This is an early allocation diagnosis, not a complete-run memory or speed result.
[Decision 0037](../docs/decisions/0037-prefix-coverage-commitments.md) replaces
17/18-bit per-position comparisons with Boolean coverage flags, monotone Boolean
differences and exact sums. The canonical codec, eight valid byte/public vectors,
33 public fields, capacity roster and original rule/MLP/block circuits stay frozen.
The candidate's private assignment changes, so its source, setups and proofs have
new identities. Exhaustive checks cover 80 four-bit mask/count combinations and
three non-Boolean masks; all three focused Go tests pass.

Command: `uv run --locked python scripts/check_gnark_input_scale.py --binary runs/w18-prefix-coverage-1792573572212248000/build/probe --expected-binary 4a1b3033591885a78b770f1cc4edb6229f99dc807ea23e065a29ecba0147112e --output runs/w18-prefix-coverage-1792573572212248000/experiment-01`
using the retained isolated uv 0.9.18 executable. The 208.398-second command fails
after generating eight real proofs. Three small proofs verify and all 18 invalid
prover attempts, 33 public changes, field alias, altered proof and wrong key reject.
The five larger proofs exist, but their batch's unavailable memory sample causes
the controller to reject after a normal exit. Its failure and 44 worker receipts
remain unchanged. A separate five-compile diagnosis observes four native `ESRCH`
samples during normal exit; the original failed run did not retain native errno.

The shared worker now preserves native errno and only resolves an absent-process
sample after reaping an actual normal exit. A live child killed after losing a
sample and generic unresolved sample failures reject; peak checks remain. Nine
new Python cases cover errno, stale errno and normal/killed exit transitions,
including both standalone and budgeted callers. The 136 focused regressions pass.

Fresh recovery command: `uv run --locked python runs/w18-prefix-coverage-1792573572212248000/recovery-01/run.py`.
It pins the original binary/setup/proofs/assignments and corrected worker before
fresh verification of all five larger proofs. No setup or proving is repeated.
The 61.886-second recovery passes those checks and compiles capacity 32, then
records the failed maximum compile: exit -9, 60.889 seconds, 15,033,548,800-byte
peak RSS, live cutoff true, no monitor failure or timeout. The limit stops it below
16 GiB; no complete maximum circuit exists. Constraint counts for capacities
8 / 32 / 256 are 205,547 / 243,222 / 512,502, versus 206,049 / 244,924 / 525,403.
Capacity 32 remains compile-only. This evidence does not qualify a full encoder,
operational input enrollment, independent verification, setup or hiding.

Keep the prior 5,840-second charge, plus the entire 180-second diagnostic and
600-second candidate reservations, leaving 580 unreserved. No refunds, private
inputs, HF token access, paid jobs, external reviewers or hardware claims.
Repository and installed-package gates are recorded after execution. Preserve
the unrelated `.gitignore` edit. PR #72 stays draft and issue #19 stays open.

Final validation: all 2,042 Python tests, `make check`, `make package-check` and
`make package-check-comparison` pass, with installed train/guard checks executed.
Both package gates use source identity
`0ffac8fe2688464163f79987443e81f3aa696f94988440f5fef7090d8cd06ef5`
before this final evidence update. The diagnostic's timed commands plus allowance
charge 40.502 seconds inside its 180-second reservation; the candidate, failure,
recovery and validation charge 425.259 seconds inside its 600-second reservation.
The entire reservations remain charged. Final-head hosted verification is separate.

## 2026-10-21 — W18 compiler Boolean-cache candidate

Hypothesis: a packed bitmap for individual unit-coefficient Boolean wires reduces
compiler allocation without changing serialized relations. Baseline `9f17d33`
still fails maximum compilation. The [decision](../docs/decisions/0038-boolean-wire-cache-candidate.md)
freezes circuit/assignment/evaluation sources and changes only one upstream
compiler file in a separately inventoried module copy. The original module cache
and default dependency remain unchanged. The copied source retains Apache-2.0
licensing; no new dependency is introduced. Initial formatting failed because
copied directories were read-only; that preparation failure is retained, and only
the fresh copy's directories were made writable before any build or execution.

Raw root: `runs/w18-boolean-cache-1792575116013016000`. The
[evidence](evidence/w18-boolean-cache-2026-10-21.json) records numeric results and
source/build/protocol hashes before this prose. Full serialized R1CS bytes match
for seven fixtures: installation, rule, MLP, attention block and commitments at
capacities 8/32/256. Two new cache tests check constants, metadata aliases,
public/private/internal wire separation and rejection of two in each of 132 input
wires on both builds. The third new Go test emits the compared fingerprints.
Existing prefix/manifest/assignment tests also pass under the patched compiler.
These are finite fixture checks, not general compiler correctness.

Command: `uv run --locked python runs/w18-boolean-cache-1792575116013016000/run_experiment.py`
using isolated uv 0.9.18. It executes the frozen input controller with only its
resource deadline reduced from 420 to 330 seconds. The 304.056-second command
retains 51 workers, fresh setups, eight actual verified proofs, 18 invalid prover
witnesses, all 33 public-input mutations, field alias, altered proof and wrong key.
All available component checks pass. Both private and public vectors match the
prior prefix run, and the corrected worker matches that run's separate recovery.

Maximum compilation still fails: the 90-second wall limit kills it after
90.307 seconds, with 14,839,169,024-byte peak RSS. Neither the 14 GiB live cutoff
nor the 16 GiB ceiling is exceeded; there is no monitor failure. No complete
maximum circuit, count or proof is produced. Different failure triggers and
single runs do not establish a speed or memory improvement. The unchanged small
constraint counts and byte equality do not qualify a complete encoder or provide
independent verifier/security/setup/hiding evidence.

Reserve 550 seconds after the prior 6,620-second charge, leaving 30 unreserved
in the existing 7,200-second proving allocation. Keep the full reservation until
an explicit receipt audit. No token, HF job, private input, spend or scheduler.
Repository and installed-package checks follow; PR #72 and issue #19 stay open.

Final gates pass all 2,042 Python tests, core package checks and combined
train/guard package checks, with installed training and guard execution required.
Both package builds use source identity
`67c908543d4763cc36c558b76476d6f3183a7ac016f59b5c8d5c4f9f61948c48`
before this final evidence update. The literal unified patch is excluded from
prose whitespace checking because its context prefixes intentionally precede Go
tabs and blank lines. Applying it to the pinned original reproduces the measured
builder bytes. Both 1,264-file inventories and the fresh setup circuit fingerprints
match their pre-run records. Timed commands plus a 40-second ancillary allowance
charge 458.185 seconds inside the 550-second reservation; the full reservation
remains charged. Exact-head hosted verification is separate from local gates.

## 2026-10-21 — W18 late compile diagnosis

Hypothesis: more wall time could finish the compact-cache maximum compile within
the unchanged memory envelope; late snapshots identify the active phase if it
fails. Baseline `eb19201` timed out after 90.307 seconds. The
[decision](../docs/decisions/0039-late-compile-diagnosis.md) freezes the circuit,
canonical codec, evaluator, compiler patch and resource limits. Only a local
standard-library profiling hook is added to a fresh ignored source copy. Numeric
[evidence](evidence/w18-late-compile-2026-10-21.json) and raw receipts precede this
prose. Raw root: `runs/w18-late-compile-1792576443956021000`.

Rechecked receipt hashes retain the earlier 5,540-second charge and replace four
later reservations with actual commands plus their original allowances. The
6,641.365-second result rounds up to 6,660. Reserve 500 of the remaining 540
seconds; authority stays at 7,200. No concurrency refund or extra spend is assumed.

Commands: `uv run --locked python runs/w18-late-compile-1792576443956021000/build_and_check.py`
and `uv run --locked python runs/w18-late-compile-1792576443956021000/run.py`, using
isolated uv 0.9.18 and the pinned offline Go environment. All six existing Go tests
pass; the seven serialized circuit fingerprints match the earlier candidate.
The smallest input compile passes before the maximum attempt. No fresh setup,
proving or verification is run; earlier proofs keep their own binary identities.

The execution roster takes 57.741 seconds. Maximum compilation exits -9 after
56.651 seconds, with a live memory cutoff and 15,037,972,480-byte peak RSS. There
is no wall timeout or monitor failure; the observed peak remains below 16 GiB.
The 40-second goroutine/heap snapshot completes in about 15 ms. The main goroutine
is in deferred range-check recomposition. Sampled live space totals approximately
6.86 GiB: instruction allocation accounts for 39.48%, hint construction 23.66%,
linear-expression addition 13.30% and range-check commit 5.52%. Hint construction
accounts for 62.19% of sampled live objects. These are allocation-site samples,
not retaining paths or complete-run attribution. All three `go tool pprof -top`
analyses succeed. Instrumentation can perturb timing and memory.

The 80-second snapshot is absent, no maximum circuit/count/proof exists, and the
conditional unchanged-binary confirmation is skipped because diagnosis failed.
The complete 1,264-file patched-module inventory, 12 probe files, worker, runners
and both binary hashes remain unchanged. The fresh run occupies about 52 MiB and
all retained runs about 18.4 GiB of filesystem allocation. No HF token, job,
private input, upload, external review or scheduler. PR #72 stays draft; #19 stays
open. Next, review a bounded HF capacity plan or a source-backed memory reduction
before another maximum attempt. Repository and package gates follow.

Final validation passes all 2,042 Python tests, `make check`, `make package-check`
and `make package-check-comparison`, including required installed train/guard
execution. Both packages use source identity
`6a3614d7b4487cf1f31243687e8ae9d9784663e834cfbd2dfcebacb43b2519ce`
before this final evidence update. Timed outer commands and the full 40-second
ancillary allowance fit the 500-second reservation; exact values and receipt
hashes are in the evidence. Keep the full reservation charged pending audit.
An unauthenticated HF hardware inventory refresh is retained locally as next-step
preparation; no job or token access occurs. Exact-head hosted CI is separate.

## 2026-10-21 — W18 Linux fallback preparation

Hypothesis: the approved L4 host's additional RAM can compile the unchanged
maximum-input relation. Baseline `d70a029` retains the Mac memory-cutoff result.
The [numeric record](evidence/w18-hf-compile-2026-10-21.json) precedes this prose;
raw root: `runs/w18-hf-compile-1792577568568485000`. Rechecking every late-diagnosis
receipt adopts its actual 200.412 seconds plus the previously retained 6,660,
rounding to 6,870. Reserve 300 local seconds for implementation checks and gates,
leaving 30. The unchanged cloud ceiling is one job, one hour, two dollars.

The separate Linux controller reuses the existing private file/hash/termination
helpers without modifying the Mac worker. It checks the container's memory limit,
denies socket creation and alternate syscall ABIs, drops inherited credentials
and file descriptors, samples procfs RSS and retains kernel peak/CPU/wall results.
It first checks actual network denial, then the eight-unit constraint count,
then maximum compilation and conditional fresh-process confirmation. Failure
skips dependent cases. Compilation never sets backend/proof qualification true.

The bootstrap admits only pinned public Hallmark sources, the unchanged reviewed
compiler-cache candidate and Go 1.26.8. It verifies the patched module inventory
and all seven small circuit fingerprints before the large attempt. The official
Python 3.12.15 slim-bookworm OCI image and Linux Go archive are digest pinned.
Docker Python's MIT and CPython's PSF/historical grants were reviewed and retained;
the image is not independently rebuilt. No system packages or model code are
installed. Read-only HF authentication/Jobs access pass using the owner's local
token; zero earlier Hallmark jobs are found. The token stays on the control plane.

Initial local fixtures pass 18 tests with four Linux kernel checks skipped; adding
container-limit cases passes 22 with the same four skips. The first full software
gate passes before a bootstrap ordering adjustment that checks container RAM
before downloading Go. An initial lint overlong string and mypy inference error
were corrected; no research job ran. Final repository/package gates and real Linux
kernel checks are still required before a cloud submission at this checkpoint.

Final local preparation gates pass 2,068 tests with four Linux-only kernel skips,
plus core and combined train/guard packages. Both package builds use source
identity `6f3da4b3c1ca7fa0c35eb34523c9d46544a07f8a545d828f57aafb23025a28ef`
before this evidence update. Thirty new tests include real Linux network denial,
credential isolation, timeout, memory cutoff and missing-monitor checks; their
kernel-dependent cases have not run on the Mac. Publish this exact source and
require the Linux CI execution before freezing/submitting a cloud job. The full
reservation remains charged. No cloud job has run at this checkpoint.

Linux push CI on `f63946fa0313409076408b421b858f96aa2c6334` executes all 30 new
tests, including the four real kernel checks, with no skips in that test file.
Run `39584591191`, core job `119170243496`, passes. The existing 87 Linux skips
belong to other platform/optional-runtime tests. Review found that a bootstrap
command timeout could discard captured diagnostics; the bootstrap now emits the
stage, elapsed-time receipt and captured logs after termination before propagating
the failure. The Linux worker is unchanged. Recheck the final source and packages
before publishing the correction and freezing a job manifest.

The corrected bootstrap passes another full local gate (2,068 tests, four Linux
skips) and both package gates with installed train/guard execution. Package source
identity is `f05cb8df00c19c9319eac92a40db56029779f87e85d92af0b51ca1a2958dcbd4`
before the final evidence update. Preserve all earlier preparation checks too.
Reserve the previously unreserved 30 seconds for local cloud-control receipts,
making this increment's total reservation 330 and leaving zero unreserved within
7,200. This changes allocation, not authority. Numeric command totals and hashes
are retained before submission. Cloud execution remains unsubmitted here.

## 2026-10-21 — W18 maximum compilation reproduced on HF

The frozen hypothesis passes its compile-only criterion: unchanged commitment
circuits at capacity 32,768 compile twice with 40,015,721 constraints. The
[numeric evidence](evidence/w18-hf-compile-2026-10-21.json) and local
`result-audit.json` precede this prose. Mutable delivery paths are that evidence,
STATE, this ledger and the stale storage-authority sentence; no runtime, circuit,
codec, evaluator or frozen input changes follow execution.

Job [6ad896465275124786e2490b](https://huggingface.co/jobs/abdelstark/6ad896465275124786e2490b)
uses public source commit `de05e111e92d356a1c472abe7ceb934660a4ccc1`, a pinned
Python image and Go archive, the existing optional Boolean-cache patch and the
same 1,264-file module inventory. All six Go tests and seven small serialized
circuit fingerprints pass. The Linux binary is
`e3f8c85e996612b38abb72345097f441c35904a43b850cc63192d89969541904`.
Local `job-manifest.json` and `job-spec.json` freeze the exact bootstrap command;
the local `control_job.py submit` is called once, followed only by `poll`/`logs`.
The post-run audit rechecks every public source pin, bootstrap/spec hash, logged
result, small fingerprint, build identity, prerequisite and resource receipt.

Actual socket denial passes first. The eight-unit compile takes 0.725 seconds.
Maximum and fresh-process confirmation take 250.655/244.997 seconds, with kernel
peak RSS 21,509,857,280/21,476,012,032 bytes. Their sampled peaks are
21,510,488,064/21,475,983,360 bytes, below the 26-billion-byte stop. There is no
timeout, memory cutoff or lost monitor. The container reports 29,999,996,928 bytes
of memory. Maximum count reproduction is not serialized-circuit reproduction:
this command retains no maximum circuit, setup, witness, proof or verifier result.
It leaves `qualified_backend` and `full_input_proof` false and status incomplete.

The provider reports COMPLETED, 4 scheduling seconds, 552 running seconds and
557 total seconds. At the launch API's 13,333 micro-USD/minute, rounding all total
time up to ten minutes gives a conservative USD 0.133330 estimate. No invoice was
available. This CPU compilation used no GPU; no private input, token in worker,
checkpoint upload, retry, scheduler, system-package install or external reviewer was involved.
The local control receipts total 15.933833 seconds; preparation, control and full
ancillary allowance total 293.657855 seconds. The final `make check-spec` passes
in 0.452052 seconds, bringing the increment to 294.109907 within its 330-second
reservation. The prior
charge was 6,870 seconds. Retain the whole reservation and all failures; zero local
proving seconds remain unreserved and the single HF job is consumed.

Before launch, all 28 exact-runtime-head jobs passed on `de05e11`: push
`39585332622` and PR `39585339006`. Push attempt one failed the macOS Python 3.13
train-package gate and cancelled 3.14 by fail-fast. Its retained outer log does
not establish a cause. Rerunning only failed jobs on the same head passed; the PR
run passed initially. Local gates already passed 2,068 tests (four Linux-only
skips) and both installed-package modes; real Linux kernel cases passed in CI.
Final evidence-only delivery still needs its own hosted head checks.

Next prepare bounded streaming for the current 256 MiB proof-artifact reader,
then a fresh setup/proving plan with explicit memory, storage and resource terms.
This result supplies no maximum proof cost. Full encoder/layer normalization,
operational enrollment, independent verifier/security/hiding/setup review and
genuine hardware remain separate missing gates. PR #72 remains draft and #19 open.

## 2026-10-21 — W18 bounded artifact streaming

The previous gate delivered commit `dd34b9b` with all 28 exact-head jobs passing:
push `39587810550` and PR `39587816547`. The next hypothesis is that adapter
streaming preserves exact small-proof behavior without whole-file adapter copies.
Baseline: `dd34b9b`; raw root: `runs/w18-stream-artifacts-1792580363962082000`.
The [numeric evidence](evidence/w18-stream-artifacts-2026-10-21.json) precedes prose.
Mutable paths are the Go file reader/test, shared Python file helper, scaling
controller, future bootstrap test inventory and their tests/docs. Circuit, codec,
compiler patch, fixtures and size caps stay fixed.

`timed.py baseline-link` reproduces acceptance of a symbolic link. Its failed test
is retained. The candidate uses bounded Go decoding, regular/single-link checks,
exact decoder counts and detected metadata/path changes. Python worker costs now
hash bounded chunks; scaling setup files carry path/hash/size pins and copy into
exclusive private files. A wrong source digest or failed copy prevents the next
worker and preserves evidence. Earlier tiny controllers keep their byte interfaces.

`timed.py focused` passes 13 Python tests. An 8 MiB copy stays below the fixed
3 MiB traced-allocation assertion. `go-test-build` and `go-boundaries` build/run
seven Go tests under the existing Mac worker, including eleven reader cases and
a tiny actual setup/prove/verify unit fixture. That fixture rejects a changed
public input and trailing bytes on each real artifact type; its temporary proof
files are not retained. `go-probe-build` builds the separate candidate binary.
`reverify` pins the prior eight-unit commitment result via published evidence,
copies its exact key/proof/input files, verifies in a fresh worker and rejects an
appended proof byte. Fresh costs and artifacts are retained. No maximum proof or
new setup campaign occurs.

The audited prior total is 7,135.886826 seconds, including the original 5,540 base
charge and all later ancillary allowances. Rounding to 7,136 leaves 64 seconds;
reserve all 64, with eight for overhead. This removes only unused reservations
and nested rounding, not measured work or allowances. The validation wrapper
caps commands at remaining time. Standard `make check` may use its normal mypy
cache; no timing comparison is claimed. Repository and core package gates follow.
The installed train/guard matrix remains required in exact-head CI. No HF job,
private upload, additional spend or authority increase occurs.

The full `make check` passes lock, lint, formatting and type checks, then reaches
the declared 39-second stop at 94% of pytest, with no test failure reported before
termination. The timeout is retained, not reported as a pass. Commands total
48.312088 seconds; with the eight-second allowance the charge is 56.312088, leaving
7.687912 inside the reserved 64. The package gate has not run. An owner question
requests 120 additional Mac-only validation seconds at zero spend, with no new HF
job. Source publication may remain draft while that validation gap is explicit;
it does not finish W18 or qualify a backend.

## 2026-10-21 — W18 source-backed setup capacity review

The preceding streaming commit `d03f9d1` passes all 28 exact-head hosted jobs:
push `39589743317`, PR `39589749300`. The local 39-second timeout and unrun package
gate remain explicit; the 120-second validation question is still pending.

Without launching a research job, inspect the pinned gnark/gnark-crypto setup,
serialization, domain and point-storage code. Hypothesis: source-derived lower
bounds can identify a concrete prerequisite before spending another maximum run.
Baseline: the two 40,015,721-constraint compilation reports. Mutable paths are
this state/ledger, the numeric evidence and a proposal; no implementation,
evaluator, circuit, source dependency or resource cap changes.

The [numeric evidence](evidence/w18-setup-capacity-2026-10-21.json) precedes the
[proposal](proposals/backend-v1/setup-capacity-options.md). Raw source snippets,
hashes and the result are in its fresh `raw_directory`. The explicit 26-stage
sum agrees with the closed form. Source-pin and arithmetic verification takes
0.003302 seconds; it allocates no FFT domain or point array and runs no Go build,
setup, proof or model. Charge the 0.003302 seconds within the existing reservation's
7.687912-second remainder, retaining its full overhead allowance. No additional
runtime reservation or authority is claimed.

The default setup uses domain size 67,108,864. Its encoded Z vector alone requires
3,221,225,428 bytes, so the current 256 MiB artifact cap cannot support it. Two
twiddle tables and two coset tables occupy 8,589,936,192 bytes. G1 conversion holds
at least 9,663,676,416 Jacobian bytes and 6,442,450,944 affine bytes simultaneously,
while the domain remains live for the proving key. Their sum is at least
24,696,063,552 bytes of backing storage, not measured RSS or a total peak bound.
The circuit, scalars/digits, extra points, masks, G2 and allocator/GC overhead are
excluded. Do not add the historical compile peak to this source bound.

The first concrete candidate is chunked G1 conversion inside the existing scalar
loop, preserving its window/table/digit choices and output ordering. It trades
additional inversions for bounded Jacobian temporaries; performance is unmeasured.
Inspection rejects the same rationale for G2: that implementation already writes
each result directly to affine. The proposal freezes the required point equivalence,
small-circuit/proof regressions and resource-plan gates before a maximum attempt.
No patch, extra job, private upload, larger host or full-backend qualification is
authorized or supplied by this analysis.

`make check-spec` passes all 51 sections, 18 invariants, 10 RFCs, 40 work items and
106 dependency edges. Source/arithmetic verification plus this documentation gate
charge 0.473966 seconds, bringing the prior streaming increment to 56.786053 of
its 64 reserved seconds, with the eight-second overhead allowance retained.
No runtime-code gate is represented as newly passed by this documentation check.

## 2026-10-21 — W18 optional G1 patch and frozen point evaluator

The source-review commit `aa6f9c7` passes all 28 exact-head hosted jobs:
push `39591302057`, PR `39591308540`. PR #72 remains draft. The selected hypothesis
is that bounding G1 Jacobian temporaries per worker preserves all output points.
Mutable candidate path: gnark-crypto's `ecc/bls12-381/g1.go` in an isolated copy;
the default module, circuit and existing compiler-cache patch remain unchanged.
The new frozen evaluator is `research/probes/gnark/patches/g1_batch_test.go`.
The [numeric record](evidence/w18-g1-candidate-preparation-2026-10-21.json) precedes
this account; its raw directory retains the protocol, commands and failed copies.

Inspection finds that `parallel.Execute` partitions by `runtime.NumCPU()`, not
`GOMAXPROCS`. Add `runtime.NumCPU()*4096+1` to the fixed length roster and assert
that a worker crosses the 4,096-point boundary. The evaluator compares coordinates
and compressed/uncompressed encodings with separate scalar multiplication, checks
input immutability and emits ordered-output digests for cross-build comparison.
Generator/infinity bases and deterministic zero/one/minus-one/wider/repeated
scalars are frozen before candidate evaluation. These are public synthetic inputs.

`go test -mod=readonly -count=1 -v -run
'^TestG1BatchEquivalence$/^generator$/^n3$' patches/g1_batch_test.go` passes against
the unchanged upstream module in 2.112453 seconds including compilation. This is
only the three-point baseline, not full-roster execution. An initial module-copy
patch check rejects an unchanged source despite a zero patch exit; retain that
copy and charge a conservative one second. A fresh explicit patch check passes
in 0.020287 seconds. Preparation of a writable fresh module copy and full 1,869-file
inventory takes 1.009594 seconds; only the intended G1 source differs.

The candidate's same small command, with its separate modfile, fails to compile
in 1.332136 seconds: the original `min` cost variable shadows the built-in used by
the chunk loop. Preserve its patch, source and compiler error. Rename only that
variable to `minCost`, keeping the cost expression/comparisons. The correction
passes Go parsing and exact patch application in 0.110213 seconds. It has not
been built or executed. The optional patch is disabled by default and absent
from the HF bootstrap. See [decision 0042](../docs/decisions/0042-bounded-g1-preparation.md).

These commands charge 5.584684 seconds inside the existing reservation, leaving
1.629263 seconds before the final documentation check. All earlier ancillary
allowances remain charged. The pending 120-second question remains unanswered;
no extra time, cloud job, setup/proof attempt or spend is inferred. Full corrected
point equivalence, serialized circuit fingerprints, small proof negatives and
allocation/latency measurements remain open before any maximum attempt.

`make check-spec` then passes all 51 sections, 18 invariants, 10 RFCs, 40 work
items and 106 edges in 0.944539 seconds. This increment totals 6.529223 seconds;
0.684723 remains inside the existing reservation. No corrected-candidate build
or full local repository/package gate is claimed from that documentation check.

## 2026-10-21 — W18 approved local gates and corrected G1 validation

The owner approved 120 additional Mac-only validation seconds under
[decision 0043](../docs/decisions/0043-approved-local-validation-extension.md).
Keep the previous proving reservation, 39-second timeout and failed G1 build
charged and unchanged. No new HF job or spend is permitted by this increment.
Hypothesis: the corrected optional G1 candidate preserves points and serialized
circuits while bounding its Jacobian temporary. Baseline: the same admitted
Boolean-cache build with unchanged gnark-crypto. Mutable paths are a fresh full
module copy, the separate diagnostic fixture and evidence/documentation; default
dependencies, circuits, point evaluator and artifact caps remain fixed.

The [numeric record](evidence/w18-approved-validation-2026-10-21.json) precedes
this account. Its raw directory retains the frozen protocol, complete 1,869-file
candidate inventory, separate modfiles/binaries, command receipts and stdout.
`make check` passes lock, lint, format, mypy and 2,081 tests with four platform
skips and one warning. Software conformance matches 156 cases; 32 genuine-evidence
cases remain unavailable. `make package-check` passes the core installed-wheel
gate. These close the previously outstanding local gates without deleting the
earlier timeout. Required train/guard execution remains in final-head hosted CI.

The corrected three-scalar candidate builds and passes first. Explicit
`go test -mod=readonly -modfile=VARIANT.mod -count=1 -v patches/g1_batch_test.go`
then passes all 16 generator/infinity cases in each variant. Every output agrees
with separate scalar multiplication and all ordered output hashes agree between
builds. On this 16-CPU host, the 65,537-point case proves that an actual worker
span exceeds 4,096. Input immutability and both encodings pass. No evaluator or
point threshold changes after observing the candidate.

Build both complete probe test binaries and invoke
`-test.run '^Test(CircuitFingerprints|ArtifactReaderBoundaries|ArtifactReaderRealProof)$' -test.v`
through the existing network-denied Mac worker. All seven serialized circuit
fingerprints match. Both variants pass eleven reader-boundary cases and the
existing cubic setup/prove/verify unit fixture, rejecting changed public input
and trailing bytes on circuit/key/proof artifacts. The unit test deletes its
temporary proof/key files; this is not a retained commitment proof campaign.

Freeze `patches/g1_alloc_test.go` and its allocation plan before running baseline
then candidate, once each, with
`-test.run '^$' -test.bench '^BenchmarkG1Batch262145$' -test.benchtime 1x -test.benchmem`.
Both produce the same ordered compressed-point digest for 262,145 deterministic
public scalars. Baseline/candidate allocated bytes are 80,061,592 / 76,999,144;
allocation counts are 250 / 2,622; operation nanoseconds are 3,697,711,000 /
3,687,230,916; worker peak RSS is 96,813,056 / 79,331,328 bytes. Report the increased
allocation count as well as the lower byte/RSS observation. One sample each cannot
establish statistical performance, whole-setup memory or maximum feasibility.

The initial 14 commands consume 86.664973 seconds; with five seconds of ancillary
allowance, 91.664973 of the new 120 seconds is charged. Final documentation/package
receipts extend this same counter in the evidence. Prior unused time is not
reclaimed. The optional G1 patch remains disabled by default. A fresh small
commitment proof/negative campaign, an explicit multi-GiB setup/storage/host plan,
the complete encoder and independent verification/security/setup evidence remain
open. W18 is incomplete and PR #72 remains draft.

Final `make check-spec` and core `make package-check` pass, including the newly
tracked diagnostic/evidence/documentation. The wheel hash is unchanged from the
initial core package gate. All 16 commands consume 93.747097 seconds; the total
charge with the five-second allowance is 98.747097, leaving 21.252903 seconds.
The raw initial result and final evidence remain separate immutable records.

## 2026-10-21 — W18 fresh small proofs with the corrected G1 candidate

The owner approved the prepared ten-minute Mac-only campaign under
[decision 0044](../docs/decisions/0044-approved-small-g1-proof-campaign.md).
Reserve 600 additional local seconds: two rosters capped at 240 seconds each,
100 seconds for preflight/build/replay/validation, and 20 seconds ancillary
allowance. Preserve the old 7,200-second proving charge and separate 120-second
validation reservation. No maximum attempt, HF job or spend is authorized here.

Hypothesis: the corrected G1 candidate preserves actual small commitment proof
acceptance/rejection with fresh setup keys. Baseline: frozen native vectors,
circuit fingerprints and the existing rejection roster. Mutable paths are a
fresh local controller copy, build/output directories and evidence; candidate
patch, circuit semantics and all expected rejections remain fixed. The
[numeric evidence](evidence/w18-g1-small-proofs-2026-10-21.json) precedes this prose.
Its raw directory retains the protocol, diff, source/module/build identities,
inputs, proofs, setup files, output inventories and every command/cost receipt.

Preflight verifies all 1,869 gnark-crypto and 1,264 gnark module files against
their frozen inventories. The complete checkout occupies 32,369,647,616 allocated
bytes according to `du -sk`, leaving 10,580,025,344 within the 40 GiB envelope;
reserve eight GiB for the two outputs. The global audit retains a conservative
7,200-second non-proof charge against 504.086 seconds of located top-level actual
elapsed receipts, including duplicates, plus unitemized historical preparation
and validation. Alongside prior proving, validation and this new reservation,
15,120 seconds are charged/reserved within the 21,600-second envelope. This is
conservative accounting, not complete timing instrumentation of old commands.

Build the candidate with the existing offline Go environment, both explicit
module replacements and `-trimpath -buildvcs=false -mod=readonly`. The new binary
first passes the existing 18-case cubic installation/proof fixture. Copy the
input-scaling controller without changing vectors or negative cases; set its
deadline to 240 seconds, remove only maximum compilation and explicitly report
`not-run-small-proof-only`. Freeze that exact diff and source before execution.

`execute.py first` and `execute.py repeat` each pass all 50 workers: eight actual
proofs at capacities 8 and 256, 18 rejected malformed witnesses, all 33 rejected
public-field changes, field alias, altered proof and wrong key, plus capacity-32
compilation. Serialized setup circuits match the frozen fingerprints, including
the independent wrong-key setup. Both runs use identical native vectors; their
three corresponding setup keys differ. Roster elapsed times are 213.851414 /
212.831651 seconds; peak worker RSS is 1,264,451,584 / 1,248,935,936 bytes.

After each roster, enroll exact key/proof/native-public-input pins outside its
output directory. Pass the enrollment manifest hash explicitly to `execute.py
replay-first` / `replay-repeat`; all eight proofs per run verify in fresh workers.
This is caller-pinned local replay with the same verifier library, not independent
verification or authenticated operational key enrollment. The original proofs and
keys remain local. Randomized proof/key bytes are not expected to reproduce.

The initial proof-result record charges 443.057732 command seconds plus the
20-second allowance. Final summary and software/package receipts extend the same
counter. No failures or old reservations are refunded. The 33-field component
retains its synthetic profile pin; full classifier/encoder binding, maximum setup
and proof, accepted setup lineage, independent security/hiding/verification and
genuine hardware remain unavailable. Keep W18 open and PR #72 draft.

Final `make check` passes all 2,081 tests with four platform skips and one warning,
plus lock/lint/format/type/spec, 156 software conformance cases and the admission
fixture. The core `make package-check` passes; required train/guard execution
remains an exact-head hosted gate. All command receipts total 494.800234 seconds;
with the 20-second ancillary allowance, 514.800234 of the approved 600 seconds is
charged, leaving 85.199766. Final retained checkout allocation is 33,955,835,904
bytes, below 40 GiB; the two proof outputs retain 718,090,504 / 718,090,659 logical
bytes. No source/runtime code or default dependency was changed by this campaign.

## 2026-10-21: maximum circuit retained on the Mac; larger proof campaign prepared

Under the owner's explicit instruction to continue without repeated approval
pauses, decision 0045 records standing execution authority. The original study
budgets, historical charges and failed runs are preserved.

Raw roots: `runs/w18-max-artifacts-1792586199768569000` and
`runs/w18-max-inventory-corrected-1792586489227090000` (the exact corrected root is
also retained in the numeric evidence). Commands: the frozen `execute.py` runs
`fixture`, `export-8`, `inspect-8`, `export-32768`, `inspect-32768`; the separate
`check_inventory.py` reloads the same externally pinned maximum circuit and
reports commitment sizes. All worker argv, environments, limits and hashes are
in the individual `plan.json` and `cost.json` files.

The 18-case cubic fixture passes. Seven small R1CS hashes are unchanged. Maximum
export succeeds in 79.599983 seconds with 17,674,289,152 bytes peak process RSS;
the 2,566,643,378-byte R1CS hash is
`cd91ff70e706fb2d3aecb83d40eae5d82c34611923b67b16a539f69291d0e489`.
Fresh inspection succeeds in 2.677502 seconds at 10,367,139,840 bytes RSS and
matches counts and bytes. Expanded inventory reports 48,477,333 total wires,
one commitment and 22,366,059 private committed wires. Raw numeric results precede
this entry in `research/evidence/w18-maximum-artifacts-2026-10-21.json`.

The first Go build missed one changed helper call in a test; corrected tests pass.
A separate inventory controller named `inspect.py` shadowed Python's standard
library and failed before a worker started. That directory is preserved; the
fresh corrected inventory run passes. No result from either failure is reused
as a passing measurement.

Decision 0046 prepares one larger-memory HF L4 job with public pinned source,
the same optional compiler/G1 patches, a tiny real-proof gate, three maximum-profile
proofs and nine invalid witnesses, followed by changed-public/key/proof rejection.
Native fixture generation matches the existing canonical encoder at eight count
boundaries. The Linux controller keeps its original compile-only defaults and
accepts an explicit bounded proof budget. New actual Linux kernel checks await
hosted CI; local macOS appropriately skips them. Stubbed scheduling tests do not
count as proof evidence. No cloud job, maximum setup or maximum proof has run in
this increment yet. Full local/package validation is recorded separately below.

Local `make check` passes, including specification/admission checks and all 156
software conformance cases; 32 full-evidence obligations remain unavailable. Core
`make package-check` passes from staged reviewed paths, retaining
`dist/package-check-uohk4ae6`; the earlier snapshot omitted untracked additions and
failed its link audit in `dist/package-check-j5rz7zoe`. Both diagnostics remain.
The installed wheel hash is
`470b8e55660e613b02f47562768ac11dbd7311586d696846031c7e9edbac2956`.
Train/guard execution and new Linux kernel cases remain exact-head hosted gates.
A temporary private synthetic-output bucket has been created; no job is submitted
yet. The GitHub repository remains public.


## 2026-10-21: W18 merge and maximum-output storage correction

PR #72 merged as `89c2585619d4404d702439a46c825c8f8241cef9` under the owner's
explicit merge instruction. All 28 final candidate checks and all 14 merged-main
checks pass. Issue #19 stays open; staged implementation does not qualify a
backend. The repository remains public. Exact CI receipts are retained in
`runs/w18-hf-maximum-1792587065696475000/ci-*-final.json`.

The L4 attempt stayed queued and was cancelled at 315.345 observed seconds. Its
empty bucket was removed. The cheaper 32-vCPU/256-GB CPU fallback passes module
verification, seven circuit fingerprints and five tiny worker cases, then exports
the maximum circuit in 141.093003386 seconds. The mounted bucket's integrity check
raises `changed file` before a maximum cost record is written. No maximum RSS/CPU
measurement, setup or proof is available. Retain the failed outcome.

All 37 files (2,566,700,934 bytes) are downloaded and all available worker-cost
pins checked. The circuit's 2,566,643,378 bytes exactly match the separately
retained Mac hash. All local hashes are checked again before removing the bucket.
The exact changed stat field is unknown. [Raw numeric evidence](evidence/w18-hf-storage-failure-2026-10-21.json)
records the source/job identities, missing costs and conservative charges;
`runs/w18-hf-cpu-maximum-1792587855982096000` retains logs, downloads and cleanup.
Neither provider timing nor the estimate is an invoice.

[Decision 0048](../docs/decisions/0048-local-disk-proof-execution.md) keeps file
validation strict and runs workers on local ephemeral disk, followed by a bounded
source-pinned copy of complete and failed artifacts. The four retention cases
cover failed output preservation, exclusive destination creation, file/directory
links and excess size. Fifty-five focused tests pass (five platform skips).
`make check` passes 2,110 tests, five Linux-only skips and one warning; pytest takes
39.83 seconds. Software conformance matches 156 cases; 32 full-evidence obligations
remain unavailable. The core package check and corrected cloud run are pending
at this commit. The protocol reserves copy time separately and stays under the
standing USD 10 campaign ceiling; no further owner permission is required.


## 2026-10-21 — Optional parallel Pedersen setup preparation (W18 / #19)

Hypothesis: disjoint parallel scalar multiplications preserve the original setup's
ordered key bytes and inputs. Baseline: the pinned serial Pedersen setup and prior
small circuit/proof roster. Mutable path: only `ecc/bls12-381/fr/pedersen/pedersen.go`
in a separate dependency copy; the optional bootstrap admits that exact source
hash and checks the full inventory. The active maximum cloud baseline is unchanged.

Raw numbers and identities were saved before this prose in
[evidence](evidence/w18-pedersen-parallel-2026-10-21.json). Sixteen sizes at one/two/four
workers match the complete serial setup bytes, preserve bases and pass the race
detector. Disclosed scalar randomness and related bases are insecure fixtures only.
The fresh 50-case real-proof roster passes in 185.746 seconds, peak RSS
1,246,986,240 bytes: eight valid proofs; 18 malformed witnesses; 33 public changes;
field alias; altered proof; wrong setup key. All eight proofs replay under retained
input/key pins. An unmodified-dependency build passes another 43 cases in 1.810
seconds. Neither verifier is independently implemented. No maximum proof, speedup,
hiding or general concurrency/security claim follows.

Exact local commands and receipts are under
`runs/w18-pedersen-parallel-1792590827210193000/`: `run_fixture.py`, `run_small.py`,
`replay_unmodified.py`, `local-evidence.json`, `result.json`,
`small-campaign-result.json`, `first-acceptance.json`, `first-enrollment.json` and
`unmodified-replay/result.json`. Use the locked `.venv/bin/python`. Protocols and
all sources were pinned before their respective executions. The actual command
wall times total 236.841 seconds; retain the full 780-second reservations until
a receipt audit. Zero cloud spend for this local preparation.

The optional bootstrap rejects altered payloads and compile-only use; its focused
suite passes 38 tests with five Linux-only skips. `make check` passes 2,111 tests
with five Linux-only skips and one warning; the core `make package-check` passes.
Hosted validation remains pending. See [decision 0049](../docs/decisions/0049-parallel-pedersen-setup.md).
Review and retain the active baseline's terminal result before deciding on one
bounded follow-up. Keep the USD 10 total ceiling and preserve all failures.

PR #75 merged as `27ce26d43702cd5ba38c5fb0ebf7433dbf1c72e8`, with all 28 candidate
checks successful. Merged workflow `39612502992` reports success. Its Linux 3.12
train-job logs contain 35 passing training tests and a passing installed train
package check; all ten job steps passed, though final job metadata was stale.
A targeted rerun of that single job completes attempt 2 with all 14 jobs passing;
the original status/log receipts remain retained.
Repository visibility remains public.


## 2026-10-21 — Serial maximum timeout retained; parallel candidate launched (W18 / #19)

The local-disk serial baseline ended ERROR. Its export passes in 166.812 seconds,
with the same 2,566,643,378-byte circuit SHA-256 as the Mac. Setup takes
3,603.555 seconds, is killed by the wall deadline, and peaks at 57,714,008,064
bytes kernel RSS. Memory-limit and monitor-failure flags are false. The generic
controller budget exception does not establish a memory failure. The
[raw numeric evidence](evidence/w18-maximum-baseline-timeout-2026-10-21.json)
records CPU, cost and artifact pins before this prose.

The 4,944,217,141-byte partial proving key establishes only that serialization
started after Setup returned; no isolated phase time was measured. It is unusable
and unenrolled. No complete verification key, maximum proof or maximum replay
exists. All 45 files / 10,077,572,415 bytes were downloaded, worker/retention pins
checked and local hashes rechecked before the temporary bucket was removed.
Exact commands and receipts remain in `runs/w18-hf-local-disk-1792588507859979000`:
`control.py poll`, `control.py logs`, `retain.py download`, `retain.py cleanup`,
`terminal.json`, `download-verified.json` and `bucket-cleaned.json`.

After this retention gate, the parallel candidate began HF job
`6ad8ce6a0a35baab53a1dff0` from exact source
`b5debd6e226b41755c702e0c490937bd7f5600f4`. All 28 checks on that source pass;
one push job required a targeted rerun after stale final metadata. Its
[launch record](evidence/w18-parallel-maximum-launch-2026-10-21.json) pins inputs,
CI, launcher and whole-checkout storage. Prior conservative compute 281 cents,
new compute reservation 480 cents and temporary-storage reserve 200 cents total
961 cents, below the unchanged 1,000-cent ceiling; these estimates are not an
invoice. The new run is active, with no result claimed. Frozen source, circuit,
inputs, outcome roster and limits remain unchanged while it runs.


## 2026-10-21 — Bounded artifact buffering (W18 / #19)

Hypothesis: 64 KiB standard-library buffers preserve exact circuit/key/proof bytes
and the existing file-boundary rejection contract. The maximum baseline reached
key serialization before timing out; the dependency encoder performs individual
48/96-byte point writes on the supplied writer. This motivates buffering, but
provides no isolated phase or maximum performance measurement. Mutable paths are
`research/probes/gnark/main.go` and its artifact tests; relation, randomness,
serialization and evaluator thresholds remain fixed. The cloud source is unchanged.

A prospective local protocol and source hashes precede execution in
`runs/w18-buffered-artifacts-1792593992352000000`. Its original adapter suite passes
in 5.359 seconds. The first candidate fixture panics because it reuses a decoded
circuit for another CBOR decode; its logs remain retained. Using a fresh decoder
for each load passes the entire probe suite in 4.236 seconds, with 652,345,344
bytes cumulative child peak RSS. These one-off command times are not a speedup
comparison. [Raw evidence](evidence/w18-buffered-artifacts-2026-10-21.json)
contains source/environment identities and failure records before this prose.

The writer flushes even when serialization fails, propagates serialization/flush
errors and syncs only after success. The limiter wraps the buffered reader so
prefetch cannot disguise an underreading decoder. Exact byte fixtures cross both
64 KiB boundaries; real circuit, key and proof bytes match direct memory
serialization. A child-only file-size limit exercises a real flush failure.
Existing alias, malformed, trailing, changed-file, circuit fingerprint and real
proof checks pass. Abrupt termination can lose at most one buffered prefix;
partial artifacts remain failures. `make check` passes 2,111 tests, five Linux-only
skips and one warning in 42.590 seconds. Core `make package-check` passes in
7.514 seconds; source snapshot `52759220c43f4512c49c8d9f64b0b55b9172eca887203386c4100039dd5c0040`.
The retained package snapshot precedes this evidence-only validation update.
No optional installed train/guard claim follows from that core package check.


The separate frozen large-key diagnostic in
`runs/w18-key-io-1792594326143760000` passes for both adapters: each reloads and
reserializes the same 77,522,639-byte proving key to its independently pinned
SHA-256. Baseline read/write phases take 15.603/1.691 seconds; buffered phases
take 15.080/0.095 seconds. Full worker times are 18.199/15.980 seconds, with
279,609,344/280,150,016 bytes peak RSS. This single sequential pair has warm
caches and is diagnostic only, with no maximum-scale extrapolation. The protocol,
runner, source pins, worker plans and costs precede this report; raw evidence
retains all values. No cloud job or private input was used for this diagnostic.

PR #76 merged as `a73c47b287ccabc13ca8387c7352afdf7d23e999` after all 28
checks passed on `9085a098ef27c42921268b3631985406a26062a8`. The merged-main
workflow is pending. The running maximum experiment retains its original source.


The hosted workflow previously ran Python fixtures without executing the Go
adapter suite. A Linux proof-artifact job now installs the already reviewed
Go 1.26.8 archive into runner-temporary storage after checking its exact SHA-256,
verifies the locked module closure and runs all Go probe tests. It uses two
threads, a 1 GiB Go soft memory target and a ten-minute job timeout. No dependency
or circuit change is introduced. Linux runtime evidence remains pending.


## 2026-10-21 — Verified parallel-setup and artifact-I/O delivery (W18 / #19)

[Delivery evidence](evidence/w18-proof-artifact-delivery-2026-10-21.json) precedes
this prose. PR #76 is merged as `a73c47b287ccabc13ca8387c7352afdf7d23e999`: all
28 candidate jobs and all 14 merged-main jobs pass. One merged job's completed
steps/logs had stale final metadata; its targeted rerun passes on attempt 2.
PR #77 is merged as `247e46a9dd75ab6b98dfd6c054643575d38adba0`: all 30 candidate
jobs and all 15 merged-main jobs pass. The newly added Linux Go suite passes
all 12 top-level tests, including the real file-size-limit flush failure.
Exact CI JSON and logs are retained in
`runs/w18-buffered-artifacts-1792593992352000000`. No maximum-result or backend
qualification claim follows; the active HF run still uses source `b5debd6`.


## 2026-10-21 — Live controller progress without changing evidence (W18 / #19)

The baseline bootstrap displays controller logs only when the long child process
exits. Hypothesis: relay bounded chunks of the existing captured files while
retaining their full bytes/hashes, exit codes and deadlines. The prospective
protocol and source pins are in the run directory linked from the
[raw evidence](evidence/w18-live-progress-2026-10-21.json). Mutable source is the
bootstrap waiter and a fixed worker-start diagnostic in the maximum controller.
The current cloud run and its evaluator are unchanged.

Three real-subprocess fixtures require a parent acknowledgement before the child
can finish, preserve split UTF-8/non-UTF-8 bytes and a large tail, retain exit
code 3, and keep a deadline as a timeout failure. The 59 focused tests pass, with
five actual-Linux checks appropriately skipped on the Mac, in 5.560 seconds.
Complete capture files still determine receipt hashes; the unrelayed tail is
emitted before the receipt. This is diagnostic plumbing, not proof evidence.
The next hosted workflow also rejects changes to `go.mod`/`go.sum` after its
Go dependency and test steps. `make check` passes 2,114 tests, five Linux-only
skips and one warning in 45.428 seconds. All 156 software conformance cases match;
32 full-evidence obligations remain unavailable. Core `make package-check` passes
in 7.862 seconds; its retained snapshot precedes this validation-only evidence
update. Hosted checks are pending.

## 2026-10-21 — Bounded integer normalization proofs (W18 / #19)

Hypothesis: constrain the missing mean, variance, inverse and affine normalization
component against an exhaustive frozen integer oracle. Baseline: the existing
attention block omits normalization. Mutable paths are the new normalization
relation, fixture builder/controller and tests, shared command dispatch, and its
future HF source inventory. Older graph relations and fixtures stay fixed.
The [numeric evidence](evidence/w18-integer-normalization-2026-10-21.json) and raw
`runs/w18-normalization-1792598409580756000` protocols/source snapshots precede
this report. Pass criterion is all 289 valid proofs plus the frozen rejection
roster and old circuit fingerprints. Owner standing approval covers the bounded,
zero-cost Mac campaign; there is no cloud job, private input or model download.

The separate Decimal oracle checks every intermediate for all 289 input pairs.
Thirteen focused Python checks and the smallest real-proof Go test pass before
the campaign. Its 605 workers pass: 289 proofs, 289 fresh verifier processes,
25 expected rejections and two fresh setups. Each proof is 244 bytes. All eleven
trace fields, all four public fields, both input range boundaries, an int32 trace
overflow, a field alias, noncanonical decimal text, changed/trailing proof bytes
and the wrong setup key reject. Setup pins are retained before proof execution.
All 4,524 recorded worker-file hashes are rechecked after completion.

Controller time is 73.013 seconds, peak worker RSS is 24,182,784 bytes and the
measured output before the final report is 110,769,391 bytes. This is one
diagnostic run; detailed host observation was collected after execution. It is
not a statistical performance comparison or floating pretrained-model agreement.
All 13 Go tests, including frozen older circuit fingerprints, pass in 4.194 seconds.
`make check` passes 2,127 tests, five platform skips and one warning in 46.453
seconds. The first package attempt excludes untracked new files and fails a
source-archive documentation link. Staging the exact reviewed files makes the
unchanged core package gate pass in 8.970 seconds; both attempts remain intact.
The package snapshot precedes this validation-only evidence update.

Commands: `scripts/build_gnark_normalization_fixture.py`, the retained locked
`go test`/`go build` plan, and `scripts/check_gnark_normalization.py` with the
binary/fixture pins in `proof-plan.json`. The candidate defines rounded integer
mean/variance, epsilon one, a finite inverse-square-root table and signed affine
parameters. It supplies neither the complete encoder nor its admission,
independent verifier, accepted setup ceremony, security/hiding review or safety
quality. Next: compose the declared normalization with a complete admitted
encoder graph under a fresh experiment. No historical proof is reassigned.

PR #78 is merged as `e97659f2695a8f0bfdc6a14159bc1554a46cc329`, with all 30
candidate checks and all 15 [main checks](https://github.com/AbdelStark/hallmark/actions/runs/39629089766)
passing. Candidate attempt 2 reruns only one job whose completed successful logs
and steps had stale final metadata. Original logs and exact delivery receipts
remain in `runs/w18-live-progress-1792596929687095000`.

## 2026-10-21 — Maximum commitment proof and cross-host replay pass (W18 / #19)

The [numeric result](evidence/w18-parallel-maximum-result-2026-10-21.json) derives
from the retained raw files before this prose. The frozen parallel candidate
`b5debd6e226b41755c702e0c490937bd7f5600f4` completes HF job
`6ad8ce6a0a35baab53a1dff0`. It keeps the original unbuffered adapter and capture
behavior, not the later merged changes. The baseline serial setup timeout,
mounted-storage guard failure and queued L4 cancellation remain retained failures.
There is no statistical speedup comparison or automatic retry.

All 47 controller cases pass their expected outcomes. The maximum batch completes
three valid witnesses and nine invalid-witness checks. Fresh cloud verification
accepts the three proofs and rejects every one of the 33 changed public fields,
a field alias, changed proof and a different setup key. The independently frozen
Mac circuit hash remains `cd91ff70e706fb2d3aecb83d40eae5d82c34611923b67b16a539f69291d0e489`.
The relation has 40,015,721 constraints. Each proof is 292 bytes; the proving key
is 14,069,971,419 bytes and the verification key 2,320 bytes.

Export takes 141.238 seconds, setup 2,195.581 seconds and the twelve-case proof
batch 1,791.308 seconds. Controller time is 4,199.004 seconds; the provider reports
4,390 seconds including scheduling and retention. Peak worker RSS is
87,162,712,064 bytes, below the recorded 150-GB sampled stop and 170-GB limit.
The 48-thread bound on a declared 32-vCPU/256-GB CPU host is unchanged. These are
whole-worker observations, including loads/serialization where applicable;
there are no isolated per-proof timings. The batch has only 8.692 seconds of
wall-time headroom. One success does not establish a reliable latency bound.

All 361 bucket files totaling 35,943,971,183 bytes are downloaded. Every worker
cost pin and retention-manifest pin matches. Both prospective Mac plans pass:
38 cases with the patched binary in 1.852 seconds and 38 with the unmodified
dependency binary in 1.710 seconds. They use the three native public assignments
frozen before cloud execution and separately retained proof/key pins. All local
file hashes are rechecked before removing the temporary bucket; authenticated
absence is confirmed. No cloud compute remains active.

Commands are retained under `runs/w18-hf-parallel-1792592951066985000`:
`control.py poll`, `retain.py download`, `.venv/bin/python replay_local.py`,
`.venv/bin/python replay_default.py`, `retain.py cleanup`, and
`summarize_result.py`. The public summary distinguishes the formatted input-file
hash from the submitted input bytes. All actual experiment inputs, raw costs,
failed attempts and source/environment hashes remain local.

Using the launch-recorded price and provider duration with one extra billed
minute gives a conservative new-compute estimate of USD 2.38. Prior compute is
bounded at USD 2.81; adding the USD 2 storage reserve gives USD 7.19 against the
unchanged USD 10 campaign ceiling. This is not an invoice.

This clears the complete-input commitment component gate. The synthetic fixed
profile, 33-field relation and shared gnark verifiers establish neither the
100-field classifier statement nor the complete encoder, independent security
review, accepted setup ceremony, hardware evidence or policy quality. Next is
the complete admitted encoder graph, using fresh identities and explicit costs;
the bounded normalization result above supplies only one required component.


## 2026-10-21 — Complete native synthetic encoder (W18 / #19 preparation)

[Numeric evidence](evidence/w18-complete-encoder-native-2026-10-21.json) is saved
before this prose. The baseline is PR #79's merged
`4e3258194b2484cfe69614f100587aee4459e946`; all 30 candidate checks and all 15
merged-main checks pass. The repository remains public.

The new graph composes byte and position embeddings, query/key/value attention,
residual/normalization, a three-unit ReLU feed-forward layer, a second
residual/normalization, masked pooling and two integer logits. The fixture pins
exact input, classifier, program, arithmetic, constants and tokenizer records.
All nine existing operators execute without optional dependencies. This is an
owned synthetic graph with explicit piecewise attention and finite two-feature
normalization tables, not an export of pretrained weights.

The smallest eight vectors match 546 tensors. Every normalization-table entry is
checked separately using 80-digit Decimal arithmetic, and all embedding classes
and masks have independent formula and padding-isolation checks. Tests also reject
rehashed malformed constants, unknown tokenizer recipes, altered bindings and
int32 overflow before rescaling. A later chunk can change the strict verdict.

The retained campaign is `runs/w18-complete-encoder-1792600222383037000`.
Source/config/fixture pins precede execution. Candidate-02 snapshots caller dictionaries before validation. The final
`candidate-03` also checks canonical private-trace decoding; its two fresh repetitions preserve every
tensor for 32,767- and 32,768-byte inputs, check the separate oracle, and reproduce
complete trace bytes exactly. Initial successful runs and three failed fixture
checks remain retained. Failures were a tuple passed to the canonical wire codec,
an incorrect expected exception for an already-rejected oversized transcript,
and a test pair whose synthetic scores were equal. Model constants and the frozen
conformance fixture did not change to improve a score.

Commands are the retained `candidate-02/controller.py`/`worker.py`, plus
`scripts/check_encoder_vectors.py` with the separate fixture hash. This campaign
uses the Mac, one worker, a 120-second bound per repetition, 8 GiB RSS and
128 MiB per file, within decision 0051's zero-cost envelope. There is no cloud
job or new asset. These are diagnostic software timings, not a latency study.
`make check` passes 2,181 tests, five platform skips and one warning in 80.885
seconds; pytest takes 78.28 seconds. All 54 added checks execute. The core
package gate passes in 12.389 seconds and runs all eight frozen encoder cases
from a fresh installed wheel. Optional installed-train/guard checks are left to
the hosted matrix. The package snapshot precedes this validation-only prose and
evidence update. Full graph proof lowering,
independent verifier/security review, actual encoder training/quality and genuine
hardware evidence remain missing; W18 and W12 are not closed.


The final native worker repetitions take 10.033 and 9.953 seconds respectively
(see raw costs for full precision); kernel peak RSS and each forward-pass timing
are retained in the numeric evidence. Each large case compares 638,976 tensors
across 16,384 chunks. The complete trace files are 15,865,297 and 15,865,306 bytes.
These timings are diagnostic, with one Mac and two repetitions, not a distribution
or proof-cost result.

## 2026-10-21 — Complete synthetic encoder proof at eight-byte capacity (W18 / #19)

[Numeric evidence](evidence/w18-complete-synthetic-encoder-proof-2026-10-21.json)
precedes this prose. PR #80's native graph merged as
`1f7294c31deed06beb5eb4a245a532143b9ec40e`; all 30 candidate and 15 merged-main
jobs passed. The new frozen experiment is
`runs/w18-complete-encoder-proof-1792601385038675000`. Its hypothesis is that the
complete fixed native graph, including both normalizations and byte commitment,
can produce actual proofs for the existing 100-field statement. Earlier component
proofs are the baseline, not evidence of this composition.

Decision 0052 fixes the 39-node, two-feature graph and all 121 scalar intermediate
values per two-token chunk. Native fixture SHA-256 remains
`8d0551ac2e9c9e2527004bc4a33392844963ffcb17b9589139448db3f068ee7d`.
The new circuit holds four chunks/eight content bytes. Its profile still declares
32,768 bytes: the tested capacity is a strict subset. The fifteen frozen witnesses
cover the eight native vectors, seven/eight-byte boundaries and equality, adjacent
and extreme int32 thresholds. Threshold variants rebind classifier identity,
input salt and digest; they are prespecified conformance checks, not calibration.

The direct lowering uses shared pinned log-derivative lookup tables. Native and
separate Decimal-oracle values agree before assignments are emitted; Go solver
checks then pass all fifteen traces and reject a changed final tensor. Both
dependency builds pass all fifteen top-level Go tests and preserve all seven
older circuit fingerprints exactly. The measured build uses the previously
reviewed boolean-cache and parallel-Pedersen candidate; the three patch hashes
are checked before compilation. No dependency or model is downloaded.

The real campaign passes 632 logical outcomes in 124 worker processes: fifteen
proofs, fifteen fresh positive verifiers, 484 changed private tensor values, ten
other input/padding mutations, 100 changed public fields, six other rejection
cases and two setups. Invalid witnesses must produce the curve's unsatisfied-
constraint error; unrelated prover errors cannot count as expected rejections.
The two setup runs reproduce the same circuit and produce different verification
keys. All proofs are 292 bytes. The circuit has 361,950 constraints and SHA-256
`ad8bf9b2e401fdebc2e0a0077cf3dd91a8004e1b3ec9e408534087701cd0328a`.

Controller time is 152.844730333 seconds. Initial setup takes 45.333014833 seconds
and the 509-case batch takes 53.836207542 seconds; peak worker RSS is
1,126,514,688 bytes. Limits are 1,800 seconds overall, 900 per setup/batch worker,
four threads, one research worker, 8 GiB RSS and 8 GiB output. Retained artifact
bytes before the result file total 550,926,095. The initial allocated checkout is
93,738,176,512 bytes, below the 128 GiB retained limit. No cloud job or spend occurs.
These are one-host diagnostic observations, not a latency distribution.

The original-dependency Mac build separately passes 117 compatibility checks:
all fifteen proofs, all 100 public-field mutations, a field alias and changed
proof bytes. Its protocol and inputs are pinned before execution. All 2,718
recorded worker-file hashes across both runs are rechecked. This uses the same
gnark verifier implementation, so it is not independent verification.

Commands are the retained launch record invoking `scripts/check_gnark_encoder.py`
with explicit binary/fixture SHA-256 pins and a fresh output directory, followed
by `default-replay.py`. Preparation preserves one test failure (683 expected
assignment fields versus the correct 685) and one incorrect local patch-file
lookup. Neither changes the frozen model, witness roster or expected outcome.
The runner's declared wall/CPU budget is passed explicitly before its first run;
offline fault tests cover worker failure, altered inputs and malformed reports.
Future HF bootstrap inventories include the embedded graph file, with a larger
size allowance only for that data file; no old cloud source/run is modified.

The acyclic identity order remains program and circuit/key before completed
classifier enrollment. The circuit exposes classifier/context binders and a
signed threshold; a relying party must independently authenticate the full
program/profile/weights/threshold/key/setup enrollment and expected public tuple.
Synthetic tags and local setup do not provide that authority. There is no trained
model quality, accepted ceremony, independent security/hiding qualification or
hardware evidence. Neither W18 nor W12 is closed. The next gate is full-capacity
encoder export/cost measurement under a new bounded plan, then maximum proving.

Local validation passes: `make check` takes 83.758 seconds (2,202 tests, five
Linux-only skips, one existing fork warning; pytest 78.41 seconds), and
`make package-check` takes 8.657 seconds. Both reproducible source archives and
wheels match; installed core checks pass. The wheel hash is unchanged because
this milestone adds optional probes, not a core runtime change. The package
snapshot precedes this validation-only evidence/prose update. Installed train
and guard fixtures remain the hosted matrix obligation.
