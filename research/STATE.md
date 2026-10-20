# Research state

Updated: 2026-10-20. Phase: private software foundation, not a deployed or cryptographically verified system. AI-assisted code and research initialization.

## Implemented

Strict dataset/config/integer-model/run contracts; exact group/transcript split checks; canonical typed research hashes and salted byte-exact transcript commitment; optional synthetic-data logistic training/PTQ; full-coverage integer inference; separate calibration; metrics and uncertainty; fresh run bundles; caller-pinned replay; offline conformance/tamper tests; locked distribution and CI definitions. See [ledger](LEDGER.md) for actual commands and results.

## Not implemented or established

TEE evidence, authenticated registry, ZK proving/verification, independent verifier implementation, real safety-policy dataset/evaluation, encoder/teacher/student training, proof/compiler qualification, public release licence, production service, deployment, partner approval or any safety guarantee. CI definitions alone are not hosted green checks. CODEOWNERS and agent rules are not enforced sandboxing or branch protection.

## Next bounded task

Prepare an admission proposal for exactly one policy/use case: relying party, approved data/licence inventory, group split and power, fixed candidate roster, success/failure criteria and resource budget. Use [PROGRAM](PROGRAM.md), [ML-PLAN](../docs/ML-PLAN.md) and [EVALUATION](../docs/EVALUATION.md). No data/model download, external inference, GPU job or background campaign until the missing authority is recorded.

In parallel only when explicitly authorized, qualify a tiny real proof graph before selecting a larger encoder. The goal is a measured statement and cost record, not a mock end-to-end demo. Preserve the hybrid hardware/ZK split and the B1/B2 trust distinction in [SPEC](../docs/SPEC.md).

## Resume

Inspect git state and actual installed environment, read the latest ledger entry, then take one falsifiable gate. Run the smallest relevant negative test. Update this state and the ledger with evidence, limits and a concrete next step. Current authority is [bootstrap-only](AUTHORITY.json).
