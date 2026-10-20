# Hallmark

Research on transcript-bound classifier verdicts. The intended system pairs hardware-attested model provenance with independently verifiable classifier computation. A classifier pass is a result under a fixed policy, not evidence of safety in the world.

## Implemented now

An offline research foundation: strict data/config/model contracts, exact group and transcript leakage checks, canonical research commitments, byte-exact transcript openings, a trained linear floor baseline, an integer reference runtime, calibration on a separate split, uncertainty-aware reports, immutable run directories and caller-pinned artifact replay. The committed fixture is harmless synthetic plumbing data. No actual TEE evidence, operational registry, ZK proof, encoder fine-tune or safety benchmark is implemented or claimed.

The separate [v1 model manifest API](docs/spec/02-public-api.md#v1-supported-interfaces)
binds ordered files, architecture, tokenizer, template, runtime and greedy generation
settings. Explicit rooted file checks reject links and mismatches. This does not
load a model or attest to execution; [schema and limits](docs/decisions/0005-model-manifests.md).

The [classifier contract API](docs/decisions/0006-classifier-contracts.md) binds
input recipes, integer graph metadata and classifier identities. Supplied hashed
operator files are checked for topology, shapes, masks, scales and conservative
range bounds. This is static validation; classifier execution and proof/backend
qualification remain separate work.

The [policy/request contracts](docs/decisions/0007-policy-request-contracts.md)
resolve the ordered classifier set and compare requests with explicit caller
expectations. `inj.direct/1` remains a proposed policy pending admission.

The [v1 opening helpers](docs/decisions/0008-transcript-input-openings.md) bind exact
transcript bytes, caller context and complete classifier input. Portable vectors
include a separate JavaScript hash check; neither is proof or hardware evidence.

The [receipt/epoch/proof containers](docs/decisions/0009-receipt-evidence-contracts.md)
check declared identities, time intervals and public-input packing. They do not
verify signatures, attestations or proofs.

The [registry enrollment API](docs/decisions/0010-external-enrollment.md) verifies
Ed25519 signatures and complete successor links against external trust and a
retained checkpoint. A local SQLite transaction persists verified state and rejects
stale writers. [Provisioning](docs/OPERATIONS.md#external-registry-checkpoint-provisioning)
requires owner-approved roots; the shipped keys are public test fixtures.

The [offline bundle contracts](docs/decisions/0011-offline-bundle-contracts.md)
check embedded bytes, logical paths, declared evidence bindings and caller limits.
Openings travel separately. Collection states and reported verification results
remain distinct; parsing a reported accepted result does not verify its evidence.

## Run

CPython 3.12–3.14 and uv (3.12 is the default local pin). From this checkout:

```sh
uv sync --locked --extra train
make check
make check-train
uv run --locked hallmark validate-data fixtures/smoke.jsonl
uv run --locked hallmark schema experiment
uv run --locked --extra train hallmark run configs/fixture.json --output runs/bootstrap
```

The run prints the SHA-256 of its manifest. Save that hash separately, then replay:

```sh
uv run --locked hallmark audit-run runs/bootstrap --dataset fixtures/smoke.jsonl --expected-manifest <saved-sha256>
```

Choose a fresh output directory on every run. Outputs contain the integer model, predictions, calibration/test metrics, configuration, code/environment snapshot and artifact hashes. Transcript text is not copied into reports. A manifest hash enrolled from an untrusted bundle is not a trust anchor. Replay checks software arithmetic and reporting, not provenance of the historical training run.

## Start here

- [Canonical specification](SPEC.md): proposed v1 scope, typed contracts, RFCs and complete implementation work map.
- [Baseline technical contract](docs/SPEC.md): existing research commitments, arithmetic and evidence limits.
- [Research program](research/PROGRAM.md): hypotheses, controls, ablations and stop gates.
- [ML and data plan](docs/ML-PLAN.md): encoder bake-off, Laya teacher, distilled student and licence review.
- [Evaluation contract](docs/EVALUATION.md): frozen splits, thresholds, uncertainty and artifact replay.
- [Agent operations](AGENTS.md): read order, commands and bounded work.
- [Current research state](research/STATE.md): next task and what remains untested.
- [Evidence sources](research/SOURCES.md): checked primary sources and inherited research limits.

The existing hybrid design is preserved in the [source packet](research/source/README.md). New normative decisions live in this repo's specification; the imported research remains a dated design record.

## Development

`make check` runs lock, formatting, lint, strict typing, tests and local documentation-link checks. `make package-check` builds wheel/sdist and checks installed CLI/type metadata. Default tests are offline. Training is an optional extra; encoder/prover/hardware work belongs to separately admitted experiments. No automatic model downloads, hosted telemetry, paid compute or open-ended agent loop.

Public repository visibility does not change the current [licence status](LICENSE.md).
See [contributing](CONTRIBUTING.md) and [security and evidence boundaries](SECURITY.md).
