# 0026 — Pinned staged qualification command

Date: 2026-10-20. Scope: W18 / issue #19.

Hypothesis: the existing real-proof controllers can run in the prescribed order
under one externally pinned protocol and shared resource budget, preserving every
failure and reporting incomplete qualification. The baseline is three standalone
scripts with separate budgets. The mutable paths are the packaged controllers,
CLI, rooted file-reading helper, their tests, schema/marker fixture and documentation.
The Go source, binary, arithmetic and all graph fixtures stay pinned to decision 0025.

`hallmark qualify PROTOCOL --expected-protocol HPROTOCOL --output FRESH_DIRECTORY`
runs installation, rule, MLP and attention block sequentially (18/134/156/233 cases).
It does not import a caller-supplied Python adapter, install software or access the
network. The existing standalone script paths remain compatibility commands.

The strict `hallmark/qualification-protocol/1` record uses the existing `protocol`
hash domain. It binds a controller source inventory, binary, three fixtures,
source/licence review, dependency review, build record, authority record, host
and limits. The hash must come from the approved plan outside the output directory.
A matching hash binds bytes; it does not authenticate approval or establish that
the review documents' claims are correct. Dependencies and the Python environment
remain governed by the locked, reviewed build environment.

Before creating output, validate the protocol, controller identity, declared sizes,
exact file hashes and fixture kinds. Read file references beneath the protocol's
trusted parent directory with descriptor-relative no-follow opens; reject aliases,
nonregular files and detected changes. Retain those exact bytes for execution,
avoiding a verified-file/reopened-file race. The caller must control the ancestor
directories and the output parent against concurrent renaming.

Each child receives the existing network/fork-denied macOS sandbox, a fixed
credential-free environment, CPU/per-file limits and a process-group timeout.
The common deadline shortens each case and each verifier timeout. Measured CPU,
RSS and aggregate output storage reject excess and stop subsequent stages.
Memory and aggregate storage remain postconditions, not hostile-worker OS quotas.
No hard memory isolation or portable Linux sandbox is claimed. Cancellation kills
and reaps the active worker; failures retain costs and a sanitized failure record.
No automatic retry is permitted by this command.

The pass criterion for this increment is all 541 actual worker cases under a fresh
setup/run identity, exact native fixture agreement, boundary/CLI tests and both
installed-package gates. All available stages passing produces `status: incomplete`,
`qualified_backend: false` and exit 3. Configuration failures exit 2; other failures
use the existing typed error mapping. A failure must never create a passing result.

Full admitted encoder runs at empty/near-boundary/maximum length, operational
program/key enrollment, independent verifier/security/hiding evidence and accepted
setup lineage remain missing. The command does not synthesize a BackendQualification
record with placeholder evidence, select a backend or authorize a privacy claim.
Previous results retain their original identities; this controller change requires
a fresh run rather than relabeling the earlier probes. Owner approval of the study
permits this bounded software/run work; acceptance of residual risk remains separate.
