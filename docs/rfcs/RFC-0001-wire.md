# RFC-0001: Versioned wire objects and transcript binding

- Status: Draft
- Authors: @AbdelStark (owner; engineering draft for review)
- Created: 2026-10-20
- Target milestone: v0.2

## Summary

Use a strict deterministic binary profile and separate v1 hash domains for immutable manifests, receipt bodies and complete classifier inputs. Preserve the existing research formats unchanged.

## Motivation

[PRD G3](../../research/source/product-requirements.txt) requires one exact transcript across evidence objects. Ambiguous serialization or an unbound tokenizer can make two valid components describe different interactions. [Data invariants](../spec/03-data-model.md#invariants) define the boundary.

## Goals

- Produce identical bytes/digests in independent implementations.
- Reject ambiguous types, extra fields and noncanonical encodings.
- Make B1 binding independently reconstructible without trusting a receipt signer.

## Non-Goals

- Migrating old research identities, proving tokenization privately, or general-purpose serialization.

## Proposed Design

W01–W05 implement the primitive codec and opening/manifest/policy contracts.
[Decision 0008](../decisions/0008-transcript-input-openings.md) records the exact
opening and input reconstruction boundary, vectors and cross-language check.
Enrollment and independent review remain separate gates.

`wire.encode` and `wire.decode` implement the [typed contracts](../spec/02-public-api.md#v1-supported-interfaces). `WireValue` is null, bool, integer in `[-2^63, 2^64-1]`, bytes, UTF-8 text, bounded list, or string-keyed map. No floats, tags, indefinite lengths or bignums. Use shortest representations and length-first ordering of encoded map keys; reject noncanonical input by bounded decoding with duplicate detection followed by byte comparison to canonical encoding. Bound nesting and byte sizes before allocating. Signatures are raw byte fields, not tagged objects.

Define `H(kind, value) = SHA256(u32be(len(tag)) || tag || encode(value))`, where `tag=ASCII("hallmark/v1/"+kind)`. The finite domains are `model`, `classifier`, `policy`, `input-profile`, `program`, `arithmetic`, `backend`, `setup`, `registry`, `epoch`, `context`, `transcript`, `input-salt`, `input`, `receipt`, `key`, `trust`, `protocol`, `review`, `corpus`, `cost`, `release`. File references use SHA-256 of exact bytes. A raw file hash and a typed identity are distinct types even though both are 32 bytes.

`C_T=H("transcript",[system_ref,salt,prompt_utf8,response_utf8])`. Require strict UTF-8 and exactly 32 random salt bytes; do not normalize, trim or concatenate roles. This is deliberately different from the legacy transcript helper. The opening is sent only through the authenticated confidential response channel or explicitly authorized B1 file exchange.

For classifier `C`, derive `salt_i=H("input-salt",[opening.salt,C])`; compute `input_digest=H("input",[salt_i,input_profile_digest,unit_count,units])`. Bytes are integer units 0..255; token IDs are integers bounded by the enrolled vocabulary. B1 derives this salt and input independently. B2 keeps salt and units private to the witness, and uses hardware to bind the public digest to the same transcript. Salting limits easy content guessing but does not hide length/verdict metadata.

Hash order: files/program/arithmetic/profile/backend/setup/key → classifier manifest → policy → request expectation and transcript → `context=H("context",[expected,transcript])` → per-classifier public inputs → receipt body/signature → bundle. The proof includes the complete context as a public input; it never hashes its own bytes into its statement.

Receipt and registry signatures use standard Ed25519 over `u32be(len(tag)) || tag || encode(body)` with distinct ASCII tags `hallmark/v1/sign/receipt` and `hallmark/v1/sign/registry`. `key_id=H("key",public_key)`. Signature verification uses a reviewed pinned implementation and rejects malformed keys/signatures; cryptographic code is not reimplemented here. Concurrency is irrelevant to pure codecs; validation raises typed errors without including offending content.

## Alternatives Considered

Canonical JSON would reuse the transport but complicates byte/integer distinctions. Full COSE would improve broad interoperability but adds header/algorithm negotiation unnecessary for this single-algorithm POC; a future COSE profile must use a new envelope version. Reusing research domains would make an unreviewed format change indistinguishable from old artifacts.

## Drawbacks

The restricted profile needs its own vectors and parser checks. It is not advertised as a standardized receipt format. B1 discloses text; B2 retains hardware trust.

## Migration / Rollout

Add separate v1 modules and schema snapshots; keep research tests and IDs intact. Owner review of decision 0002 and golden vectors precedes enrollment. No conversion of old runs into v1 receipts.

## Testing Strategy

Commit exact bytes for empty text, composed/decomposed Unicode, role swaps, all-zero test salt, random test salt, int/bool and bytes/text distinctions. Reject duplicate keys, trailing bytes, invalid Unicode, overlong integers and excess nesting. Flip each context field, salt, input unit and manifest digest; B1 must reject every mismatch. Compare vectors in two implementations.

## Open Questions

- OPEN QUESTION WIRE-REVIEW — @AbdelStark, resolution checkpoint 2026-11-02: approve the new domain/profile and signature envelope after independent vector review. No v1 enrollment until resolved; implement in work items W01–W07.

## References

- [Data model](../spec/03-data-model.md#v1-types), [registry RFC](RFC-0002-registry.md), [integer RFC](RFC-0003-integer.md).
- [CBOR deterministic encoding and length-first ordering](https://www.rfc-editor.org/rfc/rfc8949.html#section-4.2).
- [Ed25519 algorithm](https://www.rfc-editor.org/rfc/rfc8032.html#section-5.1), [COSE alternative](https://www.rfc-editor.org/rfc/rfc9052.html#section-4.2).
