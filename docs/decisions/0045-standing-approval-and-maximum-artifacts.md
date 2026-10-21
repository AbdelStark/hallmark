# 0045 — Standing execution approval and maximum circuit artifacts

Date: 2026-10-21. W18 / issue #19.

The owner explicitly instructed the agent to stop pausing for repeated approvals,
gave full approval to continue and finish, and reaffirmed Mac-first execution with
HF T4/L4 fallback. This supersedes the agent's per-increment permission barriers.
Future bounded foreground campaigns may proceed under recorded plans without
another micro-budget approval. Historical allocations and failures remain intact;
they are not erased or presented as unused time. Repository visibility stays public.

The `autonomous_execution` entry in AUTHORITY records the new execution envelope.
Its numbers are agent-selected guardrails, not numbers quoted from the owner:
one worker, four execution threads, up to two hours per worker and six hours per
campaign, 32 GiB process RSS with the existing seven-eighths sampled stop, and
128 GiB retained checkout storage. The observed Mac has 48 GiB physical RAM and
over 500 GiB free disk. HF fallback retains the approved T4/L4 classes, with at
most four additional jobs and USD 10 total estimated spend, no automatic retry
or account top-up. Refresh prices before submission. No cloud job is launched
by this decision. The original study proposal and its narrower budget stay fixed.

Scope and source rights still matter: use reviewed public assets and synthetic
inputs, keep credentials and private artifacts local, and record consumed
resources. This is not authority to contact a reviewer, add collaborators, adopt a
production policy, upload private checkpoints or run an ongoing scheduler.

Hypothesis: the unchanged maximum commitment circuit can be serialized, reloaded
and supplied to local setup under the expanded envelope. Baseline: two Linux
compiles reporting 40,015,721 constraints, seven pinned small circuit identities,
and the passed G1 candidate point/proof checks. Mutable paths: the probe's artifact
adapter and dispatch, focused tests, run controllers and evidence. The Boolean
cache/G1 patches, circuit relation, public input layout and native vectors stay fixed.

Add explicit export, inspect and setup-from-compiled operations. Keep the ordinary
256 MiB reader bound; only the maximum commitment profile permits files up to
24 GiB. File type, links, trailing bytes, concurrent changes and exclusive writes
remain checked. The parent enforces per-file OS limits and checks aggregate output;
these are not hard aggregate disk or memory quotas. Separating compilation from
setup preserves the compiled artifact if setup fails and avoids recompilation.

First test a tiny real proof through export, reload and setup, explicit size
boundaries and malformed inputs. Freeze source/binary/module identities before
the maximum run. Export and inspect must agree on constraints and all reported
wire counts; pin the exact circuit hash outside subsequent worker outputs.
Use a 600-second compile/export deadline and 300-second read deadline before
any setup, then derive storage requirements from the actual wire counts. Maximum
setup proceeds only if that bounded plan fits the host/storage envelope. Preserve
all partial files and costs on failure. A successful export or setup is not a
proof; the full admitted encoder and independent security/setup review remain
separate gates. New results have a new experiment identity; prior results are
not relabeled under this plan.
