# Run and resume guide

Read `AGENTS.md`, `research/STATE.md`, this guide, then the task's spec. Inspect branch, remote and `git status --short` before edits. Preserve other work. Do not use an old agent summary as evidence that a run passed.

## Local gates

```
uv sync --locked --extra train
make check
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 uv run --locked --extra train pytest -m train
make package-check
```

Core tests do not require scikit-learn; the training marker may skip if the extra is absent. The explicit train command and CI train job must execute it. CI has read-only repository permissions and no transcript/artifact upload. No credentials or network model/data calls are required by the tests. Dependency installation and the fresh-environment packaging check may fetch locked software packages; they do not fetch research datasets or models.

## Research run

Freeze config and evaluate a fresh directory. Set BLAS/OpenMP thread variables to 1 for the bootstrap. Save the printed manifest hash outside the bundle. Run `audit-run` with that hash and the exact dataset. Inspect the report's evidence class, counts, uncertainty and missing mechanisms before writing a conclusion. A hash supplied by the bundle's author does not authenticate that author.

Compare repeated runs on model/config/predictions/results, not `source.json` byte equality: git state, Python version and platform metadata can differ and must be explained. Full scientific reproducibility and an independent verifier remain separate gates.

## Failure and interruption

Keep failed output directories. Never overwrite a complete run or repair its hashes in place. Diagnose from a copy, issue a new experiment identity if the protocol changes, and record failed hypotheses in `research/LEDGER.md`. On resume, recheck source/data identity and actual environment; do not continue training from an undocumented checkpoint.

If no authority for a needed resource exists, produce the smallest bounded proposal with host/data/cost/policy/kill criteria. Stop before the download, paid job, hosted API call or upload. Do not start a daemon, scheduler, remote runner or multi-agent campaign merely because this project is agent-native.
