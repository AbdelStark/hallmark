---
hide:
  - toc
---

# Read a proof statement

Before asking whether a proof is fast, write down what it establishes.

Hallmark has two working proof backends and one host composition. Use the
selector to keep the computation, public expectations and exclusions together.

<div data-proof-explorer markdown="1">
<div class="hm-proof-switch" role="group" aria-label="Choose a proof relation">
<button type="button" data-proof-choice="llm" aria-pressed="true">LLM response</button>
<button type="button" data-proof-choice="classifier" aria-pressed="false">Classifier verdict</button>
<button type="button" data-proof-choice="composition" aria-pressed="false">Composition</button>
</div>
<section class="hm-proof-panel" data-proof-panel="llm" markdown="1">

### A complete short LLM response

**Computation:** the enrolled quantized TinyLlama model greedily computes all
eight answer tokens, including EOS, from the expected prompt tokens.

**Caller expectations:** model, shape and calibration roots and the exact
prompt/output token case. Tokenization and detokenization are pinned host checks.

**Cryptographic checks:** all 23 SASH segments, 22 residual links, the output
argmax and seven generated-input/previous-output equalities in one 32-position
input block.

**Outside the claim:** equivalence to unmodified floating-point Transformers
inference, authentic input capture, hardware provenance and witness hiding.

[Exact LLM statement](../LLM-PROOF.md#the-statement)

</section>
<section class="hm-proof-panel" data-proof-panel="classifier" markdown="1">

### An exact classifier verdict

**Computation:** a fixed rule, MLP or CNN computes its verdict over the complete
admitted prompt bytes. Hashing, coverage, integer arithmetic and threshold
comparison belong to the relation.

**Caller expectations:** exact request context, classifier/program identity,
circuit and verification key. The caller reconstructs expected public inputs.

**Cryptographic checks:** dedicated Groth16 equations, checked by separate
py-ecc arithmetic against those inputs.

**Outside the claim:** training history, a useful safety policy or a confidential
input capture mechanism. The combined demo limit is 96 UTF-8 bytes.

[Classifier public fields and caller checks](../PROOFS.md)

</section>
<section class="hm-proof-panel" data-proof-panel="composition" markdown="1">

### Two relations, one opened request

**Computation:** freshly verify the LLM bundle, then bind three classifier
proofs to that same prompt/response context.

**Caller expectations:** the same opened request and independently admitted
LLM/classifier identities. The classifiers inspect the prompt only; the response
is bound into their context, not classified.

**Composition checks:** request equality and verified classifier verdicts joined
with `all-pass` in host code.

**Outside the claim:** recursive aggregation or a proof of the host composition
program itself. A valid joined result may contain a classifier block.

[Exact composed join](../COMPOSED-DEMO.md)

</section>
</div>

## Why 23 segments?

TinyLlama has 22 transformer layers in this case. The final normalization and
output head form the remaining segment. Checking each proof is necessary, but
not sufficient: the outputs and inputs must connect to the same model and token
sequence.

```mermaid
flowchart LR
    P[Expected prompt tokens] --> E[Embedding / first segment]
    E --> L[All 22 transformer layers]
    L --> H[Final normalization + argmax]
    H --> O[Answer tokens through EOS]
    O -. seven generated-input links .-> P
    C[Caller-enrolled roots and expected case] --> V[Verify 23 proofs + links]
    L --> V
    H --> V
```

This is a linked bundle, not a single recursive proof. The zero expected
**inter-block** token links for this single-block case do not remove the seven
**within-block** autoregressive checks.

## Why caller checks matter

A valid proof for the wrong model or request is not the evidence the caller
wanted. The caller must compare against its own expected identities and
reconstruct the public inputs. A prover bundle cannot choose the trust anchor.

The native Mac verifier also uses **compiled enrolled shape roots**, while the
Linux path derives them at runtime. That changes preprocessing and trust;
the faster Mac timing is not a like-for-like backend speedup.

## A verifier's checklist

1. Establish the expected model, parameters, request and accepted proof system.
2. Reject incomplete bundles, changed identities or unsupported modes.
3. Check every cryptographic proof.
4. Check segment/token links and common-request binding.
5. Interpret the verified classifier verdict separately from proof validity.

[Architecture and source ownership](../ARCHITECTURE.md) trace these checks to
the actual adapters. Continue with [two proof systems](proof-systems.md).
