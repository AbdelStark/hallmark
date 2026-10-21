# inj.direct/1 study design

Frozen design version: `inj-direct-design/1`, 2026-10-20.
[Decision 0019](../../../docs/decisions/0019-approved-study-scope.md) records the
owner's scope and delegation. This design precedes data access and measurement.
It does not contain a frozen dataset or a completed admission dossier.
The owner-approved [pipeline stage](../../../docs/decisions/0033-approved-synthetic-pipeline.md)
permits agent-reviewed synthetic data without human review. It does not revise
the confirmatory quality targets below.

## Decision and comparisons

Use the rubric in [README](README.md). English prompt bytes only, at most 32,768
bytes, with complete coverage and no truncation. The seven ordered comparisons
are pass-all, block-all, byte-logistic, char-ngram, task-guard, byte-MLP and compact
encoder. Seeds are 17, 29 and 43; every seed is reported. Controls and unavailable
candidates remain in the table. Controls are not expected to pass quality gates.

The primary joint decision blocks if **any** of the fixed literal rule, integer
byte MLP or integer compact encoder blocks. Assess the complete joint decision
separately for each seed. Missing any component makes that primary comparison
unavailable; it cannot be silently replaced by an easier model.

Select patterns, architectures and hyperparameters using five train-internal
grouped folds only. The candidate configuration must declare a finite search
roster and tie break before fitting. All preprocessing vocabularies and scales
use train only. Export integer models before threshold calibration.

Allocate empirical benign calibration FPR budgets of 0.003 to the rule and
0.0035 each to MLP and encoder. The rule threshold stays one: if its fixed patterns
exceed their allocation, record failure rather than edit them on calibration.
For integer learned scores use the existing exact threshold rule in
[EVALUATION](../../../docs/EVALUATION.md), including blocking ties.
Calibrate standalone learned baselines at 0.01. Float counterparts use their
own frozen benign-calibration thresholds with the same allocation; save both.
Allocation is a selection rule, not a population FPR guarantee.

## Sampling and labels

Keep connected originals, paraphrases, translations and shared histories in one
parent group before fitting. The importer must record exact and reviewed near
duplicate links and unresolved provenance. Reject cross-split lineage.
Sort eligible group IDs by SHA-256 of `inj-direct-design/1|split|` plus the group
ID; allocate the first 60% to train, next 20% to calibration and remainder to
test (integer floor at each boundary). This applies within the frozen source and
upstream family strata, assigning each entire group once; groups spanning strata
use one explicit mixed stratum. Source/family-held-out sets are separately identified
and never mixed into these estimates. No rebalancing after scores are seen.

Within each test group choose one representative by minimum SHA-256 of
`inj-direct-design/1|representative|` plus the record ID, before label inspection.
Mixed-label groups contribute only their selected representative to the primary
counts; report all descendants separately. Apply the rubric and exclusions
without viewing model scores. Agent mappings are provisional: a human label audit
and adjudication record is required before claiming validated task quality.
The independent reviewer options include this work; synthetic labels alone fail
that gate. Model-development exposure to test previews disqualifies a source
from unseen confirmatory claims.

The exact source strata, group inventory, held-out families, assignment manifest,
label audit, evaluator, candidate code/config and assets are pinned after eligible
import, before fitting or measurement. Insufficient independent groups means
inconclusive, not permission to count descendants as independent.

## Quality, multiplicity and conditional power

For each of three seeds, require a one-sided exact upper bound on joint FPR
at most 0.01 and lower bound on joint TPR at least 0.90.
For each seed and each quantized candidate (byte-logistic, byte-MLP, compact
encoder), require the one-sided upper bound on positive-example regressions
from float-block to integer-pass at most 0.02. This conservatively bounds
the TPR loss: the paired loss is regressions minus improvements. Also report both
discordance directions and net loss. This criterion can reject a model whose net
loss is acceptable; it cannot certify it by cancelling many regressions against
improvements. The FPR gate remains separate.

There are 15 bounds: six joint FPR/TPR and nine quantization-regression bounds.
Use family alpha 0.05 and Bonferroni alpha `0.05 / 15` per bound; no independence
between seeds or models is assumed. Missing bounds make the full gate incomplete.
Report all seven comparisons without selecting a winner from test. Additional
pairwise comparisons and slices are descriptive, with counts and nominal
intervals, not confirmatory claims. Report source, family, length (0, 1–512,
513–4,096, 4,097–32,768 bytes), obfuscation and benign hard negatives. Small or
missing slices are inconclusive; no universal subgroup guarantee is asserted.

The [reproducible calculation](../../evidence/w13-design-power-2026-10-20.json)
uses exact binomial tails. Desired family power is at least 0.90, conservatively
requiring each bound to pass with probability at least `1 - 0.10 / 15`.
Planning alternatives are joint FPR 0.005, joint TPR 0.95 and positive-example
regression probability 0.005 for every quantized candidate/seed. They are
assumptions, not forecasts. Under IID root-group representatives, the required
test counts are **7,831 benign groups and 1,375 positive groups**. The separate
TPR minimum is 738; the larger positive count covers the regression gate.
Before fitting, recompute both power and acceptance cutoffs for the frozen actual
counts, not a favorable subset. Discrete cutoffs mean passing a minimum count
alone does not guarantee the power target at every larger count.
The union bound supplies family power without assuming independent endpoints.
It does not account for distribution shift, incorrect labels or hidden lineage.

If feasible sources lack these counts, run explicitly exploratory comparisons
under this design, reporting actual uncertainty and the missing power.
Do not lower a target or manufacture independent groups to make the claim pass.

## Resources, retention and stop conditions

Use the Mac first under [AUTHORITY](../../AUTHORITY.json). The local research
envelope includes setup, failures, retries and teardown: six hours total, at
most two hours per job, one foreground job, four threads, 16 GiB memory, 40 GiB
working storage (increased by decision 0033), zero spend. Proving gets at most two hours within that total;
each verification attempt at most 60 seconds. The design target for native
release overhead is at most 1,000 basis points (10%) against a matched baseline;
it is not a measured performance result. Freeze lengths and 5 cold/30 warm
repetitions before cost measurement. Resource or evidence shortfalls reject
the gate without weakening the verifier.

No private transcripts or inputs are admitted. Raw public assets, checkpoints
and per-run private outputs stay local and ignored, accessible to the owner and
authorized agent only. New study assets have a 30-day maximum retention;
per-receipt private witnesses have a 24-hour maximum. Keep failures immutable
within that window. Record deletion inventories/hashes and verify paths are
absent at expiry; filesystem deletion is not a guarantee of SSD erasure.
No background deletion service is authorized. Before a run, the foreground
runner must arrange expiry handling or use a shorter run-scoped lifetime with
cleanup before exit. Existing historical evidence is not retroactively deleted.
Retain approved public aggregate evidence and source/licence identities in git.

Stop on changed frozen terms, ambiguous rights/labels, cross-split contamination,
unsupported full-input execution, nonreproducible export or exhausted resources.
Independent review, real hardware attestation and a checked real proof remain
separate requirements for the full MVP.
