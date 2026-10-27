# 0082: Shared controller for terminal and web demos

Date: 2026-10-27. Status: implemented; local acceptance passed.

## Objective and acceptance

Build a usable TUI and web app for the complete existing proof workflows, with
live stages, logs, local resource measurements, cloud-job status, retained runs,
results and artifacts. Both interfaces use one controller and workflow catalog.
Adding another workflow must not require duplicating lifecycle logic in either UI.

Acceptance requires real process execution from both interfaces, a fresh complete
classifier proof run, retained real LLM verification, explicit paid-job plans,
cancellation/error/reconnection tests, responsive rendered web review and terminal
keyboard testing. A software smoke or replay cannot substitute for the proof runs.
The web app is local-first; publishing a remotely executable proving service is
outside this change. Existing research/source/parameter admission stays in force.

## Architecture

`apps/` is an independently locked Python project. Textual provides the TUI;
the web client uses local HTML/CSS/JavaScript and the same localhost HTTP API.
A workflow catalog owns commands, stages, prerequisites and result contracts.
A run manager owns process lifecycle, retained events, monitoring and results.
Thin clients render snapshots and invoke start/cancel; they do not implement
proof logic. Existing frozen drivers remain the execution authority.

The server binds loopback, checks Host/Origin and requires a per-process token
for mutations. It exposes only explicitly admitted artifacts, never arbitrary
filesystem paths or shell commands. Secrets are redacted from streamed logs.
One run executes at a time. Closing a browser leaves its foreground server and
run active; stopping the server requests driver cleanup before exiting.

Progress reflects observed stages, not invented percentages. Local process-tree
RSS/CPU samples are labelled local. HF status comes from retained job records
and driver output; no remote utilization is inferred. Verification validity,
policy verdict and cleanup status are separate fields.

## Frozen baseline and work bounds

Baseline: `675c99af66067d129dac30d6acc6612f4e392e68`. Mutable paths: `apps/`,
Make targets, distribution roots, CI, app guides, STATE/LEDGER and this decision.
Proof drivers, model/data/evaluator inputs and the inference lock stay frozen.
In particular, adding UI code must not change the enrolled native-verifier
source inventory. No protocol or benchmark number changes are authorized by
this UI decision.

First validate orchestration using tiny local subprocess fixtures, then execute
the frozen Mac classifier run (driver bound: two hours, 12 GiB free, no cloud).
Retained LLM verification uses existing admitted public artifacts and the native
verifier's resource bounds. No new paid job is required to test the UI initially;
paid execution retains existing live balance, price, timeout and resource gates.
Preserve every failed attempt and raw record before writing delivery claims.


## Paid-run cost admission

The original CPU CLI's $2.10 estimate accounts for worker timeouts. On 2026-10-27,
live prices give a $1.96 timeout-only bound and $2.27 after reserving 600 seconds
of provider creation/cancellation time per phase. Under the owner's standing
bounded-HF-work approval, the app uses an agent-selected $2.50 startup-inclusive
ceiling for LLM/composed runs. This is not a quotation of a numeric owner limit.
No jobs had started when this correction was made. Historical CLI records and
proving parameters remain unchanged. The GPU app ceiling remains $5.

A small app adapter runs in the proof environment, admits the startup-inclusive
price plan, records it in the monitoring directory, then calls the unchanged
original driver. It does not change model inputs, proof parameters, phase
resource limits or automatic-retry policy. The app still reports estimates,
not invoices; no automatic recharge is enabled or authorized.

## Acceptance evidence

The [QA record](../../research/evidence/demo-workbench-2026-10-27.json) records
three successful real proof workflows: fresh classifier proving from the TUI,
native retained-LLM verification from the web app, and a fresh complete paid LLM
run from the web app. The last produces all 23 segments, accepts two honest
checks, rejects 14 mutations, and confirms all three jobs terminal with buckets
deleted. Recorded running compute is $0.31, not an invoice. Final app tests,
rendered/keyboard review and distribution/docs checks pass; hosted and merge
identities are recorded on PR #129. GPU/composed complete campaigns were not
rerun. Proof/model/evaluator inputs and the 55-file native identity are unchanged.
