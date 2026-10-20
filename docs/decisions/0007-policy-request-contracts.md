# 0007: all-pass policy and explicit request expectations

Date: 2026-10-20. Implements W05 / issue #6 under the autonomous backlog request.
This is contract implementation, not policy adoption, enrollment or deployment.
No historical experiment or result is reused under this v1 interpretation.

## Policy declaration and resolution

`hallmark.policy.Policy` is a frozen artifact with
`schema_id="hallmark/policy/1"` and identity `H("policy", complete_record)`.
It requires the rubric digest, exactly three distinct classifier identities in
rule/MLP/encoder order, combination `all-pass`, language `en`, scope `prompt`, and
prompt/response byte limits in 0..32768. A zero limit admits only empty content;
it does not disable the limit. Every field is included in the identity.

Digest bytes do not reveal classifier kinds. `policy.validate_classifiers`
therefore requires an explicit three-element tuple of classifier manifests,
revalidates them and checks both their kinds and identities in order. Reordering
the digests together with the supplied manifests still fails. Duplicate kinds
with distinct identities also fail. This check performs no file access and
does not qualify classifier programs or execute all-pass over proof results.

The named policy `inj.direct/1` remains a proposal for an English single-turn
prompt-injection assay. The name, this schema and synthetic fixtures do not admit
a rubric, data, classifier, use case or relying party. W13 and POLICY-DATA in
RFC-0004 still require owner/relying-party admission.

## Requests and caller expectations

`RequestExpectation` is independently decodable and has the required
`schema_id="hallmark/request-expectation/1"` both by itself and when nested in a
request or later receipt. It pins the ASCII audience ID, 32-byte nonce,
32-byte interaction ID, model and policy digests, and an explicitly nullable
continuity expectation. No field defaults to something chosen by the sender.

`ChainExpectation` is a nested record with no schema ID. It requires a strict U64
sequence and explicitly nullable predecessor digest. Sequence zero requires null;
all later sequences require a 32-byte digest. Null continuity makes no history
claim and differs from explicitly expecting sequence zero.

`Request` has `schema_id="hallmark/request/1"` and requires the complete expectation,
prompt and system-reference digest. Prompt text is exact UTF-8, with no trimming
or normalization and a hard cap of 32768 bytes, including multibyte characters.
Empty strings are valid. Prompt text is omitted from object repr, but encoding
and JSON export still contain it and must use an authorized private channel.

`request.validate_against(expected, model=..., policy=..., classifiers=...)`
requires a separate caller expectation. After schema revalidation and classifier
resolution, it compares every expectation field, checks the actual model/policy
identities and applies the policy's prompt byte cap. Mismatches use
`REQUEST_MISMATCH` at `bind`; policy byte-limit failures use `LIMIT_EXCEEDED` at
`bind`. Malformed schemas and classifier sets use the existing sanitized
`INPUT_INVALID` parsing boundary.

The caller must construct expectations independently; using `request.expected`
as its own trust source defeats this comparison. The supplied artifacts still
need externally authenticated enrollment. No nonce is generated, consumed or
deduplicated here, and byte validation cannot prove CSPRNG use or freshness.
The requester must generate nonces securely; the later authenticated gateway
must enforce one-time admission. Prompt/system-reference transcript binding is
W02. Enforcing the response byte limit on generated content is a later serving
obligation. This API does not verify receipts, continuity history or evidence.

## Wire and snapshots

All fields are required, including nullable ones. Frozen nested records are
revalidated at encoding and comparison boundaries. Only policy has its own
typed identity here; requests/expectations do not invent new hash domains.
W02 includes the full expectation record in the specified context hash.

JSON schema projections use hex for bytes:
[policy](../schemas/policy-v1.json),
[expectation](../schemas/request-expectation-v1.json), and
[request](../schemas/request-v1.json). They cannot express all cross-field
constraints or UTF-8 byte lengths. Untrusted inputs use the canonical CBOR
decoders and explicit resolution/comparison methods; direct Pydantic error
objects are not log-safe diagnostics.

The [fixed vector](../../fixtures/wire/policy-request-v1.json) contains a harmless
prompt, synthetic unadmitted declarations and fixed public nonce/interaction
bytes. It tests encoding and contract checks only, not policy quality or security
of a deployed system.
