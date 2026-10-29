# RFC-0007: Receipt lifecycle and independent claim composition

- Status: Draft
- Authors: @AbdelStark (owner; engineering draft for review)
- Created: 2026-10-20
- Target milestone: v1.0

## Summary

Collect all required genuine evidence into a bounded offline bundle and verify it under external trust and request expectations. Preserve separate claim states and never promote pending proofs to accepted results.

## Motivation

[PRD G3–G5](../../research/source/product-requirements.txt) require common-input binding, independent verification and honest claims. Individually valid objects are insufficient if they concern different interactions.

## Goals

- Deterministic B1/B2 verification with explicit partial-trust results.
- Crash-safe, bounded proof collection with no witness leaks.
- Complete rejection reasons for every identity, freshness and composition failure.

## Non-Goals

- Hosted endpoints, sampled proofs, cascades, streaming, recursive verification or traffic-completeness claims.

## Proposed Design

Receipt states are `pending → ready | failed | expired` and terminal `blocked`. Allocate a private receipt directory exclusively; encrypt its transcript/opening/witness under a per-receipt key sealed to the qualified host. Persist the signed immutable body and state journal before returning a released response. `ReceiptStore` supports `create(body,witness)`, `claim_job(id)`, `finish(id,proofs)` and `expire(id)` with one writer per receipt. A crash recovery pass checks hashes/state, never creates ready state from partial output, and resumes only within remaining budget.

Encrypt the immutable witness payload once using AES-256-GCM with a fresh 32-byte per-receipt key, a 12-byte zero nonce and associated data `encode(["hallmark/spool/1", receipt_id, expires_at])`. One key encrypts exactly one payload once; a failed initial write destroys the key and a new attempt uses a new key. This one-use rule prevents nonce reuse without a crash-sensitive counter. `SealedWitness={schema_id:"hallmark/sealed-witness/1", receipt_id:Digest, expires_at:U64, ciphertext:bytes, sealed_key_ref:Id}` keeps key material outside the ciphertext directory. Verify authentication before decoding. The qualified host must provide rollback-resistant key lifecycle/expiry state and a trusted time source; ordinary sealed files on a rollbackable disk do not meet that gate.

Every released response requests all three proofs. There is no sampled-out status in v1. A bounded foreground worker claims one job, records each attempt separately and publishes ready state only after verification of all proofs. Failed or expired jobs cannot produce an accepted bundle. On expiry destroy the per-receipt key, retain only approved redacted metadata and signed receipts. This is cryptographic access deletion, not a promise of physical erasure of every storage layer.

The assembler embeds content-addressed files and registry history, verifies every file digest and size, enforces the [bundle schema](../spec/03-data-model.md#v1-types), and atomically publishes one complete bundle. Paths are logical names; no symlink/path traversal or archive extraction. The opening is supplied separately so a B2 bundle does not accidentally disclose it.

`verify(bundle,trust,expected,now,opening)` performs:

1. Bound/parse all structures and validate current registry/history under externally enrolled roots.
2. Compare receipt expectation against the caller's audience, nonce, interaction, model and policy. Enforce time and accepted identities. If caller continuity is nonnull, compare the receipt sequence/predecessor exactly; otherwise make no history-continuity claim.
3. Check the receipt signature under its epoch key. In B1 B-only mode this checks object consistency, not trusted hardware provenance.
4. If required, verify genuine epoch evidence and its model/key/measurement bindings. If the caller selects B1 B-only and declines those roots, mark A `not-accepted`.
5. Derive the complete context from the receipt expectation and transcript commitment. In B1 require the opening, recompute transcript and all prepared inputs/digests independently. In B2 require accepted A and the signed input digest list.
6. Require exactly the policy's three ordered classifier identities; check every input threshold/count/context/key/backend/setup and verify each genuine proof. No missing, extra or duplicate classifier is allowed.
7. Compare proof verdicts with receipt verdicts and independently evaluate all-pass. A released receipt with a failing native/proven verdict is `VERDICT_MISMATCH`; a genuine blocked policy reports `POLICY_BLOCKED` when complete evidence is available.
8. Emit the versioned result and evidence hashes. Overall accepted requires all requested claims, all proofs and policy pass. Never emit a “safe” field.

All claims include residual identifiers `policy-errors`, `adaptive-evasion`, `unobserved-traffic`; A also includes `hardware-trust`, B2 B includes `hardware-input-binding`. B1 B lists `proof-soundness`, `circuit-correctness`, `registry-trust` assumptions without hardware. Proof pending is a collection result, not a valid `Bundle` with optional proofs.

## Alternatives Considered

One aggregate proof could reduce artifact count but complicates audits and setup. Accepting partial evidence is operationally convenient but obscures what the caller requested. A network-fetching verifier adds hidden availability/freshness/SSRF behavior.

## Drawbacks

B1 exposes content and needs a second tokenizer implementation. B2 is not hardware-independent. Historical offline bundles need explicit fresh trust/collateral to establish current acceptance.

## Migration / Rollout

Add `verify`, `inspect` and `registry-check` without changing research command semantics. Publish schema/error snapshots and installed CLI tests. A receipt generated by the bootstrap remains ineligible.

## Testing Strategy

Run valid B1 A+B, B1 B-only with hardware roots declined, and B2 A+B. Reject unknown mode, opening omitted in B1, opening mismatch, proof from another receipt, missing classifier, wrong threshold, nonce replay, altered audience, stale/retired policy and incorrect all-pass. Test concurrent duplicate requests, interrupted writes, one-use encryption keys, ciphertext/associated-data tampering, rollback of expiry state, bounded retry, retention expiry and collection of pending/failed jobs.

## Open Questions

- OPEN QUESTION RETENTION — @AbdelStark, resolution checkpoint 2026-11-02: approve the proposed 24-hour retention and authenticated requester/channel policy in W13/W25. Shorter retention may be selected before admission; any change is recorded, not silently applied to old receipts.

## References

- [Authenticated encryption profile](https://www.rfc-editor.org/rfc/rfc5116.html#section-5.2).
- [Public API](../spec/02-public-api.md#v1-supported-interfaces), [error model](../spec/04-error-model.md), [registry](RFC-0002-registry.md), [hardware](RFC-0006-hardware.md).
