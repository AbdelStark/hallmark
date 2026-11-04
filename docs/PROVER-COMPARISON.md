# SASH and FlashProve compared

Hallmark drives two external LLM provers, each pinned and unchanged at the
prover: [SASH](LLM-PROOF.md), a Circle STARK prover, and
[FlashProve](FLASHPROVE.md), Anthropic's hash-based zkSNARK. They prove different
statements about different models, so this page compares what each one proves,
then what each one cost on Hallmark's own runs. No row is a like-for-like speed
claim. Every number comes from the
[comparison record](../research/evidence/prover-comparison-2026-11-04.json),
which gives the evidence file and JSON path of each one.

## What each one proves

| | SASH | FlashProve |
|---|---|---|
| Model class | Dense transformers | Mixture-of-Experts transformers only |
| Hallmark's case | TinyLlama-1.1B-Chat, real pretrained weights, `y-attnout-w12` quantization | Upstream's synthetic kits: a small model (8 layers, 4 experts, 512-token vocabulary) and a Llama 4 Maverick-shaped model |
| Statement | Greedy decoding of an 8-token answer through EOS, in one 32-position block | Each checked token, and the next token, is the committed integer model's greedy choice |
| Proof shape | 23 segment proofs (22 layers plus head), 22 residual links, 7 generated-input links | One proof per request, up to 1,024 tokens |
| Weights | Public; the caller enrolls model, shape and calibration roots | Committed and masked, except for a declared list. Hallmark does not test the hiding |
| Soundness basis | SASH's STARK implementation, not independently reviewed | Protocol proved in Lean (about 124 bits per hash query) for the Lean verifier; `cp_verify` and the CUDA prover are tested, not proved |
| Mac verifier | Patched native build, with the caller's shape roots compiled in | Unchanged upstream source, built with Apple clang |

Neither backend covers the other's model class in Hallmark. TinyLlama is dense,
so it stays on SASH. Proving Maverick itself would need Meta's gated weights,
which the run authority excludes.

## Measured on Hallmark's runs

SASH is run L1 ([GPU benchmark](GPU-BENCHMARK.md#generated-constraint-result)),
recorded 2026-10-26. FlashProve is the H200 run in
[decision 0093](decisions/0093-flashprove-backend.md), recorded 2026-11-03. Both
GPU runs used one HF H200 with driver 580.178.04. The Mac rows come from an
Apple M4 Max with 16 CPUs and 48 GiB. SASH was measured there on 2026-10-26.
FlashProve was re-timed on 2026-11-04: five calls per proof with `cp_verify`'s
default threading, timed with `/usr/bin/time -l`.

| Measurement | SASH, TinyLlama | FlashProve, small kit | FlashProve, stored full size |
|---|---:|---:|---:|
| Checked tokens | 8 | 48 | 1,000 |
| H200 prover time | 53.94 s proving sessions; 155.89 s complete segment commands | 22.28 s for the whole example: commit, prove and Linux verify | Not run by Hallmark |
| Prover memory | 8.07 GB host RSS; 67.67 GiB GPU | 0.90 GB, largest process; GPU not recorded | — |
| Proof bytes | 737,858,641 (JSON; 355,320,899 gzipped) | 4,145,980 | 18,779,540 |
| Proof bytes per checked token | 92.2 MB | 86.4 KB | 18.8 KB |
| Mac verify, one proof | 3.53 s | 0.63 s, median of 5 | 7.88 s, median of 5 |
| Mac verifier peak memory | 0.52 GB, sampled process group over the whole suite | 0.21 GB | 4.23 GB |
| Linux CPU verify | 77.61 s, 8 vCPUs, roots derived at run time | Not timed separately | — |
| Prover build | 1,815.94 s, generated CUDA kernels | 1,520.51 s on cpu-xl | — |
| Prove job, computed bound | USD 1.75; the job also ran the SIMD pair | USD 0.17 | — |

The bounds are computed upper bounds, not invoices. The SASH Linux verifier
derives the shape roots at run time; the Mac verifier has them compiled in,
which is most of the gap between 77.61 s and 3.53 s.

### What upstream reports for Maverick

Hallmark has not reproduced these figures. Upstream measured Llama 4 Maverick
(a public 4-bit conversion) on one H100 80 GB with 24 CPUs and 1,024-token
prompts, n = 3 ([performance guide](https://github.com/anthropics/FlashProve/blob/9e2bdd8ff5bf9c62f18263d7dac189b0400b260c/guide/performance.md)):

| Upstream figure | Value |
|---|---:|
| Seconds per request, 1 per batch | 58.80 |
| Seconds per request, 24 per batch | 9.21 |
| Prefill tokens per second, 24 per batch | 111.23 |
| Committing, once per commitment | about 39 minutes |
| Mean proof size | 18.78 MB |
| `cp_verify` on one thread | about 21 s |

## What the numbers show

- **Proof size.** FlashProve's Maverick-shaped proof covers 125 times as many
  checked tokens as SASH's TinyLlama bundle, at 1/39 of the bytes. Per checked
  token that is about 4,900 times smaller. Part of the gap is encoding: SASH
  writes JSON, which gzip halves. The rest has not been broken down.
- **Verification.** Both run in seconds on a laptop. FlashProve's largest proof
  needs 4.23 GB of memory. SASH's 3.53 s depends on the caller's compiled shape
  roots; without them, the Linux path takes 77.61 s.
- **Proving.** Hallmark's runs give no fair prover ratio. SASH proved a real
  1.1B dense model over 32 positions. FlashProve proved a synthetic 8-layer MoE
  over 64 positions, and its 22.28 s also includes committing and verifying.
  Upstream's 58.80 s per Maverick request at batch 1 comes from a different
  model, GPU and timer boundary.
- **Trust.** FlashProve's protocol soundness has a Lean proof. Neither
  backend's deployed C++ or Rust verifier is proved or independently reviewed.

## Reproduce

```sh
make compare-provers FLASHPROVE_RUN=runs/flashprove-gpu-...
```

This needs a passed `make e2e-flashprove` run directory, which holds the Mac
`cp_verify`, the stored upstream examples and the fresh H200 proof. The command
re-times `cp_verify` on the three proofs, requires `YES` from every call, and
copies the recorded SASH and FlashProve figures together with their source
pointers. It writes a fresh `runs/prover-comparison-*` directory, and it starts
no paid compute.
