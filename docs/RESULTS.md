# Results and limitations

As of 2026-10-25, the [owner-selected LLM integrity MVP](MVP.md) is complete.
The fixed TinyLlama response has a complete specialized proof, including EOS;
`make e2e-llm` reproduces it. The original private/hardware v1 roadmap remains
future work, with no hiding or operational qualification claimed.

Hallmark also has a working **synthetic classifier research pipeline**:
training → integer export → dedicated-circuit proofs → separate verification →
all-pass composition. It has no accepted hardware attestation or operational
hybrid verifier. [Reproduce the demo](DEMO.md) or read [what is proved](PROOFS.md).

A separate [TinyLlama experiment](LLM-PROOF.md) verifies a complete eight-token
response with 23 SASH proof segments and 22 residual links. Its quantization,
measurements and failure history are documented separately from the classifier
results below. `make e2e-llm` now [reproduces that result](../research/evidence/llm-e2e-reproduction-2026-10-23.json)
from fresh preparation, build and proofs in 31 minutes 15 seconds, with two fresh
verifications and all 14 changed-claim rejections.

The optional [native proof-only command](LLM-PROOF.md#verify-retained-proofs-on-your-mac)
checks that fixed LLM case in **3.33–4.00 seconds per honest verification** across
four recorded processes. Two fresh workflows, including compilation and all 36
mutation checks, finished in 214.45 and 203.98 seconds. This variant compiles the
caller-enrolled shape parameters; it does not repeat their derivation or establish
operational enrollment. [Its boundary evidence](../research/evidence/native-proof-boundaries-2026-10-23.json)
retains an output-token alias accepted by the earlier native boundary and four
malformed-shape crashes; all now reject explicitly. The caller already rejected
that alias. No matched cross-hardware speedup or independent security review is claimed.

## Models and task

The exact seed-17 MLP and CNN checkpoints/quantized exports are now
[published on Hugging Face](MODELS.md), with model cards, pinned revisions,
file hashes and native inference examples. Publication reuses these frozen
models; it introduces no new quality evaluation or model selection.

The current combined demo uses three fixed architectures. Model weights are
public circuit constants; no model-hiding claim is made.

| Component | Model and input | Decision |
|---|---|---|
| Rule | Literal `BAD` scan, four-byte native chunks with boundary state | Marker present → block |
| MLP | 256 byte counts, four hidden ReLU units, affine output; trained seed 17 | Integer score at or above 0 → block |
| CNN | 256 × 4 byte embedding, 32 causal width-24 convolution channels, ReLU, masked global max, affine head; 4,161 learned parameters | Integer score at or above −3,733 → block |

The CNN trains in float64, then exports exact integer semantics with signed
ties-to-even rounding and conservative int32 bounds. The exported integer graph
and threshold define the proved decision. Agreement on the recorded examples is
not an equivalence theorem for all floating-point inputs.

The CNN data is authored synthetic text using a `run: action; quote: action`
grammar. Contrastive pairs swap the active and quoted action while preserving
byte counts. This tests local context that a byte-count model cannot distinguish.
Labels describe this artificial task, not real prompt injection or safety.
Source and rights declarations travel in the committed
[v2 dataset](../fixtures/contextual-scope-v2.jsonl),
[source record](../fixtures/contextual-source-v2.json) and
[protocol](../fixtures/contextual-protocol-v2.json).

The v2 dataset has 512 rows in 256 action-pair groups: 312 train, 100 calibration
and 100 test rows. The old experiment's 100 groups, including its old test, are
explicitly exploratory training data in v2. New calibration/test pairs share no
complete pair or prompt with those old groups; they still share grammar and
vocabulary. Seeds 17, 29 and 43 and the screen thresholds were fixed before test.
Seed 17 was selected for proving before its test result.

## Synthetic quality screen

Each v2 test split contains 50 positive and 50 benign examples. The predeclared
screen requires TPR ≥ 0.8 and FPR ≤ 0.1 for every seed.

| Seed | True positives | False negatives | False positives | True negatives | Screen |
|---|---:|---:|---:|---:|---|
| 17 | 50 | 0 | 0 | 50 | Pass |
| 29 | 50 | 0 | 1 | 49 | Pass |
| 43 | 50 | 0 | 0 | 50 | Pass |

Two runs reproduced 65 substantive artifact files byte for byte, including
full/resumed training artifacts, exports and predictions. They took 168.01 and
174.78 seconds on the recorded Mac. No tested float/integer decision flips occurred.
[Raw v2 evidence](../research/evidence/w16-contextual-screen-v2-2026-10-22.json).

**The first screen failed.** Its narrower CNN produced 3 false positives among
20 benign test examples for seed 43, above the all-seed screen's limit. That
failure is retained in [v1 evidence](../research/evidence/w16-contextual-screen-v1-2026-10-22.json).
The v2 protocol starts a new experiment; it does not relabel the failed result.

These small synthetic counts do not support a population 1% false-positive claim,
real-world generalization or safety-policy adoption. The MLP marker fixture is an
arithmetic/training baseline, not a competing scope-quality result. The three
combined-demo inputs are engineering cases reused from the frozen data, not a
new held-out evaluation. See the [evaluation contract](EVALUATION.md).

## Real proof composition

Two fresh campaigns used the same frozen models and three cases, with fresh
setup keys. Each campaign generated nine proofs: rule, MLP and CNN for each case.
A separately implemented py-ecc verifier checked the exact caller-reconstructed
public inputs. The caller-side controller still supplies the trusted mapping
between model, program, circuit and key.

| Measure | Recorded result |
|---|---|
| Original proofs | 18 total; all verified |
| Three-proof sets | 6 total; expected all-pass decisions matched |
| Cross-request substitutions | 36 rejected |
| Separate arithmetic corpus | 810 cases matched expected outcomes |
| Reproduction | Both models, all three circuits and decisions matched |
| Setup keys | Six distinct verification keys across the two campaigns |
| Prompt capacity | 0–96 UTF-8 bytes; larger inputs reject |
| Proof encoding | 292 bytes per proof; verification key 5,536 bytes |

Per classifier and campaign, the arithmetic corpus has four accepted controls,
109 algebraic rejections and 22 malformed-input rejections. Accepted controls
include jointly negated Groth16 A/B points, which preserve their pairing. Proof
byte uniqueness is not an acceptance requirement.

| Circuit | Constraints | Scope |
|---|---:|---|
| Rule | 321,617 | Complete admitted prompt and literal decision |
| Trained MLP | 325,123 | Complete admitted prompt and learned integer graph |
| Trained CNN | 975,708 | Complete admitted prompt and learned integer graph |

All use dedicated gnark Groth16/BLS12-381 circuits. There is no general-purpose
zkVM. A 292-byte proof is not a 292-byte evidence bundle: keys, enrollment,
expectations, openings and model metadata are separate.

## Measured cost

Recorded host: Apple M4 Max, 48 GiB RAM, macOS arm64. Proof workers use at most
four threads; training uses one BLAS/OpenMP thread. These two local observations
are not a throughput benchmark or a latency distribution.

| Combined campaign | Wall time | Peak worker RSS | Retained output |
|---|---:|---:|---:|
| 1 | 882.75 s | 2.134 GB | 2.575 GB |
| 2 | 869.34 s | 2.143 GB | 2.575 GB |

GB here is decimal. Time includes fresh setup, proof generation, separate
verification and mutation checks. It excludes dependency acquisition, training
and any real LLM inference or hardware path. Peak worker RSS is not total machine
memory. New cloud compute cost for these campaigns was zero.

[Complete composition evidence](../research/evidence/w28-trained-common-proofs-2026-10-22.json)
contains input identities, raw numeric costs, per-worker records and failure notes.
The earlier [CNN proof campaign](../research/evidence/w18-contextual-cnn-proofs-2026-10-22.json)
also tested capacity boundaries and invalid witnesses. The
[trained MLP campaign](../research/evidence/w18-trained-mlp-proofs-2026-10-22.json)
retains its separate 8/1,024-byte experiments; those capacities do not enlarge the
combined demo's 96-byte limit.

## Walkthrough reproduction

The [documentation reproduction](../research/evidence/docs-demo-reproduction-2026-10-22.json)
ran all nine shell blocks in the [original demo guide](https://github.com/AbdelStark/hallmark/blob/7e7eab1c1c514d7e584e44f811af7fe80574a42e/docs/DEMO.md) from a fresh worktree,
including a fresh toolchain download, both training runs and new setup keys.
Nine proofs verified, all three decisions matched, 18 cross-request substitutions
rejected and 405 arithmetic cases matched. Models and circuits match the original
composition study above. Source hashes remained unchanged throughout execution.
This is an additional engineering reproduction, not new held-out quality evidence
or a controlled performance benchmark.

The [one-command reproduction](../research/evidence/e2e-entrypoint-2026-10-22.json)
then ran `make e2e` with the same frozen inputs. It passed the same nine proofs,
18 substitution rejections and 405 arithmetic outcomes, with matching model and
circuit identities. The driver took 19.20 minutes including pinned
preparation and training; the proof campaign took 15.93 minutes.
These remain engineering observations, not an additional quality study.

## What remains open

- **Qualification:** authenticated compiler/program mapping, key enrollment,
  setup custody and independent security/hiding review.
- **Operational verification:** an admitted B1 adapter and full acceptance path;
  the research binding helper is not a production acceptance API.
- **Model quality:** admitted real-data evaluation, stronger contextual models,
  longer inputs and task-matched operating points.
- **Hardware and inference:** genuine hardware evidence, protected model execution
  and response generation, B2 and full hybrid composition.

The demo always reports `qualified_backend: false` and
`hardware_claim: "not-accepted"`. Software conformance currently matches 156 cases
and reports 32 full-evidence obligations unavailable. Proof experiments add
specific research evidence; they do not silently satisfy those missing obligations.
See [STATE](../research/STATE.md) for the next gate and [SECURITY](../SECURITY.md)
for the trust boundary.
