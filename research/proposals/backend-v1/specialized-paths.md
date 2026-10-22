# Specialized classifier verification paths

Source inspection, 2026-10-22; no comparative backend benchmark or security audit.
The owner excludes a general-purpose zkVM. Choose against a complete classifier
relation, including preprocessing, all nonlinear operators and request binding.

| Path | Use in Hallmark | Gate before adoption |
|---|---|---|
| Dedicated Gnark circuit | Small exact byte/MLP correctness baseline; specialize fixed weights into indexed lookups and sums | Trained export equality, real proofs under enrolled keys, full cost, setup and privacy review |
| CommitLLM-like audit | Candidate when the verifier may receive the opened trace; fixed-commitment linear checks plus complete nonlinear checking | Cover every operator, use fresh verifier-secret randomness after commitment, compare total audit cost with native rerun; no ZK/transferable-proof claim |
| SASH-style STARK/GKR | Candidate for larger tensor/attention relations with explicit producer/consumer bindings | Complete encoder operator port, independent statement enrollment and serialized verification, quality/numerical agreement, full costs and separate privacy qualification |

## Source findings

[CommitLLM](https://github.com/lambdaclass/CommitLLM/tree/25541e83347655e44ad6e84eb901e1e7ae392a66),
MIT, uses commit-and-audit with verifier-secret Freivalds checks. Its
[README](https://github.com/lambdaclass/CommitLLM/blob/25541e83347655e44ad6e84eb901e1e7ae392a66/README.md)
explicitly excludes arbitrary-position attention-output verification on the kept
stock serving path. A consistent fabricated post-attention state remains a
reported residual hole. Reusing the checking idea is reasonable; importing that
incomplete relation as a complete encoder verifier is not.

[SASH's prover source](https://github.com/sg-ai-safety-hub/zk-inference-prover/tree/eb95bfa887299d1637550228d42086c27cbb2b3b),
Apache-2.0, specializes quantized transformer segments and their boundary links.
Its [statement](https://github.com/sg-ai-safety-hub/zk-inference-prover/blob/eb95bfa887299d1637550228d42086c27cbb2b3b/docs/statement.md)
tracks producer/consumer binding explicitly, including attention, quantization,
weights, embeddings and output selection. It identifies a biased Q/K/V projection
gap relevant to an encoder port. A valid partial segment is not a whole classifier.

Its [synthetic regression roster](https://github.com/sg-ai-safety-hub/zk-inference-prover/blob/eb95bfa887299d1637550228d42086c27cbb2b3b/prover/tests/synthetic_digest.rs)
also distinguishes the README's small shape (attention edges 3/5 unbound) from
the aligned 128-wide shape with every layer edge bound. A comparison must use the
complete intended relation and check that roster, not merely an `accepts` field.
The [CLI source](https://github.com/sg-ai-safety-hub/zk-inference-prover/blob/eb95bfa887299d1637550228d42086c27cbb2b3b/prover/src/cli.rs)
can retain statement, claims and proof bytes; the verification API consumes those
bytes. Its [build documentation](https://github.com/sg-ai-safety-hub/zk-inference-prover/blob/eb95bfa887299d1637550228d42086c27cbb2b3b/README.md)
requires Linux/CUDA linkage even for the SIMD build and does not support linking
on the Mac as shipped. HF/Modal/Vast can provide Linux compute without GCP;
the exact image/toolchain/device and price still belong in each run plan.

[Attestable's alpha report](https://attestable.com/blog/proving-llms-scale)
describes specialized inference proofs with integer matrix multiplications and
floating-point nonlinear operations. It is a relevant architectural precedent.
The post is a vendor result, not a reproducible Hallmark adapter or an independent
validation of its privacy/performance claims. Do not copy its timing into our
cost estimates.

## Next implementation

Close the trained-MLP proof connection under [decision 0058](../../../docs/decisions/0058-specialized-trained-classifier-path.md)
first. Keep the existing fixed rule/encoder proofs as regression baselines. Then
quality-screen a compact contextual classifier and require one complete
operator/binding port before scaling a tensor prover. A smaller model that fails
the task is not a successful prover optimization. Compare native rerun,
commit-and-audit and proof costs only on identical admitted models and inputs;
keep their disclosure and trust properties explicit.
