# RFC-0002: External enrollment and signed registry history

- Status: Draft
- Authors: @AbdelStark (owner; engineering draft for review)
- Created: 2026-10-20
- Target milestone: v0.2

## Summary

Use signed complete registry snapshots with a hash-linked monotonic history and externally provisioned roots. Verification never trusts a key delivered only inside a bundle.

## Motivation

[PRD G1/G2](../../research/source/product-requirements.txt) require approved models and classifiers. A valid proof of a provider-selected weaker policy does not meet those goals.

## Goals

- Reject substituted, retired, expired and rolled-back identities.
- Support explicit key rotation and offline verification.
- Retain a reproducible enrollment decision and review provenance.

## Non-Goals

- A public transparency service, automatic trust discovery, multi-organization governance or global anti-equivocation.

## Proposed Design

Implement `enroll(snapshot, trust, state, now) -> Enrollment` using [RegistryBody, TrustPolicy and RegistryState](../spec/03-data-model.md#v1-types). Entries are sorted by `(kind,digest)` with no duplicates. A snapshot is complete, includes retired entries, and must satisfy the externally pinned threshold of distinct authorized signing keys. The POC starts with threshold 1; thresholds greater than key count are invalid.

The owner provisions trusted keys and accepted artifact identities through an existing approved private channel. Provisioning records the exact snapshot digest and sequence independently from the bundle. Verification requires sequence ≥ both the trust minimum and saved state. If sequence equals saved sequence, the digest must match; if larger, supply and verify every intermediate signed snapshot and predecessor link. Use the bundle's `history:List[SignedRegistry,0..1024]` field; excessive offline history requires a new externally enrolled checkpoint, never skipped validation. Persist new state atomically only after success.

`valid_from <= issued_at < valid_until` must hold at receipt issuance. At verification, any artifact with `retired_at <= now` is rejected even if it was historically valid. The snapshot itself must be fresh at `now`. Report historical validity separately; do not infer current revocation knowledge from stale collateral or a stale snapshot.

Rotation requires a new externally enrolled `TrustPolicy` and a transition record containing old/new key IDs, activation sequence, reason and both key-set authorizations. Compromised-key emergency recovery requires owner re-enrollment, never acceptance of an unsigned replacement. The registry authoring utility refuses changed content under an existing digest and preserves all prior snapshots.

[Decision 0012](../decisions/0012-registry-authoring-rotation.md) implements the
transition schemas, separate old/new signature tags, irreversible retirement,
local retained history and atomic checkpoint/trust updates. The offline
`registry-check` CLI is available; operational roots remain unenrolled.

A local append-only history is a review log, not a globally witnessed transparency log. Equivocation can be detected by comparing different signed roots at the same sequence; this POC does not prevent a malicious registry from splitting views. Artifact URIs, if present in human documentation, are retrieval hints only; the verifier opens only embedded or explicitly supplied files checked by digest.

## Alternatives Considered

Trust-on-first-use from a bundle is convenient but gives the prover the trust anchor. A global transparency service adds independent witnesses but creates a deployment/governance project beyond a single private relying party. A flat mutable allowlist cannot explain retirement or rollback.

## Drawbacks

Offline freshness needs a recent owner-supplied snapshot. A single registry signer remains a governance root; signatures do not validate classifier quality.

## Migration / Rollout

Introduce trust and registry schemas alongside the research config, never interpreting its allowlists as signatures. Implement authoring/verification locally, then enroll only owner-reviewed manifests. Record a new decision for any change to retirement semantics.

## Testing Strategy

Reject duplicate signer counting, unknown keys, modified entries, expired snapshots, equal-sequence unequal-digest snapshots, skipped history, retired keys/artifacts and failed state writes. Test rotation with old-only, new-only and authorized transition fixtures. Offline verification must work with networking disabled.

## Open Questions

- OPEN QUESTION REGISTRY-ROOT — @AbdelStark, resolution checkpoint 2026-11-02: designate initial signing keys, custody and approved signature-library revision. W08/W09 remain unenrolled until this private operational record exists.

## References

- [Wire/signature RFC](RFC-0001-wire.md#proposed-design), [security boundaries](../spec/06-security.md#trust-boundaries).
