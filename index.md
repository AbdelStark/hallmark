---
title: Verifiable inference, explained
description: Reproduce a complete TinyLlama inference proof, inspect exact classifier decisions, and learn the cryptographic boundaries.
template: home.html
hide:
  - navigation
  - toc
---

<div class="hm-route">
<span class="hm-route-index">01</span>
<div><h3>Understand.</h3></div>
<div><p>Start with a concrete claim. Follow the roles of model, witness, proof and caller enrollment—without assuming a cryptography background.</p><a href="docs/learn/">Take the learning path →</a></div>
</div>
<div class="hm-route">
<span class="hm-route-index">02</span>
<div><h3>Reproduce.</h3></div>
<div><p>Run local classifier proofs, prove a fixed pretrained LLM response, or measure the prover on an H200. Every workflow states its costs and outputs.</p><a href="docs/START/">Choose a workflow →</a></div>
</div>
<div class="hm-route">
<span class="hm-route-index">03</span>
<div><h3>Inspect.</h3></div>
<div><p>Read the exact statements, frozen inputs, raw measurements and retained failures. Distinguish completed integrity evidence from future qualification.</p><a href="docs/research/">Explore the evidence →</a></div>
</div>

## A real model, a precise statement

```text
Prompt:   Name the capital of France in one short sentence.
Response: The capital of France is Paris.
```

Hallmark uses a pinned, disclosed quantized **TinyLlama-1.1B**. SASH's specialized
Circle STARK prover covers the complete short greedy response through EOS:
**22 transformer layers, the final normalization/output head, 23 proof segments,
22 residual links and seven generated-input links**.

The [proof statement](docs/LLM-PROOF.md#the-statement) explains what the caller
enrolls and what the verifier checks. The quantized relation is not a claim of
equivalence to the original floating-point model. Neither hardware provenance
nor witness hiding is claimed.

<div class="hm-statement">
<p class="hm-eyebrow">The central distinction</p>
<p>A proof establishes an enrolled computation. It does not establish that a classifier's policy is good, or that its inputs came from an authentic source.</p>
</div>

## Two trained classifiers, published

| Model | Architecture | Card, weights and provenance |
|---|---|---|
| Byte MLP | 1,033 parameters; byte counts and four hidden ReLU units | [Hugging Face ↗](https://huggingface.co/abdelstark/hallmark-byte-mlp) |
| Contextual byte CNN | 4,161 parameters; causal convolution and masked max pooling | [Hugging Face ↗](https://huggingface.co/abdelstark/hallmark-contextual-byte-cnn) |

Both are trained from scratch on synthetic fixtures. Their exact integer
exports are used in dedicated gnark/Groth16 classifier circuits.
[Download a pinned model](docs/MODELS.md), inspect its model card, or
[train and prove it yourself](docs/DEMO.md). These are research classifiers,
not operational safety filters.

## Measurements you can follow back to evidence

| Observation | Recorded result | Read it in context |
|---|---|---|
| Same-H200 CUDA proving | **53.94 s**, versus 547.75 s SIMD: **10.15×** | [Generated constraints, zero fallback](docs/GPU-BENCHMARK.md#generated-constraint-result) |
| Complete segment commands | **155.89 s**, versus 679.49 s SIMD: **4.36×** | [What is included](docs/GPU-BENCHMARK.md#generated-constraint-result) |
| Native Mac verification | **3.40–3.53 s** per honest check, after compilation | [Compiled enrollment boundary](docs/LLM-PROOF.md#verify-retained-proofs-on-your-mac) |
| LLM serialized proofs | **738 MB** across all 23 files | [Artifact and workflow costs](docs/LLM-PROOF.md#measured-results) |

One fixed H200 pair is not a performance distribution. Witness/interaction
generation stays on CPU. Verification timings use different preprocessing;
classifier and LLM workloads are not a matched backend comparison.
[Read the evidence map](docs/research/index.md) for raw JSON, controls and missing claims.

## Research with an inspectable trail

The [fixed-case integrity MVP](docs/MVP.md) is complete. General prompts/models,
independent backend qualification, hiding and hardware provenance remain outside
that scope. The [research state](research/STATE.md) and [ledger](research/LEDGER.md)
preserve failures and exact identities.

[Architecture](docs/ARCHITECTURE.md) · [Contribute](CONTRIBUTING.md) ·
[Security](SECURITY.md) · [MIT licence](LICENSE.md) ·
[Site build manifest](https://abdelstark.github.io/hallmark/assets/build.json)
