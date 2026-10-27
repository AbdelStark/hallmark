# Research evidence map

Use the records below to check model and input identities, measurements and
failed attempts behind the reported results.

## Current scope

The fixed-case LLM integrity MVP proves a short quantized TinyLlama response
and composes exact classifier relations over the same request. It does not
claim witness hiding, hardware
provenance, arbitrary-model support or independent security qualification.

[MVP acceptance matrix](../MVP.md) · [Current state](../../research/STATE.md) ·
[Chronological ledger](../../research/LEDGER.md)

## Follow a result to its source

| Claim | Evidence | Scope and limits |
|---|---|---|
| Generated-constraint CUDA proves the complete fixed case | [GPU JSON](../../research/evidence/llm-gpu-generated-constraints-2026-10-26.json), [protocol and measurements](../GPU-BENCHMARK.md#generated-constraint-result) | One same-H200 SIMD/CUDA pair; CPU witness generation; retained failed telemetry attempt |
| Earlier CUDA configuration was slower | [Fallback-baseline JSON](../../research/evidence/llm-gpu-benchmark-2026-10-26.json) | Real proofs, but 1,710 CPU constraint fallback calls |
| Fresh CPU-only LLM workflow reproduces the response | [Reproduction JSON](../../research/evidence/llm-e2e-reproduction-2026-10-23.json), [LLM guide](../LLM-PROOF.md) | Fixed model/quantization/token case, not arbitrary prompts |
| Dedicated classifier proofs bind one request | [Composition JSON](../../research/evidence/w28-trained-common-proofs-2026-10-22.json), [results](../RESULTS.md#real-proof-composition) | Synthetic task, fresh research setup, caller-enrolled mapping |
| Exact classifiers work under both proof backends | [Matched CPU report](../CLASSIFIER-BENCHMARK.md), [all raw samples and hashes](../../research/evidence/circle-classifiers-benchmark-2026-10-27.json) | 144 measured proofs, fresh Mac postflight and Circle/LLM join; stateless harness, different security profiles, 96-byte synthetic scope |
| Released weights match the proved models | [Publication receipt](../../research/evidence/hub-model-publication-2026-10-27.json), [model releases](../MODELS.md) | No new training or quality evaluation; native inference is not proof generation |

## H200 timing boundaries {#read-the-h200-result-correctly}

The matched pair records **547.75 s SIMD / 53.94 s CUDA** summed proving,
and **679.49 / 155.89 s** complete segment commands. The ratios are
**10.15×** and **4.36×** respectively.

Both use the same host, inputs, parameters and four Rayon threads. All 69
proof/statement/claim files match. CUDA records zero CPU constraint fallback.

The outer cached-build workflow takes **34 min 47 s**, because it includes both
backends, grid checks, transfers and fresh CPU/Mac verification. That is a
different boundary from 53.94 s. The separate original CPU-only workflow used
a different 32-vCPU host; do not use its latency as the GPU comparison baseline.

[Full timing/resource table and caveats](../GPU-BENCHMARK.md#generated-constraint-result)

## Classifier evaluation {#quality-evidence-is-a-different-axis}

The contextual CNN has a prespecified synthetic study with three seeds and
100 test rows per seed. The MLP is an arithmetic/marker fixture with no held-out
quality result. The three proof-demo cases are engineering controls, not a new
test set.

The source grammar/vocabulary is shared across synthetic splits. The earlier
CNN screen failed and is retained. Real-world safety performance has not been
evaluated; the reported scores cover the synthetic task.
[Read the model/data notes](../RESULTS.md) and [evaluation contract](../EVALUATION.md).

## Open research and qualification

- Independent backend/security/hiding qualification and setup/enrollment custody.
- General prompts/models and a reviewed numerical equivalence boundary.
- Authentic capture, hardware provenance and the broader proposed hybrid system.

The [proposed v1 specification](../../SPEC.md) is a design target beyond the
completed MVP. Check the [supported API table](../spec/02-public-api.md) before
using an interface from that specification.

## Reproduction principles

Freeze model/data/evaluator identities before measurement. Keep calibration and
test roles separate. Save raw numbers, hashes, environment and failure records
before a narrative. A new candidate does not get to change its evaluator.
[Operations](../OPERATIONS.md) and [CONTRIBUTING](../../CONTRIBUTING.md) explain
the work loop.
