# 0011: Bounded offline bundles and reported claim states

Date: 2026-10-20. Status: implemented software contract, pending owner protocol
adoption and independent review. Implements W07 / #8. No prior experiment or
research identity is migrated, and no prior result becomes v1 evidence.

## Decision

`hallmark.bundles` implements `EmbeddedFile`, `Bundle`, `ResponseEnvelope`,
`BundleStatus`, `Claim` and `VerificationResult`. The top-level schema IDs are
`hallmark/bundle/1`, `hallmark/response-envelope/1`, `hallmark/bundle-status/1`
and `hallmark/verification-result/1`. `EmbeddedFile` and `Claim` are nested
records without schema IDs, like `FileRef` and `RegistryEntry`. Existing nested
receipt, proof, epoch, registry and opening IDs remain mandatory.

Every object is frozen and strict, rejects unknown/missing fields and revalidates
before encoding. Nullable fields are required and explicitly null, never omitted.
Canonical binary `decode_bundle(raw, limits=external_limits)` is the untrusted
bundle-input boundary. JSON schemas are hex-byte projections; general Pydantic
Python/JSON constructors are not bounded stream readers.

## Bundle contents and resource bounds

`Bundle` has exactly its declared receipt, epoch, registry, history, three proof
records and 1–8,192 embedded files. History has 0–1,024 intermediate snapshots,
using W08's definition. A bundle cannot replace the caller's trust, expectation,
checkpoint or clock. It has no binding-mode selector; mode comes from external
trust. Parsing does not verify registry signatures or chain continuity.

Each embedded file must match its `FileRef` byte length and raw SHA-256. Paths are
normalized logical names, sorted and unique. Traversal, absolute paths, backslashes,
control characters and URL-like locators are rejected by the shared FileRef
contract. Names are case-sensitive and not normalized further. Identical bytes may
have distinct logical names; duplicate names are invalid even if their content
matches. No path is opened, extracted, linked or fetched.

Every epoch collateral reference must resolve to an exactly matching embedded
reference. Receipt epoch/model/key declarations must match the supplied epoch.
The three ordered proof public-input records must equal the three receipt inputs;
missing, extra, duplicate or reordered proofs fail. This is declared consistency.
Full artifact closure, manifest/backend/key/setup resolution, actual proof validity
and atomic publication remain the assembler/verifier's responsibilities.

The entire encoded value, including all headers, metadata, history and payloads,
must fit 64 MiB, nesting 16 and the codec's 1,048,576-item ceiling. Each proof is
at most 16 MiB. The bundle validator reuses the codec's value-tree measurement
before serializing a second full buffer. Caller limits can only lower these caps.
`decode_bundle` checks binary size/depth before model validation and applies the
caller proof cap to each proof. `bundle.validate_limits(limits)` performs the same
checks on an existing object. Worker time/RSS enforcement remains a separate
verifier responsibility; these methods do not start workers or accept evidence.

## Opening exchange and response lifecycle

Neither B1 nor B2 puts an opening field in a bundle. Canonical embedded wire
records declaring `hallmark/transcript-opening/1` or
`hallmark/response-envelope/1` are also rejected, so a normal serialized private
record cannot be accidentally attached as a file. This is a protocol-record check,
not a general detector of secrets in arbitrary opaque or differently encoded
bytes. The assembler must admit only the required artifact inventory; raw
transcripts and witnesses are never bundle files.

B1 exchanges the opening separately through an explicitly authorized confidential
channel. A `ResponseEnvelope` belongs to that response channel and may contain
an opening. Its repr hides response/opening values, but serialization discloses
them. A present opening must match both the response bytes and receipt commitment.
Responses use exact UTF-8, at most 32,768 bytes, with no normalization.

| Reported response status | Receipt release | Response / opening |
|---|---|---|
| pending, ready | released | response required, possibly empty; opening optional |
| blocked | blocked | both null |
| failed, expired | released | both null |

Failed/expired proof collection does not retroactively change a previously signed
release. These terminal envelopes omit private payloads. This record check does
not perform retention, deletion, durable release or recovery.

`BundleStatus` is separate collection metadata. Only `ready` carries a nonempty
bundle FileRef and no error. `pending` carries neither reference nor error;
`blocked` carries `POLICY_BLOCKED`; `expired` carries `STALE_EVIDENCE`; `failed`
carries a finite failure code other than `PROOF_PENDING`/`POLICY_BLOCKED`. All
nonready states have a null bundle reference. A ready reference alone does not
authenticate the file or prove that a worker verified it.

## Reported results are not verification

`VerificationResult` can represent reported B1 A+B, B1 B-only and B2 A+B outcomes,
as well as rejection, declined/unavailable claims, pending proofs and policy block.
It exposes no verifier or factory that converts a parsed bundle to accepted
evidence. The golden accepted-result examples are explicitly synthetic declarations.
Decoding a provider-supplied result never grants trust in its `accepted` field.

Accepted A uses hardware-attested strength; accepted B uses cryptographic
strength. Rejected/not-accepted claims have strength `none`. Every claim retains
`policy-errors`, `adaptive-evasion` and `unobserved-traffic`; A also retains
`hardware-trust`. B2 B retains `hardware-input-binding` and cannot be accepted
without accepted A. Accepted B requires `proof-soundness`, `circuit-correctness`
and `registry-trust` assumptions. B1 B rejects the two hardware-trust identifiers.

Assumptions/residuals, error codes and evidence hashes are sorted and unique,
within their schema counts. Error fields use the existing finite `ErrorCode`
vocabulary, not arbitrary messages. There is no `safe` field.

An overall accepted report requires accepted B, policy pass, no rejection of A,
no error codes and nonempty evidence references. B1 may decline A for B-only
requirements. `validate_requirements(external_trust)` checks the reported mode
and whether an accepted report satisfies the caller's required A; it does not
authenticate the report, its referenced evidence or the trust policy's provenance.

A policy verdict requires accepted B. A false verdict and `POLICY_BLOCKED` must
occur together; this distinguishes a reported genuine policy block from a native
collection status whose proof has not been checked. `PROOF_PENDING` requires B
not-accepted, not rejected. `PROOF_INVALID` requires rejected B and
`ATTESTATION_INVALID` requires rejected A. Any nonaccepted overall result needs
at least one reason code. These consistency rules do not implement the verifier's
ordered execution stages or independent evaluation.

Four schema snapshots and 17 structural/report examples are shipped in
`docs/schemas/` and `fixtures/wire/bundles-v1.json`. The receipt signatures,
hardware quotes and proof payloads in those examples remain unverified.
