# Evidence ledger

Entries distinguish local software results, statistical conclusions, literature reports and proposed work. Never replace a failed entry with a favorable rerun.

## 2026-10-20: bootstrap software checks and negative classifier result

Purpose: exercise the research and integer-execution contracts on harmless amber/violet marker data. Dataset SHA-256: `a7b2c3f3b978623273b72fa3853344b4059725a5b147540c5a1e906a11977ae7`. Fixed config: [fixture](../configs/fixture.json). There are 24 training, 12 calibration and 16 test records, balanced within splits.

Local software evidence: `make check` passes lock validation, Ruff lint/format, strict mypy, 29 tests and local Markdown file-link checks. `make package-check` builds wheel/sdist, checks required contents and installs the wheel with locked core dependencies in a fresh environment, then runs the installed CLI. Host: macOS arm64, Python 3.12.12, uv 0.9.18. Training used one BLAS/OpenMP thread. CI definitions are present; these local results do not establish hosted CI status.

Repeat experiment commands, each with `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1`:

```
uv run --locked --extra train hallmark run configs/fixture.json --output runs/bootstrap-003
uv run --locked --extra train hallmark run configs/fixture.json --output runs/bootstrap-004
uv run --locked hallmark audit-run runs/bootstrap-003 --dataset fixtures/smoke.jsonl --expected-manifest 4326f9b8987b6e465ab2bc32d15d2a94eef76d3c21c1ff8b79bc6f36a8fe9088
diff -qr runs/bootstrap-003 runs/bootstrap-004
```

Both complete run directories were byte-identical, with manifest SHA-256 `4326f9b8987b6e465ab2bc32d15d2a94eef76d3c21c1ff8b79bc6f36a8fe9088`. Replay returned `research-replay-matched`. Source snapshots identify the exact pre-publication code; the later CLI type annotation changes no arithmetic. Runs remain local and gitignored, not hosted evidence.

Negative result: threshold `-273`; calibration TP=6, FP=0, TN=6, FN=0; test TP=8, FP=8, TN=0, FN=0. Test FPR is 1.0. The report correctly says `insufficient-evidence`; this is not a useful classifier result. The fixture includes split names in its text, a visible distribution shift/confound for the weak byte baseline. That is a candidate explanation, not an experimentally isolated cause. We did not tune the threshold or change the fixture after seeing test outcomes. Even a perfect result on eight benign examples would lack power for a 1% FPR claim.

Earlier bootstrap-001/002 were also retained; repeated model/prediction/result files matched. Tamper tests reject changed reports under the original hash and mathematically inconsistent reports even after rehashing a bundle. Those checks exercise software integrity/replay only. No real safety-policy, hardware or proof result is claimed.

Hosted execution: the first private GitHub run could not start any steps because of an account payment/spending-limit block. This is not a hosted pass or a code-test failure. Billing settings were not changed.

The local Python 3.13 core-only check caught a mypy configuration gap: the optional NumPy import was not exempted when NumPy was absent. Adding it to the existing missing-optional-import override fixes that environment without installing training dependencies into core. The train-enabled environment still checks against installed NumPy types. This is a tooling fix, not a model, data or evaluation change.

Final local matrix: Python 3.12.12 with the train extra, `make check`, 29 passed; fresh Python 3.13.11 core-only environment, `make check`, 28 passed and the optional train test skipped. Both passed strict typing, lint/format and docs checks. Fresh installed-wheel/CLI checks passed on both interpreter versions. Linux/hosted CI remains unexecuted because of the account block; these are local macOS results, not substituted hosted passes.
