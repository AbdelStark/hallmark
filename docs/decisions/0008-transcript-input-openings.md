# 0008: exact v1 transcript and complete-input openings

Date: 2026-10-20. Implements W02 / issue #3 under the autonomous backlog request.
No historical experiment is migrated or reused. Enrollment still requires the
WIRE-REVIEW gate; hash reconstruction does not supply policy or evidence acceptance.

## Transcript and context

`hallmark.openings.TranscriptOpening` is a frozen record with required
`schema_id="hallmark/transcript-opening/1"`, 32-byte `system_ref`, `prompt`,
`response` and a 32-byte `salt`. Each text field is strict UTF-8, capped at 32768
bytes with no normalization, trimming or role concatenation. Empty text is valid.
The record exposes the existing checked CBOR encode/decode boundary and a
[JSON schema projection](../schemas/transcript-opening-v1.json).

`opening.commitment()` computes the RFC-0001 formula:

```text
C_T = H("transcript", [system_ref, salt, prompt_utf8, response_utf8])
```

The two text payloads are CBOR byte strings in that preimage, not CBOR text.
The opening record's encoding is a separate versioned map; hashing that map would
produce the wrong commitment. `verify_commitment(expected_digest)` compares an
explicit external 32-byte digest and raises `OPENING_FAILED` at `bind` on mismatch.
It does not infer where the expected digest came from.

`opening.context(expected)` requires the complete validated caller-held
`RequestExpectation` and computes `H("context", [expected, C_T])`. The nested
expectation includes its schema ID and explicit nullable continuity as fixed in
decision 0007. All expectation fields are bound. Context includes neither proof
bytes nor receipt signatures, preserving the acyclic statement order.

## Complete classifier input

`derive_input_salt(salt, classifier_digest)` checks both 32-byte inputs and computes
`H("input-salt", [salt, classifier_digest])`.

```python
input_commitment(
    opening, classifier, profile, *,
    token_units=None, vocabulary_size=None,
)
```

The call revalidates all three contracts and checks that the classifier names the
actual profile and the correct encoding for its kind. Rule and MLP input is the
complete UTF-8 prompt byte sequence, reconstructed locally. Supplying token units
or a vocabulary for these kinds is rejected; a caller cannot substitute a prefix.
The response is not classifier input in v1, but remains bound by transcript/context.

For an encoder, `token_units` must be an explicit tuple of original content IDs
independently computed by the caller, and `vocabulary_size` must be an explicit
integer in 1..2^64. Every ID is an exact integer in `[0, vocabulary_size)`;
booleans and coercions fail. Fixed prefix/suffix/padding IDs must fit the same
vocabulary. The original units exclude these per-chunk recipe tokens and padding.
Both encodings enforce `profile.max_units` before hashing; exceeding it fails
with `LIMIT_EXCEEDED` at `parse`, never truncates, and never consumes an unbounded
iterator. Unit count is derived from the supplied sequence, not a separate claim.

The returned digest is exactly:

```text
salt_i = H("input-salt", [opening.salt, classifier.identity()])
input_digest = H("input", [salt_i, profile.identity(), len(units), units])
```

Changing the classifier, profile, salt, order, count or any unit changes this
preimage. The entire sequence is included even beyond the first chunk.

This module has no tokenizer, chunk execution, model loading, I/O or hardware
dependency. An encoder caller must obtain its complete units and vocabulary from
the independently pinned local tokenizer/files; the provided integer bound alone
does not authenticate them or prove text-to-token correspondence. Never reuse
receipt-supplied tokens as B1 truth. Qualified tokenizer integration, chunk/mask
coverage and independent verifier execution remain their own implementation gates.
The synthetic token vector checks integer encoding only.

## Privacy, migration and verification

Production salts must be generated with a CSPRNG. Size validation cannot prove
randomness or prevent reuse. The opening reveals text and salt, so B1 exchange
requires an authenticated confidential channel or explicit authorized file
exchange. B2 retains them in its private witness. Salting does not hide public
length/verdict metadata and becomes ineffective against guessing when disclosed.
Object repr omits prompt, response and salt; CBOR/JSON serialization includes them.
Direct Pydantic error objects must not be logged; checked methods use sanitized errors.

The legacy `hallmark.integrity.transcript_commitment` retains its
`hallmark/v0/transcript\0` prefix, length framing and hex-string return type.
The v1 method uses the typed v1 CBOR formula and returns raw 32-byte digests.
They are intentionally incompatible. Old research runs are not v1 receipts and
must not be rehashed or silently converted. Policy byte caps, request admission,
enrollment, proof verification and genuine hardware evidence remain separate gates.

The [portable vectors](../../fixtures/wire/openings-v1.json) contain only harmless
synthetic text and public fixed salts. They cover empty input, composed/decomposed
Unicode, role swaps, whitespace/NUL/emoji, late bytes and U64 token boundaries.
Exact preimage bytes and resulting digests are included; U64 input IDs use decimal
strings in the JSON fixture to avoid JavaScript number precision loss.

The Python suite and a separate standard-library JavaScript encoder/hash checker
consume these vectors. Run `node scripts/check_opening_vectors.mjs` from the root;
it is optional developer tooling, not a package runtime or CI dependency. Its
cross-language agreement is an implementation check by the same contributor,
not the independent reviewer or verifier required for full v1 acceptance.
