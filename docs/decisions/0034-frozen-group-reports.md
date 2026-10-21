# 0034 — Frozen group-aware reports

Date: 2026-10-21. Scope: W17 descriptive evaluation software.

Hypothesis: caller-pinned held-out predictions can produce reproducible slice and
paired comparison reports without model scoring, fitting or threshold selection.
The baseline W15 evaluations contain per-row scores and primary/all-row counts,
but lack shared slice reports, paired resampling and quantization comparisons.
Mutable paths are the report API/command, synthetic fixture, tests, schema
snapshots, package checks and documentation. Existing evaluators, datasets,
thresholds and historical evidence remain unchanged.

`GroupReportPlan/1` binds the exact ordered test records, source inventory,
provenance, evaluator source and Python/random implementation, candidate roster,
fit/calibration pins, fixed three-seed roster, annotations and exclusions. Each
family/variant has all seeds 17/29/43 or one explicitly untrained member. A failed
or unavailable member is retained; it cannot silently disappear or contribute to
a median. A report performs no selection and cannot authenticate when supplied
artifacts were frozen. The caller independently enrolls the expected plan.

Use the already frozen label-independent representative rule for each root
group. Exclude only whole groups declared in the plan, with reasons. Select
representatives globally before slicing, so a mixed group cannot become multiple
independent examples across slices. All-descendant counts are separate and have
no binomial intervals. Root-group intervals are explicitly conditional on
correct independent grouping; software cannot establish semantic independence.
Exact duplicate prompts in different groups reject.

Report language, source, family, four fixed UTF-8 length bins, supplied obfuscation
and benign-hard-negative annotations. Missing annotations say unavailable.
Empty denominators are null. Preserve confusion counts, nominal Wilson intervals
and the exact conditional zero-FP upper bound. Slices and their worst values are
descriptive, overlapping and uncorrected for multiplicity. Fewer than 7,831 benign
or 1,375 positive representatives is insufficient evidence under the existing
study design; reaching those counts still requires the actual-count power
calculation and does not pass a quality gate.

For each prespecified pair, draw 10,000 paired root-group bootstrap samples with
the declared seed. Multinomial sampling from the eight joint
(label,left-decision,right-decision) cells is distribution-equivalent to sampling
root representatives with replacement. It preserves pairing and avoids work
proportional to every input record for each replicate. Report right-minus-left
TPR/FPR percentile intervals (nearest rank), undefined-denominator draw counts,
joint counts and exact sorted-distribution digests. Python and its random module
are pinned; cross-version numerical identity is not promised. Training seeds
are never pooled into the sample size. Report every seed and their prespecified
median only when all declared members and denominators are available.

Quantization pairs require the same family/seed and separately frozen float and
native integer calibrations. Report both positive discordance directions, both
benign directions, net TPR loss and scaled score error. Nominal descriptive
intervals are separate from the study's 15 simultaneous exact acceptance bounds.
The full joint classifier, actual-count power check and authenticated admission/
once-only test history remain outside this descriptive adapter. A confirmatory
request therefore remains inconclusive; synthetic/exploratory reports do not
evaluate a confirmatory decision. No report can return a quality claim.

The command consumes bounded files and writes a fresh private output with
exclusive synchronized files; failures after directory creation retain a sanitized
failure record. It never loads a model or invokes training/calibration. Supplied
scores are caller evidence, not independently verified inference.

The owner authorized agent-reviewed synthetic pipeline development in decision
0033. Reusing retained W15 control predictions here creates a new, explicitly
synthetic reporting experiment with recorded prior exposure; it does not amend
or reclassify the earlier result. Human review is not required for this software
gate. Any future confirmatory evaluator change needs a new identity and the
existing owner/admission review before scientific results are reused.
