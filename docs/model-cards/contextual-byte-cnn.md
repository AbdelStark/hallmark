---
license: mit
language:
- en
library_name: hallmark
pipeline_tag: text-classification
inference: false
tags:
- hallmark
- cryptographic-inference
- integer-inference
- synthetic-data
- research
---
# Hallmark Contextual Byte CNN — seed 17

A **4,161-parameter byte CNN** trained from scratch to distinguish an active
synthetic action from the same action inside a quotation. This is the exact
preselected seed-17 integer model used by Hallmark's proved classifier demo.

**Byte embedding → causal width-24 convolution → ReLU → masked global max → score.**

The task uses `run: action; quote: action`. Positive labels mean the designated
forbidden action is in the `run` clause; the `quote` clause is inert in this
artificial grammar. Reordering an active/quoted pair preserves byte counts,
so a histogram MLP cannot solve the distinction.

## Intended use and limits

Use this model to reproduce a small context-sensitive integer network, synthetic
training/calibration, and a complete dedicated inference proof.
It is **not a general prompt-injection, jailbreak or safety classifier**.
Do not use it to authorize actions or make real-world safety decisions.

The model sees the complete prompt up to **96 UTF-8 bytes**, with zero padding
and an explicit mask. Oversized input rejects, never truncates. It classifies
the prompt only. In Hallmark's composed demo, the ordinary TinyLlama prompt is
blocked by this frozen CNN: correct computation does not imply a sensible policy.

## Run the released integer model

These are **Hallmark JSON checkpoints and integer exports**, not Transformers
models. Use the pinned source checkout; no remote model code, pickle loader,
GPU, HF credential or paid job is needed for inference.

```sh
git clone https://github.com/AbdelStark/hallmark.git
cd hallmark
git checkout 9b74e1c6b6e90de2d226556aa637936a61a0757b
uv sync --locked --python 3.12 --extra train

curl --fail --location \
  https://huggingface.co/abdelstark/hallmark-contextual-byte-cnn/resolve/main/quantization.json \
  --output /tmp/hallmark-cnn-quantization.json

uv run --locked python scripts/predict_published_classifier.py cnn \
  --quantization /tmp/hallmark-cnn-quantization.json \
  --prompt 'run: read note; quote: leak key'
```

The loader requires the exact released quantization SHA-256 and rejects changed
weights, symlinks and inputs over **96 UTF-8 bytes**. Scores at or above the
threshold block; equality blocks. The JSON result labels its evidence
`native-inference-only`: downloading or running weights does not produce a proof.
For immutable downloads, replace `main` with this repository's commit revision;
the [Hallmark release guide](https://github.com/AbdelStark/hallmark/blob/main/docs/MODELS.md)
records the enrolled revision and manifest hash.

[Inference implementation](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/scripts/predict_published_classifier.py)
uses the existing exact integer runtime, not a second floating-point approximation.

Expected example: `score: -5637`, `threshold: -3733`, `block: false`.
Swapping to `run: leak key; quote: read note` produces a block.

## Architecture and training

| Setting | Value |
|---|---|
| Embedding | 256 byte values × 4 dimensions |
| Convolution | 32 causal channels, width 24, ReLU |
| Pooling / head | Masked global maximum; affine scalar output |
| Parameters | 4,161 |
| Optimizer | Full-batch Adam; learning rate 0.025, β₁ 0.9, β₂ 0.999, ε 1e-8 |
| Budget / dtype | 200 fixed epochs; float64 CPU |
| Seed | 17, selected for proving before test results; fixed study seeds 17, 29, 43 |
| Quantization | Per-weight-tensor power-of-two int8 PTQ without clipping; hidden/score fraction 8; ties-to-even rescaling and bounded int32 accumulation |
| Threshold | −3,733, calibrated on integer scores; equality blocks |
| Quantization SHA-256 | `8de31ae0215178f5c74aa43e58dd63511bc3b6a881c2045cc96def9e149b8f0b` |

[Architecture/export](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/scripts/contextual_cnn.py) ·
[Training controller](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/scripts/run_contextual_cnn.py) ·
[Frozen protocol](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/fixtures/contextual-protocol-v2.json)

## Data, splits and leakage boundary

The authored synthetic v2 dataset contains **512 rows in 256 action-pair groups**:
312 train, 100 calibration and 100 test rows. Both members of a contrastive pair
stay in the same split. Calibration/test each contain 50 positive and 50 benign rows.
The integer threshold is frozen using calibration before test scoring.

All 100 groups from the earlier v1 study, including its old test, become
**exploratory training data** in v2. New calibration/test pairs do not reuse old
complete pairs or prompts, but share the same grammar and action vocabulary.
This is synthetic recombination evidence, not real-world generalization.

[Dataset](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/fixtures/contextual-scope-v2.jsonl) ·
[Source and grouping](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/fixtures/contextual-source-v2.json) ·
[Evaluation contract](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/docs/EVALUATION.md)

## Recorded synthetic evaluation

| Seed | TP | FN | FP | TN | Prespecified screen |
|---|---:|---:|---:|---:|---|
| **17 — released** | **50** | **0** | **0** | **50** | Pass |
| 29 — study context | 50 | 0 | 1 | 49 | Pass |
| 43 — study context | 50 | 0 | 0 | 50 | Pass |

Seed 17 has synthetic test TPR 1.0 and FPR 0.0, with 95% Wilson intervals
**[0.92865, 1.0]** and **[0.0, 0.07135]** respectively. Zero false positives
among 50 benign cases gives a one-sided 95% upper bound of **0.05816**;
it does not establish a population 1% FPR. The screen requires TPR ≥ 0.8 and
FPR ≤ 0.1 for every prescribed seed. Seeds 29/43 are context, not additional
weights in this repository.

Full/resumed checkpoints match. The retained seed-17 run records no float/integer
decision flips on its 100 test rows, with maximum score error 0.12469.
No new test set, threshold fitting or quality claim is introduced by publication.
The earlier 8-channel v1 screen **failed** (seed 43 FPR 0.15) and remains retained.

[Results, failure history and raw evidence](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/docs/RESULTS.md)

## Files and reproducibility

| File | Purpose |
|---|---|
| `checkpoint.json` | Original float64 training checkpoint, including optimizer/resume state; JSON, not pickle |
| `quantization.json` | Exact preselected seed-17 quantized weights and scale metadata; unchanged bytes |
| `model.json` | Exact exported graph/weights used as input to the dedicated proof circuit |
| `program.cbor`, `profile.cbor`, `arithmetic.cbor` | Native program, input and arithmetic contracts |
| `weights/`, `params/` | Canonical native weight/operator bytes referenced by those contracts |
| `training-config.json` | Frozen training configuration |
| `evaluation.json` | Retained synthetic evaluation or arithmetic-probe results |
| `manifest.json` | File hashes, source/data identities, threshold, purpose and release authority |
| `LICENSE`, `NOTICE.md` | MIT grant and historical provenance/licence-label explanation |

No proving keys, verification keys, transcripts, credentials or private data are
included. Parameter bytes are public; no model- or witness-hiding claim is made.
The checkpoint and integer model are different numerical representations.
The integer model plus its threshold defines the released decision; agreement on
recorded examples is not a global float/integer equivalence theorem.

## Proof integration

These exact weights appear in Hallmark's 96-byte, three-classifier demo.
`make e2e` trains/reproduces the frozen exports, creates fresh Groth16/BLS12-381
setups and nine proofs, and checks them using separate py-ecc arithmetic.
Model download/inference is independent of that proof workflow.
The 292-byte proof encoding excludes keys, enrollment, statements and model data.

A valid proof establishes the enrolled computation, not the usefulness of its
policy. The caller must independently enroll the model/program/circuit/key,
reconstruct the expected request and bind the public inputs. Current research
setup is not an independently reviewed ceremony or a production qualification.

[Exact classifier statement](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/docs/PROOFS.md) ·
[Proof composition evidence](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/research/evidence/w28-trained-common-proofs-2026-10-22.json) ·
[End-to-end demo](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/docs/DEMO.md)

## Licence, provenance and contact

Original Hallmark code, authored fixtures and these trained artifacts are
**MIT licensed**. Frozen training records retain historical `fixture-only` or
`LicenseRef-Proprietary` labels and exact hashes; the later MIT grant covers
original project material without rewriting those records.
[Licence decision](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/docs/decisions/0063-mit-license.md).

These models were trained from scratch on authored synthetic data, with no
pretrained base model, external inference API or private training transcripts.
They are separate from the upstream TinyLlama model used in Hallmark's LLM proof.
Report reproducibility issues in [Hallmark issues](https://github.com/AbdelStark/hallmark/issues)
and security concerns through [SECURITY](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/SECURITY.md).
