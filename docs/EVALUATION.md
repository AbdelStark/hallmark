# Evaluation contract

The evaluator is part of the research protocol, not an optimizer-controlled metric. Changing splits, policy, preprocessing, metrics or acceptance criteria starts a new experiment identity and decision. The bootstrap tests validate plumbing, not safety capability.

## Data admission

Each JSONL row follows `Record` in `src/hallmark/contracts.py`: stable record/group/family IDs, source and exact source revision, licence, policy, split, language, prompt, response and binary label. Label 1 means policy-positive/block; label 0 means benign/pass. The schema does not infer intent or label quality. Contradictory policies must never be pooled into a single target without a recorded mapping.

The experiment pins the byte SHA-256 of the entire dataset and allowlists reviewed sources/licences. Declaration in a config does not constitute legal approval. All three splits must exist. Record IDs are unique; a group cannot cross splits; an identical exact prompt/response pair cannot cross splits. Mutations, paraphrases, translations, synthetic descendants and shared conversation history belong to one upstream group. Exact matching cannot catch semantic duplicates or contaminated pretraining: run a separately reviewed near-dedup and lineage audit before real evaluation.

Files are bounded to 8 MiB and text fields to 32,768 characters in this baseline. Oversized inputs fail rather than truncate. Symlink inputs and nonregular files fail. These checks are not isolation against an adversary concurrently mutating the filesystem; use a trusted, read-only dataset snapshot for a real run.

The separate [v1 import API](decisions/0021-lineage-data-admission.md) checks
caller-pinned approval and source bytes before producing normalized records,
raw-row lineage and immutable-by-convention split artifacts. It groups parent
closure, shared histories, identical prompts and reviewed ASCII case/whitespace
equivalents before the frozen study split. It retains contrastive rows and
requires a complete candidate review inventory. Semantic duplicates, truthful
lineage, human annotations and source rights remain review obligations. Its
larger import limits do not change the baseline loader's 8 MiB limit.

## Frozen selection procedure

1. Fix policy, source/lineage inventory, group split, target FPR, confidence level, budget, candidate roster and stopping rule before training.
2. Use train for fitting; use calibration only for the selected threshold. Model/hyperparameter selection needs a train-internal validation split or fixed cross-validation, not repeated test feedback.
3. Quantize and export first. On benign calibration integer scores `b`, choose the smallest integer threshold admitting at most `floor(target_fpr * len(b))` false positives: descending score at that index, plus one. Thus `score >= threshold` blocks, including ties.
4. Freeze the artifact. Evaluate test once for the declared decision. Preserve negative/failed results. Later iterations require new predeclared test data or explicitly exploratory reporting.

The small fixture uses a single prespecified baseline and does not implement encoder selection, train-internal folds or multiple-testing controls. Calibration empirical FPR is not a population guarantee.

The separate [grouped comparison API](decisions/0028-grouped-baseline-selection.md)
implements five train-internal rotations: three fitting folds, one internal
threshold fold and one validation fold. Vocabulary and optimizer fitting receive
only the fitting rows. Group assignment and representatives do not use labels.
Every declared candidate/seed and failure is retained; selection uses pooled
representative TPR, lower FPR, then lexical candidate ID, separately per family
and seed. Nonconverged or incomplete candidates are ineligible. These selection
estimates are not held-out quality results.

Its outer calibration/evaluation calls require separately retained fit/calibration
pins and reject wrong split tags or overlapping groups/prompts. Integer thresholds
use boundary plus one; float n-gram thresholds use the next representable float.
The allowed false-positive count uses exact decimal arithmetic. Test primary
counts use one representative per group; all-descendant counts stay separate.
The caller still enforces admitted inputs, once-only testing and the final quality
gate. The original experiment/evaluator identities above are unchanged.

The [fixed pretrained guard](decisions/0030-complete-input-guard.md) enters the
same outer calibration/evaluation path through `bind_guard`. Its score is the
maximum float64 logit margin over every contiguous content-token block, using the
pinned lossy tokenizer and float32 CPU graph. It performs no local fitting or
train-internal selection; its undocumented pretraining overlap remains unresolved.
Engineering probes, including positive margins on harmless repetitive inputs,
do not establish a calibrated low-FPR operating point.

## Metrics and uncertainty

Primary model gate: TPR at the fixed calibration policy, reported alongside test FPR and counts. `TPR = TP / (TP + FN)` and `FPR = FP / (FP + TN)`. Missing denominators are null, never 0. Report confusion matrix and Wilson two-sided intervals with `z = NormalDist.inv_cdf(1 - alpha/2)`.

For zero false positives in `n` independent benign test examples, a one-sided exact upper bound is `1 - alpha^(1/n)`. At alpha 0.05, demonstrating an upper bound at most 0.01 requires at least 299 independent benign examples with zero false positives. At 0.001 it requires at least 2,995. These are minimum counts conditional on zero events, not a power calculation or protection against distribution shift. Correlated descendants are not independent observations.

The shipped test split has only eight benign records. Even perfect fixture predictions cannot establish a 1% FPR bound. The report must say `insufficient-evidence`. No pooled average substitutes for subgroup evidence: later real evaluations report language, policy family, source, length, obfuscation, attack lineage and benign hard-negative slices with counts/intervals and multiplicity disclosure. Predefine minimum subgroup power; small slices stay inconclusive.

Future candidate comparisons use paired examples and group-aware bootstrap confidence intervals for deltas, prespecified seeds and held-out attack families. Separate in-distribution, source-held-out, adaptive and temporal evaluations. Report clean quality, quantization drift, float/integer decision disagreements, worst slices and attack success. AUROC alone is not a low-FPR operating point.

## Evidence artifacts and replay

`hallmark run` writes a fresh directory with five artifacts and then a complete manifest: frozen config; integer model; predictions; results; source/environment/training record. The manifest hashes their exact bytes. Source records include Python module snapshots, git revision/status/diff, installed package versions and lockfile hash when available. Failed admitted runs write `failure.json` and never a complete manifest. Do not reuse directories or relabel failed runs as successful.

Enroll the manifest hash outside the bundle. `audit-run` checks the enrolled hash, exact artifact set, data hash, model/config agreement, calibration rule and replayed predictions/metrics. An attacker who supplies both a modified bundle and the supposedly trusted hash controls the starting point. Replay does not retrain the model or authenticate its training history. Reproduction means repeating training from an exact source/environment/data identity and comparing substantive model/results, not timestamps or git-dirty metadata.

`source.json` embeds code/diffs and local environment metadata. It is private evidence, not an automatically safe upload. Data text is excluded from prediction reports, but the input dataset and trained weights may still be sensitive. No hosted tracker or artifact uploader is configured.

## Cost and proof evaluation, not implemented

Measure the whole path on a named host: preprocessing, inference, quantization/export, setup, witness generation, proving, verification, serialization and attestation checks. Record CPU/GPU/RAM/VRAM, versions, thread count, cold/warm mode, batch size, sequence/chunk count, repetitions, p50/p95, peak memory, proof bytes and failures. Setup cost is not free; amortization states its denominator. Compare candidates on identical inputs and actual approved proof backends. Host inference speed and parameter count do not establish proving performance.

Accept proof integration only after bit-exact host/circuit decisions on adversarial and boundary vectors, rejection of every mutated public input and key, overflow/range tests, complete chunk coverage and an independently checked proof. A compiler's successful import is not end-to-end verification.
