# RFC-0006: Genuine attestation and measured release control

- Status: Draft
- Authors: @AbdelStark (owner; engineering draft for review)
- Created: 2026-10-20
- Target milestone: v0.3

## Summary

Bind a confidential serving instance's epoch key, actual loaded model, accelerator and complete response path using genuine platform evidence. Native integer classifiers gate release inside that measured boundary.

## Motivation

[PRD G1](../../research/source/product-requirements.txt) is about which model produced the response. Measuring a loader or signing a receipt alone does not establish that predicate.

## Goals

- Verify CPU and accelerator evidence, collateral, freshness and accepted measurements.
- Prevent weight replacement, debug operation and bypass of native gating.
- Make platform assumptions and evidence gaps explicit in claim A.

## Non-Goals

- Multi-node serving, physical-security certification, pure-ZK model inference or buying a host under bootstrap authority.

## Proposed Design

Use [EpochRecord and ModelManifest](../spec/03-data-model.md#v1-types). The host qualification fixes one confidential VM/accelerator platform, exact firmware/runtime measurements and a pinned offline evidence verifier. `HardwareQualification={schema_id:"hallmark/hardware-qualification/1", platform:Id, image:Digest, loader:Digest, runtime:Digest, roots:List[Digest], collateral_policy:FileRef, device_binding:FileRef, verifier:Digest, host_authority:Digest, negative_report:Digest}`.

The measured process generates its Ed25519 epoch key internally. Define `epoch_challenge=H("epoch",[epoch_id,public_key,model_digest,measurement,issued_at,expires_at])`. Both CPU and accelerator evidence must bind this challenge using the platform's documented nonce/report-data mechanism. The platform adapter specifies exact packing and any padding; it may not silently hash/truncate to fit. It verifies device association and the protected CPU-to-accelerator path, not just two independently valid quotes. Host qualification also verifies trusted time and rollback-resistant lifecycle/key storage required by RFC-0007; unsupported persistence blocks that host.

The platform verifier checks certificate chains, revocation/TCB, debug/security mode, collateral validity and freshness at the caller's time. Epoch lifetime is at most one hour and no greater than collateral validity; use a new key on restart/rotation. A request requiring fresher evidence starts a new epoch under its admitted budget. The local fixture can test parsing and negative wrappers but cannot produce accepted genuine evidence.

Loader opens the manifest's exact ordered files read-only, validates hashes, architecture, tokenizer, template, greedy generation settings and numerical mode, then exclusively instantiates the measured inference runtime. A signed digest of a file that was never used is insufficient. Changes to files, runtime config or devices after admission stop the process. Qualification must demonstrate the loaded weights and protected output route using controlled mutation/bypass tests.

TLS/authentication terminates inside the measured gateway. The untrusted host cannot replace a response after classification without breaking the user opening. The gateway buffers the complete response, runs all three exact enrolled classifier programs on the prompt, constructs input digests/context, and signs the receipt only after durable encrypted witness storage. A native block returns a signed blocked status with no response/opening; a classifier/storage/epoch failure releases nothing. No streaming partial text.

`handle(request,enrollment,budget)` is single-writer per instance; nonce/audience requests are authenticated and deduplicated before inference. Keys never leave the measured process. B2 claim B is rejected if this byte-to-input path cannot be validated.

## Alternatives Considered

Per-request quotes narrow freshness but may add cost; epoch keys are selected for the POC with an explicit one-hour cap and revocation checks. CPU-only evidence cannot qualify an accelerator path. A stand-in signature server would exercise software but not claim A.

## Drawbacks

Hardware roots and platform assumptions remain trusted. The exact supported host and device-binding mechanism are unresolved. Native gating can release while proofs are pending, which is visible as unverified status.

## Migration / Rollout

Keep hardware evidence unsupported in the existing CLI. Implement a fail-closed adapter only after host authorization and platform qualification. Do not enable remote runners or background services as part of the spec backlog publication.

## Testing Strategy

Use genuine accepted collateral, then stale/revoked/debug/wrong-measurement/wrong-key/wrong-device cases. Swap a model shard after hashing, bypass the classifier call, modify response bytes after signing and transplant accelerator evidence across epochs. Every mutation must fail at the named boundary. Test crash before durable spool/signature and blocked response redaction.

## Open Questions

- OPEN QUESTION HOST — @AbdelStark, resolution checkpoint 2026-11-09: designate and authorize a host, platform verifier revisions, device-binding evidence and measured runtime through W22/W23. Missing genuine linkage blocks claim A and B2; no software substitute.

## References

- [Security model](../spec/06-security.md), [wire RFC](RFC-0001-wire.md), [lifecycle RFC](RFC-0007-verifier.md).
