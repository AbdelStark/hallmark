# Release and versioning

## Private delivery gates

The repository is public and the owner adopted the [MIT licence](../../LICENSE.md)
on 2026-10-22. Packages remain unpublished. Third-party data, weights and software
retain their own terms; the project licence does not grant rights to those assets.
Package publication and access to private research material remain separate owner
instructions. [Decision 0063](../decisions/0063-mit-license.md) records the change;
frozen experiment records retain their historical licence labels and hashes.

Every release packet contains source commit plus tree hash, lock and build-environment identity, wheel/sdist hashes, artifact inventory, license/restriction inventory, conformance result, independent-verifier result, actual hosted-check status, known limitations and a changelog. Research/hardware evidence is included only through approved private access; raw transcripts and checkpoints stay outside git.

## Compatibility

Use package semantic versioning. Before 1.0 a minor bump may change experimental APIs with a migration note; patch releases do not change verdict semantics. From 1.0 incompatible caller changes require a major version. Deprecation is documented and warned for two minor releases and at least 90 days before removal, unless a security flaw requires immediate rejection with an advisory and migration.

Wire schema/domain IDs, package versions, model identities and policy versions are independent. A patch fixing security may reject formerly accepted malformed artifacts; it must not reinterpret valid older signatures under new arithmetic. Legacy research replay remains labeled as such. New protocol/evaluation semantics require a decision, owner review and updated golden/negative vectors. Prior statistical results are not reused across protocol identities without explicit revalidation.

## Dependency inventory

These are actual declared constraints and lock selections, inspected at bootstrap. They describe the current environment, not a recommendation that upstream has no newer version. The lock is authoritative for platform distributions and hashes.

| Dependency | Constraint; locked version | Reason |
|---|---|---|
| Python | `>=3.12,<3.15`; local pin 3.12 | CPython 3.12/3.13/3.14 core/package and required-train matrix; exact local/hosted evidence is recorded per change |
| cbor2 | `>=5.6,<6`; 5.9.0 | Existing research deterministic CBOR; major change requires vectors |
| pydantic | `>=2.10,<3`; 2.14.1 | Strict schemas; reject major API drift |
| cryptography | `==50.0.2`; 50.0.2 | Raw Ed25519 registry verification; [pre-install review](../../research/evidence/w08-dependency-review-2026-10-20.json) |
| numpy | train extra `>=2,<3`; 2.5.4 | Explicit float64 fitting arrays |
| scikit-learn | train extra `>=1.6,<2`; 1.9.1 | Existing logistic floor with recorded solver |
| hatchling | build `==1.32.4` | Exact backend plus all five build transitives in `build-system.requires` and the locked build group |
| mypy | dev `>=1.15,<2`; 1.20.2 | Strict source typing |
| pytest | dev `>=8.3,<10`; 9.1.1 | Offline tests |
| pytest-cov | dev `>=6,<8`; 7.1.0 | Branch coverage diagnostics |
| ruff | dev `>=0.11,<1`; 0.17.1 | Existing lint/format gate |
| uv | CI pin 0.9.18 | Existing lock/install/build commands |

Runtime transitives in `uv.lock`: annotated-types 0.8.0, pydantic-core 2.50.1, typing-extensions 4.16.0, typing-inspection 0.4.4; train dependency closure includes scipy 1.18.1, joblib 1.6.0, threadpoolctl 3.7.0, narwhals 2.27.1 and cloudpickle 3.1.2. Dev transitives are also exact in the lock. Transitive constraints are the resolved `==` versions, not independently widened ranges.

The signature dependency's exact transitives are cffi 2.1.1 and pycparser 3.11;
the linked review records all distribution hashes, licence metadata, target
platforms and primary advisory sources. This software selection is not approval
for operational signing-root custody. New model-runtime, tokenizer, proof and
hardware dependencies require explicit admission. Reviewed proof/guard dependencies
are recorded in the [dependency inventory](../DEPENDENCIES.md) and
[probe guide](../../research/probes/gnark/README.md). Their implementation issues must record exact package/source/image revisions, hashes, licence review, security review and supported Python/platforms before installation. Qualification decides the finite dependency set; no `latest`, remote model code, dynamic code fetch or unpinned fallback is allowed. This is an explicit admission gate, not a claim of a completed integration.

## Contributor and automation workflow

Use one bounded PR per work item, link its requirement and RFC, and attach the exact validation command/result. Owners review protocol, arithmetic, evaluation and security changes. PR CI is read-only, offline except locked package installation, and never runs untrusted code on a privileged hardware host. Optional integration jobs run only after explicit admission on an isolated approved host.

Package and docs checks must include root SPEC, all sections/RFCs and the roadmap in the sdist. The wheel contains code/type metadata only, with no fixtures or private evidence. `make check-spec` now validates internal anchors, RFC templates, requirement coverage and tracker links; the explicit [live audit](../SPEC-CHECK.md#live-issue-audit) checks current GitHub metadata. Offline CI does not establish current issue state. The private release checklist requires hosted tests on the final commit; billing-blocked jobs remain a blocking dependency, not a software pass.


## Implemented reproducible package gate

W37 / #38 adds `make package-check` and `make package-check-train` with two
independent source builds under a fixed epoch and recorded build environment.
The wheel rebuilt from the sdist must also match. The gate checks exact source/
archive inventories, bounded safe members, wheel RECORD hashes and recognizable
credential patterns, then installs hash-pinned dependencies and the built wheel
in fresh environments. Core and optional training remain separate gates.

See [build operation and evidence](../PACKAGING.md), the [actual licence inventory](../DEPENDENCIES.md)
and [decision 0016](../decisions/0016-reproducible-packaging.md). This does not
produce the release manifest, reviewer approval or hardware/proof evidence above.
