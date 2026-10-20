# Contributing privately

Read [AGENTS.md](AGENTS.md), the [canonical spec](SPEC.md) and [evaluation contract](docs/EVALUATION.md). Keep changes bounded and test their negative path. Run `make check` and `make package-check`; run `make check-train` when training or evaluation changes. The latter fails if its required training tests skip or do not execute. Supported interpreters are CPython 3.12, 3.13 and 3.14; CI checks core/package and training separately on each.

Do not add data, weights, secrets, private transcripts or generated run directories to git. A new dependency needs a concrete need and licence/supply-chain review. A model or dataset link is not permission to fetch or redistribute it. Use the locked local environment, never the system interpreter.

Protocol/evaluator changes require a decision, conformance tests and a new experiment identity where comparability changes. Document assumptions and evidence strength. Keep failed experiments in the private evidence ledger. No public licence is granted by this repository; adding collaborators, publishing, external issues/comments and subsequent remote writes require owner authority.

The v1 specification branch and its private implementation issues are authorized by the current bootstrap request. Implementation, data/compute access, collaborators and release remain subject to the recorded admission gates. Link implementation PRs to a work item and RFC; retain failed/unavailable evidence explicitly.
