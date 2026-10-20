# RFC-0009: Negative corpus and independent verification

- Status: Draft
- Authors: @AbdelStark (owner; engineering draft for review)
- Created: 2026-10-20
- Target milestone: v1.0

## Summary

Freeze a versioned valid/negative corpus and require a separately implemented verifier to agree on every case. Keep software vectors, genuine hardware evidence and real proofs separately labeled.

## Motivation

[PRD G4 and M4](../../research/source/product-requirements.txt) explicitly require independent implementation and rejection of negative cases. Sharing the reference evaluator with replay cannot meet that requirement.

## Goals

- A mechanical expected result for every named failure mode.
- Complete corpus agreement with implementation provenance.
- Real end-to-end evidence for hardware/proof composition.

## Non-Goals

- Certifying all possible adversarial behavior or independently proving the soundness of an underlying proof library.

## Proposed Design

W33 implements the bounded primary component corpus and explicit unavailable
evidence obligations in [decision 0013](../decisions/0013-frozen-conformance-corpus.md).
Its software-only gate does not satisfy the full comparison gate below. W34's
independent implementation and W35's genuine hybrid evidence remain absent.
The implementation adds named component checks, mutation descriptions, expected
digests/integers and missing-dependency IDs to `Case`; the exact current records
are in the [schema snapshots](../schemas/conformance-case-v1.json).

`Case={schema_id:"hallmark/conformance-case/1", case_id:Id, parent:Optional[Id], evidence_class:Literal["software-vector","real-proof","real-hardware","hybrid"], inputs:List[FileRef], trust:Digest, expected_request:Digest, now:U64, expected:{accepted:bool, claim_a:Id, claim_b:Id, code:Optional[Id]}, requirement:Id}`. Cases are immutable; the corpus manifest sorts case IDs and hashes every input. Security failures need a minimal one-field mutation and its expected code.

Cover every [error-table](../spec/04-error-model.md#contract-and-ordering) rejection plus the original packet's altered prompt/response, swapped model file, unregistered model, classifier swap, threshold swap, replay, chain break, wrong salt, tokenizer swap, late payload, false gateway pass, different-receipt proof, retired policy and debug quote. A receipt-chain check uses a separately supplied expected predecessor when continuity is claimed; a single offline receipt does not establish global history.

Independent implementation starts from the frozen spec and public harmless vectors, in `independent/`, with its own parser, commitment, input preparation, integer, policy and result code. Prefer a separate runtime/language; if Python is used, no imports from the primary implementation are allowed. Record source/dependency provenance and reviewer attestation of that separation. A shared proof verifier is explicitly disclosed.

The comparison harness executes both programs with identical enrolled trust/request/time and compares full claim status, codes and input digests; intermediate integer vectors are checked too. Result schema is `{corpus:Digest, primary:Digest, independent:Digest, cases:List[{case_id:Id, primary:Id, independent:Id, match:bool}], unavailable:List[Id]}`. Exit nonzero on mismatch or any required unavailable case.

Real-hardware/proof cases are produced only on admitted hosts and stored in approved local evidence paths. Offline CI may check harmless fixture structure, but unavailable real cases cannot be counted as passed. At v1 acceptance an owner-reviewed report must identify every actual executed case and artifact identity.

## Alternatives Considered

Duplicating the primary verifier's calls gives differential plumbing coverage but preserves the same logical bugs. Fuzzing alone misses stable interoperability vectors. A mock hardware signature cannot demonstrate the measured execution path.

## Drawbacks

Independent implementation and review are substantial work. Shared cryptographic libraries can retain common-mode failures. Passing a finite corpus establishes tested conformance, not exhaustive security.

## Migration / Rollout

Freeze v1 vectors before implementations, permit corrections only through decisions and new corpus IDs, and never rewrite old results to match changed expectations. Keep existing software tests as a separate baseline.

## Testing Strategy

Self-test the comparison harness with one deliberately wrong result and one unavailable required case. Add every mutation listed above, plus parser bounds, key rotation and B1/B2 trust transitions. Reproduce the entire genuine hybrid suite from fresh directories with independently supplied trust.

## Open Questions

- OPEN QUESTION INDEPENDENCE — @AbdelStark, resolution checkpoint 2026-11-09: designate a permitted independent implementer/reviewer and record separation rules in W34. New collaborators or sharing require specific approval; until then the gate remains blocked.

## References

- [Testing strategy](../spec/07-testing-strategy.md), [wire](RFC-0001-wire.md), [composition](RFC-0007-verifier.md).
