# Requirements and implementation coverage

## Coverage rule

Each W identifier is one bounded implementation PR, with its exact scope, acceptance tests, dependencies and exclusions in the committed [work map](../roadmap/work-items.json). The detailed sections/RFCs are normative; this table is their execution index. A work item closes only when its issue contains the evidence, including real-resource gates where required. Tracking issues group work and are not additional implementation scope.

The source anchors below use named goals/sections from the immutable [PRD](../../research/source/product-requirements.txt), [hybrid packet](../../research/source/hybrid-specification.txt) and [ML packet](../../research/source/ml-engineering.txt). Derived controls explain their rationale in the linked RFC; they are not invented product features.

## Source requirement disposition

| Source intent | v1 disposition | Work coverage |
|---|---|---|
| PRD G1: genuine model-bound evidence | Retained; no signature-only surrogate | W03, W06, W22–W24, W27, W35 |
| PRD G2: classifier proofs | Retained for rule, MLP and compact encoder | W04, W10–W12, W18–W21, W28 |
| PRD G3: exact common transcript | Retained in B1 and B2 with distinct trust | W01–W02, W05–W07, W26–W28 |
| PRD G4: independent verifier and negative corpus | Retained; primary replay is insufficient | W33–W35 |
| PRD G5: typed honest claims | Retained; pending/declined/invalid distinct | W07, W27–W31, W38–W40 |
| PRD signed registry; hybrid history/rotation | Retained as signed private snapshot history; global witnesses deferred | W08–W09 |
| PRD native release gate; proof off latency path | Retained with all-response bounded collection, no streaming | W24–W26 |
| PRD quality agreement and cost reporting | Retained with fixed policy/data/budgets and raw measurements | W13–W17, W18–W21, W32, W35 |
| PRD three-role cheats and two reviewer reproductions | Retained privately, authority-gated | W39–W40 |
| ML staged data/training/export/evaluation | First policy and compact student retained; teacher/distillation later | W13–W17 |
| Package/API/schema/CI/security maintenance | Derived from reproducible, independently implementable delivery | W01–W09, W29–W31, W36–W39 |
| Cascades, sampled proofs, hidden classifiers, B3, recursive proofs | Deferred explicitly; not required for the bounded all-pass C0 claim | No v1 issues |
| Production integration, public release and frontier-model proofs | Source non-goals/extensions; separate authorization | No v1 issues |

## Work items

| ID | Deliverable | RFC | Milestone | Depends on |
|---|---|---|---|---|
| <a id="w01"></a>W01 | wire: implement strict v1 encoding and domain-separated identities | [0001](../rfcs/RFC-0001-wire.md#proposed-design) | v0.2 | None |
| <a id="w02"></a>W02 | wire: implement transcript and complete-input opening contracts | [0001](../rfcs/RFC-0001-wire.md#proposed-design), [0003](../rfcs/RFC-0003-integer.md#proposed-design) | v0.2 | W01, W05 |
| <a id="w03"></a>W03 | wire: add immutable model and generation manifest schemas | [0001](../rfcs/RFC-0001-wire.md#proposed-design), [0006](../rfcs/RFC-0006-hardware.md#proposed-design) | v0.2 | W01 |
| <a id="w04"></a>W04 | wire: add classifier and numerical profile manifest schemas | [0001](../rfcs/RFC-0001-wire.md#proposed-design), [0003](../rfcs/RFC-0003-integer.md#proposed-design), [0005](../rfcs/RFC-0005-proofs.md#proposed-design) | v0.2 | W01 |
| <a id="w05"></a>W05 | wire: add policy and external request expectation schemas | [0001](../rfcs/RFC-0001-wire.md#proposed-design), [0007](../rfcs/RFC-0007-verifier.md#proposed-design) | v0.2 | W03, W04 |
| <a id="w06"></a>W06 | wire: add receipt, epoch and proof artifact schemas | [0001](../rfcs/RFC-0001-wire.md#proposed-design), [0005](../rfcs/RFC-0005-proofs.md#proposed-design), [0006](../rfcs/RFC-0006-hardware.md#proposed-design) | v0.2 | W03, W04, W05 |
| <a id="w07"></a>W07 | wire: add bounded offline bundle and result schemas | [0001](../rfcs/RFC-0001-wire.md#proposed-design), [0007](../rfcs/RFC-0007-verifier.md#proposed-design) | v0.2 | W06 |
| <a id="w08"></a>W08 | registry: implement external trust and rollback-safe enrollment | [0002](../rfcs/RFC-0002-registry.md#proposed-design) | v0.2 | W01, W03, W04, W05 |
| <a id="w09"></a>W09 | registry: sign snapshots and implement rotation and retirement | [0002](../rfcs/RFC-0002-registry.md#proposed-design) | v0.2 | W08 |
| <a id="w10"></a>W10 | classifiers: implement the complete-input integer rule program | [0003](../rfcs/RFC-0003-integer.md#proposed-design) | v0.3 | W02, W04, W13 |
| <a id="w11"></a>W11 | classifiers: implement the byte-feature integer MLP runtime | [0003](../rfcs/RFC-0003-integer.md#proposed-design) | v0.3 | W02, W04 |
| <a id="w12"></a>W12 | classifiers: execute the qualified encoder integer graph | [0003](../rfcs/RFC-0003-integer.md#proposed-design), [0005](../rfcs/RFC-0005-proofs.md#proposed-design) | v0.3 | W04, W18 |
| <a id="w13"></a>W13 | research: prepare the single-policy data and resource admission | [0004](../rfcs/RFC-0004-ml.md#proposed-design), [0006](../rfcs/RFC-0006-hardware.md#proposed-design), [0008](../rfcs/RFC-0008-operations.md#proposed-design) | v0.2 | None |
| <a id="w14"></a>W14 | research: implement lineage-preserving data admission and splitting | [0004](../rfcs/RFC-0004-ml.md#proposed-design) | v0.3 | W13 |
| <a id="w15"></a>W15 | research: implement frozen baseline and MLP training comparisons | [0003](../rfcs/RFC-0003-integer.md#proposed-design), [0004](../rfcs/RFC-0004-ml.md#proposed-design) | v0.3 | W11, W14 |
| <a id="w16"></a>W16 | research: train and export one compact encoder reproducibly | [0003](../rfcs/RFC-0003-integer.md#proposed-design), [0004](../rfcs/RFC-0004-ml.md#proposed-design) | v0.3 | W12, W14, W15 |
| <a id="w17"></a>W17 | research: add frozen slice reports and group-aware comparisons | [0004](../rfcs/RFC-0004-ml.md#proposed-design) | v0.3 | W14, W15 |
| <a id="w18"></a>W18 | proofs: qualify a pinned backend and exact full-graph profile | [0005](../rfcs/RFC-0005-proofs.md#proposed-design) | v0.3 | W04, W13 |
| <a id="w19"></a>W19 | proofs: prove and verify the complete byte-rule decision | [0003](../rfcs/RFC-0003-integer.md#proposed-design), [0005](../rfcs/RFC-0005-proofs.md#proposed-design) | v0.3 | W10, W18 |
| <a id="w20"></a>W20 | proofs: prove and verify the bounded integer MLP decision | [0003](../rfcs/RFC-0003-integer.md#proposed-design), [0005](../rfcs/RFC-0005-proofs.md#proposed-design) | v0.3 | W11, W18 |
| <a id="w21"></a>W21 | proofs: prove and verify the entire qualified encoder | [0003](../rfcs/RFC-0003-integer.md#proposed-design), [0005](../rfcs/RFC-0005-proofs.md#proposed-design) | v0.3 | W12, W16, W18 |
| <a id="w22"></a>W22 | hardware: qualify genuine epoch and accelerator evidence | [0006](../rfcs/RFC-0006-hardware.md#proposed-design) | v0.3 | W03, W06, W09, W13 |
| <a id="w23"></a>W23 | hardware: bind loaded model and protected response path | [0006](../rfcs/RFC-0006-hardware.md#proposed-design) | v0.3 | W03, W22 |
| <a id="w24"></a>W24 | hardware: gate release with all enrolled integer classifiers | [0006](../rfcs/RFC-0006-hardware.md#proposed-design), [0007](../rfcs/RFC-0007-verifier.md#proposed-design) | v0.3 | W05, W10, W11, W12, W23, W25 |
| <a id="w25"></a>W25 | receipts: implement bounded encrypted proof spool and recovery | [0007](../rfcs/RFC-0007-verifier.md#proposed-design) | v0.3 | W06, W13, W22 |
| <a id="w26"></a>W26 | receipts: assemble complete offline C0 evidence bundles | [0007](../rfcs/RFC-0007-verifier.md#proposed-design) | v1.0 | W07, W09, W19, W20, W21, W24, W25 |
| <a id="w27"></a>W27 | verification: verify enrollment, receipt and hardware claim A | [0002](../rfcs/RFC-0002-registry.md#proposed-design), [0006](../rfcs/RFC-0006-hardware.md#proposed-design), [0007](../rfcs/RFC-0007-verifier.md#proposed-design) | v1.0 | W08, W09, W22, W26 |
| <a id="w28"></a>W28 | verification: verify B1 and B2 proofs and all-pass composition | [0003](../rfcs/RFC-0003-integer.md#proposed-design), [0005](../rfcs/RFC-0005-proofs.md#proposed-design), [0007](../rfcs/RFC-0007-verifier.md#proposed-design) | v1.0 | W02, W19, W20, W21, W27 |
| <a id="w29"></a>W29 | verification: expose typed v1 CLI and supported library API | [0007](../rfcs/RFC-0007-verifier.md#proposed-design) | v1.0 | W07, W26, W28, W30 |
| <a id="w30"></a>W30 | operations: add typed errors and redact all trust-boundary failures | [0008](../rfcs/RFC-0008-operations.md#proposed-design) | v0.2 | None |
| <a id="w31"></a>W31 | operations: add bounded local events and immutable failure records | [0008](../rfcs/RFC-0008-operations.md#proposed-design) | v0.3 | W30 |
| <a id="w32"></a>W32 | operations: measure full-path cost with raw samples and caps | [0005](../rfcs/RFC-0005-proofs.md#proposed-design), [0008](../rfcs/RFC-0008-operations.md#proposed-design) | v0.3 | W13, W18, W31 |
| <a id="w33"></a>W33 | conformance: freeze v1 golden and adversarial evidence corpus | [0001](../rfcs/RFC-0001-wire.md#proposed-design), [0009](../rfcs/RFC-0009-conformance.md#proposed-design) | v0.2 | W01, W02, W03, W04, W05, W06, W07, W08, W09, W30 |
| <a id="w34"></a>W34 | conformance: build a separately implemented offline verifier | [0009](../rfcs/RFC-0009-conformance.md#proposed-design) | v1.0 | W33, W28 |
| <a id="w35"></a>W35 | conformance: execute the genuine hybrid mutation and recovery suite | [0006](../rfcs/RFC-0006-hardware.md#proposed-design), [0007](../rfcs/RFC-0007-verifier.md#proposed-design), [0009](../rfcs/RFC-0009-conformance.md#proposed-design) | v1.0 | W26, W27, W28, W33, W34 |
| <a id="w36"></a>W36 | delivery: enforce core, train and gated integration CI | [0010](../rfcs/RFC-0010-release.md#proposed-design) | v0.2 | None |
| <a id="w37"></a>W37 | delivery: make private builds reproducible and verify inventories | [0010](../rfcs/RFC-0010-release.md#proposed-design) | v0.2 | None |
| <a id="w38"></a>W38 | delivery: enforce spec traceability and contributor documentation | [0010](../rfcs/RFC-0010-release.md#proposed-design) | v0.2 | None |
| <a id="w39"></a>W39 | delivery: assemble the evidence-bound private v1 release packet | [0010](../rfcs/RFC-0010-release.md#proposed-design) | v1.0 | W17, W29, W32, W35, W36, W37, W38 |
| <a id="w40"></a>W40 | delivery: reproduce the three-role demo with authorized reviewers | [0007](../rfcs/RFC-0007-verifier.md#proposed-design), [0009](../rfcs/RFC-0009-conformance.md#proposed-design), [0010](../rfcs/RFC-0010-release.md#proposed-design) | v1.0 | W39 |

## Cross-cutting closure

Every typed schema is owned by W01–W09, W13–W14, W18, W22, W25, W29–W33 or W39. Every security/error branch requires its subsystem negative tests plus W33/W35; W30 owns common translation/redaction. W38 owns docs/anchor/coverage enforcement. Existing baseline behavior is retained and regression-checked by each affected item; it is not re-filed as an unimplemented feature.

Every invariant maps to the work above: CLAIMS/QUALITY/COMPLETE-V1 to W13/W17/W28/W39; COMMON-INPUT/IDENTITY/NO-CYCLE to W01–W07/W19–W21/W28; SCHEMA/TIME/EXTERNAL-EXPECTATION to W01/W05–W09/W27/W29; ONE-WRITER/FAIL-CLOSED to W24–W26; ERROR-PRIVACY/ERROR-TRUTH to W30–W31; NETWORK/KEYS to W09/W22/W25/W27–W28; BUDGET to W13/W18/W25/W32; CONFORMANCE/NO-SUBSTITUTION to W18–W24/W33–W35.

A changed requirement requires updating its work-map entry, linked issue and corpus vectors in the same review. New research results require their own admitted experiment identity; an issue closure cannot alter old evidence.
