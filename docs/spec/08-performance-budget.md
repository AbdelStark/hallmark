# Performance and resource budget

## Current authority

Bootstrap runs are local CPU, one training thread, at most 60 seconds per command, no external model/data access and no paid/GPU/background campaign. These limits remain in force. Publishing the spec and issues does not change [AUTHORITY](../../research/AUTHORITY.json).

## Proposed v1 envelopes

These are implementation caps and measurement proposals, not observed throughput or permission to allocate a host:

| Operation | Cap / proposed target | Response on breach |
|---|---|---|
| Prompt and response | Each ≤32,768 UTF-8 bytes; no truncation | `LIMIT_EXCEEDED` |
| Encoder input | ≤32,768 units; chunks ≤512 units including special tokens | Reject oversize input profile |
| Bundle / each proof | 64 MiB / 16 MiB | Reject before full decode/verification |
| Offline verification | Caller budget ≤60 s total; 2 GiB worker RSS proposed default | Terminate worker, no accepted result |
| Local spool | 32 pending receipts, 1 GiB encrypted bytes, 24 h maximum witness retention proposed default | Stop admitting requests; expire and delete per-receipt key |
| Foreground proof worker | One job at a time; at most one retry within approved total budget | Failed/expired receipt; never increase cap |
| Research cost sample | 5 cold and 30 warm repetitions proposed minimum per admitted length/graph | Incomplete measurement if absent; no extrapolated p95 |

The integer reference targets exactness first. No serving latency or proving time is invented as a demonstrated capability. The relying party and owner must fill and sign `BudgetAdmission={host:Id, hardware:Digest, max_wall_seconds:U64, max_cost_minor:U64, currency:Id, max_memory_bytes:U64, max_disk_bytes:U64, threads:U64, jobs:U64, max_proof_seconds:U64, max_verify_seconds:U64, max_native_overhead_basis_points:U64, approved_by:Id, approval_ref:Digest}` before any non-bootstrap campaign. All values are positive except a zero cost cap for explicitly free resources; currency uses a declared fixed unit.

**INV-BUDGET:** setup, compilation, witness generation, failed attempts, retries and teardown count toward the admitted cost/time cap. A lower-complexity graph needs a new candidate identity; weakening the verifier is never a performance optimization.

## Measurement procedure

Freeze dataset/length roster, native baseline, exact model/graph/backend, setup reuse policy, host and repetitions before measurement. Use identical requests with confidential mode on/off where authorized, and state the engine, concurrency and exclusion rules. Record first-use setup separately; amortized setup cost states its reuse count. Preserve every failure, timeout and unsupported operator.

Report p50/p95 per stage, throughput with wall-clock denominator, peak resident/device memory, proof and bundle bytes, success fraction, and native release overhead relative to the matched baseline. A source/model hash or host inference timing is not a proving result. Raw [StageSample](05-observability.md#metrics-and-costs) records precede prose.

RISK: a useful encoder may exceed the approved proof budget. Owner @AbdelStark resolves by the v0.3 qualification gate using measured costs, not an inherited paper estimate. v1 stays blocked until a qualified encoder and budget exist.
