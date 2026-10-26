# Hallmark

**Prove a complete LLM response. Verify exact classifier decisions.**

[![Research checks](https://github.com/AbdelStark/hallmark/actions/workflows/check.yml/badge.svg)](https://github.com/AbdelStark/hallmark/actions/workflows/check.yml)

[Architecture and proof flows](docs/ARCHITECTURE.md) · [LLM proof](docs/LLM-PROOF.md) · [MVP scope](docs/MVP.md) · [Composed demo](docs/COMPOSED-DEMO.md) · [Classifier proofs](docs/PROOFS.md) · [Documentation](docs/README.md)

Hallmark is MIT-licensed research software for verifiable LLM inference and text
classification. Its **fixed-case LLM integrity MVP is complete**: a pinned,
disclosed quantized TinyLlama-1.1B generates “The capital of France is Paris.”,
and all 23 proof segments verify through the final EOS token.

The LLM path uses SASH's specialized Circle STARK prover. It requires neither a
general-purpose zkVM nor hardware attestation, and makes no witness-hiding claim.
[The proof explanation](docs/LLM-PROOF.md) gives the prompt, model, arithmetic,
public expectations and exact verifier checks. Run `make e2e-llm` to reproduce it
with local preparation and bounded HF CPU jobs.

The classifier path trains an MLP and a contextual byte CNN, combines them with a
literal rule, and checks real Groth16 proofs with separate py-ecc arithmetic.
These are custom gnark circuits on BLS12-381. `make e2e` runs that workflow entirely
on your Mac; `make e2e-composed` binds three classifier proofs to the proved LLM
prompt and response.

The [MVP acceptance record](docs/MVP.md) separates this working integrity demo
from the future private, hardware-attested v1 system. The classifier data is
synthetic and its input limit is 96 UTF-8 bytes. A valid proof establishes the
stated computation, not that a classifier is a useful safety policy. Arbitrary
prompts/models and production qualification remain outside this fixed case.

## Which command proves what?

| Command | Workload | Actual proof system |
|---|---|---|
| `make e2e` | Three synthetic requests × rule, MLP and CNN; authored response, **no LLM inference** | 9 dedicated **gnark/Groth16** proofs, separate py-ecc verification; entirely local |
| `make e2e-llm` | Complete fixed quantized TinyLlama response through EOS | 23 **SASH Circle STARK** segments; Mac preparation and bounded HF CPU jobs |
| `make verify-llm LLM_RUN=…` | Fresh local verification of retained LLM proofs | Adapted native SASH verifier; no weights or paid jobs |
| `make e2e-composed` | Both workflows, bound to the same request | 23 SASH segments + 9 classifier control proofs + 3 new classifier proofs; host composition |

**[Read the architecture guide](docs/ARCHITECTURE.md)** for the end-to-end diagrams,
exact statements, caller/prover boundaries and SASH integration. SASH is fetched
as hash-pinned upstream source and invoked through CLI adapters. The Linux Rust
prover is unchanged; witness preparation and the optional Mac verifier have
explicit patches. These are real inference proofs of the disclosed quantized
relation, not proofs of equivalence to the original floating-point model.

Classifiers currently use Groth16 because those complete circuits were built
first. No matched benchmark establishes that it beats Circle STARK. The new
**[Circle STARK classifier epic #112](https://github.com/AbdelStark/hallmark/issues/112)**
tracks complete rule/MLP/CNN proofs and a fair comparison against gnark and native
execution. That backend is planned; it is not part of today's working demo.

## What exactly is proved?

For the LLM, the enrolled quantized model computes the displayed complete greedy
answer from the expected prompt tokens. The proof covers embedding, every
transformer layer, final normalization and output argmax, including EOS. The
caller supplies the expected model/shape/calibration roots and exact token case.
Tokenization and detokenization are pinned caller checks outside the circuit.
See the [LLM statement](docs/LLM-PROOF.md#the-statement) for the exact boundaries.

For a fixed integer classifier and a particular prompt, Hallmark proves that the
classifier computes the stated pass/block verdict on the complete prompt bytes.
A **valid proof can prove a block**: proof validity and classifier approval are
separate outcomes.

The classifier proofs cover input hashing and integer inference, including the final
threshold comparison. Classifier training supplies the weights; its history is not
proved. The caller checks request/model/key binding, and host code combines three verified verdicts
with `all-pass`. The standalone classifier demo uses an authored response. The
[composed demo](docs/COMPOSED-DEMO.md) instead binds these classifier relations
to the proved TinyLlama prompt and response.

Read [the proof statement, public inputs and trust boundary](docs/PROOFS.md) for a
concrete example and the exact division between circuit checks and caller checks.

## What the classifier demo does

![Synthetic training, integer export and dedicated proofs feed a separate verifier, bound to the caller request and enrolled keys, then an all-pass classifier gate.](docs/assets/classifier-pipeline.svg)

The caller reconstructs the public inputs from its own transcript opening and
expected context. The prover's bundle cannot choose those expectations. The
controller pins each compiled circuit and verification key before proving.

| Classifier | Computation | Role in the demo |
|---|---|---|
| Literal rule | Complete byte scan for `BAD`, including chunk boundaries | Blocks the marker case |
| Trained MLP | Byte counts → four hidden ReLU units → score | Learned arithmetic baseline; insensitive to word order within a chunk |
| Trained CNN | Byte embeddings → width-24 convolution → ReLU → masked max pooling → score | Distinguishes an active action from the same action inside a quotation |

Each classifier sees the complete prompt admitted by this demo. Oversized inputs
are rejected, never silently truncated. In the standalone classifier demo the
response is authored fixture text; its proofs make no LLM generation claim.

The fixed three-case run produces:

| Case | Rule | MLP | CNN | Classifier gate |
|---|---|---|---|---|
| Benign action, quoted restricted action | Pass | Pass | Pass | `release: true` |
| Restricted action, quoted benign action | Pass | Pass | Block | `release: false` |
| Benign case prefixed with `BAD; ` | Block | Pass | Pass | `release: false` |

`release` is the demo's all-pass classifier decision. It is not authorization to
release a real model response. Results retain `qualified_backend: false` and
`hardware_claim: "not-accepted"`.

## Start here

### Prove a pretrained LLM response

On an **Apple Silicon Mac**, with Git, Make, **uv 0.9.18**, **16 GiB free storage**,
32 GB RAM and an HF account with Jobs access and prepaid credits, set `HF_TOKEN`
in the environment or ignored
`.env` file, then run:

```sh
make e2e-llm
```

The command downloads pinned TinyLlama-1.1B weights, generates “The capital of
France is Paris.” and produces fresh SASH proofs for the complete quantized
inference. It builds, proves and verifies on three sequential CPU jobs with a
**$2.10 timeout-based cost ceiling**. No local GPU is needed. See the
[LLM guide](docs/LLM-PROOF.md#run-it) for the exact statement, limits and artifacts.
The recorded fresh run took **31 minutes 15 seconds**, with a **$0.31 compute
bound**; two full verifications took about **80 seconds** each.

Already have a completed run? Verify its proofs locally with
`make verify-llm LLM_RUN=runs/llm-e2e-...`. This optional native verifier needs no
weights or HF credentials. Recorded honest checks take **3.33–4.00 seconds**
after compilation. It uses compiled parameters for the fixed case;
see [local verification and its trust boundary](docs/LLM-PROOF.md#verify-retained-proofs-on-your-mac).
For signer-authorized parameters, [verify a signed enrollment](docs/LLM-PROOF.md#verify-a-signed-parameter-enrollment)
with a public key obtained through your own authenticated channel.

### Train, prove and verify classifiers

On an **Apple Silicon Mac**, with Git, Make, curl and **uv 0.9.18** on `PATH`:

```sh
git clone https://github.com/AbdelStark/hallmark.git
cd hallmark
make e2e
```

One command prepares pinned Python/Go environments, trains both models, builds the
circuits, generates **nine real proofs** and checks them with the separate verifier.
It checks **18 cross-request substitutions** and **405 arithmetic cases**, then
prints the three decisions and the path to its result. Every run gets a fresh
local evidence directory; failures return nonzero and retain their logs.

Allow **12 GiB free storage** and roughly **20 minutes plus dependency/build time**
on the recorded M4 Max. No GPU, API token, cloud account, downloaded model weights
or private data is needed. See the [demo guide](docs/DEMO.md) for prerequisites,
progress, expected output, resource bounds and troubleshooting.

### Check LLM generation and classifiers together

```sh
make e2e-composed
```

This joins the proved TinyLlama response with three new classifier proofs bound
to the exact same opened request. It uses the prerequisites of both demos and
32 GiB free storage. Supply `LLM_RUN` and `CLASSIFIER_RUN` to reuse caller-owned
preparation without new cloud jobs; proofs are freshly verified and classifier
keys/proofs are always new. See the [composed workflow and exact join](docs/COMPOSED-DEMO.md).
To require an external signer's authorization of the LLM case and verifier,
use [signed LLM parameters](docs/COMPOSED-DEMO.md#signed-llm-parameters).
The complete fresh workflow has been reproduced in **66 minutes 50 seconds**, with
**$0.31 bounded cloud compute** rather than an invoice. It includes fresh LLM
witnesses/proofs, classifier training, twelve classifier proofs and the negative
check suites. See the [recorded fresh run and retained failures](docs/COMPOSED-DEMO.md#recorded-fresh-preparation).
The frozen synthetic CNN blocks this ordinary prompt: valid proofs establish its
computation, not a sensible safety policy.

### Quick software smoke test

For a smaller check on Linux or macOS, from the checkout:

```sh
uv sync --locked --python 3.12
uv run --locked hallmark validate-data fixtures/smoke.jsonl
make check-conformance
```

Expect a dataset summary, then **156 matched software cases** and **32 unavailable
full-evidence obligations**. This smoke test checks software contracts; it does
not generate a proof. Core CI also covers CPython 3.13 and 3.14. Packages are not
published; use the checkout.

## Evidence, with its limits

| Question | Current evidence | What it does not establish |
|---|---|---|
| Can training reproduce the integer models? | Three fixed seeds; full/resumed checkpoints agree; repeated CNN exports and decisions match | Robustness to other runtimes, data or tasks |
| Does the CNN learn the synthetic scope task? | All three v2 seeds detect 50/50 positives; false positives are 0/50, 1/50 and 0/50 | Real-world safety or a population 1% false-positive rate |
| Can the three classifiers be proved together? | Original two campaigns: **18 real proofs**, **6 verified three-proof sets** | Authenticated compiler/enrollment or a trusted setup ceremony |
| Do the checks reject altered claims? | **36 cross-request substitutions rejected**; **810 arithmetic cases matched expected outcomes** | A security audit or proof of absence of implementation bugs |
| Is the full hybrid system complete? | Software contracts and bounded classifier proofs exist | Hardware provenance, protected response generation, B2 or operational hybrid acceptance |

The arithmetic corpus includes valid controls and malformed/rejected cases; its
810 cases are not 810 rejected attacks. The first CNN screen **failed** and remains
published. The second screen is a new experiment with fresh calibration/test
pairs, sharing a synthetic grammar and vocabulary. See [results and model/data
notes](docs/RESULTS.md) for counts, identities, costs and direct evidence links.

## How the project is organized

```text
src/hallmark/             Contracts, native integer runtimes, training and binding
scripts/                 Reproducible experiments and local validation commands
research/probes/gnark/   Dedicated Go proof circuits and negative fixtures
research/probes/py_ecc/  Separate proof decoder and pairing verifier
fixtures/                Authored synthetic data and frozen protocols
tests/                   Contract, arithmetic, mutation and distribution checks
docs/                    Walkthroughs, specifications and design decisions
research/                Current state, numeric evidence and chronological ledger
```

The [API reference](docs/spec/02-public-api.md) distinguishes supported library
interfaces from proposed commands. The research proof controllers run from source;
there is no production `verify-b` endpoint to deploy.

## Documentation

| I want to… | Read |
|---|---|
| Understand the Make targets, architecture and backend choices | [Proof flows, SASH integration and caller boundaries](docs/ARCHITECTURE.md) |
| Understand exactly what a classifier proof establishes | [Classifier statement and trust boundary](docs/PROOFS.md) |
| Run the whole classifier demo | [Demo walkthrough](docs/DEMO.md) |
| Prove a complete pretrained LLM response | [TinyLlama workflow and proof statement](docs/LLM-PROOF.md) |
| Assess the models, data and measured results | [Results and limitations](docs/RESULTS.md) |
| Find a contract, recipe or research record | [Documentation index](docs/README.md) |
| Understand the proposed full system | [Canonical specification](SPEC.md) |
| Reproduce or resume a research experiment | [Operations guide](docs/OPERATIONS.md) |
| Understand split, calibration and test rules | [Evaluation contract](docs/EVALUATION.md) |
| See what remains unfinished | [Current state](research/STATE.md) |
| Implement and compare Circle STARK classifier proofs | [Epic #112 and its five implementation tasks](https://github.com/AbdelStark/hallmark/issues/112) |

## Development

```sh
uv sync --locked --python 3.12
make check
make package-check
make check-train
make package-check-train
```

`make check` runs lock, lint, formatting, strict typing, tests, documentation and
software conformance checks. Core-only environments legitimately skip optional
training; the train gate requires execution. Package checks build and install
fresh wheel/sdist artifacts. CI also checks a fresh synthetic proof with the
separate arithmetic verifier; it does not run the full Mac demo or attest hardware.

Start with [CONTRIBUTING](CONTRIBUTING.md) for setup, focused checks and the PR
workflow. Changes to integer semantics or binding need rejection tests; changes
to data, thresholds or evaluation need a new experiment identity. Keep failures
and raw evidence. Never commit credentials, private transcripts, checkpoints or
local run directories.

## Security and licence

See [SECURITY](SECURITY.md) for trust assumptions and private reporting. Setup
custody, authenticated operational enrollment, independent security/hiding review
and operational verifier integration remain future qualification gates. They do
not block the owner-selected [integrity MVP](docs/MVP.md).

Hallmark is released under the **[MIT licence](LICENSE.md)**. Third-party software,
referenced datasets and model weights retain their own terms; see the
[dependency notices](docs/DEPENDENCIES.md). Packages and model checkpoints are
not published. Historical experiment records preserve their original licence
labels and hashes; [decision 0063](docs/decisions/0063-mit-license.md) records the
licence adoption without rewriting those artifacts.
