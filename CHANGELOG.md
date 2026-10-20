# Changelog

## Unreleased

Add immutable v1 model, file-reference and greedy generation contracts, a fixed
CBOR/hash vector and JSON schema snapshot. Bind all execution-relevant fields in
the model identity. Explicit rooted file checks reject links, nonregular files,
duplicate filesystem aliases and mismatches within a caller's byte budget.
No model loading, hardware evidence or enrollment is supplied.

Require actual training-test execution in the train CI job; skips and incomplete
execution now fail `make check-train`. Check core/package and training separately
on CPython 3.12, 3.13 and 3.14. Keep CI read-only without privileged integration
hosts, secrets or artifact uploads.

Replace raw CLI failure text with versioned, sanitized error JSON. Preserve
input/argument exit 2; execution/storage/resource failures now exit 3.
Unexpected failures receive local random diagnostic IDs. Add the finite error
taxonomy and stage ordering without modifying historical run artifacts.

Add a separate bounded v1 CBOR value codec and 22 domain-separated identities,
with canonicality, type, Unicode and resource-limit rejection. Preserve all legacy
research hashes. Artifact schemas, enrollment and cryptographic verification remain
separate implementation gates.

Proposed private v1 specification: canonical index, twelve specification sections, ten RFCs and a filed implementation backlog with dependency tracker. Preserve existing runtime/evaluation semantics and historical results. Include the corpus and tracker in source distributions; no new hardware, proof or classifier-quality capability is claimed.

## 0.1.0, 2026-10-20

Private research initialization: hybrid technical specification, evaluation/data/ML research plans, bounded agent workflows, strict data/model/run contracts, synthetic marker fixture, optional trained linear baseline, exact integer inference/calibration, uncertainty reports, caller-pinned replay, conformance and tamper tests, locked packaging and CI. TEE evidence, ZK proofs, real safety evaluation and encoder training are not implemented.
