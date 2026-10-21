# 0043 — Approved additional local validation

Date: 2026-10-21. W18 / issue #19.

The owner approved the pending request and instructed work to resume: "go ahead,
i approve the request for what's needed. resume the goal".

Record 120 additional seconds of Mac-only validation at zero spend. Prioritize
the retained streaming change's full `make check` and core `make package-check`.
Use remaining time for the prepared corrected G1 candidate's build and frozen
point/circuit regression checks. This is a bounded local validation increment,
not a maximum-size setup/proving campaign or another HF job. The six-hour total
local envelope, memory, storage and thread limits remain unchanged.

Keep the earlier two-hour W18 charge, timeout and failed candidate intact. Use a
fresh run directory, pin exact source/dependency/evaluator inputs before commands,
record each command's elapsed time and stop within the new allowance. Reserve
five seconds for preparation/audit overhead. Do not reuse the failed candidate's
modfile: build a fresh complete module copy from the corrected committed patch.

Passing software gates closes the outstanding local validation gap. It does not
qualify the full encoder, maximum setup/proving, independent verifier, accepted
setup lineage or genuine hardware. Any new measured research campaign still
needs its own bounded plan under the owner's current authority.
