---
title: Circle STARK verifiable inference, explained
description: Run the TinyLlama and classifier proof workflows, learn what their verifiers check, and inspect the benchmark evidence.
template: home.html
hide:
  - navigation
  - toc
---

<div class="hm-route">
<span class="hm-route-index">01</span>
<div><h3>Learn</h3></div>
<div><p>Learn what a verifier checks and how the caller chooses the model and inputs it expects. No cryptography background required.</p><a href="docs/learn/">Read the learning guide →</a></div>
</div>
<div class="hm-route">
<span class="hm-route-index">02</span>
<div><h3>Run</h3></div>
<div><p>Prove classifier decisions on a Mac, prove a TinyLlama response with HF Jobs, or benchmark the prover on an H200.</p><a href="docs/START/">Choose a workflow →</a></div>
</div>
<div class="hm-route">
<span class="hm-route-index">03</span>
<div><h3>Check</h3></div>
<div><p>Check the proof statements, model and input hashes, raw measurements, and failed runs behind each result.</p><a href="docs/research/">Find the evidence →</a></div>
</div>

## The TinyLlama case {#a-real-model-a-precise-statement}

```text
Prompt:   Name the capital of France in one short sentence.
Response: The capital of France is Paris.
```

Hallmark proves this response from a pinned, quantized **TinyLlama-1.1B**.
SASH's Circle STARK prover covers greedy generation through EOS:
**22 transformer layers, the final normalization/output head, 23 proof segments,
22 residual links and seven generated-input links**.

The [proof statement](docs/LLM-PROOF.md#the-statement) lists the model and input
identities the caller must choose, and the checks the verifier performs. The
proof covers the disclosed quantized model; equivalence to the original
floating-point model, hardware provenance and witness hiding are unproven.

<div class="hm-statement">
<p class="hm-eyebrow">What verification establishes</p>
<p>A valid classifier proof can return “block” for a harmless prompt. The proof checks the computation; evaluating the policy and authenticating its inputs require separate evidence.</p>
</div>

## Published classifiers {#two-trained-classifiers-published}

| Model | Architecture | Card, weights and provenance |
|---|---|---|
| Byte MLP | 1,033 parameters; byte counts and four hidden ReLU units | [Hugging Face ↗](https://huggingface.co/abdelstark/hallmark-byte-mlp) |
| Contextual byte CNN | 4,161 parameters; causal convolution and masked max pooling | [Hugging Face ↗](https://huggingface.co/abdelstark/hallmark-contextual-byte-cnn) |

Both are trained from scratch on synthetic fixtures. Dedicated **STWO Circle
STARK** circuits prove decisions from their integer exports by default. Gnark
remains an explicit comparison backend.
[Download a pinned model](docs/MODELS.md), inspect its model card, or
[train and prove it yourself](docs/DEMO.md). These are research classifiers,
not operational safety filters.

## Recorded measurements {#measurements-you-can-follow-back-to-evidence}

| Observation | Recorded result | Read it in context |
|---|---|---|
| Same-H200 CUDA proving | **53.94 s**, versus 547.75 s SIMD: **10.15×** | [Generated constraints, zero fallback](docs/GPU-BENCHMARK.md#generated-constraint-result) |
| Complete segment commands | **155.89 s**, versus 679.49 s SIMD: **4.36×** | [What is included](docs/GPU-BENCHMARK.md#generated-constraint-result) |
| Native Mac verification | **3.40–3.53 s** per honest check, after compilation | [Compiled enrollment boundary](docs/LLM-PROOF.md#verify-retained-proofs-on-your-mac) |
| Circle classifier workflow | **4.98 min warm median**, nine proofs | [Matched CPU study; 19.96 GB maximum sampled RSS](docs/CLASSIFIER-BENCHMARK.md) |
| LLM serialized proofs | **738 MB** across all 23 files | [Artifact and workflow costs](docs/LLM-PROOF.md#measured-results) |

One fixed H200 pair is not a performance distribution. Witness/interaction
generation stays on CPU. Verification timings use different preprocessing;
classifier and LLM workloads are not a matched backend comparison.
[Read the evidence map](docs/research/index.md) for raw JSON, controls and missing claims.

## Research status {#research-with-an-inspectable-trail}

The [fixed-case integrity MVP](docs/MVP.md) is complete. General prompts/models,
independent backend qualification, hiding and hardware provenance remain outside
that scope. The [research state](research/STATE.md) and [ledger](research/LEDGER.md)
preserve failures and exact identities.

[Architecture](docs/ARCHITECTURE.md) · [Contribute](CONTRIBUTING.md) ·
[Security](SECURITY.md) · [MIT licence](LICENSE.md) ·
[Site build manifest](https://abdelstark.github.io/hallmark/assets/build.json)
