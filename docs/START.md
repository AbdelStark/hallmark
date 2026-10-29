# Choose a workflow

`make e2e` trains and proves classifiers locally. Use `make e2e-llm` to prove
the TinyLlama response, or choose another workflow below.

| I want to… | Command | Where / resources | Success signal |
|---|---|---|---|
| Check software contracts | `make check-conformance` | Linux/macOS; core environment; no account | 156 matched cases, 32 unavailable full-evidence obligations; no proof |
| Run a published classifier | `scripts/predict_published_classifier.py` | Linux/macOS; core for MLP, train extra for CNN | Integer score after checking model hashes; native inference only |
| Train, prove and verify classifiers | `make e2e` | Apple Silicon Mac; 12 GiB free; uv 0.9.18 | Nine Circle proofs, 63 public-input and 18 substitution rejections |
| Prove a complete TinyLlama response | `make e2e-llm` | Mac preparation; 32 GB RAM, 16 GiB free; HF CPU jobs | 23 new segments, two honest verifications, 14 rejected mutations |
| Verify retained LLM proofs locally | `make verify-llm LLM_RUN=…` | Mac; native Rust toolchain; 8 GiB free; no HF credentials | Two honest checks, 36 rejected mutations |
| Measure SIMD/CUDA proving | `make benchmark-llm-gpu …` | Mac controller; HF CPU/H200 jobs; completed caller-owned LLM run | Matched full runs, 69 identical artifacts, fresh CPU/Mac checks |
| Bind LLM and classifier proofs | `make e2e-composed` | Both sets of prerequisites; 32 GiB free | Same-request verified relations and classifier verdicts |

![How Hallmark works: the caller pins roots, programs and the request; SASH proves the TinyLlama answer as 23 linked segments and STWO proves three classifier verdicts; the verifier checks every proof and that both name the same request.](assets/figures/overview.svg)

Prefer an interactive interface? Run `make demo-tui` or `make demo-web` from a
checkout. The [workbench](WORKBENCH.md) uses these same drivers and retains their
results; opening an interface does not start a proof or paid job.

## Get the checkout

```sh
git clone https://github.com/AbdelStark/hallmark.git
cd hallmark
```

Python packages are not published. Trained classifiers are
[available on Hugging Face](MODELS.md).

## The smallest software check

```sh
uv sync --locked --python 3.12
uv run --locked hallmark validate-data fixtures/smoke.jsonl
make check-conformance
```

This validates data and software contracts. It does not generate a cryptographic
proof or run hardware attestation.

## A local proof workflow

With Git, Make, uv 0.9.18, Rust nightly-2025-07-14 and an Apple Silicon Mac:

```sh
make e2e
```

Allow several minutes plus the first Rust build; the sampled worker cap is 30 GiB.
No GPU, token, cloud account or pretrained checkpoint is needed.
[Read the outputs and troubleshooting guide](DEMO.md).

## A complete LLM response

Set your HF token in the environment or ignored `.env`, check prepaid credits,
then use the [LLM workflow](LLM-PROOF.md#run-it). It starts three sequential paid
CPU jobs, under a **$2.10 timeout-based cost ceiling**.

The [GPU benchmark](GPU-BENCHMARK.md#run-it) is separate: it reuses a completed
reviewed public witness archive and starts CPU/H200 jobs under a **$5 ceiling**.
It does not train a new model. Read the run plan and balance-input requirements
before launching.

## Related guides {#what-to-read-next}

- [Learn the concepts](learn/index.md): statements, witnesses and caller enrollment.
- [Architecture](ARCHITECTURE.md): checks inside the circuits and in caller code.
- [Research evidence](research/index.md): measurements, failed runs and limits.
