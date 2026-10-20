# Error model

## Contract and ordering

Target API errors are `HallmarkError(code: ErrorCode, stage: Stage, retryable: bool)`, with no raw value, path, exception string or transcript attached. `Stage` is one of `parse`, `enroll`, `attest`, `bind`, `execute`, `prove`, `verify`, `store`. CLI translation follows [public API](02-public-api.md#v1-supported-interfaces). `ErrorCode` is exactly the codes in the table below. Unexpected exceptions become `INTERNAL_ERROR` with a local random diagnostic ID; they never result in an accepted claim.

Check in this order: size/type/schema; external trust/config; registry; request/time; receipt signature; hardware if required; opening/input binding; proof and integer verdict; aggregate policy. Return the first failed stage and a deterministically sorted list of codes within that stage. A proof backend is never called on an input that failed earlier checks. Claim B-only B1 verification may explicitly decline hardware validation, while still requiring enrollment and complete binding/proof checks.

| Code | Trigger | Response and recovery |
|---|---|---|
| `INPUT_INVALID` | Duplicate/extra keys, invalid type/UTF-8/version/encoding, malformed signature or digest | Reject; create a corrected new artifact |
| `LIMIT_EXCEEDED` | Size, nesting, unit/chunk count or declared resource bounds exceeded | Reject before allocation/work; new admission for a larger profile |
| `TRUST_MISSING` | No externally enrolled key, model, policy or required hardware root | No claim acceptance; enroll through owner-controlled channel |
| `REGISTRY_INVALID` | Signature threshold, time, sequence, predecessor or entry mismatch | Reject; restore trusted snapshot/history, never lower local sequence |
| `ARTIFACT_RETIRED` | Any required artifact retired by the verification time | Reject; retain historical evidence without current acceptance |
| `REQUEST_MISMATCH` | Nonce/audience/interaction/model/policy differs | Reject; never retry under changed expectations |
| `STALE_EVIDENCE` | Expiry, stale hardware collateral, future issuance | Reject; acquire fresh evidence under approved host access |
| `SIGNATURE_INVALID` | Receipt signature does not verify under epoch key | Reject permanently |
| `ATTESTATION_INVALID` | Invalid chain/TCB/freshness/debug state or missing device binding | Reject A and B2; no mock fallback |
| `MEASUREMENT_UNKNOWN` | Serving image, loader or accelerator measurements not enrolled | Reject until independently reviewed enrollment |
| `OPENING_FAILED` | Byte-exact commitment differs | Reject; no normalization repair |
| `INPUT_BINDING_FAILED` | Tokenizer, length, masks, chunk coverage or input digest differs | Reject B; new complete proof required |
| `PROOF_INVALID` | Proof/key/setup/backend mismatch or verifier false | Reject B; preserve failed artifact |
| `VERDICT_MISMATCH` | Receipt, proof, integer comparison or all-pass result disagree | Reject; stop serving and investigate |
| `POLICY_BLOCKED` | Valid evidence establishes any classifier block | Report valid evidence separately; overall accepted is false |
| `PROOF_PENDING` | Proof absent or unfinished | No accepted bundle; explicit later collection |
| `RESOURCE_EXHAUSTED` | Timeout, OOM or approved job-count cap | Kill worker, retain failure, no automatic budget increase |
| `STORAGE_FAILED` | Disk full, existing output, failed durable write or encryption | No release/new complete artifact; preserve prior state |
| `INTERNAL_ERROR` | Unexpected implementation/backend exception | Fail closed; local sanitized diagnostic, manual investigation |

## State and retry rules

Request/receipt identity is immutable. A failed job may be retried once within its original approved total budget using the same inputs/key/setup; each attempt has a separate record. Invalid evidence, schema, policy and signature failures are never retried automatically. Expired jobs delete their per-receipt encryption keys and cannot return to ready. Duplicate completed requests return the same signed receipt only to the authenticated requester; the ledger does not expose existence to other audiences.

**INV-ERROR-PRIVACY:** no normal stdout/stderr/event contains raw prompts, responses, tokens, salts, weights, keys, local absolute paths or external provider exception text.

**INV-ERROR-TRUTH:** unavailable, pending, declined trust, invalid evidence and policy-blocked are distinct states. None is reported as proof failure if no proof was actually checked.

## Implemented diagnostic boundary

`hallmark.errors` exports `ErrorCode`, `Stage`, `ERROR_CODES`, `STAGES`,
`HallmarkError`, `sanitize_exception` and `first_stage_errors`.
`HallmarkError(code, stage, retryable=False)` validates finite metadata;
`as_dict()` emits only `schema_id="hallmark/error/1"`, `code`, `stage`, `retryable`
and `diagnostic_id`. Unexpected failures get a random UUID4 hex ID; normal
failures have null IDs. The ID is a correlation handle, not proof that a
private traceback or diagnostic file exists.

The CLI applies this boundary to argument parsing and execution. Invalid
values/Unicode/schema and absent/non-file input paths produce `INPUT_INVALID`
at `parse`. Timeouts and memory exhaustion produce `RESOURCE_EXHAUSTED`;
other filesystem failures produce `STORAGE_FAILED` at `store`. Unexpected
exceptions, including failed child processes, produce `INTERNAL_ERROR`.
Existing typed errors retain their code/stage. External messages, notes, causes
and process output never enter the JSON record.

Exit 2 means `INPUT_INVALID`, `LIMIT_EXCEEDED` or `TRUST_MISSING`. Exit 3 means
`PROOF_PENDING`, `RESOURCE_EXHAUSTED`, `STORAGE_FAILED` or `INTERNAL_ERROR`.
The other codes exit 1 (rejected claim/policy). No error maps to exit 0.
The research CLI does not implement proof/attestation acceptance just because
the taxonomy includes those codes.

`first_stage_errors` accepts 1–64 typed errors and selects the earliest of
`parse`, `enroll`, `attest`, `bind`, `execute`, `prove`, `verify`, `store`, sorting
within that stage by code and retryability. It organizes diagnostics; it does
not execute a verifier or replace the detailed check order above.

`WireError` retains its codec API as a `HallmarkError` subclass. Internal research
helpers still raise their existing exceptions; callers exposing those failures
must apply the diagnostic boundary. Existing run files, source/diff snapshots and
the legacy two-field `failure.json` are preserved, not sanitized or rehashed.
Versioned local events and immutable attempt/failure records are implemented in
`hallmark.events`; see [observability](05-observability.md#implemented-event-storage).
[Decision 0004](../decisions/0004-error-boundary.md) records the compatibility change.
