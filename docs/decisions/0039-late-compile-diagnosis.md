# 0039 — Diagnose the late maximum-input compile phase

Date: 2026-10-21. Scope: W18 / issue #19, local compiler feasibility.

The compact Boolean-cache candidate preserves seven small serialized circuits and
passes fresh small-proof checks, but maximum compilation times out at 90.307
seconds below the memory cutoff. Hypothesis: a longer bounded compile may finish
inside the unchanged memory envelope; late snapshots can identify the active
phase if it fails. No circuit, canonical encoding, proof evaluator or default
dependency changes in this experiment. The old timeout remains a failed result.

Recheck the selected outer-command receipts by hash. Keep the earlier audited
5,540-second charge and all original allowances; replace four later unused
reservations with measured commands plus their full allowances. The resulting
6,641.365-second charge rounds conservatively to 6,660. This adopts that receipt
review, leaving 540 seconds in the existing 7,200-second local proving allocation.
Reserve 500 for this experiment and its software gates, leaving 40 unreserved.
This is accounting reconciliation, not increased authority or a concurrency refund.

Add an ignored Go standard-library diagnostic init hook, active only for
`input-compile 32768`, to a fresh source copy of the pinned compiler candidate.
Capture goroutine/heap profiles and runtime memory counters near 40 and 80 seconds,
including actual snapshot timings and write failures. Do not force collection.
These are sampled diagnostics that can perturb execution; they are not complete
allocation traces or standalone performance measurements. Pin the hook, complete
source/build environment and existing patched-module inventory before running.

First compare the seven small serialized circuit fingerprints against the prior
candidate and compile the smallest input fixture. Bound maximum diagnostic
compilation at 180 seconds and 720 CPU seconds. Only if it finishes within limits,
run the unchanged prior binary in a fresh directory with the same caps and require
the same constraint count. A diagnostic-only success is not reproduced production
compilation. Preserve failures and incomplete snapshots. Do not repeat small-proof
setup/proving or reassign those earlier proofs to the diagnostic binary.

Keep four threads, the 1 GiB Go soft limit, 14 GiB live RSS cutoff, 16 GiB peak
ceiling, one foreground job, 1 GiB new artifacts and 40 GiB retained storage.
The execution roster is capped at 370 seconds; build/fixture and software gates
fit the full 500-second reservation. No token, paid compute, new dependency,
private input, upload, contact or scheduler. Full-input proving, full encoder,
operational enrollment and independent verifier/security/setup/hiding gates remain.
