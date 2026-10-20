# 0015: Bounded private event attempts

Date: 2026-10-20. Status: implemented software boundary for W31 / #32; owner review
is required before operational adoption or reuse as a measurement protocol.

## Decision

Use `hallmark.events.EventLog` for a fresh local event directory and
`inspect_events` for a closed directory. The writer generates a UUID4 run ID;
there is no input for a content hash, audience, request ID or arbitrary metadata.
Events have exactly the fields in [observability](../spec/05-observability.md).
Stages, outcomes and error codes are finite. Starts have no duration; terminal
stage events use monotonic nanoseconds and require nonnegative U64 durations.
Ordinals start at zero within each attempt and must be contiguous.

A completed stage does not mean a completed attempt. Before work starts, create
and sync `attempt-N.pending`. Append each event to `events.jsonl`, complete short
writes, sync and read back the appended bytes. On attempt exit, recheck the whole
stream and write a bounded `AttemptRecord` into the pending file. It records
run ID, attempt index, event count, exact attempt-byte SHA-256, status and finite
failure metadata. No original exception, path, input digest or diagnostic text
is serialized. Completed records have no error metadata and require at least
one completed stage pair. Failure outside a stage is retained too.

Publish `attempt-N.json` with an exclusive hard link, sync the directory, remove
the pending link and sync again. On a reported failure, retain/recreate the
pending link and remove only the final link made by that publication. No later
work is admitted after uncertain I/O. The reader rejects malformed sequences,
changed bytes, duplicate ordinals, unsafe files or inconsistent receipts. A
pending attempt or an unsealed well-formed prefix is incomplete. A partial JSON
line is invalid, never complete. Reads use a shared nonblocking lock; they fail
while the writer owns its exclusive lock.

After one explicitly retryable transient failure, the caller may start one more
attempt in the same log. Only `RESOURCE_EXHAUSTED`, `STORAGE_FAILED` and
`INTERNAL_ERROR` can carry retry permission. The log never retries work itself,
never removes the first failure and never permits another attempt after success.
A caught stage error still fails its enclosing attempt. The caller must keep
inputs/key/setup unchanged and stay inside the original approved total budget;
this metadata-only log cannot enforce those external execution conditions.

## Bounds and privacy

The implementation supports POSIX local filesystems and an owner-controlled
parent directory. A new run directory is mode 0700; regular files are mode 0600,
owned by the effective user, without symlinks or external hardlinks. Writers
cannot reuse a path, change threads or survive a fork as another writer. A
crashed directory is retained for inspection; there is no resume/repair API.

Admission requires `4096 <= max_bytes <= 1048576`, with at most 4,096 events and
two attempts. Each event line is at most 512 bytes; each attempt record at most
1,024. Two record slots are reserved before event admission so cap exhaustion
can retain a finite `STORAGE_FAILED` record. The cap measures serialized file
payload, not filesystem allocation or process memory. Readers bound input size,
line length and directory inventory before schema/sequence checks.

There is no telemetry, network call, raw provider-output capture, automatic
retention job, content-to-run index or encryption/key manager. Metadata remains
private: timing, stages and failure codes can identify activity. Keep directories
outside git under the run's approved access, backup, retention and deletion
policy; include failed attempts. Permissions do not encrypt data or protect it
from the same OS account, an administrator or backups.

The reader checks UUID4 syntax, not entropy or historical provenance. A malicious
author can fabricate a syntactically valid UUID, events and matching digests.
These checks do not authenticate execution, establish filesystem durability
independently, or produce a cryptographic verdict. They assume cooperative
single-account access and a functioning local filesystem. Network filesystems,
physical power-loss behavior and compound failures that also prevent both
failure-marker retention and removal of a published receipt are not qualified;
quarantine affected archives rather than using a completion report.

## Compatibility and validation

This is a new v1 API used by the installed-package fixture and intended for the
W32 measurement harness. It does not rewrite legacy research `run` bundles,
`failure.json`, manifests, source snapshots, or historical results. The frozen
W33 corpus is unchanged; new conformance checks live in `tests/test_events.py`.

Tests cover sentinel privacy, strict schemas and sequence tampering, deterministic
monotonic durations, explicit retry retention, byte/event caps, live locks,
thread/fork/process ownership, process exit before/during/after a stage, short
writes, disk failures, each publication sync and unsafe paths. The installed
wheel exercises a retained failure followed by an explicit successful retry.
These are software checks, not performance measurements, worker isolation,
proof verification or a successful hardware run. W32 still owns cost samples,
quantiles, resource/process ownership and full-path measurement.
