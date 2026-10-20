# Hallmark

Private research on transcript-bound classifier verdicts. The intended system pairs hardware-attested model provenance with independently verifiable classifier computation. A classifier pass is a result under a fixed policy, not evidence of safety in the world.

## Implemented now

An offline research foundation: strict data/config/model contracts, exact group and transcript leakage checks, canonical research commitments, byte-exact transcript openings, a trained linear floor baseline, an integer reference runtime, calibration on a separate split, uncertainty-aware reports, immutable run directories and caller-pinned artifact replay. The committed fixture is harmless synthetic plumbing data. No actual TEE evidence, signed registry, ZK proof, encoder fine-tune or safety benchmark is implemented or claimed.

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

Private initialization is not an open-source release. [Licence status](LICENSE.md), [contributing](CONTRIBUTING.md), [security and evidence boundaries](SECURITY.md).
