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
