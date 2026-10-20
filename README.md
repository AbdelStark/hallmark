# Hallmark

Research on transcript-bound classifier verdicts. The intended system pairs hardware-attested model provenance with independently verifiable classifier computation. A classifier pass is a result under a fixed policy, not evidence of safety in the world.

## Implemented now

The repository is public; packages are unpublished and no open-source licence
has been adopted. See [licence status](LICENSE.md).

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
expectations. The [prototype `inj.direct/1` study](docs/decisions/0019-approved-study-scope.md)
is approved; actual assets, measurement admission and production policy adoption
remain separate gates.

The [data import API](docs/decisions/0021-lineage-data-admission.md) checks pinned
source/review bytes, preserves raw-row provenance and groups connected lineage
before splitting. Its 26-row marker fixture retains contrastive examples.
It does not authenticate human review or establish real-data quality.

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

The [registry authoring API](docs/decisions/0012-registry-authoring-rotation.md)
signs reviewed snapshots, retains complete local history and enforces irreversible
retirement. Key rotation requires both old and new thresholds and externally supplied
policies. `registry-check` verifies offline files and atomically advances the checkpoint
and its trust binding. Operational key custody remains an owner gate.

The [offline bundle contracts](docs/decisions/0011-offline-bundle-contracts.md)
check embedded bytes, logical paths, declared evidence bindings and caller limits.
Openings travel separately. Collection states and reported verification results
remain distinct; parsing a reported accepted result does not verify its evidence.

The [frozen conformance corpus](docs/decisions/0013-frozen-conformance-corpus.md)
checks 156 software cases and reports 32 unavailable hardware/proof obligations.
`make check-conformance` checks software scope and its failure self-tests.
The full-evidence gate remains incomplete; there is no independent verifier.

The [package gate](docs/PACKAGING.md) compares two builds under a pinned toolchain,
checks exact source/archive inventories and exercises fresh installed core/train
contracts. [Dependency notices](docs/DEPENDENCIES.md) are recorded separately
from project release approval.

The [private event log](docs/decisions/0015-private-event-storage.md) retains
allowlisted stage events and failed attempts, with bounded storage and durable
completion checks. It has no telemetry; metadata stays under the run's private
retention policy. Full-path cost measurement remains separate work.

The [native byte-count MLP](docs/decisions/0014-integer-mlp-runtime.md) now executes
bound affine/ReLU/affine exports with exact signed rescaling, full prompt coverage
and strict threshold comparison. Fixed and generated vectors check every layer.
This supplies native arithmetic, not trained-policy quality or a proof.

The optional [MLP trainer](docs/decisions/0027-record-level-mlp-training.md) fits
one loss per complete record, resumes pinned optimizer checkpoints and exports
the native integer graph. Its three-seed marker fixture checks numerical and
resume behavior; see the [fixture command](docs/OPERATIONS.md#mlp-training-fixture).
The [grouped comparison pipeline](docs/decisions/0028-grouped-baseline-selection.md)
adds pass/block controls, the preserved byte-logistic floor, exact-text character
n-grams, five train-internal folds and separate native calibration/evaluation.
Guard runtime integration and admitted real-data evaluation remain unfinished.

The [literal byte-rule runtime](docs/decisions/0020-complete-byte-rule.md) scans
every prompt byte with bounded state across chunk boundaries. It binds exact
patterns/provenance and blocks score one at threshold one. Independent complete-byte
oracle tests cover early, spanning and late matches. The marker patterns establish
matching behavior only; no general injection detection or proof is claimed.

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

Contributor setup, required checks and evidence boundaries are in
[CONTRIBUTING](CONTRIBUTING.md). `make check-spec` checks local anchors and
requirement coverage; the [explicit live audit](docs/SPEC-CHECK.md) checks issue metadata.
