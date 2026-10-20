# RFC-0008: Redacted failures and reproducible cost accounting

- Status: Draft
- Authors: @AbdelStark (owner; engineering draft for review)
- Created: 2026-10-20
- Target milestone: v0.3

## Summary

Standardize typed failures, allowlisted local events and raw per-stage cost samples. Bound all external processes and keep private inputs out of routine diagnostics.

## Motivation

[PRD honest claims and cost metrics](../../research/source/product-requirements.txt) require knowing what executed, what failed and what was measured. Current generic exception strings can reveal input paths or backend text.

## Goals

- Stable error codes and exit behavior without input leakage.
- Raw numeric samples before derived summaries.
- No telemetry, unbounded retry or hidden compute escalation.

## Non-Goals

- A hosted metrics service, per-user analytics, performance promises without measurements or a scheduler.

## Proposed Design

Use `HallmarkError`, `Event` and `StageSample` from [errors](../spec/04-error-model.md#contract-and-ordering) and [observability](../spec/05-observability.md#local-event-contract). Error translation occurs once at each trust boundary; domain code does not stringify arbitrary input. Allow only known stage/code/outcome values. Unexpected child-process output remains in a restricted local failure file only when explicitly admitted; ordinary diagnostics contain a random correlation ID.

Wrap each admitted external invocation in a process owner that enforces `JobBudget`, tracks descendant termination and records monotonic elapsed time/peak memory. Set explicit thread/device/dtype values, clear inherited secrets and disable network where the approved host can enforce it. Where OS enforcement is unavailable, label the run's resource boundary as monitored rather than isolated and do not use it to make sandbox claims.

Extend stage sampling with `CostStage=Literal["preprocess","native","export","setup","witness","prove","verify","attest","serialize"]`. Cost samples use `CostStage`; operational events use the coarser `Stage`. Store hardware/config/graph/key/source/lock identities in `cost-manifest.json`, raw `samples.jsonl`, failure list and `summary.json` under a fresh directory. These files are private evidence, not automatically publishable artifacts.

Statistics use the [fixed quantile rule](../spec/05-observability.md#metrics-and-costs). Report cold/warm results separately and include failed/timeout counts and maximum cap. A failed trial contributes to the success denominator and censored-time reporting; it is never deleted. Setup amortization includes its denominator. Comparison uses matched input profiles and fixed repetition order or predeclared randomized order with seed.

Current baseline exceptions migrate to safe codes without changing arithmetic or reports. Current `source.json` intentionally retains source/diffs privately; do not claim the event redaction contract sanitizes historical bundles.

## Alternatives Considered

Raw exceptions are convenient for debugging but can leak transcripts/paths. Hosted tracing eases aggregation but adds disclosure and service authority. Timing only the verifier call hides setup, preprocessing and failed work.

## Drawbacks

Sanitized errors require private local diagnostics for investigation. Portable peak-memory measurement may be coarse; methods and limitations must be recorded. Repetition counts can be expensive and need admission.

## Migration / Rollout

Add typed errors/redaction first, then events, then the measurement harness. Preserve old results and error strings as versioned historical behavior; no retroactive measurement claims. CLI exit-code changes apply to new v1 commands and documented baseline diagnostic hardening.

## Testing Strategy

Inject a unique content sentinel into malformed JSON/Unicode, paths, subprocess stderr, validation errors, timeouts and storage failures; assert it is absent from stdout/stderr/events. Check sample counts, deterministic p50/p95 and null optional device memory. Kill workers and exhaust disk caps; no successful result or orphan process may remain.

## Open Questions

- OPEN QUESTION COST-HOST — @AbdelStark, resolution checkpoint 2026-11-09: approve the host, cost/latency/memory caps and profiler method through W13/W32 before measured campaigns.

## References

- [Budget](../spec/08-performance-budget.md), [evaluation costs](../EVALUATION.md#cost-and-proof-evaluation-not-implemented), [proof adapter](RFC-0005-proofs.md).
