# FlashProve proofs

[FlashProve](https://github.com/anthropics/FlashProve) is Anthropic's research
prototype for zero-knowledge proofs of LLM inference
([announcement](https://www.anthropic.com/research/provable-inference)). A provider
commits to a Mixture-of-Experts model's weights once. For each request, its GPU
then proves that every checked token was the committed model's greedy choice.
Anyone can check the proof on a CPU in seconds, without the weights.

Hallmark drives FlashProve as a pinned external backend: upstream commit
`9e2bdd8` (v0.16.0, Apache-2.0), unchanged, called through command-line adapters
([decision 0092](decisions/0092-flashprove-backend.md)). FlashProve proves MoE
models only, so Hallmark's dense TinyLlama response stays on
[SASH](LLM-PROOF.md).

| Command | What it does | Needs |
|---|---|---|
| `make verify-flashprove` | Builds `cp_verify`, checks the two stored upstream proofs, runs 99 rejection cases | Mac or Linux, a C++17 compiler, about 5 GB RAM, no GPU, no spend |
| `make e2e-flashprove GPU_CREDIT_BALANCE_USD=…` | Builds the prover, commits to and proves the small synthetic kit on one HF H200, rechecks the proof here | `HF_TOKEN`, prepaid HF credit; worst case USD 3.27 |

## Verify stored proofs

```sh
make verify-flashprove
```

The command downloads the pinned 158 MB archive and checks its SHA-256 and size.
It then builds `cp_verify` and checks two proofs that ship with upstream:

- `accepted-proof`: a small model, 3 checked tokens and the next token;
- `full-size`: a model of Llama 4 Maverick's shape, 1,001 tokens in one proof.

Both use synthetic weights. Every expected value comes from Hallmark's
[pin file](../research/probes/flashprove/source.json), not from the proof
directory: commitment ID, range and next token. Then upstream's three tables of
altered copies run, and each of the 99 copies must be rejected by the check
the table names.

On Linux the build is upstream `verifier/build.sh`. On macOS, Hallmark compiles
the same source with Apple clang, using the same macros and source digest, and
labels the result `apple-clang`. Results go to a fresh `runs/flashprove-verify-*`
directory.

## Prove on a GPU

```sh
make e2e-flashprove GPU_CREDIT_BALANCE_USD=31
```

Give the balance you checked yourself. The command refuses to start if the
balance is below the worst case, or if another HF job is active. It runs the
free local suite first, then two jobs, one attempt each:

1. **Build** (cpu-xl, at most 3,600 s): upstream `verifier/build.sh` and
   `prover/build.sh` with CUDA 13.2.2 (nvcc V13.2.86), as an ordinary account.
2. **Prove** (H200, at most 900 s): upstream `run_target_example.sh
   target_small_f2_roomy`. It commits to synthetic weights, proves one 64-token
   request (15 prompt tokens, 48 of the model's own, plus the next token) and
   runs Linux `cp_verify`.

Only public files come back. The secret key directory stays on the worker.
Hallmark then checks that the configuration and request match the pinned kit
byte for byte. It takes the commitment ID that `cp_commit` printed, verifies the
proof on this machine and requires six altered copies to be rejected.

## What a pass means

A pass means `cp_verify` accepted a proof of this statement: under the integer
model committed under this ID, each checked token is the greedy choice. Here the
models are synthetic. A pass says nothing about a served model, about Llama 4
Maverick or about weight hiding. The `bits=` figures are the verifier's own
accounting, not a security level. Upstream's Lean soundness theorem covers the
Lean verifier, not `cp_verify` and not the CUDA prover.
