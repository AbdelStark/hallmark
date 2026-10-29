# 0090: Circle STARK is the only classifier proof backend

Date: 2026-10-29. Status: owner-requested; local acceptance below.

The owner requests removal of the pairing-based classifier backend: its Go
circuits, separate Python pairing verifier, comparison benchmark and every
workflow that depended on them. Circle STARK (STWO) classifiers already cover the
rule, MLP and CNN statements and are the default ([0085](0085-circle-default.md)).
One backend reduces code, dependencies, CI and documentation to maintain.

Removed: the Go circuit and Python pairing-verifier probe directories, the
benchmark timing overlay and HF campaign helpers, `hallmark qualify` and its
protocol schema, the pairing probe/compile/maximum modules and proof drivers, the
matched benchmark/report/archive scripts and plan, the `BACKEND` Make switch, the
`proof-artifacts` CI job, the two app workflows, their tests, and the decisions,
proposals and evidence that only concerned that backend. The last commit
containing them is `b7b8376b584836f29066708b663006c2cae7328e`; history remains in
git.

Kept unchanged: the four Circle circuit/compiler sources and Rust engine (backend
identity `c035913b…1ded7d`), model exports, arithmetic, thresholds, the rule
program records (moved to `fixtures/rule-program.json`, same classifier and
program identities), caller enrollment pin and request contracts. Run-authority
approval records cited by `research/AUTHORITY.json` are kept as owner policy
history, with mentions of the removed files reworded.

Pruned: remaining Circle, LLM and training evidence records no longer list
source hashes, files, commands or comparison rows for the removed backend; no
other field changed. Their original bytes are at `b7b8376`. A recorded identity
that hashed a full source inventory is recomputable only from that commit.

Changed identity: the native LLM verifier inventory now lists only the 17 files
the verifier loads, instead of every `src/hallmark` module, so unrelated package
edits stop changing it. Its identity becomes `5ba4d1f4…6bda3e09`. Signed LLM
parameter enrollments bound to the earlier identity need a new owner signature,
and the `circle-reference-2026-10-28` release verifies from a checkout of
`b7b8376`, whose LLM verifier identity `8567c911…02b342a` matches its manifest.
The shared worker sandbox is now `hallmark._worker`; its cost records use
`hallmark.worker-cost/1`.

Pass criteria: `make check` and train/app/docs/package gates pass; the Circle
statements and programs are byte-identical to the previous commit; bare `make e2e`
still produces nine freshly verified Circle proofs with the same caller enrollment
pin. No security, hiding, hardware or qualification claim changes.

## Acceptance

Local Mac, 2026-10-29. `make check` passes (2,162 tests, 46 optional skips, spec,
conformance and admission); `make check-train` 61 tests; `make check-demo` 55
tests; `make docs` 142 pages with no issues; `make package-check` passes under the
recorded uv 0.9.18. On six prompts with synthetic exports, the previous commit and
this change produce identical classifier and policy identities, native rows and
compiled Circle programs, so engine enrollment is unchanged.

Bare `make e2e` (pinned nightly-2025-07-14, uv 0.9.18, CPython 3.12.12) freshly
trains, builds both Circle targets and generates nine proofs. All nine are freshly
verified; 63 public-input mutations, 18 cross-request substitutions and three
invalid rosters reject. Verdicts are `[1,1,1]`, `[1,1,0]`, `[0,1,1]`, and the caller
enrollment pin is the unchanged `56c29c74…6cd635e`. The controller takes 289.78 s.
This is one local observation, not a timing distribution. Hosted CI receipts are
tracked on the PR.
