# Published classifier models

The exact **seed-17 MLP and contextual CNN used in Hallmark's proved demo** are
public on Hugging Face. Both were trained from scratch on authored synthetic
fixtures and are released under MIT. Their model cards document architecture,
data/splits, training, quantization, checks and limitations.

| Model | Parameters | Threshold: score ≥ threshold blocks | Download and card |
|---|---:|---:|---|
| Byte-count MLP | 1,033 | 0 | [abdelstark/hallmark-byte-mlp](https://huggingface.co/abdelstark/hallmark-byte-mlp) |
| Contextual byte CNN | 4,161 | −3,733 | [abdelstark/hallmark-contextual-byte-cnn](https://huggingface.co/abdelstark/hallmark-contextual-byte-cnn) |

These are custom **Hallmark JSON checkpoints, quantizations and native CBOR
exports**, not Transformers models. The frozen integer graph and threshold
define the decision. The original float64 checkpoint also includes optimizer
state for same-environment resume. No pickle loading or remote model code is needed.
The literal rule has no trained weights; TinyLlama remains an
[upstream model](https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0), not a
Hallmark-trained release.

The frozen MLP always allows within the 96-byte proof-demo domain: a
[conservative integer bound](../research/evidence/mlp-domain-bound-2026-10-27.json)
places every admitted score in [−5600, −2338], below threshold 0. Its complete
arithmetic remains a proof-pipeline baseline; it is not a useful filter at this
length limit. The rule and CNN provide block controls.
[Follow-up #131](https://github.com/AbdelStark/hallmark/issues/131) tracks a new
model-quality experiment without changing the frozen comparison or release.

## Download and run

From the Hallmark checkout, using uv 0.9.18 and Python 3.12:

```sh
uv sync --locked --python 3.12 --extra train

curl --fail --location \
  https://huggingface.co/abdelstark/hallmark-contextual-byte-cnn/resolve/51461ea4401188a14997c5003ea2073ffb91e1ed/quantization.json \
  --output /tmp/hallmark-cnn-quantization.json

uv run --locked --extra train python scripts/predict_published_classifier.py cnn \
  --quantization /tmp/hallmark-cnn-quantization.json \
  --prompt 'run: read note; quote: leak key'
```

Expected result:

```json
{"block": false, "evidence": "native-inference-only", "input_bytes": 31, "model": "cnn", "score": -5637, "threshold": -3733}
```

Swapping the actions to `run: leak key; quote: read note` produces a block.
The MLP uses the same command with `mlp` and its own quantization:

```sh
curl --fail --location \
  https://huggingface.co/abdelstark/hallmark-byte-mlp/resolve/05b2bdef120d3aea9133af042d15ed1a3a621aa9/quantization.json \
  --output /tmp/hallmark-mlp-quantization.json

uv run --locked python scripts/predict_published_classifier.py mlp \
  --quantization /tmp/hallmark-mlp-quantization.json \
  --prompt 'run: read note; quote: leak key'
```

Its score is −3,959 and it passes. Equal byte histograms produce the same MLP
score, so it cannot learn the active/quoted distinction. The MLP inference path
needs only core dependencies; CNN export construction needs NumPy from `train`.
Native inference runs on Linux/macOS without a GPU, HF credential or paid job.
The full proof reproduction still has the [Mac demo prerequisites](DEMO.md).

The [loader](../scripts/predict_published_classifier.py) admits only the exact
two released quantizations, hash-checking bytes before parsing. It rejects
symlinks, modified weights and inputs over **96 UTF-8 bytes**, without truncation.
Output is native inference, not a proof. To generate and separately check
dedicated classifier proofs, use `make e2e`.

## Immutable identities

Both repositories have a `v1.0.0` tag. For reproducibility, pin the full commit,
not a mutable branch or tag:

| Model | Hub commit | Manifest SHA-256 |
|---|---|---|
| MLP | `05b2bdef120d3aea9133af042d15ed1a3a621aa9` | `2c5d2d0cc1e823c5d8ea14670dd700c076c96a43d11d69096a44579693de7050` |
| CNN | `51461ea4401188a14997c5003ea2073ffb91e1ed` | `79a68793ad97e1bef47bc9328756416d30f781ce1ff2b33f8f126681e1ed380e` |

The [publication receipt](../research/evidence/hub-model-publication-2026-10-27.json)
lists every released file, byte count and SHA-256. The per-repository
`manifest.json` records data/source identities and release authority.
Quantization pins match the existing [end-to-end driver](../scripts/run_e2e.py).
Regenerated `model.json` bytes match the retained proof-circuit inputs exactly.

## Model cards and validation

[MLP card source](model-cards/byte-mlp.md) ·
[CNN card source](model-cards/contextual-byte-cnn.md) ·
[Publication decision](decisions/0080-public-classifier-models.md)

Publication checks:

- Original full/resumed checkpoints match byte for byte.
- Requantization reproduces the exact preselected exports.
- Native exported models match the proved-model bytes.
- All 100 CNN test scores and decisions match retained predictions; no fitting,
  new test selection or threshold tuning occurs.
- Anonymous downloads at both pinned Hub commits match every artifact hash.
- Documented inference controls run from the downloaded weights.

The model cards disclose the CNN's failed earlier screen, three prescribed
seeds, uncertainty and shared synthetic grammar/vocabulary. Seed 17 was
preselected for proving before test results. The MLP has arithmetic probes,
not a held-out quality evaluation. Neither model is an operational safety filter;
the frozen CNN blocks the ordinary TinyLlama prompt in the composed demo.

## Licence and trust boundary

MIT covers original models, code and authored fixtures under
[decision 0063](decisions/0063-mit-license.md). Frozen data and training records
keep historical `fixture-only` / `LicenseRef-Proprietary` labels and hashes;
each Hub release includes a notice explaining the later grant.
No private data, setup keys or third-party model checkpoints are republished.

A model download does not authenticate training history, enroll a circuit/key,
or prove an inference. Read the [classifier statement](PROOFS.md) for public
inputs, caller responsibilities and setup assumptions. Hardware provenance,
witness hiding and independent backend qualification remain outside this release.
