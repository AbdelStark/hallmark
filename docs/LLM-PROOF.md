# A proved TinyLlama response

Hallmark has verified a complete short response from a **pretrained, quantized
TinyLlama-1.1B-Chat-v1.0** using SASH's specialized Circle STARK prover. It uses
neither a general-purpose zkVM nor hardware attestation.

```text
Prompt:   Name the capital of France in one short sentence.
Response: The capital of France is Paris.
```

The answer has eight tokens, including EOS. All 23 proof segments and all 22
connections between layers verify against roots enrolled before proving.
[Raw results and hashes](../research/evidence/llm-response-composition-2026-10-23.json)
retain the failed first composition as well as the corrected result.

**This is a research result, not yet a one-command LLM demo.** `make e2e` runs the
[synthetic classifier workflow](DEMO.md). The LLM runs and large proof artifacts
remain local; packaging a reproducible LLM command is the next implementation task.
A fresh worker containing no weights or witness accepted the complete response
twice and rejected all 14 changed claims.

## The statement

For the enrolled quantized model and exact input token sequence, the answer tokens
are the greedy continuation computed by the pinned SASH relation. The proof
covers the model's embedding, 22 transformer layers, final normalization and
output projection/argmax. The caller pins the model, arithmetic parameters,
calibration, shapes and exact prompt/answer IDs.

The pinned chat template turns the prompt into **25 tokens**. A causal block of
32 positions contains those tokens plus the first seven answer tokens. Output
positions 24–31 produce the eight answer tokens, including EOS. Checking that the
first seven outputs equal the appended inputs closes the generation loop; the
caller separately checks the final EOS output. This is why the grid reports
seven generated input positions while proving eight output tokens.

```text
25 prompt IDs + first 7 answer IDs
  → embedding → layers 0…21 → final norm → output head
  → 8 expected answer IDs at positions 24…31, ending in EOS
```

This is the disclosed `y-attnout-w12` integer/quantized relation. It is not a proof
that every floating-point Transformers execution returns the same text. The
original fixed-length generation continued for 16 steps; this experiment proves
the complete first answer through EOS and discloses that selection. It does not
claim stochastic sampling or a held-out language-quality evaluation.

## What the caller checks

| Binding | Check |
|---|---|
| Text and tokens | Apply the pinned tokenizer/chat template locally; compare exact prompt and answer IDs |
| Model and arithmetic | Supply previously enrolled model/preprocessed roots, calibration and shape digests |
| Coverage | Require exactly 22 transformer segments and one final-norm head, with 32 positions each |
| Generation | Check all prompt IDs, seven generated input links and all eight answer IDs |
| Layer connections | Verify all 22 residual commitment links |
| Proofs | Run the real SASH verifier on every segment; reject any failure |

The [caller guard](../research/probes/sash/check_response.py) checks the statement,
including a digest of the complete parameter object. It rejects the delayed-value
profile and requires the head's final normalization. **Passing this Python guard
is not proof verification**: SASH's `boundary-grid --verify` must also accept the
entire bundle. The caller's expected roots must come from its own enrollment;
roots supplied only by the prover are insufficient.

The tokenizer, checkpoint-to-quantized-model preparation and enrollment are host
software responsibilities. The verifier implementation is the same pinned SASH
implementation used by the prover; a fresh process is not an independently
developed verifier or security audit. No trace blinding or witness-hiding claim
is made.

## Measured result

| Measure | Recorded result |
|---|---:|
| Accepted proof segments | 23 / 23 |
| Residual links | 22 / 22 |
| Enrolled shape roots | 23 / 23 |
| Answer tokens, including EOS | 8 |
| Serialized proofs | 737,858,641 bytes |
| Proofs plus statements and claims | 761,015,496 bytes |
| Fresh proof-only verification, two processes | 83.99 / 79.16 seconds |
| Changed claims rejected | 14 / 14 |
| Peak verifier process RSS | 14.35 GB |

Verification used an HF CPU Upgrade worker with 8 vCPUs, 32 GB RAM and four Rayon
threads. The 22 transformer proofs took 307.00 seconds of summed prove-stage time
on a different, larger CPU worker; the corrected head took 21.90 seconds on the
smaller worker. These are separate measurements, not one end-to-end wall-time
benchmark. The original proving run reached 113.44 GB peak RSS. No GPU was used
for these proofs; the build still required CUDA libraries for linking.

The caller guard rejected 11 mutations: changed prompt, answer, model root,
calibration, missing layer, wrong coordinate, final output, token alias, Boolean
token, open-scale profile and weaker security parameters. The cryptographic
verifier rejected altered proof commitments, a residual boundary and an output
claim. The original proof files were rehashed afterward and remained unchanged.

## Failures that changed the implementation

1. An exact integer witness accumulator was rounded through float32. A
   [one-line Python fix](../research/probes/sash/exact-gemm.patch) preserves it;
   regression tests compare the helper with an int64 oracle.
2. The delayed-value profile left an activation-scale equality unchecked. Its
   proof cannot qualify for complete inference, even when its broad binding
   summary says all edges are bound. The experiment uses the existing non-delayed
   profile; the Rust prover and verifier remain unmodified.
3. Combining `--head` and `--residual-stream` selected the wrong proof family for
   the output head. All individual proofs passed, but the last layer connection
   failed. Extracting only the final-norm head repaired that connection without
   changing the other 22 proofs. [Decision 0068](decisions/0068-prove-the-output-head-final-norm.md).

The result establishes one bounded computation under the enrolled relation. It
does not establish model quality, safety-policy quality, authentic capture of a
real interaction, hardware provenance, hiding or independently reviewed
cryptographic security. See the [source review](../research/real-llm-proof-plan.md)
for the pinned model/source revisions and remaining qualification work.
