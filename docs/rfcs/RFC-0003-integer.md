# RFC-0003: Complete inputs and exact integer classifiers

- Status: Draft
- Authors: @AbdelStark (owner; engineering draft for review)
- Created: 2026-10-20
- Target milestone: v0.3

## Summary

Treat each exported integer program as the classifier. Prove complete input coverage and strict threshold comparison for one rule, one byte-feature MLP and one compact encoder.

## Motivation

[PRD G2 and verdict agreement](../../research/source/product-requirements.txt) cannot be met by a float reference that differs from the circuit. The [baseline](../SPEC.md#5-executable-integer-classifier) establishes the simpler integer floor, not an encoder implementation.

## Goals

- Exact agreement among native execution, witness computation and independent arithmetic.
- No omitted tail, padding-dependent verdict or unproved feature extractor.
- Versioned numerical semantics and complete tokenizer provenance.

## Non-Goals

- Hidden weights, activation probes from an unproved model, learned input truncation or a new proving system.

## Proposed Design

W04 implements the input/classifier/arithmetic contracts and parameter-bound
static checks in [decision 0006](../decisions/0006-classifier-contracts.md).
W11 implements the bounded native MLP in
[decision 0014](../decisions/0014-integer-mlp-runtime.md), including its exact
export and numerical profile. Rule/encoder execution, witness generation and
backend qualification remain separate work.

`prepare_input` consumes only the prompt in v1, preserving bytes. The byte programs use all UTF-8 bytes; the encoder uses a pinned local tokenizer implementation/files with no remote code. Tokenization is independent in B1. Special prefix/suffix tokens are fixed by a versioned tokenizer recipe. `InputProfile` fixes `prefix_tokens:List[U64,0..8]` and `suffix_tokens:List[U64,0..8]`. `chunk_size` includes these tokens; content capacity must be positive.

Partition all content units contiguously at content capacity, add the fixed prefix/suffix per chunk, right-pad to static size and create masks. Empty input creates one empty-content chunk. Masked padding contributes nothing to pooling, attention or max. `unit_count` counts original content; `chunk_count=max(1,ceil(unit_count/capacity))`. The proof recomputes the salted input digest from the concatenated content and enforces every chunk's index, mask and bounds; checking a subset is invalid.

Rule: an enrolled finite list of nonempty byte patterns, total pattern bytes ≤4096, matched anywhere in the complete prompt with literal case-sensitive semantics. Score is 1 on any match and 0 otherwise, threshold is 1. The program must carry suffix state across chunk boundaries. This is a rubric subset, not a general injection detector.

MLP: byte counts per chunk, one hidden affine/ReLU layer with width ≤64, one scalar output; int8 weights, int32 bias and accumulated outputs. No external embeddings. All weight/bias/shape files are in the program manifest. Use mathematical signed sums and prove admitted worst-case bounds before execution. Reject overflow instead of wrapping or clipping.

Encoder: one frozen, static-shape compact graph selected by W18 qualification. The export includes `ArithmeticProfile={tensors:List[TensorSpec], nodes:List[NodeSpec], output:Id}`. `TensorSpec={name:Id, shape:List[U64,1..4], signed_bits:U64 in 2..32, fractional_bits:U64 in 0..30, minimum:I32, maximum:I32}`. `NodeSpec={id:Id, op:Id, inputs:List[Id], output:Id, parameters:FileRef}`. Nodes form a topologically ordered DAG, with one producer per tensor and checked shapes/ranges.

Allowed operations are gather, affine, add, multiply, reshape, transpose, masked reduction, ReLU and bounded integer lookup. Attention/normalization/nonlinearities must lower to these operations with exact tables and reciprocal/rounding rules in hashed parameter files; no opaque float op is allowed. Signed rescaling uses nearest ties-to-even on the exact rational value, with no saturation. Every lookup constrains its index and returned table value; masks are boolean. An unsupported graph is rejected, not approximated during verification. The qualification report states every approximation relative to the float parent.

All three programs aggregate `score=max(chunk_scores)` and `pass=(score<threshold)`; rule streaming state is included in its complete-input program. Encoder score is int32 unsafe-minus-safe logit difference. Threshold equality blocks. Do not use softmax for the final comparison. Program/profile changes create new manifests.

## Alternatives Considered

Float tolerances would hide threshold flips. A probe on served-model activations adds hardware-dependent input authenticity. Discarding long inputs is cheaper but violates full coverage; bounded rejection is allowed, truncation is not.

## Drawbacks

Max pooling misses cross-chunk semantic relationships. Static integer lowering may reduce quality or reject available encoders. B1 tokenizer independence takes additional implementation work.

## Migration / Rollout

Keep the existing byte-linear artifact and scale contract intact. Add new versioned program/profile artifacts and matching native/proof vectors; only qualified exports enter the registry.

## Testing Strategy

Test empty inputs, exact capacity, capacity+1, multibyte boundaries, patterns spanning chunks, late positive tails, padding changes, maximum signed ranges and ties-to-even for negative halfway values. Compare full intermediate integer tensors on boundary vectors and final decisions across the complete frozen evaluation corpus. Invalid node shapes, unconstrained lookup values and overflow must reject.

## Open Questions

- OPEN QUESTION INTEGER-GRAPH — @AbdelStark, resolution checkpoint 2026-11-09: select the exact encoder graph/tokenizer after RFC-0005 qualification and data admission. W12/W16/W21 cannot claim encoder completion before its numerical profile is reviewed.

## References

- [Data model](../spec/03-data-model.md#v1-types), [ML plan](../ML-PLAN.md#training-distillation-and-quantization), [proof RFC](RFC-0005-proofs.md).
