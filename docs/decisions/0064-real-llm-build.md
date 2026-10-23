# 0064: Qualify a real LLM response proof

2026-10-23. Research protocol under the owner's standing implementation and
compute approval. Relates to #19. No backend adoption or change to the existing
classifier proof statements.

## Target

The owner requested a short generated response from a real pretrained LLM,
accepted a disclosed quantized model, and allowed minutes to a few hours of
proving with fast verification. Witness privacy is optional. The acceptance
gate remains a complete response proof, including the prompt computation,
all layers, output selection and token continuity; a synthetic layer or a
one-token milestone does not complete it.

Assess SASH at `eb95bfa887299d1637550228d42086c27cbb2b3b` first. Its root and
vendored Stwo licences are Apache-2.0. The [source review](../../research/real-llm-proof-plan.md)
records the exact relation and alternatives. TinyLlama-1.1B-Chat-v1.0 at
`fe8a4ea1ffedaf415f4da2f062534de366a451e6` is the first model candidate:
public, ungated, Apache-2.0, and an ordinary Llama architecture. Compatibility
and quantized response usefulness are unmeasured at protocol freeze.

## Ordered gates

1. Build the unmodified pinned source with its pinned Rust toolchain on the
   Mac. Reproduce the upstream synthetic digest before changing any build code.
   Also require the aligned synthetic shape, whose layer bindings are complete.
   The smaller README example explicitly leaves two edges unbound.
2. Install the upstream locked witness environment separately from Hallmark.
   Run its model-free primitive and extraction checks. Fetch only the exact
   reviewed model/config/tokenizer files; retain their hashes and never execute
   remote model code. Freeze calibration and demo prompts before inference.
3. Generate a short answer using the declared quantized arithmetic. Compare
   against the original model, retaining every mismatch and failure. This is an
   engineering screen, not a language-model benchmark or safety evaluation.
4. Extract and prove the complete prompt and 8–16 generated tokens. Enroll model
   roots, calibration, tokenizer, arithmetic and expected coverage outside the
   prover's output. Verify in a fresh process without weights or witness traces.
5. Reject changed prompt, answer, model/calibration, omitted/reordered segments,
   KV substitutions, argmax ties that violate the decoding rule, and proof-byte
   changes. Record preparation, witness, proof and verification costs separately.

Keep this work sequential under #19. Revisit dependent classifier and verifier
issues after the whole-graph gate. Existing hardware/release dependencies remain;
they do not block this integrity-only experiment.

## First build envelope

Mac arm64, four build/prover threads, one compute worker, 1,800 seconds per job,
24 GiB sampled process-group RSS stop, 16 GiB additional local disk, zero cloud
spend. Preserve the compiler output, command, lockfile/source hashes, measured
costs and failed directory. A timeout or compiler failure is a failed build,
not a reason to weaken arithmetic or disable a binding.

Upstream documents macOS type checking but no linking. If the actual build
confirms that limitation, use the already approved HF/Modal/Vast compute under
a separately frozen job manifest with a fresh balance/price check, finite
timeout, no automatic retries and an initial total campaign ceiling of $5.
The source currently needs CUDA 12.9 libraries even for the Linux CPU backend.
No new top-up, scheduler, private upload, collaborator or hardware purchase is
part of this protocol.

The prior classifier results and evaluation contracts remain unchanged. This
experiment cannot establish historical inference provenance, zero knowledge,
hardware attestation, production soundness or classifier quality.
