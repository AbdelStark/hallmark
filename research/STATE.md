# Research state

Updated: 2026-10-20. Phase: research software foundation in a public repository, not a deployed or cryptographically verified system. AI-assisted code and research initialization.

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

## Not implemented or established

TEE evidence, operational registry enrollment/authoring/rotation, ZK proving/verification, full bundle assembly and combined verification, independent verifier implementation, real safety-policy dataset/evaluation, encoder/teacher/student training, proof/compiler qualification, public release licence, production service, deployment, partner approval or any safety guarantee. CI definitions alone are not hosted green checks. CODEOWNERS and agent rules are not enforced sandboxing or branch protection.

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
W37 / #38 is locally validated; exact-head hosted delivery is next. Then implement
#39 traceability and reassess the actual remaining prerequisites. The current work map has 106 dependency edges, including W04's reuse
of W03 file references and W07's opening/signed-registry dependencies on W02/W08;
the historical 102-edge publication audit is unchanged. Re-evaluate dependencies
before #39 spec traceability and the remaining admission/integration work. Research,
real proofs, genuine hardware and independent verification remain required for
the full MVP.

Next: [W13 / issue #14](https://github.com/AbdelStark/hallmark/issues/14), prepare an admission proposal for exactly one policy/use case: relying party, approved data/licence inventory, group split and power, fixed candidate roster, success/failure criteria and resource budget. The draft proposes one English single-turn prompt-injection assay; the owner and relying party have not adopted it. Use [PROGRAM](PROGRAM.md), [ML-PLAN](../docs/ML-PLAN.md) and [EVALUATION](../docs/EVALUATION.md). No data/model download, external inference, GPU job or background campaign until the missing authority is recorded.

In parallel only when explicitly authorized, qualify a tiny real proof graph before selecting a larger encoder. The goal is a measured statement and cost record, not a mock end-to-end demo. Preserve the hybrid hardware/ZK split and the B1/B2 trust distinction in [SPEC](../docs/SPEC.md).

## Resume

Inspect git state and actual installed environment, read the latest ledger entry, then take one falsifiable gate. Run the smallest relevant negative test. Update this state and the ledger with evidence, limits and a concrete next step. Research-run authority remains [bootstrap-only](AUTHORITY.json); repository visibility follows [AGENTS.md](../AGENTS.md).
