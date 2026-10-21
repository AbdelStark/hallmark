# 0030 — Complete-input CPU guard comparison

Date: 2026-10-20. Scope: W15 engineering, not held-out policy measurement.

Use the ONNX assets selected in decision 0029 and the optional, exactly locked
`guard` runtime. The [dependency review](../../research/evidence/w15-guard-dependencies-2026-10-20.json)
extends the historical W37 inventory without changing it. The
[power calculation refresh](../../research/evidence/w15-design-power-lock-refresh-2026-10-20.json)
repeats the unchanged statistical script: every field except the lock hash equals
the retained W13 calculation, including the numerical environment and all counts.
No statistical target or prior measured result is revised. Pin and read the exact
model/tokenizer bytes before parsing; reject external tensor data, custom domains
and embedded functions/training graphs. Use CPU execution only, one sequential
batch and explicit thread counts. No remote code, pickle, implicit download or
HF credentials are needed by the adapter.

Tokenize the entire UTF-8 prompt, capped at 32,768 bytes, with truncation and
padding disabled. Keep the published tokenizer's normalization: it strips edge
whitespace, applies its precompiled character map and collapses repeated spaces.
This is lossy preprocessing, not byte-preserving evidence. Split the resulting
content token sequence into contiguous, nonoverlapping blocks of 510. Add CLS/SEP
to every block and evaluate it without padding; empty content gets CLS/SEP once.
Reject excess tokens or chunks instead of dropping a suffix. The record score is
the maximum of `float64(logit[1]) - float64(logit[0])` over all blocks; native
model logits are float32. This fixed adaptation differs from the publisher's
truncated inference and needs its own calibration and evaluation.

The baseline has no fitted vocabulary, optimizer, RNG selection or resume state.
Its pretrained data remain incompletely documented. Treat contamination review
as unresolved; absence of local fitting does not establish an unseen test set.
Use the existing separate calibration/evaluation boundaries after pinning the
loaded guard and bounds. No candidate or threshold tuning on test is allowed.

First pass an authored tiny ONNX/tokenizer fixture, including late-token coverage,
Unicode/empty/maximum input, malformed outputs, changed assets and unsafe graph
rejections. Then run fixed harmless probes on the acquired real graph on the Mac,
recording full input hashes, token/chunk counts, logits, exact runtime/source
identities, time and peak memory. Freeze the probes before inference and retain
failures. Neither fixture correctness nor plausible real-model scores establish
the study's FPR/TPR targets, cryptographic binding or an independent verification.
