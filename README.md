# Hallmark

**Circle STARK proofs of LLM inference and exact classifier decisions.**

[![Documentation](https://img.shields.io/badge/Docs-GitHub%20Pages-203c35?style=for-the-badge&logo=readthedocs&logoColor=white)](https://abdelstark.github.io/hallmark/)
[![Research checks](https://img.shields.io/github/actions/workflow/status/AbdelStark/hallmark/check.yml?branch=main&style=for-the-badge&label=checks&logo=githubactions&logoColor=white)](https://github.com/AbdelStark/hallmark/actions/workflows/check.yml)
[![Default prover: Circle STARK](https://img.shields.io/badge/Default_Prover-Circle_STARK-203c35?style=for-the-badge)](docs/CIRCLE-CLASSIFIERS.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-566b55?style=for-the-badge&logo=opensourceinitiative&logoColor=white)](LICENSE.md)

[![Hugging Face: Byte MLP](https://img.shields.io/badge/Hugging%20Face-Byte%20MLP-ffd21e?style=for-the-badge&logo=huggingface&logoColor=203c35)](https://huggingface.co/abdelstark/hallmark-byte-mlp)
[![Hugging Face: Contextual CNN](https://img.shields.io/badge/Hugging%20Face-Contextual%20CNN-ffd21e?style=for-the-badge&logo=huggingface&logoColor=203c35)](https://huggingface.co/abdelstark/hallmark-contextual-byte-cnn)

[What is proved](#what-is-proved) · [How it runs](#how-it-runs) · [Performance](#performance) · [Quickstart](#quickstart) · [Proof downloads](docs/REFERENCE-RUN.md#download-and-verify) · [Documentation site](https://abdelstark.github.io/hallmark/)

Hallmark proves two kinds of computation and checks them against one request:

- **An LLM answer.** A pinned, quantized **TinyLlama-1.1B** computes
  “The capital of France is Paris.” token by token, through end-of-sequence.
  SASH's Circle STARK prover covers every layer; the result is 23 linked proofs.
- **Classifier decisions.** A byte rule, an MLP and a CNN reach exact pass/block
  verdicts on the same prompt. Dedicated STWO Circle STARK circuits prove each one.

The verifier checks every proof against model and program identities the
caller pinned before proving, then checks that both proofs refer to the same
request. Circle STARK is the default everywhere; gnark/Groth16 stays available
as an explicit comparison backend.

This is a fixed-case **research integrity MVP**: one prompt, one model, public
witnesses, no hardware attestation. [Where the proof ends](#where-the-proof-ends)
lists what it does not claim.

![How Hallmark works: the caller pins roots, programs and the request; SASH proves the TinyLlama answer as 23 linked segments and STWO proves three classifier verdicts; the verifier checks every proof and that both name the same request.](docs/assets/figures/overview.svg)

## At a glance

| | TinyLlama answer · run L1 | Classifier decisions · run C1 |
|---|---|---|
| What is proved | 8 tokens through EOS, all 22 layers + head | 3 requests × 3 classifiers |
| Proofs | 23 linked segments | 9 independent proofs |
| Proving | **53.94 s** GPU session on one H200 (547.75 s on CPU) | **24.06 s** final STWO calls on an M4 Max |
| Verification | **3.40–3.53 s** per check on a Mac, roots compiled in | **0.807 s** for all nine |
| Proof size | 737.86 MB of JSON | 18.06 MB of JSON |

Each number has a stated boundary and none of them is an end-to-end latency.
Read [Performance](#performance) before quoting one. The actual proofs, logs and
machine records are public: [download and verify them](docs/REFERENCE-RUN.md) ·
[artifacts](https://github.com/AbdelStark/hallmark/releases/tag/circle-reference-2026-10-28) ·
[reference Discussion](https://github.com/AbdelStark/hallmark/discussions/133).

## What is proved

### The TinyLlama answer

```text
Prompt:   Name the capital of France in one short sentence.
Response: The capital of France is Paris.
```

![What the TinyLlama proof covers: a 32-position input block, 23 segment proofs stacked as layers, the output head's argmax at positions 24 to 31, and seven links feeding each output back as the next input.](docs/assets/figures/llm-statement.svg)

The chat template turns the prompt into 25 tokens. One causal block of 32
positions holds those 25 plus the first seven answer tokens. The proof covers
the embedding, all 22 transformer layers and the final norm plus output head,
as **23 segment proofs** joined by **22 residual links**. The head's argmax at
positions 24–31 yields the eight answer tokens. Seven of them must equal the
next input token, which closes the autoregressive loop; the caller checks that
the eighth is EOS.

The relation is the disclosed quantization profile `y-attnout-w12`, not the
original floating-point model. The 23 segments form a linked bundle checked
together, not a single recursive proof. [Exact LLM statement](docs/LLM-PROOF.md#the-statement).

### A classifier decision

![What one classifier proof states: a witness of prompt bytes, salt and intermediate values; four constrained steps (complete input, SHA-256 commitment, integer classifier, threshold decision); a public statement of 100 fields.](docs/assets/figures/classifier-statement.svg)

For a fixed integer classifier `F`, threshold `t` and the complete prompt `x`
(at most 96 UTF-8 bytes), the proof shows that `verdict = 1` exactly when
`F(x) < t`, and that `x` matches a salted SHA-256 commitment. The weights are
constants compiled into the circuit; training is not proved. Each proof carries
100 public fields. The circuit recomputes the input digest; the caller rebuilds
the context digest and classifier identity from its own request.

![Nine proofs, nine verdicts: the allow request passes all three classifiers; the CNN blocks the contextual case; the rule blocks the BAD-prefixed case. Every proof verifies.](docs/assets/figures/verdict-matrix.svg)

A valid proof can say “block”. Proof validity and classifier approval are
separate outcomes. The frozen MLP allows every admitted input (its
[integer score bound](research/evidence/mlp-domain-bound-2026-10-27.json) is
[−5600, −2338] against threshold 0); it exercises the full MLP arithmetic while
the rule and CNN provide the blocks. [Model limits](docs/MODELS.md).

### Where the proof ends

![Three columns: what is proved by the STARK, what the caller checks, and what is not claimed.](docs/assets/figures/trust-boundary.svg)

| Path | Cryptographic statement | Caller responsibilities |
|---|---|---|
| **LLM — SASH Circle STARK** | The enrolled quantized model computes the complete greedy answer through EOS: embedding, every transformer layer, final normalization and output argmax, with all segment and token links checked | Enroll model, shape and calibration roots and the exact token case before proving; check tokenization and detokenization outside the circuit |
| **Classifiers — STWO Circle STARK (default)** | The rule, MLP or CNN arithmetic on the complete 96-byte input, plus its exact salted SHA-256 commitment | Enroll the circuit, preprocessing and backend identities before proving; rebuild expected public inputs and the complete roster ([details](docs/CIRCLE-CLASSIFIERS.md)) |
| **Classifiers — gnark/Groth16 comparison** | The same logical relation on BLS12-381 | Rebuild public inputs; check circuit, key, model and context binding |
| **Composition — host verification** | Both verified relations refer to the same opened request | Check the shared prompt/response context; combine verified verdicts with `all-pass` |

The classifier caller currently reruns native inference to derive the expected
verdicts, so this demo does not show verification being cheaper than a rerun.
[LLM statement](docs/LLM-PROOF.md#the-statement) ·
[classifier public inputs](docs/PROOFS.md) ·
[composition](docs/COMPOSED-DEMO.md).

## How it runs

### The LLM: `make e2e-llm`

![The TinyLlama workflow: prepare on a Mac, then three Hugging Face CPU jobs build the prover, prove 23 segments and verify them; an optional native verifier rechecks on the Mac.](docs/assets/figures/llm-pipeline.svg)

Your Mac downloads the pinned checkpoint, quantizes it, decodes greedily and
extracts the witness. Three sequential CPU jobs then build the unchanged SASH
prover, derive the model roots and compare them with the caller's enrollment
before proving, and verify the bundle in fresh processes. The verifier never
receives weights or the witness. SASH is fetched as hash-pinned upstream source
and driven through CLI adapters; the CPU prover is unchanged upstream Rust.
[Source ownership and patches](docs/ARCHITECTURE.md#how-sash-is-integrated).

### The classifiers: `make e2e`

![The classifier workflow: train, export, compile and enroll once; then build the witness, prove with STWO, verify in a fresh process and bind the result, nine times. All 84 rejection checks pass.](docs/assets/figures/classifier-pipeline.svg)

### Both, one request: `make e2e-composed`

![Composition: the opened request feeds a freshly verified 23-segment LLM bundle and three new classifier proofs; a host join checks they share the request and rejects 16 changed bindings. Integrity passes; the CNN blocks, so release is false.](docs/assets/figures/composition.svg)

The join is host code over two verified results, not recursive aggregation.
Classifiers read the prompt; the response is bound into their context, not
classified. [Architecture and every command](docs/ARCHITECTURE.md).

## Performance

Three named runs, three machines, three timing boundaries. **L1** is one H200
CPU-then-GPU pair for the LLM; **C1** is one fresh classifier run on a Mac;
**J1** is the composition. They are component measurements, not one fresh
end-to-end latency, and a single run is not a distribution. MB and GB are
decimal; GiB is binary. [Every stage and raw file](docs/REFERENCE-RUN.md) ·
[how to read these numbers](docs/PERFORMANCE.md).

### L1 — the TinyLlama answer on one NVIDIA H200

![TinyLlama proving on one H200: CUDA cuts the proving session from 547.75 s to 53.94 s (10.15×); complete segment commands go from 679.49 s to 155.89 s (4.36×); trace generation is unchanged.](docs/assets/figures/perf-llm-gpu.svg)

Same host, inputs and parameters, CPU then GPU, 2026-10-26: HF Jobs H200
profile with 23 provider vCPUs, 256 GB RAM and four Rayon threads. All 23 proofs
and 22 links verify, and all 69 proof, statement and claim files match byte for
byte across backends. Preparation and the generated-kernel build are reused.

| All 23 proof segments | CPU / SIMD | GPU / CUDA |
|---|---:|---:|
| Trace-generation timers | 31.84 s | **32.14 s** |
| **Proving-session timers** | 547.75 s | **53.94 s** |
| ↳ Interaction work, **inside** session timer | 60.72 s | 36.95 s |
| Inline verification timers | 77.62 s | 34.40 s |
| **Complete prover segment commands** | 679.49 s | **155.89 s** |
| Separate full-grid **CPU** verifier on H200 host | 85.35 s | **84.32 s** |
| **Actual proof JSON, all 23 files** | 737,858,641 bytes | **737,858,641 bytes** |
| Sampled peak host RSS | 103.75 GB | 8.07 GB |
| Sampled peak GPU memory | — | 67.67 GiB |

The session timer starts after trace generation and includes commitments and
interaction work, so **do not add the nested interaction row**. Complete
commands also include loading, inline checks and serialization; the
[timer breakdown](docs/PERFORMANCE.md#what-a-segment-command-contains) shows how
they stack. Constraints run on CUDA with zero CPU fallback; witness and
interaction generation stay on the CPU.

| Verification and enclosing stages | L1 | Boundary |
|---|---:|---|
| Native Mac full-bundle check | **3.40 / 3.53 s** | Per honest check on an M4 Max **after compilation**, shape roots compiled in |
| Fresh Linux full-bundle check | **77.40 / 77.61 s** | Per honest check on a separate 8-vCPU / 32-GB worker, roots derived at runtime |
| Generated-kernel build job | **1,815.94 s** | Earlier CPU job's running time; 77 kernel shapes |
| Model-root command | **113.86 s** | Separate command before the segment runs |
| Complete cached-build benchmark | **2,086.78 s** | Both backends, fixtures, transfers, checks and Mac suites |

The two verifiers share SASH's cryptography but preprocess differently, so
their times are not a matched speedup. Linux rejects all 14 mutations; the Mac
verifier rejects all 36. [Download the LLM proofs](https://github.com/AbdelStark/hallmark/releases/download/circle-reference-2026-10-28/llm-proofs.tar.gz)
(355 MB gzip of the 737.86 MB payload) · [GPU method](docs/GPU-BENCHMARK.md).

### C1 — the classifier workflow on an Apple M4 Max

![One fresh classifier run, zoomed in: of the 302.96 s run, CNN training takes 172.94 s and the proof campaign 93.50 s; inside it, nine prover commands take 50.03 s, of which final STWO proving is 24.06 s.](docs/assets/figures/perf-classifier-c1.svg)

One fresh default run on 2026-10-28: 16 logical CPUs, 48 GiB RAM, four prover
threads, populated dependency caches and an empty Rust target directory. It
trains the MLP and CNN and proves all three classifiers on all three requests.

| Stage | C1 measurement | Boundary |
|---|---:|---|
| MLP training/export | **1.95 s** | Complete child command |
| CNN training/export/screen | **172.94 s** | Complete child command |
| Rust prover / proof-only verifier builds | **24.82 / 9.57 s** | Two locked Cargo commands |
| Host witness construction | **15.613 s** | Nine witnesses, outside the prover processes |
| Preprocessing and model commitment | **7.882 s** | Inside prover commands; repeated per proof |
| **Final STWO proving calls** | **24.061 s** | Nine final calls; excludes the trace and commitment work before them |
| **Complete prover commands** | **50.028 s** | Parsing, every engine stage and serialization |
| **Fresh proof-only verifier commands** | **0.807 s** | Nine fresh processes; excludes the caller's native rerun |
| **Actual serialized proofs** | **18,063,779 bytes** | Nine canonical JSON proof files |
| Proof campaign | **93.50 s** | Enrollment, witnesses, proving, checks and host work |
| **Complete observed controller** | **302.96 s** | Training, builds, proofs and checks; excludes uv bootstrap |
| Maximum sampled worker-tree RSS | **23.45 GB** | Maximum across workers, not a sum |

Rows nest: preprocessing and final proving sit inside the prover commands. All
63 changed public inputs, 18 cross-request substitutions and three invalid
rosters reject. [Every C1 stage and each proof's time and size](docs/REFERENCE-RUN.md#c1-default-classifier-workflow) ·
[download proofs and logs](https://github.com/AbdelStark/hallmark/releases/download/circle-reference-2026-10-28/reference-records.tar.gz).

### Classifiers on one A100

![Circle classifier proving on one A100: CUDA runs the nine prover commands 4.16× faster, 92.41 s to 22.22 s; per classifier, rule 7.659 to 2.049 s, MLP 7.660 to 2.109 s, CNN 15.567 to 3.205 s.](docs/assets/figures/perf-classifier-gpu.svg)

Three CPU/CUDA pairs of the unchanged C1 circuits; all 54 proofs pass the stock
verifier and match the C1 proof bytes. Training, witness preparation and
verification are excluded. [Method, all 54 checks and resource records](docs/CLASSIFIER-GPU-BENCHMARK.md).

### Circle versus gnark

![Circle versus gnark: warm nine-proof workflow medians 298.88 s versus 781.25 s; Circle proofs are about 2 MB against 292 bytes, and Circle peaks near 20 GB of memory against 2.65 GB.](docs/assets/figures/perf-backends.svg)

A separate matched study on an 8-vCPU HF CPU worker: three fresh and five warm
workflows per backend, 144 proofs. Circle is faster end to end because each stateless
gnark command spends most of its time parsing the assignment, R1CS and proving
key; gnark's proofs are roughly 7,000 times smaller and its proving step alone
is shorter. The backends differ in
security assumptions and verifier implementation, so this is not an
equal-security ranking. [All ranges, stages and raw samples](docs/CLASSIFIER-BENCHMARK.md).

### J1 — both proofs, one request

The retained-input composed command takes **266.29 s**: native LLM workflow
216.87 s (fresh build, two honest checks, 36 mutations) and classifier controller
44.12 s (three new proofs, 6,020,695 bytes). The join re-verifies the classifier
proofs and rejects **16 changed bindings and rosters**. Integrity passes; verdicts
`[1, 1, 0]` make release false. It reuses the L1 LLM proof bytes and is **not
fresh GPU proving**. [Exact join and timings](docs/REFERENCE-RUN.md#j1-same-request-composition).

## Quickstart

```sh
git clone https://github.com/AbdelStark/hallmark.git
cd hallmark
```

Python packages are not published; work from the checkout.

| I want to… | Command | Needs | Cost |
|---|---|---|---|
| Train, prove and verify classifiers | `make e2e` | Apple Silicon Mac, 12 GiB free | Local only |
| Prove the TinyLlama answer | `make e2e-llm` | Mac with 32 GB RAM, 16 GiB free, HF token and credits | ≤ $2.10 of HF CPU jobs |
| Verify retained LLM proofs | `make verify-llm LLM_RUN=…` | Mac, Rust toolchain, 8 GiB free | Local, offline |
| Reproduce the H200 measurement | `make benchmark-llm-gpu …` | A completed LLM run, HF credits | ≤ $5 of HF CPU/H200 jobs |
| Bind both to one request | `make e2e-composed` | Both sets of prerequisites, 32 GiB free | Paid LLM jobs unless you reuse runs |
| Check software contracts only | `make check-conformance` | Linux or macOS | Local, no proof |

All proof workflows need Git, Make, **uv 0.9.18** and Rust
**nightly-2025-07-14**. Each run prints a fresh `runs/` directory; failures exit
nonzero and keep their logs.

### Classifiers, locally

```sh
make e2e
```

Trains the MLP and byte CNN, exports the integer graphs, builds the locked STWO
prover and proof-only verifier, and generates **nine Circle STARK proofs**. Each
is freshly verified, and **63 public-input mutations, 18 cross-request
substitutions and three invalid rosters** must reject. Expect the benign request
to pass, the CNN to block the contextual one and the rule to block the marker
one. Allow a few minutes plus the first Rust build, and room for the 30-GiB
sampled worker cap. No GPU, token or pretrained weights are needed.
`make e2e BACKEND=gnark` runs the Groth16 baseline instead.
[Outputs and troubleshooting](docs/DEMO.md).

### The TinyLlama answer

Set `HF_TOKEN` in the environment or an ignored `.env`, check your credits, then:

```sh
make e2e-llm
```

Downloads the pinned 2.2-GB Apache-2.0 checkpoint, prepares the witness locally
and starts **three sequential paid HF CPU jobs** under a **$2.10 timeout-based
ceiling**. Success means 23 new proofs, two honest verifications and 14 rejected
mutations. No local GPU is needed. [Run guide](docs/LLM-PROOF.md#run-it).

To re-verify those proofs on your Mac, with no weights or credentials:

```sh
rustup toolchain install nightly-2025-07-14 --profile minimal   # once
make verify-llm LLM_RUN=runs/llm-e2e-...
```

Builds may download locked dependencies; verification itself runs offline. Read
the [shape-enrollment trust boundary](docs/LLM-PROOF.md#verify-retained-proofs-on-your-mac),
including optional signed parameters.

### The H200 measurement

```sh
make benchmark-llm-gpu \
  LLM_RUN=/path/to/completed/llm-e2e-run \
  GPU_CREDIT_BALANCE_USD=YOUR_CHECKED_BALANCE
```

Starts paid HF CPU/H200 jobs under a **$5 single-run ceiling**. It reuses the
frozen public witness, builds generated CUDA kernels, compares SIMD and CUDA on
one H200, and verifies the GPU proofs in fresh CPU and Mac processes.
`GPU_BUILD_RUN=…` reuses a matching build. [Run plan, costs and failures](docs/GPU-BENCHMARK.md).

### Both proofs, one request

```sh
make e2e-composed
```

Runs both workflows and binds three new classifier proofs to the proved LLM
request. Pass `LLM_RUN=… CLASSIFIER_RUN=…` to reuse your own runs without new
cloud jobs; LLM proofs are re-verified and the three classifier proofs are
always new. [Walkthrough and signed enrollment](docs/COMPOSED-DEMO.md).

### A software check, no proofs

```sh
uv sync --locked --python 3.12
uv run --locked hallmark validate-data fixtures/smoke.jsonl
make check-conformance
```

Expect a dataset summary, then **156 matched software cases** and **32
unavailable full-evidence obligations**. Core CI also covers CPython 3.13 and 3.14.

### Demo apps

```sh
make demo-tui
make demo-web
```

A terminal and a local web workbench over the same workflow controller: live
stages, process memory and CPU, logs, HF job status, verification results and
retained artifacts. Paid workflows show their cost bounds before launch.
[Workbench guide](docs/WORKBENCH.md).

## Published models

The exact seed-17 classifiers used by the proofs are on **Hugging Face**, with
model cards, JSON checkpoints, quantized weights, native exports, evaluation
records and hash manifests:

| Model | Architecture | Card and weights |
|---|---|---|
| Byte MLP | 1,033 parameters; byte counts → 4 ReLU units → score | [abdelstark/hallmark-byte-mlp](https://huggingface.co/abdelstark/hallmark-byte-mlp) |
| Contextual byte CNN | 4,161 parameters; byte embeddings → causal convolution → masked max → score | [abdelstark/hallmark-contextual-byte-cnn](https://huggingface.co/abdelstark/hallmark-contextual-byte-cnn) |

Both are MIT-licensed synthetic research models trained from scratch, exported
as Hallmark JSON/CBOR rather than Transformers models. Native inference does not
generate a proof. TinyLlama is an upstream pretrained model, not a Hallmark
release. [Download and run the models](docs/MODELS.md#download-and-run) ·
[immutable revisions](docs/MODELS.md#immutable-identities).

## Limits

- **One fixed case.** The pipeline proves this TinyLlama answer to this prompt.
  Another prompt, length or model needs a new case and a new enrollment.
- **Integrity, not privacy.** Witnesses are public: there is no zero-knowledge
  or hardware-provenance claim. Caller enrollment is the trust anchor; a prover
  cannot authenticate its own parameters.
- **Synthetic classifiers.** Inputs are capped at 96 UTF-8 bytes and longer ones
  reject. Synthetic accuracy is not a useful safety policy: the frozen CNN blocks
  the ordinary LLM prompt in the composed demo.
- **Unreviewed cryptography.** Circle proofs use caller-enrolled public
  preprocessing; the gnark baseline uses a local circuit-specific setup, not a
  reviewed ceremony. Neither backend has independent security qualification, and
  results say so: `qualified_backend: false`, `hiding_claim: false`,
  `hardware_claim: "not-accepted"`.
- **Bounded measurements.** Proof sizes exclude enrollment and keys. GPU timings
  are single matched observations. Failures and source and environment hashes
  stay in the research record.

The [MVP acceptance matrix](docs/MVP.md) separates completed integrity work from
the original private/hardware v1 roadmap. [Decision 0085](docs/decisions/0085-circle-default.md)
made Circle the default: lower workflow time in the recorded harness, at the cost
of larger proofs, more memory and different security assumptions.

## Documentation

| I want to… | Read |
|---|---|
| Understand the proofs from scratch | [Learning path](docs/learn/index.md) |
| Read the measurements correctly | [Performance](docs/PERFORMANCE.md) |
| Download actual proofs and audit every stage | [Reference runs](docs/REFERENCE-RUN.md) |
| Trace commands, flows and source ownership | [Architecture](docs/ARCHITECTURE.md) |
| Inspect the exact LLM relation | [LLM proof guide](docs/LLM-PROOF.md) |
| Inspect classifier circuits and public inputs | [Classifier proofs](docs/PROOFS.md) · [Circle details](docs/CIRCLE-CLASSIFIERS.md) |
| Reproduce GPU timings | [LLM on H200](docs/GPU-BENCHMARK.md) · [classifiers on A100](docs/CLASSIFIER-GPU-BENCHMARK.md) |
| Run the joined workflow | [Composed demo](docs/COMPOSED-DEMO.md) |
| Assess model and data quality | [Results and limitations](docs/RESULTS.md) |
| Find any contract or research record | [Documentation index](docs/README.md) |
| See completed work and open gates | [Current state](research/STATE.md) |

## Development

Build the [documentation site](https://abdelstark.github.io/hallmark/) with
`make docs` or preview it with `make docs-serve`; its toolchain is locked
separately ([site maintenance](docs/DOCUMENTATION.md)). Figures are generated
from the evidence records with `python scripts/render_figures.py`.

```sh
uv sync --locked --python 3.12
make check
make package-check
# For training changes:
make check-train
make package-check-train
```

`make check` covers the lockfile, lint, formatting, strict typing, tests,
documentation and software conformance. A core environment may skip optional
training; the train gate requires it. Package checks build and install fresh
wheel and sdist artifacts. CI checks a fresh synthetic proof with separate
arithmetic; it does not run paid GPU jobs or the full Mac demos.

| Path | Responsibility |
|---|---|
| `src/hallmark/` | Contracts, native integer runtimes, training and binding |
| `scripts/` | Experiment controllers, reproducible workflows, validation and figures |
| `research/probes/sash/` | Pinned SASH adapters, patches and the fixed LLM case |
| `research/probes/circle/` | STWO gate AIR, prover and proof-only verifier |
| `research/probes/gnark/` | Groth16 comparison circuits and negative fixtures |
| `research/probes/py_ecc/` | Separate Groth16 proof decoder and pairing verifier |
| `fixtures/` · `tests/` | Synthetic data, frozen protocols, arithmetic and rejection checks |
| `docs/` · `research/` | Guides, decisions, numeric evidence and the research ledger |

Start with [CONTRIBUTING](CONTRIBUTING.md). Arithmetic or binding changes need
rejection tests; data or evaluation changes need a new experiment identity. The
[supported API](docs/spec/02-public-api.md) separates implemented interfaces
from proposed ones. Keep raw evidence and failures; never commit credentials,
private transcripts, checkpoints or local runs.

## Security and licence

Read [SECURITY](SECURITY.md) for trust assumptions and private vulnerability
reporting. [Open an issue](https://github.com/AbdelStark/hallmark/issues) for
reproducibility problems or scoped improvements, with the command, source
revision and a sanitized failure log.

Hallmark is **[MIT licensed](LICENSE.md)**. Third-party software, data and model
weights keep their own terms; see [dependency notices](docs/DEPENDENCIES.md).
Historical evidence keeps its original licence labels and hashes
([decision 0063](docs/decisions/0063-mit-license.md)).
