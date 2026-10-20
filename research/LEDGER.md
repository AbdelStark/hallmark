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
