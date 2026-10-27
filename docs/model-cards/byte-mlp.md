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
# Hallmark Byte MLP — seed 17

A **1,033-parameter byte-count MLP** trained from scratch for Hallmark's
integer-arithmetic and proof-pipeline experiments. This is the exact seed-17
model used by the proved classifier demo.

**256 byte counts → 4 ReLU units → affine score → threshold 0.**

It is a synthetic marker baseline. It cannot distinguish reordered text with
the same byte histogram, including the active/quoted contrastive pairs used
to test the contextual CNN. It is not a trained prompt-injection detector or
a general safety classifier.

## Intended use and limits

Use this model to reproduce training/resume, power-of-two post-training
quantization, integer graph execution, and dedicated inference proofs.
Do not use it to authorize actions or filter real harmful content. The training
fixture is tiny and artificial; there is **no held-out quality evaluation**.

The released inference/proof demo accepts at most **96 UTF-8 bytes**, without
truncation. The training/native program uses 512-byte chunks and a larger native
capacity; that does not enlarge the admitted proof-demo limit. Byte counts lose
order within a chunk. Unicode is encoded as UTF-8 bytes, not semantic tokens.

This particular quantized model **always returns allow within the 96-byte demo
domain**. A conservative interval relaxation over all 256 byte counts with
total count at most 96 bounds its score to **[−5600, −2338]**, below threshold 0.
The full arithmetic is still constrained by its inference proofs; it provides
no discriminative decision inside that domain. The rule and contextual CNN
supply the combined workflow's block controls. This is an integer-bound
analysis, not a quality evaluation or a cryptographic proof.
[Bound and method](https://github.com/AbdelStark/hallmark/blob/16586c7716bd675186b9af0f0b833670b3977f38/research/evidence/mlp-domain-bound-2026-10-27.json) ·
[Separate model-quality follow-up](https://github.com/AbdelStark/hallmark/issues/131).

## Run the released integer model

These are **Hallmark JSON checkpoints and integer exports**, not Transformers
models. Use the pinned source checkout; no remote model code, pickle loader,
GPU, HF credential or paid job is needed for inference.

```sh
git clone https://github.com/AbdelStark/hallmark.git
cd hallmark
git checkout 9b74e1c6b6e90de2d226556aa637936a61a0757b
uv sync --locked --python 3.12

curl --fail --location \
  https://huggingface.co/abdelstark/hallmark-byte-mlp/resolve/main/quantization.json \
  --output /tmp/hallmark-mlp-quantization.json

uv run --locked python scripts/predict_published_classifier.py mlp \
  --quantization /tmp/hallmark-mlp-quantization.json \
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

Expected example: `score: -3959`, `threshold: 0`, `block: false`.

## Training and quantization

| Setting | Value |
|---|---|
| Data | 12 authored marker training records in 12 groups: 6 positive, 6 benign |
| Initialization / selected seed | Seed 17; seeds 17, 29 and 43 were prescribed in the fixture |
| Optimizer | Full-batch momentum SGD, learning rate 0.05, momentum 0.8, L2 0.001 |
| Budget / dtype | 80 epochs; float64 CPU |
| Input features | Byte counts normalized by 512 during fitting; equivalent scale folded into the integer export |
| Quantization | Power-of-two PTQ, int8 weights, bounded int32 arithmetic and ties-to-even rescaling |
| Released scale metadata | First fraction 7, last fraction 2; hidden scale 256, score scale 4096 |
| Decision | Integer score ≥ 0 means block |
| Quantization SHA-256 | `f8090161455ee56cdcd73eaab44437efa3b278a786d7c246491da5f1e1431a9c` |

[Training fixture](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/fixtures/mlp-training.json) ·
[Trainer](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/src/hallmark/mlp_training.py) ·
[Export](https://github.com/AbdelStark/hallmark/blob/9b74e1c6b6e90de2d226556aa637936a61a0757b/src/hallmark/mlp_export.py)

## Recorded checks

The retained seed-17 fit reaches loss **0.33660603576065673** at the fixed
80-epoch limit. Full and resumed checkpoints match exactly in the recorded
environment. Seven arithmetic probes cover empty input, chunk boundaries,
multiple chunks, maximum native input length and Unicode.
These validate software arithmetic/resume, not accuracy or generalization.
Some training/probe lengths exceed 96 bytes and are not admitted by the Hub
inference example or combined proof demo.

The model assigns equal scores to equal-byte-count contextual pairs. This is
a known architectural limit, not an evaluation failure to conceal.
The selected model and exported bytes are reused without retraining or
selection on a new test set for this release.

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
