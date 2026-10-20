# Release and versioning

## Private delivery gates

The package remains private and `LicenseRef-Proprietary`. A repository issue, signed manifest or installable wheel grants no permission to redistribute source, data or weights. Public release and new reviewers/collaborators need owner authorization. Review the dependency/model/data inventory with the appropriate owner; do not infer legal rights from a metadata tag.

Every release packet contains source commit plus tree hash, lock and build-environment identity, wheel/sdist hashes, artifact inventory, license/restriction inventory, conformance result, independent-verifier result, actual hosted-check status, known limitations and a changelog. Research/hardware evidence is included only through approved private access; raw transcripts and checkpoints stay outside git.

## Compatibility

Use package semantic versioning. Before 1.0 a minor bump may change experimental APIs with a migration note; patch releases do not change verdict semantics. From 1.0 incompatible caller changes require a major version. Deprecation is documented and warned for two minor releases and at least 90 days before removal, unless a security flaw requires immediate rejection with an advisory and migration.

Wire schema/domain IDs, package versions, model identities and policy versions are independent. A patch fixing security may reject formerly accepted malformed artifacts; it must not reinterpret valid older signatures under new arithmetic. Legacy research replay remains labeled as such. New protocol/evaluation semantics require a decision, owner review and updated golden/negative vectors. Prior statistical results are not reused across protocol identities without explicit revalidation.

## Dependency inventory

These are actual declared constraints and lock selections, inspected at bootstrap. They describe the current environment, not a recommendation that upstream has no newer version. The lock is authoritative for platform distributions and hashes.

| Dependency | Constraint; locked version | Reason |
|---|---|---|
| Python | `>=3.12,<3.15`; local pin 3.12 | Modern typing; 3.12/3.13 CI definitions currently exist, 3.14 support must be tested before claiming it |
| cbor2 | `>=5.6,<6`; 5.9.0 | Existing research deterministic CBOR; major change requires vectors |
| pydantic | `>=2.10,<3`; 2.14.1 | Strict schemas; reject major API drift |
| numpy | train extra `>=2,<3`; 2.5.4 | Explicit float64 fitting arrays |
| scikit-learn | train extra `>=1.6,<2`; 1.9.1 | Existing logistic floor with recorded solver |
| hatchling | build `>=1.27,<2` | Existing wheel/sdist backend; build isolation must gain an exact reviewed pin |
| mypy | dev `>=1.15,<2`; 1.20.2 | Strict source typing |
| pytest | dev `>=8.3,<10`; 9.1.1 | Offline tests |
| pytest-cov | dev `>=6,<8`; 7.1.0 | Branch coverage diagnostics |
| ruff | dev `>=0.11,<1`; 0.17.1 | Existing lint/format gate |
| uv | CI pin 0.9.18 | Existing lock/install/build commands |

Runtime transitives in `uv.lock`: annotated-types 0.8.0, pydantic-core 2.50.1, typing-extensions 4.16.0, typing-inspection 0.4.4; train dependency closure includes scipy 1.18.1, joblib 1.6.0, threadpoolctl 3.7.0, narwhals 2.27.1 and cloudpickle 3.1.2. Dev transitives are also exact in the lock. Transitive constraints are the resolved `==` versions, not independently widened ranges.

New signature, model-runtime, tokenizer, proof and hardware libraries have no admitted version yet. Their implementation issues must record exact package/source/image revisions, hashes, licence review, security review and supported Python/platforms before installation. Qualification decides the finite dependency set; no `latest`, remote model code, dynamic code fetch or unpinned fallback is allowed. This is an explicit admission gate, not a claim of a completed integration.

## Contributor and automation workflow

Use one bounded PR per work item, link its requirement and RFC, and attach the exact validation command/result. Owners review protocol, arithmetic, evaluation and security changes. PR CI is read-only, offline except locked package installation, and never runs untrusted code on a privileged hardware host. Optional integration jobs run only after explicit admission on an isolated approved host.

Package and docs checks must include root SPEC, all sections/RFCs and the roadmap in the sdist. The wheel contains code/type metadata only, with no fixtures or private evidence. `make check-spec` must validate internal anchors, RFC templates, requirement coverage and tracker links. The private release checklist requires hosted tests on the final commit; billing-blocked jobs remain a blocking dependency, not a software pass.
