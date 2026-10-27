# Contributing

Hallmark is MIT-licensed research software. To try it first, follow the
[demo walkthrough](docs/DEMO.md). For a code or documentation contribution,
read [AGENTS.md](AGENTS.md), [STATE](research/STATE.md), the [canonical spec](SPEC.md)
and the relevant RFC/work item before changing behavior. The project licence does
not change third-party data/model terms or authorize paid compute, operational keys or access to private
research material. Keep the repository public unless the owner explicitly asks otherwise.

## Setup and checks

Use the locked environment on CPython 3.12, 3.13 or 3.14. Linux and macOS CI run
core/package and required-training/installed-train checks separately.

```sh
uv sync --locked
make check-spec
make check
make package-check
```

For changes to fitting, calibration, evaluation or installed training:

```sh
make check-train
make package-check-train
```

Training uses only the harmless local fixture with one BLAS/OpenMP thread. A core
environment may skip optional training; the required train gate fails on a skip.
The [package guide](docs/PACKAGING.md) explains retained build outputs and limits.
No system-package installation, dataset/model download or remote model code is
part of this workflow.

## One work item per PR

For documentation and site changes, use `make docs` for a strict build and
generated-link checks, and `make docs-serve` for a local preview. Stage new
documentation/asset paths explicitly before building; the site deliberately
excludes untracked files and ignored research runs. The optional toolchain has
its own lockfile, preserving inference/verifier identities. See the
[site maintenance guide](docs/DOCUMENTATION.md) for source layout and deployment.

Choose an actionable item from the [tracker](docs/roadmap/IMPLEMENTATION.md).
Check its actual issue and dependencies; a tracker status is a dated observation.
Link the requirement, RFC and issue in the PR. State the behavior change, exact
validation commands/results and remaining limitations. Exercise the negative path.
Commit reviewed paths only and preserve unrelated work. An issue closes when its
acceptance evidence exists; a blocked real-resource gate cannot be replaced by a fixture.

`make check` includes the offline [specification gate](docs/SPEC-CHECK.md).
When changing a requirement, update its coverage entry, work map, tracker and
live issue together. Run the explicit read-only live audit before publication:

```sh
uv run --locked python scripts/check_spec.py --live --output /tmp/hallmark-spec-audit-new.json
```

Choose a fresh output name for each audit. It needs authenticated `gh` read access;
normal tests/CI do not contact GitHub. The audit records metadata and body hashes,
not approval or proof that an issue's scientific criteria passed.

Protocol/evaluator changes need a decision, owner review and updated conformance
tests; a changed protocol starts a new experiment identity. Keep the historical
source packet, frozen corpus and previous results intact. Review the
[implemented versus proposed API](docs/spec/02-public-api.md),
[security boundary](SECURITY.md) and [release gates](docs/spec/09-release-and-versioning.md).

Never commit private transcripts, checkpoints, credentials or local runs. Preserve
failed experiments outside git and record safe numeric evidence in the ledger.
New dependencies need a concrete need and licence/supply-chain review. Sending
messages, adding collaborators, sharing private material and publishing a package
need specific authority; the active backlog instruction authorizes its scoped
issue/PR bookkeeping, not those other actions.
