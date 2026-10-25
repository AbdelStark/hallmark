# Hallmark v1 specification

Original proposed private POC, 2026-10-20. Hallmark binds hardware-attested model provenance and real classifier proofs to one exact interaction. A classifier pass is a policy result, never a safety guarantee. At that date, the 0.1.0 package implemented offline research fixtures and replay.

The owner selected the [LLM integrity MVP](docs/MVP.md) for current completion
on 2026-10-25. This original private-v1 contract and its unmet requirements stay
preserved as future work; see [decision 0076](docs/decisions/0076-integrity-mvp-scope.md).

## Read order and authority

Read the overview, relevant section and RFC, then its work item. RFCs are concrete drafts awaiting owner review. [Decision 0002](docs/decisions/0002-v1-specification-scope.md) records scope and publication authority. [Baseline SPEC](docs/SPEC.md) continues to define existing arithmetic/research artifacts; new v1 identities do not reinterpret old runs. [STATE](research/STATE.md) and [LEDGER](research/LEDGER.md) describe actual evidence. The [source packet](research/source/README.md) preserves original intent without turning historical estimates into results.

## Specification sections

- [Thesis, scope and acceptance](docs/spec/00-overview.md)
- [Boundaries and data flow](docs/spec/01-architecture.md)
- [Caller contracts and compatibility](docs/spec/02-public-api.md)
- [Schemas and named invariants](docs/spec/03-data-model.md)
- [Failure taxonomy and recovery](docs/spec/04-error-model.md)
- [Redaction, events and costs](docs/spec/05-observability.md)
- [Trust and threat boundaries](docs/spec/06-security.md)
- [Conformance and evidence gates](docs/spec/07-testing-strategy.md)
- [Resource caps and profiling](docs/spec/08-performance-budget.md)
- [Private release and dependency policy](docs/spec/09-release-and-versioning.md)
- [Canonical language](docs/spec/10-glossary.md)
- [Requirement-to-work coverage](docs/spec/11-requirements.md)

## RFC index

| RFC | Decision | Status |
|---|---|---|
| [0001](docs/rfcs/RFC-0001-wire.md) | Versioned wire objects and transcript binding | Draft |
| [0002](docs/rfcs/RFC-0002-registry.md) | External enrollment and signed registry history | Draft |
| [0003](docs/rfcs/RFC-0003-integer.md) | Complete inputs and exact integer classifiers | Draft |
| [0004](docs/rfcs/RFC-0004-ml.md) | Admitted data and frozen classifier evaluation | Draft |
| [0005](docs/rfcs/RFC-0005-proofs.md) | Real proof qualification and bounded adapters | Draft |
| [0006](docs/rfcs/RFC-0006-hardware.md) | Genuine attestation and measured release control | Draft |
| [0007](docs/rfcs/RFC-0007-verifier.md) | Receipt lifecycle and independent claim composition | Draft |
| [0008](docs/rfcs/RFC-0008-operations.md) | Redacted failures and reproducible cost accounting | Draft |
| [0009](docs/rfcs/RFC-0009-conformance.md) | Negative corpus and independent verification | Draft |
| [0010](docs/rfcs/RFC-0010-release.md) | Private reproducible delivery and review | Draft |

## Execution boundary

v1 retains genuine confidential serving, rule/MLP/encoder proofs, B1/B2, independent verification and private reviewer reproduction. [The work map](docs/spec/11-requirements.md) covers every implementation deliverable. Current code is not v1. Data/model access, paid or GPU compute, hardware hosts, collaborators, policy adoption and release remain explicitly admitted actions. This specification publication authorizes none of those by implication.

## Implementation tracker

The [live implementation tracker](docs/roadmap/IMPLEMENTATION.md) links all 40 work issues, 10 subsystem trackers, dependencies and owned open questions.
