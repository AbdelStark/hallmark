# 0044 — Approved fresh small-proof campaign for the G1 candidate

Date: 2026-10-21. W18 / issue #19.

The owner replied "approved" to the prepared ten-minute Mac-only proof campaign,
at zero spend and without an HF job. Allocate 600 additional local seconds:
two sequential fresh rosters capped at 240 seconds each, 100 seconds for
preflight/build/validation, and 20 seconds of ancillary allowance. The previous
7,200-second proving charge and separate 120-second validation approval remain
intact. The proving allocation becomes 7,800 seconds within the unchanged
six-hour total local envelope. Memory, storage and thread limits do not increase.

Hypothesis: the corrected bounded G1 candidate preserves actual small commitment
proof acceptance and rejection with fresh setup keys. The baseline consists of
the frozen native vectors, circuit fingerprints and existing rejection roster;
historical proofs cannot qualify the new build. Mutable paths are a fresh local
controller copy, build/output directories and evidence. The default dependency,
candidate patch, circuit, vector semantics and rejection expectations stay fixed.

Copy `scripts/check_gnark_input_scale.py` into a new run directory. Change its
roster deadline from 420 to 240 seconds, omit maximum-capacity compilation and
report that omission explicitly. Preserve all eight small proofs at capacities
8 and 256, all 18 invalid witnesses, all 33 public-input mutations, the field
alias, changed proof, wrong key and capacity-32 compile. Freeze the exact copy,
diff, vectors and worker/source/module identities before execution. This creates
a new experiment identity; it does not revise historical evaluation outcomes.

First verify the retained full module inventory and source pins, global timing
receipts and eight GiB of available retained-storage headroom. Build a separately
pinned candidate worker and run the smallest existing real-proof fixture. Use
four execution threads, a 16 GiB peak ceiling with the existing 14 GiB sampled
stop, 256 MiB per file, four GiB output per roster and 40 GiB total storage.
Keep one foreground worker, all failure artifacts and exact numeric costs.

Repeat only after the first roster passes. Enroll each generated verification
key, proof and native public-input identity outside the output before fresh
replay workers. Compare substantive circuit/vector identities across runs;
randomized setup keys and proof bytes need not match. Reject any source mismatch,
unexpected acceptance, resource excess or monitor failure. Do not tune or weaken
the roster after seeing a result. The existing software conformance expectations
remain unchanged; full repository/package gates follow within the allowance.

This approval supplies no maximum-size setup/proof, additional cloud job, complete
encoder qualification, independent verifier/security/hiding review, accepted
setup lineage or genuine hardware evidence. Publication remains research evidence
on the existing draft PR, not a backend selection or policy release.
