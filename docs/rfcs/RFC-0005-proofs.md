# RFC-0005: Real proof qualification and bounded adapters

- Status: Draft
- Authors: @AbdelStark (owner; engineering draft for review)
- Created: 2026-10-20
- Target milestone: v0.3

## Summary

Qualify a real existing proof backend against exact integer programs and complete public inputs before enrolling it. Implement separate rule, MLP and encoder proof tasks; no mock path can produce a v1 proof result.

## Motivation

[PRD G2](../../research/source/product-requirements.txt) requires cryptographic execution evidence. A graph import, witness check or hash replay is not that evidence.

## Goals

- Independently verify real proofs under externally enrolled keys.
- Bind the complete context, classifier, input digest, coverage and verdict.
- Measure setup, witness, proving, verification, failures and memory.

## Non-Goals

- A new proof system, recursive aggregation, hidden classifier weights or unapproved proving runs.

## Proposed Design

W06 implements `ProofInputs` packing and proof-container schemas in
[decision 0009](../decisions/0009-receipt-evidence-contracts.md). These are structural
checks; no proof adapter or acceptance path is supplied.

Use the [prove/verify interfaces](../spec/02-public-api.md#v1-supported-interfaces). Each backend runs as a bounded child process with argv arrays, a fresh private working directory, fixed environment and no inherited credentials/network. Parent enforces wall time and termination of descendants; worker resource controls and their platform limitations are recorded. Success requires expected files and a fresh independent verifier invocation, not a zero process exit alone.

`BackendQualification={schema_id:"hallmark/backend/1", source:Digest, dependencies:List[FileRef], build:Digest, proof_system:Id, security_parameters:FileRef, zero_knowledge:bool, setup:Digest, supported_programs:List[Digest], public_input_layout:FileRef, verifier:Digest, license_review:Digest, security_review:Digest, conformance:Digest, costs:Digest}`. No unspecified defaults enter setup or verification. `zero_knowledge` must be true for v1 private-witness claims. Record setup lineage and whether trusted setup is required; a generated parameter file is not an independently trusted setup.

The record and caller-pinned dependency/metadata file checks are implemented in
`hallmark.backend`; see [decision 0023](../decisions/0023-backend-declaration-contract.md).
This is structural binding only. The runner, whole-graph evidence and semantic
security/setup admission remain open; no true field can substitute for them.

Public input layout serializes `ProofInputs` in fixed field order. Pack each 32-byte digest as 32 byte-range-constrained field elements; never reduce a digest modulo the scalar field. Booleans constrain to 0/1; counts are range-constrained U64 and within the admitted profile; signed int32 thresholds use a specified offset encoding `x+2^31`, range 0..2^32−1. Layout is part of backend identity. Native and circuit adapters reject aliases.

The relation checks program/key/setup identity, full salted input commitment, chunk count/masks/indices, exact integer operations/ranges, max aggregation and strict threshold. Context is a public interaction binder; B1 independently connects the input digest to context's transcript, while B2 relies on the attested receipt's link. No claim that a free context field alone proves the transcript opening is allowed.

Qualification order: tiny byte/rule graph, bounded MLP, one encoder operator block, complete encoder at empty/near-boundary/maximum admitted length. Record unsupported operators and failures. Candidate selection uses correctness, hiding, reviewability, licence, independent verification and full cost under a frozen budget; convenience or parameter count alone cannot select it. A failed full graph does not inherit a successful tiny graph's qualification.

Proof artifacts include exact backend/key identities and public inputs. The verifier obtains the enrolled key from trusted artifacts, not a key supplied only beside the proof. Save all failed attempts; one retry only for explicitly transient worker failures within the original total budget.

## Alternatives Considered

A general VM may simplify semantics but incur tensor cost; an arithmetic graph backend may be efficient but has compiler/operator risks. Select only after matched qualification. Host replay and simulated proofs cannot satisfy the cryptographic goal.

## Drawbacks

No specific backend is declared qualified today. Genuine setup and encoder runs may exceed current authority. Shared verifier libraries remain a common-mode risk even with an independent wrapper.

## Migration / Rollout

Implement adapter protocols and offline negative fixtures first. Admit backend source/licence/setup and resource plan before installation/runs. Enroll each actual graph/key separately; retain old evidence under its original identity.

## Testing Strategy

Verify a real proof, then mutate every digest byte, count, threshold, verdict, key and setup. Exercise negative integer values, overflow, field aliases, unconstrained padding and omitted last chunks. Kill a worker mid-write and verify no complete proof is published. Compare host/circuit intermediate values on frozen vectors and final verdicts on the entire admitted evaluation set; disclose which cases have full proofs versus witness-only checks.

## Open Questions

- OPEN QUESTION BACKEND — @AbdelStark, resolution checkpoint 2026-11-09: W18 must name a pinned reviewed backend/setup and authorized host with measured full-graph support. W19–W21 remain blocked until their graph-specific qualification passes.

## References

- [Integer RFC](RFC-0003-integer.md), [performance budget](../spec/08-performance-budget.md), [independent conformance](RFC-0009-conformance.md).
