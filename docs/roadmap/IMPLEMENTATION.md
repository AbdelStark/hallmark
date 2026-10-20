# Implementation Tracker — 2026-10-20

Generated from the specification corpus in [PR #1](https://github.com/AbdelStark/hallmark/pull/1), pinned commit `ad058ad74a6dc23ae95cc523d7bf468a06d4c4ce`. Every v1 implementation deliverable is filed: 40 bounded work issues plus 10 RFC tracking issues. Implementation issues represent one contributor PR; trackers are dashboards. This tracker is updated as gates land. Closing an issue requires its acceptance evidence, not just merging code.

The [machine-readable work map](work-items.json) contains exact scopes, tests, labels, milestones, dependencies and live URLs. The [source requirement disposition](../spec/11-requirements.md#source-requirement-disposition) maps original intent to this scope. Later extensions are explicitly excluded; genuine hardware, three classifier kinds and independent verification remain mandatory.

## Status and authority

`blocked` labels identify prerequisite work or an unresolved owner gate. W13 can prepare its proposal now, but data/policy/resource admission awaits approval. W36 is merged; public hosted CI now executes successfully. The initial billing block is historical. Filing issues supplies no compute, data, sharing or release authority. Reviewer issues do not add collaborators or contact anyone.

Local bootstrap checks: 29 tests, strict typing/lint/format, file links and installed distribution passed. [Raw corpus evidence](../../research/evidence/spec-bootstrap-2026-10-20.json) and [live publication audit](../../research/evidence/spec-publication-2026-10-20.json) record the scope. The initial hosted spec checks had no executed steps because of the account billing/spending-limit block; final-head status is attached to the PR. No billing settings were changed.

Current dependency graph: 105 edges. W02 now depends on W05 for the typed external
request expectation used by context hashing; the original 102-edge publication
audit is preserved. W04 reuses W03 file-reference contracts, so that implementation dependency is now explicit.
W07 embeds signed registry snapshots and therefore now explicitly depends on W08.
Next sequence: deliver W08 (#9), then W07 (#8), W09 (#10) and W11 (#12), subject to their actual prerequisites.

Merged delivery: [W01 evidence](../../research/evidence/w01-wire-2026-10-20.json),
[W30 evidence](../../research/evidence/w30-errors-2026-10-20.json) and
[W36 evidence](../../research/evidence/w36-ci-2026-10-20.json). W03 is merged in [PR #55](https://github.com/AbdelStark/hallmark/pull/55). Its
[main CI](https://github.com/AbdelStark/hallmark/actions/runs/39406784978) passed
on `f844342c18af85d8cb0b1160521c58938f9d87ea`.
W04 is merged in [PR #56](https://github.com/AbdelStark/hallmark/pull/56). Its
[main CI](https://github.com/AbdelStark/hallmark/actions/runs/39409355612) passed
on `f456b4a749d795f2f22f19e5d2ae5fd90b099539`.
W05 is merged in [PR #57](https://github.com/AbdelStark/hallmark/pull/57). Its
[main CI](https://github.com/AbdelStark/hallmark/actions/runs/39411367808) passed
on `1d344d55b44efae9b0232c46d4553dfe59f49288`.
W02 is merged in [PR #58](https://github.com/AbdelStark/hallmark/pull/58). Its
[main CI](https://github.com/AbdelStark/hallmark/actions/runs/39412814966) passed
on `fbd6c90f65e5e535f8dfb839012f1bd3bd544097`.

W06 is merged in [PR #59](https://github.com/AbdelStark/hallmark/pull/59). Its
[main CI](https://github.com/AbdelStark/hallmark/actions/runs/39414504221) passed
on `774887d0e40b82459d4f7ca8657400d9905577ad`.
W08's [local evidence](../../research/evidence/w08-enrollment-2026-10-20.json)
passes; exact-head hosted delivery is next. Operational root custody remains open.

## Milestone: v0.2

| # | Work | Title | Area | Priority | Effort | RFC | Status | Depends on |
|---|---|---|---|---|---|---|---|---|
| [#2](https://github.com/AbdelStark/hallmark/issues/2) | W01 | wire: implement strict v1 encoding and domain-separated identities | wire | p0 | m | 0001 | Merged; PR #52 | None |
| [#3](https://github.com/AbdelStark/hallmark/issues/3) | W02 | wire: implement transcript and complete-input opening contracts | wire | p0 | m | 0001, 0003 | Merged; PR #58 | [#2](https://github.com/AbdelStark/hallmark/issues/2), [#6](https://github.com/AbdelStark/hallmark/issues/6) |
| [#4](https://github.com/AbdelStark/hallmark/issues/4) | W03 | wire: add immutable model and generation manifest schemas | wire | p0 | s | 0001, 0006 | Merged; PR #55 | [#2](https://github.com/AbdelStark/hallmark/issues/2) |
| [#5](https://github.com/AbdelStark/hallmark/issues/5) | W04 | wire: add classifier and numerical profile manifest schemas | wire | p0 | m | 0001, 0003, 0005 | Merged; PR #56 | [#2](https://github.com/AbdelStark/hallmark/issues/2), [#4](https://github.com/AbdelStark/hallmark/issues/4) |
| [#6](https://github.com/AbdelStark/hallmark/issues/6) | W05 | wire: add policy and external request expectation schemas | wire | p0 | s | 0001, 0007 | Merged; PR #57 | [#4](https://github.com/AbdelStark/hallmark/issues/4), [#5](https://github.com/AbdelStark/hallmark/issues/5) |
| [#7](https://github.com/AbdelStark/hallmark/issues/7) | W06 | wire: add receipt, epoch and proof artifact schemas | wire | p0 | m | 0001, 0005, 0006 | Merged; PR #59 | [#4](https://github.com/AbdelStark/hallmark/issues/4), [#5](https://github.com/AbdelStark/hallmark/issues/5), [#6](https://github.com/AbdelStark/hallmark/issues/6) |
| [#8](https://github.com/AbdelStark/hallmark/issues/8) | W07 | wire: add bounded offline bundle and result schemas | wire | p0 | m | 0001, 0007 | Open; blocked | [#7](https://github.com/AbdelStark/hallmark/issues/7), [#9](https://github.com/AbdelStark/hallmark/issues/9) |
| [#9](https://github.com/AbdelStark/hallmark/issues/9) | W08 | registry: implement external trust and rollback-safe enrollment | registry | p0 | m | 0002 | Local gates passed; hosted delivery pending | [#2](https://github.com/AbdelStark/hallmark/issues/2), [#4](https://github.com/AbdelStark/hallmark/issues/4), [#5](https://github.com/AbdelStark/hallmark/issues/5), [#6](https://github.com/AbdelStark/hallmark/issues/6) |
| [#10](https://github.com/AbdelStark/hallmark/issues/10) | W09 | registry: sign snapshots and implement rotation and retirement | registry | p0 | m | 0002 | Open; blocked | [#9](https://github.com/AbdelStark/hallmark/issues/9) |
| [#14](https://github.com/AbdelStark/hallmark/issues/14) | W13 | research: prepare the single-policy data and resource admission | research | p0 | m | 0004, 0006, 0008 | Open; blocked | None |
| [#31](https://github.com/AbdelStark/hallmark/issues/31) | W30 | operations: add typed errors and redact all trust-boundary failures | operations | p0 | m | 0008 | Merged; PR #53 | None |
| [#34](https://github.com/AbdelStark/hallmark/issues/34) | W33 | conformance: freeze v1 golden and adversarial evidence corpus | conformance | p0 | m | 0001, 0009 | Open; blocked | [#2](https://github.com/AbdelStark/hallmark/issues/2), [#3](https://github.com/AbdelStark/hallmark/issues/3), [#4](https://github.com/AbdelStark/hallmark/issues/4), [#5](https://github.com/AbdelStark/hallmark/issues/5), [#6](https://github.com/AbdelStark/hallmark/issues/6), [#7](https://github.com/AbdelStark/hallmark/issues/7), [#8](https://github.com/AbdelStark/hallmark/issues/8), [#9](https://github.com/AbdelStark/hallmark/issues/9), [#10](https://github.com/AbdelStark/hallmark/issues/10), [#31](https://github.com/AbdelStark/hallmark/issues/31) |
| [#37](https://github.com/AbdelStark/hallmark/issues/37) | W36 | delivery: enforce core, train and gated integration CI | delivery | p1 | m | 0010 | Merged; PR #54 | None |
| [#38](https://github.com/AbdelStark/hallmark/issues/38) | W37 | delivery: make private builds reproducible and verify inventories | delivery | p1 | m | 0010 | Open | None |
| [#39](https://github.com/AbdelStark/hallmark/issues/39) | W38 | delivery: enforce spec traceability and contributor documentation | delivery | p2 | m | 0010 | Open | None |

## Milestone: v0.3

| # | Work | Title | Area | Priority | Effort | RFC | Status | Depends on |
|---|---|---|---|---|---|---|---|---|
| [#11](https://github.com/AbdelStark/hallmark/issues/11) | W10 | classifiers: implement the complete-input integer rule program | classifiers | p1 | m | 0003 | Open; blocked | [#3](https://github.com/AbdelStark/hallmark/issues/3), [#5](https://github.com/AbdelStark/hallmark/issues/5), [#14](https://github.com/AbdelStark/hallmark/issues/14) |
| [#12](https://github.com/AbdelStark/hallmark/issues/12) | W11 | classifiers: implement the byte-feature integer MLP runtime | classifiers | p1 | m | 0003 | Open | [#3](https://github.com/AbdelStark/hallmark/issues/3), [#5](https://github.com/AbdelStark/hallmark/issues/5) |
| [#13](https://github.com/AbdelStark/hallmark/issues/13) | W12 | classifiers: execute the qualified encoder integer graph | classifiers | p1 | l | 0003, 0005 | Open; blocked | [#5](https://github.com/AbdelStark/hallmark/issues/5), [#19](https://github.com/AbdelStark/hallmark/issues/19) |
| [#15](https://github.com/AbdelStark/hallmark/issues/15) | W14 | research: implement lineage-preserving data admission and splitting | research | p0 | m | 0004 | Open; blocked | [#14](https://github.com/AbdelStark/hallmark/issues/14) |
| [#16](https://github.com/AbdelStark/hallmark/issues/16) | W15 | research: implement frozen baseline and MLP training comparisons | research | p1 | m | 0003, 0004 | Open; blocked | [#12](https://github.com/AbdelStark/hallmark/issues/12), [#15](https://github.com/AbdelStark/hallmark/issues/15) |
| [#17](https://github.com/AbdelStark/hallmark/issues/17) | W16 | research: train and export one compact encoder reproducibly | research | p1 | l | 0003, 0004 | Open; blocked | [#13](https://github.com/AbdelStark/hallmark/issues/13), [#15](https://github.com/AbdelStark/hallmark/issues/15), [#16](https://github.com/AbdelStark/hallmark/issues/16) |
| [#18](https://github.com/AbdelStark/hallmark/issues/18) | W17 | research: add frozen slice reports and group-aware comparisons | research | p1 | m | 0004 | Open; blocked | [#15](https://github.com/AbdelStark/hallmark/issues/15), [#16](https://github.com/AbdelStark/hallmark/issues/16) |
| [#19](https://github.com/AbdelStark/hallmark/issues/19) | W18 | proofs: qualify a pinned backend and exact full-graph profile | proofs | p0 | l | 0005 | Open; blocked | [#5](https://github.com/AbdelStark/hallmark/issues/5), [#14](https://github.com/AbdelStark/hallmark/issues/14) |
| [#20](https://github.com/AbdelStark/hallmark/issues/20) | W19 | proofs: prove and verify the complete byte-rule decision | proofs | p1 | m | 0003, 0005 | Open; blocked | [#11](https://github.com/AbdelStark/hallmark/issues/11), [#19](https://github.com/AbdelStark/hallmark/issues/19) |
| [#21](https://github.com/AbdelStark/hallmark/issues/21) | W20 | proofs: prove and verify the bounded integer MLP decision | proofs | p1 | m | 0003, 0005 | Open; blocked | [#12](https://github.com/AbdelStark/hallmark/issues/12), [#19](https://github.com/AbdelStark/hallmark/issues/19) |
| [#22](https://github.com/AbdelStark/hallmark/issues/22) | W21 | proofs: prove and verify the entire qualified encoder | proofs | p1 | l | 0003, 0005 | Open; blocked | [#13](https://github.com/AbdelStark/hallmark/issues/13), [#17](https://github.com/AbdelStark/hallmark/issues/17), [#19](https://github.com/AbdelStark/hallmark/issues/19) |
| [#23](https://github.com/AbdelStark/hallmark/issues/23) | W22 | hardware: qualify genuine epoch and accelerator evidence | hardware | p0 | l | 0006 | Open; blocked | [#4](https://github.com/AbdelStark/hallmark/issues/4), [#7](https://github.com/AbdelStark/hallmark/issues/7), [#10](https://github.com/AbdelStark/hallmark/issues/10), [#14](https://github.com/AbdelStark/hallmark/issues/14) |
| [#24](https://github.com/AbdelStark/hallmark/issues/24) | W23 | hardware: bind loaded model and protected response path | hardware | p0 | l | 0006 | Open; blocked | [#4](https://github.com/AbdelStark/hallmark/issues/4), [#23](https://github.com/AbdelStark/hallmark/issues/23) |
| [#25](https://github.com/AbdelStark/hallmark/issues/25) | W24 | hardware: gate release with all enrolled integer classifiers | hardware | p0 | m | 0006, 0007 | Open; blocked | [#6](https://github.com/AbdelStark/hallmark/issues/6), [#11](https://github.com/AbdelStark/hallmark/issues/11), [#12](https://github.com/AbdelStark/hallmark/issues/12), [#13](https://github.com/AbdelStark/hallmark/issues/13), [#24](https://github.com/AbdelStark/hallmark/issues/24), [#26](https://github.com/AbdelStark/hallmark/issues/26) |
| [#26](https://github.com/AbdelStark/hallmark/issues/26) | W25 | receipts: implement bounded encrypted proof spool and recovery | receipts | p0 | m | 0007 | Open; blocked | [#7](https://github.com/AbdelStark/hallmark/issues/7), [#14](https://github.com/AbdelStark/hallmark/issues/14), [#23](https://github.com/AbdelStark/hallmark/issues/23) |
| [#32](https://github.com/AbdelStark/hallmark/issues/32) | W31 | operations: add bounded local events and immutable failure records | operations | p1 | s | 0008 | Open | [#31](https://github.com/AbdelStark/hallmark/issues/31) |
| [#33](https://github.com/AbdelStark/hallmark/issues/33) | W32 | operations: measure full-path cost with raw samples and caps | operations | p1 | m | 0005, 0008 | Open; blocked | [#14](https://github.com/AbdelStark/hallmark/issues/14), [#19](https://github.com/AbdelStark/hallmark/issues/19), [#32](https://github.com/AbdelStark/hallmark/issues/32) |

## Milestone: v1.0

| # | Work | Title | Area | Priority | Effort | RFC | Status | Depends on |
|---|---|---|---|---|---|---|---|---|
| [#27](https://github.com/AbdelStark/hallmark/issues/27) | W26 | receipts: assemble complete offline C0 evidence bundles | receipts | p1 | m | 0007 | Open; blocked | [#8](https://github.com/AbdelStark/hallmark/issues/8), [#10](https://github.com/AbdelStark/hallmark/issues/10), [#20](https://github.com/AbdelStark/hallmark/issues/20), [#21](https://github.com/AbdelStark/hallmark/issues/21), [#22](https://github.com/AbdelStark/hallmark/issues/22), [#25](https://github.com/AbdelStark/hallmark/issues/25), [#26](https://github.com/AbdelStark/hallmark/issues/26) |
| [#28](https://github.com/AbdelStark/hallmark/issues/28) | W27 | verification: verify enrollment, receipt and hardware claim A | verification | p0 | m | 0002, 0006, 0007 | Open; blocked | [#9](https://github.com/AbdelStark/hallmark/issues/9), [#10](https://github.com/AbdelStark/hallmark/issues/10), [#23](https://github.com/AbdelStark/hallmark/issues/23), [#27](https://github.com/AbdelStark/hallmark/issues/27) |
| [#29](https://github.com/AbdelStark/hallmark/issues/29) | W28 | verification: verify B1 and B2 proofs and all-pass composition | verification | p0 | m | 0003, 0005, 0007 | Open; blocked | [#3](https://github.com/AbdelStark/hallmark/issues/3), [#20](https://github.com/AbdelStark/hallmark/issues/20), [#21](https://github.com/AbdelStark/hallmark/issues/21), [#22](https://github.com/AbdelStark/hallmark/issues/22), [#28](https://github.com/AbdelStark/hallmark/issues/28) |
| [#30](https://github.com/AbdelStark/hallmark/issues/30) | W29 | verification: expose typed v1 CLI and supported library API | verification | p1 | m | 0007 | Open; blocked | [#8](https://github.com/AbdelStark/hallmark/issues/8), [#27](https://github.com/AbdelStark/hallmark/issues/27), [#29](https://github.com/AbdelStark/hallmark/issues/29), [#31](https://github.com/AbdelStark/hallmark/issues/31) |
| [#35](https://github.com/AbdelStark/hallmark/issues/35) | W34 | conformance: build a separately implemented offline verifier | conformance | p0 | l | 0009 | Open; blocked | [#34](https://github.com/AbdelStark/hallmark/issues/34), [#29](https://github.com/AbdelStark/hallmark/issues/29) |
| [#36](https://github.com/AbdelStark/hallmark/issues/36) | W35 | conformance: execute the genuine hybrid mutation and recovery suite | conformance | p0 | l | 0006, 0007, 0009 | Open; blocked | [#27](https://github.com/AbdelStark/hallmark/issues/27), [#28](https://github.com/AbdelStark/hallmark/issues/28), [#29](https://github.com/AbdelStark/hallmark/issues/29), [#34](https://github.com/AbdelStark/hallmark/issues/34), [#35](https://github.com/AbdelStark/hallmark/issues/35) |
| [#40](https://github.com/AbdelStark/hallmark/issues/40) | W39 | delivery: assemble the evidence-bound private v1 release packet | delivery | p1 | m | 0010 | Open; blocked | [#18](https://github.com/AbdelStark/hallmark/issues/18), [#30](https://github.com/AbdelStark/hallmark/issues/30), [#33](https://github.com/AbdelStark/hallmark/issues/33), [#36](https://github.com/AbdelStark/hallmark/issues/36), [#37](https://github.com/AbdelStark/hallmark/issues/37), [#38](https://github.com/AbdelStark/hallmark/issues/38), [#39](https://github.com/AbdelStark/hallmark/issues/39) |
| [#41](https://github.com/AbdelStark/hallmark/issues/41) | W40 | delivery: reproduce the three-role demo with authorized reviewers | delivery | p2 | m | 0007, 0009, 0010 | Open; blocked | [#40](https://github.com/AbdelStark/hallmark/issues/40) |

## Tracking Issues

Each tracker includes all work carrying its RFC label, including downstream integration; its milestone is the latest child milestone.

- [#42 [Tracking] Wire encoding and transcript binding](https://github.com/AbdelStark/hallmark/issues/42) — RFC-0001.
- [#43 [Tracking] External enrollment and registry history](https://github.com/AbdelStark/hallmark/issues/43) — RFC-0002.
- [#44 [Tracking] Exact integer classifiers and complete inputs](https://github.com/AbdelStark/hallmark/issues/44) — RFC-0003.
- [#45 [Tracking] Data admission and frozen ML evaluation](https://github.com/AbdelStark/hallmark/issues/45) — RFC-0004.
- [#46 [Tracking] Real proof qualification and adapters](https://github.com/AbdelStark/hallmark/issues/46) — RFC-0005.
- [#47 [Tracking] Genuine hardware evidence and release gating](https://github.com/AbdelStark/hallmark/issues/47) — RFC-0006.
- [#48 [Tracking] Receipt lifecycle and offline verification](https://github.com/AbdelStark/hallmark/issues/48) — RFC-0007.
- [#49 [Tracking] Errors, private events and cost accounting](https://github.com/AbdelStark/hallmark/issues/49) — RFC-0008.
- [#50 [Tracking] Independent verifier and negative corpus](https://github.com/AbdelStark/hallmark/issues/50) — RFC-0009.
- [#51 [Tracking] Private release and reviewer reproduction](https://github.com/AbdelStark/hallmark/issues/51) — RFC-0010.

## Cross-Cutting Dependencies

- [#3](https://github.com/AbdelStark/hallmark/issues/3) depends on [#2](https://github.com/AbdelStark/hallmark/issues/2): Implement v1 transcript opening, per-classifier salt derivation and acyclic context hashing.
- [#4](https://github.com/AbdelStark/hallmark/issues/4) depends on [#2](https://github.com/AbdelStark/hallmark/issues/2): Add ModelManifest, FileRef and greedy GenerationConfig schemas and identities.
- [#5](https://github.com/AbdelStark/hallmark/issues/5) depends on [#2](https://github.com/AbdelStark/hallmark/issues/2): Add ClassifierManifest, InputProfile and typed arithmetic graph schemas.
- [#6](https://github.com/AbdelStark/hallmark/issues/6) depends on [#4](https://github.com/AbdelStark/hallmark/issues/4), [#5](https://github.com/AbdelStark/hallmark/issues/5): Add ordered three-classifier all-pass Policy, Request and RequestExpectation.
- [#7](https://github.com/AbdelStark/hallmark/issues/7) depends on [#4](https://github.com/AbdelStark/hallmark/issues/4), [#5](https://github.com/AbdelStark/hallmark/issues/5), [#6](https://github.com/AbdelStark/hallmark/issues/6): Add ReceiptBody, SignedReceipt, EpochRecord, ProofInputs and ProofArtifact boundaries.
- [#8](https://github.com/AbdelStark/hallmark/issues/8) depends on [#7](https://github.com/AbdelStark/hallmark/issues/7): Add Bundle with registry history, EmbeddedFile, ResponseEnvelope, BundleStatus and typed claims.
- [#9](https://github.com/AbdelStark/hallmark/issues/9) depends on [#2](https://github.com/AbdelStark/hallmark/issues/2), [#4](https://github.com/AbdelStark/hallmark/issues/4), [#5](https://github.com/AbdelStark/hallmark/issues/5), [#6](https://github.com/AbdelStark/hallmark/issues/6): Implement TrustPolicy, RegistryState and Enrollment with mandatory external identities.
- [#10](https://github.com/AbdelStark/hallmark/issues/10) depends on [#9](https://github.com/AbdelStark/hallmark/issues/9): Implement registry authoring and signature threshold verification using an exact reviewed dependency.
- [#11](https://github.com/AbdelStark/hallmark/issues/11) depends on [#3](https://github.com/AbdelStark/hallmark/issues/3), [#5](https://github.com/AbdelStark/hallmark/issues/5), [#14](https://github.com/AbdelStark/hallmark/issues/14): Implement a bounded enrolled literal byte-pattern classifier with cross-chunk state.
- [#12](https://github.com/AbdelStark/hallmark/issues/12) depends on [#3](https://github.com/AbdelStark/hallmark/issues/3), [#5](https://github.com/AbdelStark/hallmark/issues/5): Implement bounded byte-count affine/ReLU/scalar layers and full max aggregation.
- [#13](https://github.com/AbdelStark/hallmark/issues/13) depends on [#5](https://github.com/AbdelStark/hallmark/issues/5), [#19](https://github.com/AbdelStark/hallmark/issues/19): Implement the selected static integer graph and independent input preparation contract.
- [#15](https://github.com/AbdelStark/hallmark/issues/15) depends on [#14](https://github.com/AbdelStark/hallmark/issues/14): Add normalized-record lineage sidecars, source approval checks and immutable dataset/split manifests.
- [#16](https://github.com/AbdelStark/hallmark/issues/16) depends on [#12](https://github.com/AbdelStark/hallmark/issues/12), [#15](https://github.com/AbdelStark/hallmark/issues/15): Add pass-all/block-all, character n-gram and approved guard comparisons beside byte logistic and MLP.
- [#17](https://github.com/AbdelStark/hallmark/issues/17) depends on [#13](https://github.com/AbdelStark/hallmark/issues/13), [#15](https://github.com/AbdelStark/hallmark/issues/15), [#16](https://github.com/AbdelStark/hallmark/issues/16): Train the admitted encoder under three fixed seeds with explicit device/dtype and resume state.
- [#18](https://github.com/AbdelStark/hallmark/issues/18) depends on [#15](https://github.com/AbdelStark/hallmark/issues/15), [#16](https://github.com/AbdelStark/hallmark/issues/16): Implement versioned reports with low-FPR counts, uncertainty, slices and paired group bootstrap.
- [#19](https://github.com/AbdelStark/hallmark/issues/19) depends on [#5](https://github.com/AbdelStark/hallmark/issues/5), [#14](https://github.com/AbdelStark/hallmark/issues/14): Implement qualification runner and BackendQualification manifest with reviewed licence/setup/dependency pins.
- [#20](https://github.com/AbdelStark/hallmark/issues/20) depends on [#11](https://github.com/AbdelStark/hallmark/issues/11), [#19](https://github.com/AbdelStark/hallmark/issues/19): Implement real rule proof adapter over complete salted input with cross-chunk matching.
- [#21](https://github.com/AbdelStark/hallmark/issues/21) depends on [#12](https://github.com/AbdelStark/hallmark/issues/12), [#19](https://github.com/AbdelStark/hallmark/issues/19): Implement MLP relation with full input commitment, all chunks, ranges and ties-to-even rescaling.
- [#22](https://github.com/AbdelStark/hallmark/issues/22) depends on [#13](https://github.com/AbdelStark/hallmark/issues/13), [#17](https://github.com/AbdelStark/hallmark/issues/17), [#19](https://github.com/AbdelStark/hallmark/issues/19): Implement full graph proof with tokenizer input digest, masks, complete chunks and max decision.
- [#23](https://github.com/AbdelStark/hallmark/issues/23) depends on [#4](https://github.com/AbdelStark/hallmark/issues/4), [#7](https://github.com/AbdelStark/hallmark/issues/7), [#10](https://github.com/AbdelStark/hallmark/issues/10), [#14](https://github.com/AbdelStark/hallmark/issues/14): Implement pinned platform verifier with offline CPU/accelerator collateral and common epoch challenge.
- [#24](https://github.com/AbdelStark/hallmark/issues/24) depends on [#4](https://github.com/AbdelStark/hallmark/issues/4), [#23](https://github.com/AbdelStark/hallmark/issues/23): Implement measured loader and exclusive inference path using exact manifest files/runtime/settings.
- [#25](https://github.com/AbdelStark/hallmark/issues/25) depends on [#6](https://github.com/AbdelStark/hallmark/issues/6), [#11](https://github.com/AbdelStark/hallmark/issues/11), [#12](https://github.com/AbdelStark/hallmark/issues/12), [#13](https://github.com/AbdelStark/hallmark/issues/13), [#24](https://github.com/AbdelStark/hallmark/issues/24), [#26](https://github.com/AbdelStark/hallmark/issues/26): Execute all three enrolled integer classifiers before releasing any response.
- [#26](https://github.com/AbdelStark/hallmark/issues/26) depends on [#7](https://github.com/AbdelStark/hallmark/issues/7), [#14](https://github.com/AbdelStark/hallmark/issues/14), [#23](https://github.com/AbdelStark/hallmark/issues/23): Implement one-use AES-256-GCM witness encryption, sealed key references, rollback-resistant lifecycle state, atomic journal and exclusive foreground jobs.
- [#27](https://github.com/AbdelStark/hallmark/issues/27) depends on [#8](https://github.com/AbdelStark/hallmark/issues/8), [#10](https://github.com/AbdelStark/hallmark/issues/10), [#20](https://github.com/AbdelStark/hallmark/issues/20), [#21](https://github.com/AbdelStark/hallmark/issues/21), [#22](https://github.com/AbdelStark/hallmark/issues/22), [#25](https://github.com/AbdelStark/hallmark/issues/25), [#26](https://github.com/AbdelStark/hallmark/issues/26): Collect signed receipt, epoch/collateral, registry/history and all three verified proofs.
- [#28](https://github.com/AbdelStark/hallmark/issues/28) depends on [#9](https://github.com/AbdelStark/hallmark/issues/9), [#10](https://github.com/AbdelStark/hallmark/issues/10), [#23](https://github.com/AbdelStark/hallmark/issues/23), [#27](https://github.com/AbdelStark/hallmark/issues/27): Implement external request/time comparisons, signature consistency, registry history and genuine hardware verification.
- [#29](https://github.com/AbdelStark/hallmark/issues/29) depends on [#3](https://github.com/AbdelStark/hallmark/issues/3), [#20](https://github.com/AbdelStark/hallmark/issues/20), [#21](https://github.com/AbdelStark/hallmark/issues/21), [#22](https://github.com/AbdelStark/hallmark/issues/22), [#28](https://github.com/AbdelStark/hallmark/issues/28): Implement independent B1 openings/input reconstruction and B2 hardware-dependent binding.
- [#30](https://github.com/AbdelStark/hallmark/issues/30) depends on [#8](https://github.com/AbdelStark/hallmark/issues/8), [#27](https://github.com/AbdelStark/hallmark/issues/27), [#29](https://github.com/AbdelStark/hallmark/issues/29), [#31](https://github.com/AbdelStark/hallmark/issues/31): Add verify, inspect, registry-check and qualify with mandatory external trust/expectations.
- [#32](https://github.com/AbdelStark/hallmark/issues/32) depends on [#31](https://github.com/AbdelStark/hallmark/issues/31): Implement allowlisted Event stream with monotonic ordinals and one writer per run.
- [#33](https://github.com/AbdelStark/hallmark/issues/33) depends on [#14](https://github.com/AbdelStark/hallmark/issues/14), [#19](https://github.com/AbdelStark/hallmark/issues/19), [#32](https://github.com/AbdelStark/hallmark/issues/32): Implement fixed CostStage samples, bounded process lifecycle and fresh cost manifests.
- [#34](https://github.com/AbdelStark/hallmark/issues/34) depends on [#2](https://github.com/AbdelStark/hallmark/issues/2), [#3](https://github.com/AbdelStark/hallmark/issues/3), [#4](https://github.com/AbdelStark/hallmark/issues/4), [#5](https://github.com/AbdelStark/hallmark/issues/5), [#6](https://github.com/AbdelStark/hallmark/issues/6), [#7](https://github.com/AbdelStark/hallmark/issues/7), [#8](https://github.com/AbdelStark/hallmark/issues/8), [#9](https://github.com/AbdelStark/hallmark/issues/9), [#10](https://github.com/AbdelStark/hallmark/issues/10), [#31](https://github.com/AbdelStark/hallmark/issues/31): Implement Case/corpus schemas and harmless golden/mutation vectors for every rejection obligation.
- [#35](https://github.com/AbdelStark/hallmark/issues/35) depends on [#34](https://github.com/AbdelStark/hallmark/issues/34), [#29](https://github.com/AbdelStark/hallmark/issues/29): Implement independent parsing, hashing, token binding, integer execution and policy verification from the frozen spec.
- [#36](https://github.com/AbdelStark/hallmark/issues/36) depends on [#27](https://github.com/AbdelStark/hallmark/issues/27), [#28](https://github.com/AbdelStark/hallmark/issues/28), [#29](https://github.com/AbdelStark/hallmark/issues/29), [#34](https://github.com/AbdelStark/hallmark/issues/34), [#35](https://github.com/AbdelStark/hallmark/issues/35): Produce real-hardware/proof hybrid cases on an admitted host and compare both verifiers.
- [#40](https://github.com/AbdelStark/hallmark/issues/40) depends on [#18](https://github.com/AbdelStark/hallmark/issues/18), [#30](https://github.com/AbdelStark/hallmark/issues/30), [#33](https://github.com/AbdelStark/hallmark/issues/33), [#36](https://github.com/AbdelStark/hallmark/issues/36), [#37](https://github.com/AbdelStark/hallmark/issues/37), [#38](https://github.com/AbdelStark/hallmark/issues/38), [#39](https://github.com/AbdelStark/hallmark/issues/39): Implement ReleaseManifest and assemble source/build/evidence/licence inventory with limitations.
- [#41](https://github.com/AbdelStark/hallmark/issues/41) depends on [#40](https://github.com/AbdelStark/hallmark/issues/40): Create provider/auditor/user terminal demo with exact opening and both claim strengths.

The dependency graph has no cycles. All 50 issues have explicit dependency bodies and a cross-link comment; each implementation edge is linked in both endpoint bodies, and child issues link to their RFC trackers. Independent work can proceed without admitting a research campaign. The tracker and live bodies must be updated together when scope changes.

## Open questions and decisions

All ten RFCs remain Draft. Resolution checkpoints are proposed review dates, not scheduled jobs. Owner: @AbdelStark; the relying-party owner must also approve the policy/evaluation protocol.

| Question | Resolution checkpoint | Work / acceptance gate |
|---|---|---|
| Wire/signature profile and independent vectors | 2026-11-02 | [#2](https://github.com/AbdelStark/hallmark/issues/2), [#3](https://github.com/AbdelStark/hallmark/issues/3) |
| Registry root custody and pinned signature library | 2026-11-02 | [#9](https://github.com/AbdelStark/hallmark/issues/9), [#10](https://github.com/AbdelStark/hallmark/issues/10) |
| Exact integer encoder and tokenizer graph | 2026-11-09 | [#13](https://github.com/AbdelStark/hallmark/issues/13), [#19](https://github.com/AbdelStark/hallmark/issues/19) |
| Relying party, rubric, data/licences, split/power, quality and resource caps | 2026-11-02 | [#14](https://github.com/AbdelStark/hallmark/issues/14) |
| Real backend, setup, hiding and full-graph qualification | 2026-11-09 | [#19](https://github.com/AbdelStark/hallmark/issues/19), [#20](https://github.com/AbdelStark/hallmark/issues/20), [#21](https://github.com/AbdelStark/hallmark/issues/21), [#22](https://github.com/AbdelStark/hallmark/issues/22) |
| Authorized hardware host, device path, trusted time and lifecycle state | 2026-11-09 | [#23](https://github.com/AbdelStark/hallmark/issues/23), [#24](https://github.com/AbdelStark/hallmark/issues/24) |
| Retention and authenticated requester policy | 2026-11-02 | [#14](https://github.com/AbdelStark/hallmark/issues/14), [#26](https://github.com/AbdelStark/hallmark/issues/26) |
| Cost host, profiling method and caps | 2026-11-09 | [#14](https://github.com/AbdelStark/hallmark/issues/14), [#33](https://github.com/AbdelStark/hallmark/issues/33) |
| Independent implementer/reviewer and permitted sharing | 2026-11-09 | [#35](https://github.com/AbdelStark/hallmark/issues/35) |
| Ownership/licences, hosted execution and two authorized reviewers | 2026-11-09 | [#37](https://github.com/AbdelStark/hallmark/issues/37), [#38](https://github.com/AbdelStark/hallmark/issues/38), [#40](https://github.com/AbdelStark/hallmark/issues/40), [#41](https://github.com/AbdelStark/hallmark/issues/41) |

Decisions made without inventing missing approval: propose one English single-turn prompt-injection assay; use greedy stand-in generation, public classifier weights, all-pass policy and all-response C0 proofs; retain B1 and B2 with separate trust; defer cascades/sampling/B3/recursion/distillation; use a private branch/PR; restore private repository visibility before publication. [Decision 0002](../decisions/0002-v1-specification-scope.md) records the rationale and limits.

## Completion standard

This bootstrap deliverable is a specification and filed backlog, not an implemented v1. v1 requires every issue's evidence, zero missing genuine cases, independent agreement and owner-approved private review. Missing hardware, proof support, data rights or budget blocks implementation acceptance; a simpler fixture cannot close those gates.
