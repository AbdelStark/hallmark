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

The [C1 reference run](REFERENCE-RUN.md#c1-default-classifier-workflow) uses the
same frozen models and three cases. It generates nine Circle STARK proofs: rule,
MLP and CNN for each case. Fresh proof-only verifiers check them, and the run
rejects 63 changed public inputs, 18 cross-request substitutions and three
invalid rosters. The caller-side controller still supplies the trusted mapping
between model, program, circuit and enrollment. Inputs are limited to 0–96 UTF-8
bytes; larger inputs reject. [Circle classifier details](CIRCLE-CLASSIFIERS.md).

## What remains open

- **Qualification:** authenticated compiler/program mapping, preprocessing
  enrollment and independent security/hiding review.
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
