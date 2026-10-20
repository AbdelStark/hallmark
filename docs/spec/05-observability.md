# Observability

## Local event contract

No hosted telemetry is part of v1. Operators explicitly choose a private output directory. Events use newline-delimited JSON:

```text
Event = {
  schema_id: "hallmark/event/1",
  run_id: Id, attempt: U64, ordinal: U64,
  stage: Stage, outcome: "started" | "completed" | "failed",
  elapsed_ns: U64 | null, code: ErrorCode | null
}
```

Only these fields are allowed. `run_id` is a fresh random identifier, never derived from content or an audience. A local restricted index maps it to an artifact digest when needed. Ordinals strictly increase within an attempt. Durations use a monotonic clock; elapsed time is null for starts. Failure events have a code, complete events do not. An event file failing to persist prevents claiming a complete measurement run, but never changes a cryptographic verdict.

Normal diagnostics contain no transcript, token, salt, score, model tensor, signing key, request nonce, user ID or raw input hash. Digests and length/score slices needed for research belong in explicitly private reports. Even metadata may identify interactions; events have the same access/retention policy as their run.

## Metrics and costs

`StageSample={stage:CostStage, repetition:U64, elapsed_ns:U64, peak_rss_bytes:U64, peak_device_bytes:U64|null, output_bytes:U64, success:bool, code:ErrorCode|null}`. Samples append to an immutable per-run result directory. Aggregate p50/p95 using nearest-rank quantiles, with sorted values and rank `ceil(q*n)` starting at 1. Report all failures separately and the denominator; never compute a fast p95 from only the successful attempts without labeling it conditional.

`CostStage` is `preprocess`, `native`, `export`, `setup`, `witness`, `prove`, `verify`, `attest` or `serialize`. Record each separately; operational events retain their coarser `Stage` values. Benchmark metadata pins hardware/OS/drivers, source/lock/image, graph/key/setup, dataset/input-length profile, threads, batch/concurrency and cold/warm mode. Hardware snapshots and command lines need redaction before sharing.

Metrics are counts and durations, not per-record remote traces. No unbounded labels, prompt hashes or audiences in metric dimensions. At most one foreground writer per run, bounded by the admission's disk cap; exhaustion produces `STORAGE_FAILED` and a retained failed run.

## Audit evidence

Cryptographic evidence bytes, verifier conditions and the externally trusted inputs are retained locally with hashes under the authorized retention policy. A second reader can recompute aggregates from raw samples. Logging a digest does not authenticate execution. [RFC-0008](../rfcs/RFC-0008-operations.md#testing-strategy) requires content-sentinel tests on every exit path, including subprocess exceptions and invalid Unicode.
