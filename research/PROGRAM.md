# Research program

Research question: can a small, useful classifier produce exact, transcript-bound verifiable decisions at an operationally useful cost, alongside an independently described hardware provenance claim? The result is a policy assay, not a proof of safety.

## Falsifiable hypotheses

| ID | Hypothesis | Required comparison | Falsification / next decision |
|---|---|---|---|
| H0 | Baseline reporting and integer semantics are internally consistent | Exact reference vectors, independent histogram arithmetic, hash tampering, calibrated replay | Any mismatch blocks further measurement; bootstrap tests cover software only |
| H1 | A compact integer student preserves useful task quality at a fixed low FPR | Task-matched existing guard, float parent, n-gram floor, held-out families | Inconclusive FPR bound or unacceptable prespecified quality loss rejects adoption |
| H2 | One chosen real backend proves the entire decision within an agreed budget | Identical graph, sequence/chunks, hardware and inputs; include setup and failure rate | Unsupported op, host/circuit mismatch or budget breach rejects that candidate |
| H3 | The hybrid binds both genuine evidence objects to the exact same interaction | Independent opening, nonce/audience/key/policy/chunk mutations | Any accepted mismatch blocks an end-to-end claim |
| H4 | Distillation improves the measured quality/cost frontier | Same train/calibration/test identities, teacher supervision ablation, paired seeds | No defensible frontier gain means keep the simpler student |

Quality, latency and memory acceptance budgets must be chosen with the relying party before H1/H2. They are not invented after results. No real-data, hardware or proof hypothesis has been tested in this bootstrap.

## Work packages and exit artifacts

1. **Foundation, implemented:** strict schemas; harmless fixture; linear fitting; integer reference; calibration/uncertainty; immutable bundles; caller-pinned replay; offline tests. Exit is reproducible software evidence, not semantic classifier quality.
2. **Admission, next:** one policy and relying-party use case; licence/source/lineage ledger; approved grouped split; powered benign test; baseline roster; frozen protocol and explicit compute budget. Exit is an owner-reviewed experiment proposal, with no downloads assumed.
3. **Operator qualification:** real backend and one small graph, bit-exact conformance, negative proof verification and full cost record. Exit is a reproduced proof statement and limits; a toy circuit does not qualify an encoder.
4. **Quality/cost frontier:** task-matched baselines, integer/float/PTQ/optional QAT, length and group slices, uncertainty and paired comparisons. Exit includes every failed candidate and a model-selection decision.
5. **Hybrid binding:** genuine TEE evidence on an authorized host; exact model manifest; proof/attestation/common-input verification; replay and downgrade rejection. Exit requires independent review, not a mocked demo.
6. **Private review packet:** short architecture/limitations memo backed by the evidence above. Public release, collaborators and deployments are separate decisions.

## Essential ablations

Quantization: float versus integer at the same fixed policy. Length: one chunk versus full max aggregation, long adversarial tails and boundary shifts. Distillation: hard labels alone versus soft teacher outputs, teacher errors and task transfer. Architecture: byte/n-gram floor versus tiny MLP versus one encoder under equal data/selection budgets. Binding: opened-text B1 versus TEE-bound B2, with the different trust assumption written explicitly. Hidden versus public weights: report proof-system cost and disclosure trade-offs without assuming hidden weights prevent adaptive attacks.

## Adaptive evaluation and stop rules

Attack with encoding/Unicode transformations, benign quoting/context, role swaps, indirect injection, long prefixes/suffixes, split harmful content, multilingual variants and classifier-aware search. Preserve parent groups and novelty lineage. An adaptive attack set created after reading test outcomes is a new evaluation set, not an unbiased retest. Keep transcript content local and approved.

Stop on evaluator mutation, licence ambiguity, unapproved data/compute, inability to reproduce a selected result, arithmetic mismatch, data contamination or missing transcript coverage. Do not rescue a failing experiment by changing threshold, removing difficult slices or excluding failed proof runs after the fact. If power is insufficient, report inconclusive and propose the additional independently sampled data needed.

## Reproducibility standard

Every substantive result identifies source revision plus dirty diff, locked environment and actual versions, dataset/split hashes, policy/threshold, checkpoint and export hashes, seeds, host/resources, full commands, raw counts/costs, exclusions/failures and evaluator revision. Repeat from a fresh directory before a confirmatory claim. A second implementation/reviewer checks critical arithmetic and binding. Agent-generated hypotheses and prose are labeled; measured results require artifacts and replay. No literature result is treated as a local result.
