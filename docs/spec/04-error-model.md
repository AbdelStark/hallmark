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

Existing v0.1 failure messages and `failure.json` do not yet implement this taxonomy. [RFC-0008](../rfcs/RFC-0008-operations.md) defines the migration and sentinel tests.
