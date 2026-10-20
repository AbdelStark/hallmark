# 0028 — Train-internal grouped baseline selection

Date: 2026-10-20. Scope: W15 / issue #16, continuing draft PR #73.

Hypothesis: a finite comparison roster can fit and select candidates using only
training records, with group-disjoint fitting, threshold selection and validation,
while preserving every failed candidate and the unchanged byte-logistic floor.
Baseline: the record-level MLP component at `865691f`; no grouped selector or
character n-gram baseline exists. Mutable paths are additive baseline/selection
code, synthetic fixtures, tests, package checks and documentation. The historical
evaluator, dataset, thresholds, MLP protocol and previous results stay frozen.

This fills previously unspecified train-internal selection details; it does not
reuse previous quality results. Real study measurements still require the final
admission dossier and owner/relying-party review. Synthetic checks do not grant it.

Reject any calibration/test record before serializing labels, importing optional
libraries or fitting. Validate complete prompt bytes, one English prompt policy,
unique IDs, declared resource caps and both classes. Identical prompts must have
one group. Parent/semantic grouping remains the reviewed importer's obligation.

Sort group IDs by SHA-256 of `inj-direct-design/1|fold|` plus the ID, then assign
round-robin to five folds without labels. Rotation j validates on fold j, chooses
its internal threshold on fold (j+1) mod 5, and fits on the other three. No
validation record enters fitting or internal threshold choice. Choose one
representative per validation group by the study's record-ID hash rule before
reading labels. Folds with missing required classes fail visibly; do not repartition
after seeing labels. Final outer calibration/test sets are not arguments to selection.

The finite candidate list and seeds are explicit. Rank candidates within each
family separately for each seed by pooled validation TPR, then lower validation
FPR, then lexical candidate ID. Only candidates completing all five rotations and
their declared convergence checks are eligible. Missing denominators or failed
fits are ineligible, not zero scores. Report every seed and candidate; never select
a favorable seed. Selection estimates are not held-out quality evidence.

Character n-grams count exact Unicode substrings, including whitespace, with no
normalization or truncation. Fit the vocabulary on fitting rows only, choose the
most frequent terms with lexical ties, and normalize counts by the number of
available n-gram positions. A float64 liblinear logistic regression uses declared
C, tolerance, iteration cap and seed. Save vocabulary, coefficients, intercept,
iterations, convergence status, source/runtime/config/data identities. This solver
does not expose resumable optimizer state: its explicit resume mode is cold-fit
only. MLP optimizer resume retains decision 0027's contract.

Internal learned thresholds use only benign internal-calibration scores, exact
decimal FPR arithmetic and blocking equality. Integer scores use boundary plus
one; finite float scores use the next representable value above the boundary.
Controls are fixed pass-all/block-all decisions, never calibrated into one another.
The complete seven-row study roster keeps guard/encoder omissions explicit.

After selection, refit on all training rows and retain its identity before outer
calibration. The separate calibration/evaluation API requires caller-pinned fit
and calibration identities, exact split tags and disjoint group/prompt identities.
It evaluates native integer MLP/logistic scores and float n-gram scores with
blocking equality. Test primary counts use one preselected representative per
group; descendant counts are separate. The caller still owns measurement
admission and once-only test execution. These functions do not claim quality
from a software result or replace W17's complete slice/uncertainty comparison.

Pass the software increment only after group-isolation and held-out-label spies,
training-only vocabulary checks, exact threshold/tie cases, actual fixed-seed
fitting, visible nonconvergence/unsupported long-input failures, deterministic
reproduction and installed core/train checks. Store numeric artifacts before prose.
An unavailable guard is not an implemented comparison; source/runtime admission
and actual guard integration remain required before the whole W15 issue closes.
