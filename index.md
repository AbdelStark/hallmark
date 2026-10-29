---
title: Circle STARK verifiable inference, explained
description: Download actual Circle STARK proofs, inspect stage timings and machine records, and verify the TinyLlama and classifier reference runs.
template: home.html
hide:
  - navigation
  - toc
---

<div class="hm-route">
<span class="hm-route-index">01</span>
<div><h3>Learn</h3></div>
<div><p>What a verifier checks, and how the caller fixes the model and inputs it expects. No cryptography background required.</p><a href="docs/learn/">Read the learning guide →</a></div>
</div>
<div class="hm-route">
<span class="hm-route-index">02</span>
<div><h3>Run</h3></div>
<div><p>Prove classifier decisions on a Mac, prove the TinyLlama answer with HF Jobs, or benchmark the prover on an H200.</p><a href="docs/START/">Choose a workflow →</a></div>
</div>
<div class="hm-route">
<span class="hm-route-index">03</span>
<div><h3>Check</h3></div>
<div><p>Download the actual proofs, then check the statements, hashes, raw measurements and failed runs behind each result.</p><a href="docs/REFERENCE-RUN/">Get the proofs →</a></div>
</div>

## What the LLM proof covers {#a-real-model-a-precise-statement}

```text
Prompt:   Name the capital of France in one short sentence.
Response: The capital of France is Paris.
```

![What the TinyLlama proof covers: a 32-position input block, 23 segment proofs stacked as layers, the output head's argmax at positions 24 to 31, and seven links feeding each output back as the next input.](docs/assets/figures/llm-statement.svg)

The prompt becomes 25 tokens; one 32-position block holds them plus the first
seven answer tokens. SASH proves the embedding, all **22 transformer layers**
and the final norm and output head as **23 segment proofs** joined by **22
residual links**. The head's argmax at positions 24–31 gives the eight answer
tokens, and seven of them must equal the next input, which closes the loop
through EOS.

The proof covers the disclosed quantized model. Equivalence to the original
floating-point model, hardware provenance and witness hiding are not claimed.
[The exact statement](docs/LLM-PROOF.md#the-statement).

## What a classifier proof states

![What one classifier proof states: a witness of prompt bytes, salt and intermediate values; four constrained steps (complete input, SHA-256 commitment, integer classifier, threshold decision); a public statement of 100 fields.](docs/assets/figures/classifier-statement.svg)

<div class="hm-statement">
<p class="hm-eyebrow">What verification establishes</p>
<p>A valid classifier proof can return “block” for a harmless prompt. The proof checks the computation; whether the policy is any good, and whether its inputs are authentic, need separate evidence.</p>
</div>

## Where the proof ends

![Three columns: what is proved by the STARK, what the caller checks, and what is not claimed.](docs/assets/figures/trust-boundary.svg)

## Recorded measurements {#measurements-you-can-follow-back-to-evidence}

![TinyLlama proving on one H200: CUDA cuts the proving session from 547.75 s to 53.94 s (10.15×); complete segment commands go from 679.49 s to 155.89 s (4.36×); trace generation is unchanged.](docs/assets/figures/perf-llm-gpu.svg)

![One fresh classifier run, zoomed in: of the 302.96 s run, CNN training takes 172.94 s and the proof campaign 93.50 s; inside it, nine prover commands take 50.03 s, of which final STWO proving is 24.06 s.](docs/assets/figures/perf-classifier-c1.svg)

| Observation | Recorded result | Read it in context |
|---|---|---|
| L1 GPU proving-session timer | **53.94 s**, versus 547.75 s SIMD | [Session boundary and raw segment logs](docs/REFERENCE-RUN.md#l1-complete-tinyllama-response) |
| L1 complete segment commands | **155.89 s**, versus 679.49 s SIMD | Includes loading, trace generation, proving, inline verification and serialization |
| L1 full-bundle verification | **84.32 s** CPU grid on the H200 host; **3.40–3.53 s** compiled-root Mac checks | [Different preprocessing, same proof payload](docs/PERFORMANCE.md#verifying-the-llm-bundle) |
| L1 actual LLM proof JSON | **737,858,641 bytes** across 23 proofs | [Download proofs, statements and claims](https://github.com/AbdelStark/hallmark/releases/download/circle-reference-2026-10-28/llm-proofs.tar.gz) |
| C1 nine classifier proofs | **24.061 s** final STWO calls; **50.028 s** complete prover processes | [Every stage and per-proof record on M4 Max](docs/REFERENCE-RUN.md#c1-default-classifier-workflow) |
| C1 classifier verification and size | **0.807 s** in nine fresh verifier processes; **18,063,779 proof bytes** | [Actual proofs, caller inputs and logs](https://github.com/AbdelStark/hallmark/releases/download/circle-reference-2026-10-28/reference-records.tar.gz) |
| C1 complete controller | **302.96 s**, including fresh training, builds, proofs and checks | Excludes uv bootstrap; one instrumented observation |

L1 and C1 are separate component runs on different machines, not one measured
end-to-end workflow, and one run is not a distribution. The
[performance guide](docs/PERFORMANCE.md) explains every timer boundary, and the
[evidence map](docs/research/index.md) links the raw JSON, controls and missing
claims.

## Published classifiers {#two-trained-classifiers-published}

| Model | Architecture | Card, weights and provenance |
|---|---|---|
| Byte MLP | 1,033 parameters; byte counts and four hidden ReLU units | [Hugging Face ↗](https://huggingface.co/abdelstark/hallmark-byte-mlp) |
| Contextual byte CNN | 4,161 parameters; causal convolution and masked max pooling | [Hugging Face ↗](https://huggingface.co/abdelstark/hallmark-contextual-byte-cnn) |

Both are trained from scratch on synthetic fixtures. Dedicated **STWO Circle
STARK** circuits prove decisions from their integer exports.
[Download a pinned model](docs/MODELS.md), read its model card, or
[train and prove it yourself](docs/DEMO.md). These are research classifiers,
not operational safety filters.
