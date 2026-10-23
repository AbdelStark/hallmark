# A short response from a real pretrained LLM

2026-10-23. Source review and implementation gate, not a reproduced LLM proof.
The owner chose a short generated response, minutes to a few hours of proving,
fast verification, and an explicitly pinned and disclosed quantized model.
Witness privacy is optional. This proposal does not alter the classifier protocol.

## Recommendation

Use **SASH as the first integration candidate**, with **TinyLlama-1.1B-Chat-v1.0**
as the initial model to assess. Prove a complete short greedy continuation from
a real prompt. The application should display the actual response, model identity,
proof-generation cost and a separate verifier's result. Changing the prompt,
answer or model should visibly reject.

TinyLlama is a pretrained instruction-tuned model with an Apache-2.0 model card
and ordinary Llama attention/RMSNorm/SiLU operations. Its 22 layers, width 2,048,
32 query heads, four KV heads and 32,000-token vocabulary are a better initial
match to SASH's implemented relation than Gemma's additional operations. This is
an architectural fit now supported by native inference and complete witness
extraction on one prompt. Actual proof compatibility and caller-side verification
remain open. This does not establish language-model quality.

Model revision: [`fe8a4ea1ffedaf415f4da2f062534de366a451e6`](https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0/tree/fe8a4ea1ffedaf415f4da2f062534de366a451e6).
The two smaller candidates are
[SmolLM2-135M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct/tree/12fd25f77366fa6b3b4b768ec3050bf629380bac)
and [SmolLM2-360M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct/tree/a10cc1512eabd3dde888204e902eca88bddb4951).
Both use the Llama family without QKV biases, but their widths (576/960), head
counts (9/15) and tied output embeddings need checking. Parameter count alone
does not predict prover cost. Do not switch to random weights to make a test pass.

## Why SASH, and why not Gemma first?

Source pin: [`eb95bfa887299d1637550228d42086c27cbb2b3b`](https://github.com/sg-ai-safety-hub/zk-inference-prover/tree/eb95bfa887299d1637550228d42086c27cbb2b3b),
Apache-2.0. Its [statement](https://github.com/sg-ai-safety-hub/zk-inference-prover/blob/eb95bfa887299d1637550228d42086c27cbb2b3b/docs/statement.md)
covers transformer segments, pinned-weight multiplication, attention, nonlinear
operations, residual and KV boundaries, embedding selection and strict argmax.
It is a specialized Circle STARK construction, with lookup tables and reductions,
not execution inside a general-purpose zkVM.

The [upstream research note](https://www.aisafety.sg/research/what-proving-llm-inference-actually-costs-research-note)
reports full quantized Llama-3.1-8B generation. For 4,096 prompt positions plus
512 generated positions it reports 1.02 hours of proving-loop wall time, separately
13 minutes of witness extraction, about two minutes of CPU verification and
18.5 GiB of serialized proofs on an H100. These are author measurements, not our
reproduction or an estimate for TinyLlama. Shorter blocks incur substantial fixed
overhead; scaling these figures by parameter count or response length is invalid.

That note explicitly excludes Gemma's additional normalization and local/global
attention operations from the supported proof shape. Gemma branches in the
Python witness generator do not establish a complete Gemma proof. The current
Google 270M and 1B model metadata also report gated Gemma terms; no terms were
accepted and no gated files were downloaded in this review.

SASH has no trace blinding, which matches this experiment's integrity-only scope.
Its reported security parameters and negative controls are not an independent
security audit. The public [results repository](https://github.com/sg-ai-safety-hub/zk-inference-results/tree/11decec3c0b62c707618aab5deb82750b355d202)
contains author measurements; several headline manifests mark `prover_dirty:true`.
A fresh run must pin a clean source tree and all calibration inputs instead of
claiming a commit alone reproduces those records.

## What the first demo must establish

For pinned quantized weights, arithmetic, tokenizer and chat template, the displayed
answer is the greedy continuation of the displayed complete prompt. Prove every
required prompt position and generated token, including the transition from the
last prompt position to the first answer token. Use an explicit bounded output
length first; do not silently claim natural EOS termination or stochastic sampling.

Tokenization and detokenization may remain outside the circuit because the
verifier sees the text and independently applies pinned code. The verifier must
receive trusted model roots, calibration, expected shape/coverage and prompt/answer
tokens from its caller. A manifest supplied only by the prover is insufficient.

The [upstream grid verifier](https://github.com/sg-ai-safety-hub/zk-inference-prover/blob/eb95bfa887299d1637550228d42086c27cbb2b3b/prover/src/boundary.rs)
has an actual proof-verification mode, but optional checks remain caller obligations.
Require `--verify`, `--prompt`, `--verify-calibration`, independently enrolled
`--expect-model-roots`, complete expected layers/blocks and output equality.
Reject all unsound skip flags, gaps and unchecked bindings. Do not accept a
chain-only report as cryptographic verification.

## Bounded implementation sequence

1. Build the pinned upstream synthetic digest case to test the environment only.
2. Load the pinned real model; freeze calibration and quantization separately
   from a small public prompt evaluation set. Check response usefulness and
   report divergence from the original numerical model. No training is needed.
3. Prove one real layer with all required bindings and range checks, then all
   layers plus the output head for one next-token step as an internal milestone.
4. Prove 8–16 generated tokens with the complete prompt included. Export proof
   files and verify in a fresh process without model weights or witness traces.
5. Reject changed prompt/response/model/calibration, missing/reordered segments,
   KV substitutions, incorrect argmax ties and altered proof bytes. Measure cold
   preparation, witness extraction, proving, verification, peak memory and disk.

The final acceptance gate is step 4 plus step 5, not the one-token milestone.
Target a readable short answer and laptop-scale verification; these are targets,
not latency promises. If the 1.1B shape exceeds limits, assess SmolLM2 before
changing the statement or weakening checks.

## Compute and alternatives

The pinned [upstream build](https://github.com/sg-ai-safety-hub/zk-inference-prover/blob/eb95bfa887299d1637550228d42086c27cbb2b3b/README.md)
type-checks on macOS but does not link there; Linux currently requires CUDA 12.9
even for the CPU backend. Use the Mac for source, data and quality preparation;
make a bounded Linux job on an already approved provider the first build/proof
path. A native Mac port is optional follow-up work. No GCP dependency follows.
GPU model, memory fit, actual available balance and a cost-capped job manifest
must be measured/verified before launch; no cloud price or spend is asserted here.

[The alternative-source review](llm-proof-alternatives.md) explains why DeepProve's
current and historical core licences prevent assuming a permissive integration,
why the published zkGPT demo's random weights do not meet this task, and why
zkLLM's released verifier architecture needs substantial additional work.

The [first execution preflight](evidence/llm-preflight-2026-10-23.json) now retains
two failed Mac links, an exact-hash TinyLlama download and a successful native
quantized response. The Linux CPU build reproduced the upstream aligned synthetic
proof digest and passed its three selected integration suites. The corrected real
witness covers all 22 layers plus the output head: 25 prompt positions and seven
generated input positions, whose last eight head outputs include the answer EOS.
A 23-segment proof and changed-claim rejection are still required. [Decision 0064](../docs/decisions/0064-real-llm-build.md)
records the implementation sequence and resource envelope. The alternatives note
retains its separate interrupted Git LFS download.

## Current reproduction boundary

The engineering prompt is “Name the capital of France in one short sentence.”
Its pinned chat template produces 25 tokens. Both the reference and quantized
model emit `The capital of France is Paris.` followed by EOS in eight tokens.
The original fixed 16-step run also retains the subsequent whitespace; selecting
the eight-token answer for the proof is a disclosed engineering choice, not a
held-out result or evidence that every prompt works.

The proof plan uses one causal block of 32 positions. It must establish every
layer for the complete prompt and first seven generated tokens, then the output
head at positions 24–31 for all eight answer tokens. The caller must compare the
last output token explicitly: it has no following input position for the grid's
continuity check to cover.

The first full extraction incorrectly passed `--embed` to every layer. Source
review caught this before proving: that flag enables an embedding lookup wherever
the table exists. A fresh extraction uses it only on layer 0. All 1,856 written
arrays now match their recorded digests, all 22 residual links agree byte for byte,
and the head outputs match all eight expected answer IDs. This is witness checking,
not a proof. Both extraction attempts remain retained.

The plan pins each layer's exponent-table width from the actual witness bounds.
Layer 0 still needs 26 bits (67,108,864 rows); the other layers need 21–25 bits.
These bounds do not change the model's arithmetic. They motivate a bounded
high-memory Linux CPU proof attempt before selecting a GPU configuration.

The first real layer-0 root build subsequently rejected the witness on one
attention row. The upstream Python `int_gemm_exact` helper cast its exact float64
result back to float32, losing an odd integer above 2²⁴. The
[one-line patch and regression](probes/sash/README.md) retain the selected dtype;
[decision 0065](../docs/decisions/0065-exact-llm-witness-accumulators.md) gives this
candidate a new identity. Fresh generation returns the same answer. All 23,552
attention rows in its new witness agree with exact integer Q/K products and
the exponent-table rule. The Rust proof and verifier code remain unchanged.

The corrected root builder passes; its roots were retained locally before proving.
Proof generation then aborted on a 32 MiB allocation under the frozen 96 GiB
address-space cap, after 363.917 proving seconds. Peak child RSS was 96,638,864 KiB.
All eight output files are retained and hashed. No real-layer proof was produced;
the next gate is a separately bounded larger-memory run of the same candidate.
