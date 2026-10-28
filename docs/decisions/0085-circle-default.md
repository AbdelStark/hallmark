# 0085: Circle STARK is the default research workflow

Date: 2026-10-28. Status: owner-selected; local acceptance passed, delivery checks tracked on PR.

The owner explicitly selects Circle STARK as the default and base case for
commands, demos, headlines and documentation. This supersedes the operational
gnark-default choice in decisions 0083/0084 and the completed comparison report.
It does not change the recorded measurements or establish a security ranking.

Hypothesis: default classifier and composed workflows can run entirely with
Circle STARK proofs, without first generating a Groth16 setup or proof. Baseline
is `f613c611cefa9037320082b73777f26c9ec45990`. Preserve all 55 LLM verifier source
pins, the four classifier circuit/compiler sources and Rust engine, the model
exports, arithmetic, thresholds and immutable benchmark plans/data.

Mutable paths: Make dispatch, new native model-preparation/default controllers,
the existing Circle orchestration driver, workbench adapters/catalog/result
views, focused tests, current docs, STATE/LEDGER and new acceptance evidence.
Gnark remains an explicitly selected comparison workflow. Old workflow IDs and
historical results retain their original meaning.

Pass criteria: bare `make e2e` builds/enrolls Circle and generates/verifies nine
proofs with its binding negatives; default retained-input `make e2e-composed`
checks 23 SASH proofs and three new Circle classifier proofs for one request;
web/TUI choose Circle first and validate the actual new result contracts.
There is no Go/py-ecc setup prerequisite for either default classifier path.
Local, distribution, app, docs, exact-head CI, main and Pages gates must pass.
Keep the existing gnark commands available with `BACKEND=gnark`.

Run locally, one proof workflow at a time, four prover threads, at most 30 GiB
sampled worker RSS, 4 GiB per classifier campaign and 1,800 seconds for that
campaign. The classifier controller is capped at two hours; keep 8 GiB free during proving.
Retained LLM composition needs no new paid proof job; fresh LLM jobs keep their
existing admission ceilings and source/parameter checks. No hiding, hardware,
independent qualification or production-policy claim follows from the default.

New acceptance runs have new directories. Existing CPU/GPU measurements remain
labelled with their original source, stateless harness and timing boundaries;
they are not measurements of the new preparation/controller path.

## Acceptance

[The numeric record](../../research/evidence/circle-default-2026-10-28.json)
retains bare Make training/proving, retained-LLM default composition and an actual
browser-launched nine-proof run, with source, enrollment and artifact hashes.
The 55-file LLM identity and classifier engine/compiler identity are unchanged.
Core checks pass 2,588 tests with 50 optional/platform skips; all 56 app tests
pass. Strict docs and core distribution checks pass after correcting three old
anchors. Initial fixture/menu/docs failures are retained, not proof samples.
No new paid jobs or hiding/hardware/qualification claims are introduced.
