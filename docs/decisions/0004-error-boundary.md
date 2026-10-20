# 0004: sanitized CLI failures

Date: 2026-10-20. Implements W30 / issue #31 and RFC-0008 under the owner's
autonomous backlog request.

The old CLI printed `str(exc)` for runtime and filesystem failures, and argparse
echoed arbitrary arguments. A missing-path fixture confirmed that a private path
sentinel appeared in stderr. Unexpected exceptions could escape as tracebacks.

Translate errors once at the CLI boundary into a finite `hallmark/error/1`
record. Preserve successful command output and arithmetic; replace unsafe text
diagnostics. Argument and input errors still exit 2. Resource/storage/unexpected
execution failures now exit 3, so scripts must test for nonzero rather than
assuming every failure is 2. Unexpected errors get random diagnostic IDs and
never become successful results.

Keep error codes and stages usable by the wire codec and future adapters.
Stage ordering only organizes errors; the future verifier must still enforce
its sequential trust checks before invoking a backend. Events, process
isolation and durable failure-record migration belong to separate work items.

Do not alter old run bundles or their hashes. Source snapshots and legacy
library exceptions are not covered by a claim that CLI diagnostics are
redacted. Sentinel tests cover actual CLI parsing, file validation, Unicode,
all code variants, child-process exceptions, timeouts, storage and failed-run
records. No external provider, hardware or proof was exercised.
