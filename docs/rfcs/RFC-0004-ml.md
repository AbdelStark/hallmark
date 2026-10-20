# RFC-0004: Admitted data and frozen classifier evaluation

- Status: Draft
- Authors: @AbdelStark (owner; engineering draft for review)
- Created: 2026-10-20
- Target milestone: v0.3

## Summary

Admit one prompt-injection policy and a frozen experiment before data access, train candidates under explicit numerical/resource contracts, and evaluate the final integer models without test-driven selection.

## Motivation

The [program's H1](../../research/PROGRAM.md#falsifiable-hypotheses) asks whether a compact integer model is useful at a fixed low FPR. A correct proof of a useless classifier does not answer it. The current marker fixture's negative result remains visible.

## Goals

- Keep data licence, purpose, privacy, lineage and approval attached to every record.
- Separate fitting, selection, calibration and held-out evaluation.
- Report failed candidates, uncertainty and float/integer drift.

## Non-Goals

- Teacher inference/distillation, external judges, broad multilingual policies or bootstrap data downloads.

## Proposed Design

Create `AdmissionProtocol={schema_id:"hallmark/admission/1", policy:Digest, relying_party_role:Id, rubric:Digest, sources:List[SourceApproval], split_manifest:Digest, candidate_roster:List[Candidate], seeds:Vec[U64,3], evaluator:Digest, target_fpr:DecimalString, alpha:DecimalString, min_tpr:DecimalString, max_quality_loss:DecimalString, subgroup_rules:FileRef, power_plan:FileRef, budget:BudgetAdmission, approval_ref:Digest}`. Decimal strings encode exact rationals for selection contracts; research v0.1 floats remain unchanged.

`SourceApproval={source_id:Id, revision:Digest, license_text:Digest, purpose:Id, approval_ref:Digest, restrictions:FileRef}`. `Candidate={id:Id, code:Digest, base_files:List[FileRef], config:Digest}`. A local admission utility validates the protocol and refuses missing review evidence. Owner/relying-party choices for TPR, loss margin and power are required before measurement; no automatic “reasonable” values are supplied.

The [W13 proposal](../../research/proposals/inj-direct-v1/README.md) originally left
unapproved terms null in a separate draft schema. The owner's
[study approval](../decisions/0019-approved-study-scope.md) now supplies scope,
quality, design delegation and resource authority; exact source/candidate/
evaluator inventories and final measurement review remain unresolved. The
[engineering contract](../decisions/0018-admission-proposal.md) uses a pre-training
`StudyPolicy` rather than a final deployed classifier policy. A review binds all
terms except the top-level review reference; the final protocol then pins that
review. An independently authenticated caller supplies the expected review digest.
Source revisions and code/configuration fields hash exact manifest documents;
declared asset inventories still require approved byte verification. The harmless
`make check-admission` fixture grants no access or measurement authority.

Data import preserves raw UTF-8 hashes and records every transformation, parent group and label mapping. Group connected components include originals, mutations, translations and shared histories before splitting. Near-duplicate checks flag candidates for review without deleting benign/adversarial contrastive pairs automatically. Use one approved source manifest and immutable split manifest; retain held-out attack families. Real data is outside git. `Record/1` remains the normalized assay input; a versioned lineage sidecar links each record to source row, parents, rubric, annotator/adjudication evidence and transformation recipe.

W14's [local importer](../decisions/0021-lineage-data-admission.md) now implements
these byte/provenance/group boundaries and the frozen split recipe. Its automatic
near-candidate rule covers ASCII case/whitespace equivalence only; broader
semantic relationships require reviewed parent/history links. The shipped
synthetic review documents grant no real source or measurement admission.

Freeze the roster: pass-all/block-all sanity controls, existing byte-logistic floor, character n-gram linear baseline, one approved task-matched guard, the byte MLP and one compact encoder. All parameters/folds are predeclared; model selection uses train-internal grouped folds only. Fit tokenization/vocabulary where applicable on train only. The encoder uses three fixed seeds; seed choice is never selected on test.

Training declares device, dtype, optimizer/scheduler, batch/length policy, deterministic mode, RNG state and resume identity. CPU floor uses float64; an encoder run must record its actual precision and deterministic-operation exceptions before running. Resume requires exact data/source/config and optimizer/RNG states. Export integer semantics and validate before calibration. Multi-chunk positive labels use a documented record-level max/multiple-instance objective; never label every chunk positive.

Calibration uses the fixed integer model and benign calibration scores: the smallest threshold meeting the allowed false-positive count, with equality blocking. Evaluate test once after artifact freeze. Preserve raw counts, Wilson intervals, null denominators and the exact zero-FP bound in [EVALUATION](../EVALUATION.md#metrics-and-uncertainty). General comparisons use paired group bootstrap with 10,000 resamples and a prespecified seed; report the resampling unit and every excluded group. Three training seeds are reported individually and as a prespecified summary, not as independent test examples.

Report language/source/length/attack-family slices, float/integer flips, low-FPR TPR, worst-slice counts and adaptive-set provenance. Insufficient power is inconclusive; 299 zero-event independent benign examples is only a conditional bound, not a complete power design. Adaptive attacks created after test feedback form a new exploratory set.

## Alternatives Considered

Pooling all safety tasks obscures incompatible labels. Calibrating float outputs before integer export can select the wrong threshold. Large teacher pipelines add access/cost/confounds before a useful student frontier exists.

## Drawbacks

Admission may block research when data rights or power are unclear. Three seeds and group-aware intervals cost more than a single favorable run. The first use case cannot establish general safety.

## Migration / Rollout

Keep original fixtures/config/evaluator and ledger results immutable. New policy/data/evaluator choices create new experiment IDs and decision records. Add imports and training only after owner admission; draft proposals alone require no download.

## Testing Strategy

Reject a source without approval, cross-split descendant, changed dataset hash, empty benign calibration, altered threshold, resumed run under a different config and any model selection access to test. Test tied scores, all-positive/all-negative slices, correlated group resampling and deterministic seeded export. Repeat selected training in fresh directories and compare substantive artifacts.

## Open Questions

- OPEN QUESTION POLICY-DATA — @AbdelStark with the designated relying-party owner, resolution checkpoint 2026-11-02: approve rubric, source/licence inventory, split/power, quality margins and host budget in W13 before W14–W17 measurement. No data source is admitted by this RFC.

## References

- [Evaluation contract](../EVALUATION.md), [ML plan](../ML-PLAN.md), [resource budget](../spec/08-performance-budget.md#proposed-v1-envelopes).
