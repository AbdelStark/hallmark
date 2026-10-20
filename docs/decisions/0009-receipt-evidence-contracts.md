# 0009: receipt, epoch and proof-container contracts

Date: 2026-10-20. Implements W06 / issue #7 under the autonomous backlog request.
These are structural contracts and checks of declared references. No signature,
quote or proof is accepted, no backend is qualified, and no old experiment is reused.

## Records and structural invariants

`hallmark.receipts` adds frozen records with required schema IDs, including when
nested: `ProofInputs` (`hallmark/proof-inputs/1`), `ReceiptBody`
(`hallmark/receipt/1`), `SignedReceipt` (`hallmark/signed-receipt/1`),
`EpochRecord` (`hallmark/epoch/1`) and `ProofArtifact` (`hallmark/proof-artifact/1`).
All fields, including nullable ones, are required. Checked CBOR methods revalidate
nested records and reject extra fields and unchecked-copy corruption.

`ProofInputs` names context, classifier, input digest, original unit count, chunk
count, signed int32 threshold and boolean verdict. Unit count is 0..32768 and
chunk count 1..32768, no greater than `max(1, unit_count)`. The explicit
`validate_profile(classifier, profile)` checks classifier/profile identities,
encoding kind, exact threshold, the lower profile unit cap and
`chunk_count=max(1, ceil(unit_count/content_capacity))`. Content capacity subtracts
the fixed prefix/suffix from chunk size. This checks counts, not actual chunks,
masks, input opening or execution.

`ReceiptBody` requires exactly three distinct classifier inputs. Every input
context must equal `H("context", [expected, transcript])`. Sequence zero has a null
predecessor; later sequences require a digest. Nonnull continuity must match the
body exactly; null continuity makes no history claim. `released` requires all
three declared verdicts true, and `blocked` requires at least one false.
A storage, classifier or epoch failure is not a native policy block and releases
nothing; these records do not model such failures as a successful policy verdict.

Decoding cannot determine kinds from opaque identities. The explicit
`validate_policy(policy, classifiers, profiles)` resolves the policy's exact
rule/MLP/encoder order, checks its identity against the expectation, and checks
each input's threshold/count/profile. `validate_expectation(expected, now=...)`
requires independently supplied expectations and compares every field.
Reusing the receipt's own expectations as trust defeats that boundary.

## Public-input layout

`ProofInputs.to_fields()` returns exactly 100 mathematical integers:

| Positions | Meaning | Range |
|---|---|---|
| 0–31 | context bytes, original order | 0..255 each |
| 32–63 | classifier bytes, original order | 0..255 each |
| 64–95 | input-digest bytes, original order | 0..255 each |
| 96 | original unit count | 0..32768, further bounded by profile |
| 97 | chunk count | 1..32768, exact profile relation |
| 98 | signed threshold plus 2^31 | 0..2^32−1 |
| 99 | verdict | false=0, true=1 |

`from_fields` requires an exact 100-element tuple of exact integers, rejects
out-of-range aliases/booleans and reconstructs the record. Digests are never
reduced modulo a scalar field. Negative thresholds use the specified offset,
not two's complement or a signed field residue. The schema ID is fixed by this
layout and is not another field. The
[machine-readable layout](../schemas/proof-input-layout-v1.json) must be pinned
as a backend artifact, with a field modulus greater than 2^32−1 and circuit
constraints for every bound and relation. Packing is not a proof adapter.

## Epoch, receipt identity and signature message

Epochs have raw 32-byte IDs/keys, model/measurement digests, two required opaque
evidence payloads and 1..256 collateral references sorted by unique path.
References remain logical names; validation performs no file access.
`issued_at < expires_at`, with an epoch lifetime of at most 3600 seconds.

`epoch.challenge()` is exactly the RFC-0006 list preimage:
`H("epoch", [epoch_id, key, model, measurement, issued_at, expires_at])`.
`epoch.identity()` hashes the entire epoch record in the same domain. The list
and map are distinct encodings; the challenge excludes quotes/collateral to avoid
a cycle, while the record identity includes them. A receipt's `epoch` field
references the complete record identity. `epoch.key_id()` is `H("key", key)`.

`body.identity()` is `H("receipt", complete_body)`. `body.signing_bytes()` returns
`u32be(len(tag)) || tag || encode(body)` for `tag=ASCII("hallmark/v1/sign/receipt")`.
It neither signs nor verifies. A `SignedReceipt` carries that body, a key digest
and exactly 64 opaque signature bytes. Key/signature size is checked here;
Ed25519 point/encoding/signature validity requires the later pinned crypto verifier.

`signed.validate_epoch(epoch, now=...)` compares epoch identity, model and key ID,
checks receipt issuance within the epoch and checks both intervals at the explicit
caller clock. Current means `issued_at <= now < expires_at`, with no hidden clock
or skew allowance. Receipt expiry need not equal epoch expiry; either expired
interval fails. The clock itself must be a strict U64. These checks do not
authenticate time, enforce caller max-age policy, or examine collateral validity.

## Opaque payload and trust boundaries

Each proof and each CPU/accelerator evidence field is nonempty and at most 16 MiB.
These implementation hard caps keep individual containers bounded; aggregate
wire/bundle limits still apply. `ProofArtifact.validate_inputs` requires external
`ProofInputs`, classifier/profile records and an explicit `max_proof_bytes` in
1..16 MiB. It checks equality, backend/verifier-key references and the lower byte
budget. Classifier identity also binds its program and setup declarations.
It never invokes a verifier or treats arbitrary nonempty bytes as a valid proof.

Malformed structures use sanitized `INPUT_INVALID`; payload budgets use
`LIMIT_EXCEEDED`. External request mismatch uses `REQUEST_MISMATCH`; declared
reference mismatch uses `INPUT_BINDING_FAILED`; outside-clock intervals use
`STALE_EVIDENCE`, all at `bind` for these comparison methods. No accepted/verified
flag, signature verifier, attestation verifier or proof verifier is supplied.

Opaque evidence, proof and signature bytes are omitted from repr, but serialization
still includes them. Use authorized channels and never log raw Pydantic error
objects. [Fixtures](../../fixtures/wire/receipts-v1.json) use explicit synthetic
non-signatures, non-proofs and non-attestations; their successful parsing and
reference matching cannot establish claims A/B. Authenticated enrollment,
qualified cryptographic/hardware adapters and independent verification remain gates.
