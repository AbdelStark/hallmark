# 0091: Audit fixes for paid runs, verifier boundaries and lost tests

Date: 2026-10-29. Status: owner-requested; implemented and validated on main.

The owner requested fixes for every finding of the 2026-10-29 whole-repository
audit ([tracking issue #159](https://github.com/AbdelStark/hallmark/issues/159)).
The audit found no wrong acceptance in the Circle classifier path, the wire
decoder or the signature checks. The fixes, merged as PRs #160–#165 and this
record's PR, change three recorded contracts.

**Paid LLM ceilings.** HF bills a job's Starting window, and the controller
cancels a job only at its timeout plus 600 s. `planned_cost` now counts that
window once for every caller; the duplicate wrappers are gone. At the recorded
prices the startup-inclusive worst case of `make e2e-llm` is $2.27, above the
earlier $2.10 CLI ceiling and inside the $2.50 the workbench already used for the
same workflow. The CLI and composed paths now use that $2.50 ceiling. The GPU
benchmark bound ($4.66) is unchanged. `DELETED` is a terminal job stage; paid
GPU runs check local verifier prerequisites before creating any job; the one-off
credit-check exception flag from 0088/0089 is removed.

**Native LLM mutation suite.** Changed prompt and changed model root were
rejected only by the Python pre-check. Two native-only variants now require the
compiled verifier itself to reject them while all 23 proofs still verify. The
native suite grows from 38 to 40 cases (38 rejections); the Linux suite is
unchanged. [Evidence](../../research/evidence/llm-native-mutations-2026-10-29.json)
records the first run on the published proofs.

**Verifier-side boundaries.** Registry enrollment now enforces successor rules
between consecutive snapshots, so a retired entry cannot be revived or dropped.
Proof workers may signal only processes in their own sandbox. The verifier time
budget applies to `circle-verify` again, and a directory in a work directory no
longer loses the cost record. CNN admission rejects any export whose per-site
integer bound could leave int32; the frozen CNN passes. The worker runner tests
deleted with the pairing backend are restored, and the CNN circuit and Rust
verifier rejection paths now have tests in CI.

**Identities.** The Circle backend identity `c035913b…1ded7d`, the caller
enrollment pin, models, thresholds, proof relations and the LLM case are
unchanged. The native LLM verifier identity becomes `39d2ee50…5879ef`, because
`_worker.py`, `run_llm_e2e.py`, `classifier_manifest.py` and `uv.lock` are in its
inventory. Signed LLM enrollments need a new owner signature, as in 0090. The
unused `pytest-cov` dependency is removed under a new
[dependency review](../../research/evidence/dev-dependency-removal-2026-10-29.json).

## Acceptance

[Numeric record](../../research/evidence/audit-fixes-validation-2026-10-29.json),
local Mac, main `1bc6b72` with all six fix PRs merged. Bare `make e2e` passes in
253.87 s: nine fresh Circle proofs, 63 public-input mutations, 18 substitutions
and three rosters rejected, enrollment pin unchanged. The documented conformance
command passes in 187.60 s: ten boundaries, 22 invalid witnesses rejected by
constraint checks and three maximum-input proofs freshly verified. Native LLM
verification of the published proofs passes in 203.59 s with identity
`39d2ee50…`: 23 proofs, 22 links, two honest checks and all 38 mutations
rejected, including the two statement mutations. `make check` (2,251 tests, 45
optional skips), `check-train` (63), `check-demo` (60), `docs` (147 pages) and
`package-check` pass. One false mypy error came from a stale local cache and
passes with a clean cache. These are single local observations, not timing
distributions. No cloud job, spend, hardware, hiding or qualification claim.
