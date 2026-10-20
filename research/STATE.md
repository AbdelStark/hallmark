# Research state

Updated: 2026-10-20. Phase: research software foundation in a public repository, not a deployed or cryptographically verified system. AI-assisted code and research initialization.

## Implemented

Strict dataset/config/integer-model/run contracts; exact group/transcript split checks; canonical typed research hashes and salted byte-exact transcript commitment; optional synthetic-data logistic training/PTQ; full-coverage integer inference; separate calibration; metrics and uncertainty; fresh run bundles; caller-pinned replay; offline conformance/tamper tests; locked distribution and CI definitions. See [ledger](LEDGER.md) for actual commands and results.

W01 / issue #2 adds a separate bounded v1 primitive codec and 22 typed hash domains.
The [evidence](evidence/w01-wire-2026-10-20.json) records 108 codec tests, 137 total
local tests and an isolated installed-wheel codec check. Legacy fixed hashes are
unchanged. This validates value encoding only; artifact schemas and trust remain
separate gates.

W30 / issue #31 adds typed errors and sanitized CLI failures, including argparse,
filesystem/Unicode and child-process errors. Its
[evidence](evidence/w30-errors-2026-10-20.json) records the reproduced path leak,
52 privacy tests, 189 total local tests and an installed CLI error check.
Historical run artifacts remain unchanged; versioned events are still W31.

## Not implemented or established

TEE evidence, authenticated registry, ZK proving/verification, independent verifier implementation, real safety-policy dataset/evaluation, encoder/teacher/student training, proof/compiler qualification, public release licence, production service, deployment, partner approval or any safety guarantee. CI definitions alone are not hosted green checks. CODEOWNERS and agent rules are not enforced sandboxing or branch protection.

## Next bounded task

The [proposed v1 corpus](../SPEC.md) defines the full hybrid POC, with 10 draft RFCs and explicit owner-review gates. Merged [PR #1](https://github.com/AbdelStark/hallmark/pull/1) contains the corpus and [implementation tracker](../docs/roadmap/IMPLEMENTATION.md): 40 work issues, 10 RFC trackers and 102 implementation dependency edges. The [live audit](evidence/spec-publication-2026-10-20.json) checked all issue bodies, labels, milestones, comments and child checklists. This is specification/backlog delivery, not implementation or new scientific evidence; see [decision 0002](../docs/decisions/0002-v1-specification-scope.md). The owner explicitly authorized public repository visibility on 2026-10-20; the standing visibility instruction is in [AGENTS.md](../AGENTS.md).

Local Python 3.12 train-enabled and Python 3.13 core-only baseline gates pass, including isolated wheel checks. Earlier private hosted runs could not start because of an account billing/spending-limit block. After the owner made the repository public, hosted [run 39398412605](https://github.com/AbdelStark/hallmark/actions/runs/39398412605) passed on `48f2d7066b62a42f971cd10dbbc2cdbae720b82e`. Each implementation PR still needs checks on its own commit. Billing settings were not changed.

The owner requested autonomous implementation through `.agents/harness/goal.md`,
sequentially with one issue per PR. #2 is merged in [PR #52](https://github.com/AbdelStark/hallmark/pull/52);
its merge-commit [CI run](https://github.com/AbdelStark/hallmark/actions/runs/39401155509)
passed. After #31 error privacy, the engineering queue is #37 CI enforcement
(reassess its stale billing blocker),
#38 reproducible packaging, #39 spec traceability; re-evaluate the dependency queue
after each delivery. Research, real proofs, genuine hardware and independent
verification remain required for the full MVP.

Next: [W13 / issue #14](https://github.com/AbdelStark/hallmark/issues/14), prepare an admission proposal for exactly one policy/use case: relying party, approved data/licence inventory, group split and power, fixed candidate roster, success/failure criteria and resource budget. The draft proposes one English single-turn prompt-injection assay; the owner and relying party have not adopted it. Use [PROGRAM](PROGRAM.md), [ML-PLAN](../docs/ML-PLAN.md) and [EVALUATION](../docs/EVALUATION.md). No data/model download, external inference, GPU job or background campaign until the missing authority is recorded.

In parallel only when explicitly authorized, qualify a tiny real proof graph before selecting a larger encoder. The goal is a measured statement and cost record, not a mock end-to-end demo. Preserve the hybrid hardware/ZK split and the B1/B2 trust distinction in [SPEC](../docs/SPEC.md).

## Resume

Inspect git state and actual installed environment, read the latest ledger entry, then take one falsifiable gate. Run the smallest relevant negative test. Update this state and the ledger with evidence, limits and a concrete next step. Research-run authority remains [bootstrap-only](AUTHORITY.json); repository visibility follows [AGENTS.md](../AGENTS.md).
