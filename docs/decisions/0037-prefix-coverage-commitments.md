# 0037 — Constrain complete-input coverage with prefix masks

Date: 2026-10-21. Scope: W18 / issue #19, commitment candidate optimization.

The 32,768-byte commitment component still has no completed circuit or proof.
Its prior maximum compile exceeded the local 16 GiB envelope. Before changing
the candidate, a fresh diagnostic binary added a Go standard-library heap
snapshot at four seconds. The unchanged maximum circuit was stopped below a
deliberately lowered 2 GiB ceiling, after the snapshot was written. The sampled
heap attributes about 83% of its live allocation to the per-encoded-byte padding
comparison. This is an early compiler sample, not a profile of the entire compile
or an isolated latency measurement. Raw source, profile and tool output are retained.

Hypothesis: explicit prefix masks eliminate repeated 17/18-bit comparisons and
reduce compiler cost without changing the public relation. Mutable paths are
`input_scale.go`, its private assignment generator, focused tests and new evidence.
The canonical codec/hash, all eight valid input byte vectors, 33 public fields,
capacity roster, rule/MLP/block circuits and historical artifacts stay frozen.
The new source and setups have new identities; old proofs are not reassigned.

For a Boolean vector `a`, constrain every difference `a[i-1] - a[i]` to be Boolean
and constrain its sum to the required count. A 0-to-1 transition would produce
minus one, so the only allowed vector is exactly that many leading ones followed
by zeros. The lengths are far below the scalar modulus; sums cannot wrap. Keep
the existing count range checks. Apply this relation separately to input-unit
coverage and encoded-byte coverage. Input coverage controls canonical byte
packing; encoded coverage uses the already constrained final prefix position.
Inactive units and encoded padding must remain zero. Every active indexed read,
CBOR header, byte range and SHA-256 constraint stays in the circuit.

This changes the private witness representation only. The generator appends
unit/encoded masks; the public assignment remains 33 fields. Tests include every
four-element Boolean mask against every count, non-Boolean masks and real prover
attempts with wrong mask counts, gaps and hidden nonzero padding. Gap forgeries
preserve the mask sums and adjust the other witness fields, so a count check alone
cannot explain their rejection. Native vectors must exactly match the prior
public values, bytes, CBOR data and positions before execution.

First run the smallest fixture. Then repeat the eight actual boundary proofs,
fresh verification and all public/key/proof mutations under the frozen candidate.
Require lower intermediate constraint counts and retain the bounded maximum
compile regardless of outcome. A cutoff, crash or timeout remains a failed
maximum feasibility result; it cannot qualify the full encoder or select a backend.

Keep the prior 5,840-second charge including the entire memory-cutoff reservation.
Reserve 180 seconds for diagnosis and 600 for this candidate, leaving 580 seconds
unreserved in the existing 7,200-second local proving allocation. The candidate
run is capped at 420 seconds total, 120 seconds per setup/batch and 90 seconds for
maximum compilation, four threads, a 14 GiB live cutoff under the 16 GiB ceiling,
4 GiB new artifacts and 40 GiB total retained storage. No new dependency, token
access, private input, paid compute or scheduler is involved. Ordinary HF T4/L4
fallback remains available under the existing separate authority; no job has
been launched and no GPU speedup for this CPU-only gnark path is assumed.

The first candidate command generated all eight proofs, but its controller failed
after the larger proving batch: the worker exited normally while its last memory
sample was unavailable. Preserve that failed run. A separate native diagnosis
observed `ESRCH` during normal exit. Extend the mutable paths to the shared worker
and its tests: preserve native errno and resolve an absent-process sample only
when the child is reaped with an actual normal exit. A still-live child is killed
and rejected; generic unresolved sample failures and peak-RSS checks still reject.
This changes process accounting, not a verifier, circuit or acceptance relation.

A new recovery identity freezes the corrected worker and separately pins the
existing binary, setup, five unverified proofs and public assignments. Verify
those artifacts in fresh processes, then run the previously unexecuted 32-byte
and maximum compile probes. Do not repeat setup/proving or rewrite the original
failure. Recovery is capped at 120 seconds within the same 600-second reservation.
