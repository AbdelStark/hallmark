# 0029 — Guard asset selection for bounded qualification

Date: 2026-10-20. Scope: W15 / issue #16. This is delegated source selection,
not a measurement admission, installation, download of weights or quality claim.

Select Protect AI's `deberta-v3-base-prompt-injection-v2` at
`90c9989b1a342275dd0d1a95aad283c04e075671` for a fixed task-matched research
comparison. The [source review](../../research/evidence/w15-guard-source-selection-2026-10-20.json)
retains exact metadata bytes, licence observations, advertised asset hashes and
remaining gates. The owner's decision 0019 delegates public source selection.

The pinned model card and model LICENSE agree on Apache-2.0. The pinned Microsoft
base-model card declares MIT, and its linked implementation has retained MIT
terms. Rely on the publishers' express model grants for bounded public-input
research. No conflicting model-specific or gated terms were observed in those
files. Preserve model/base notices with any acquired assets. This review does
not establish rights to every upstream training example or authorize acquiring
the unnamed, unlicensed data described by the guard card. In particular, its
equation of absent licences with public domain is not adopted.

The archived project's maintenance and training-provenance gaps remain recorded.
Its reported metrics are not reproduced results. Its named training sources and
unknown additional sources must be considered during contamination review; they
cannot simply be relabelled unseen confirmatory data.

Prefer the supplied ONNX model for local qualification with standard, separately
reviewed runtime/tokenizer packages. No remote Python model code or pickle state
is needed. This avoids acquiring a second framework and duplicate weight format;
it does not establish graph correctness or model quality. The approximately
739 MB advertised graph is still unverified until the exact download passes its
recorded byte hash. Record fresh storage/time limits before acquisition.

The published usage examples truncate at 512 tokens. This study requires complete
32,768-byte input coverage, so qualify full-input tokenization and explicit chunk
masking/aggregation before any comparison. Actual weights/tokenizer inspection,
runtime dependency review, execution, dataset/label audit and final admission
remain open. No HF token or paid compute was used for this metadata review.
