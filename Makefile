.PHONY: e2e check check-train check-guard check-comparison check-conformance check-spec check-admission test package-check package-check-train package-check-guard package-check-comparison smoke

check:
	uv lock --check
	uv run --locked ruff check .
	uv run --locked ruff format --check .
	uv run --locked mypy
	uv run --locked pytest
	$(MAKE) check-spec
	$(MAKE) check-conformance
	$(MAKE) check-admission

e2e:
	uv run --locked --python 3.12.12 --extra train python scripts/run_e2e.py

check-admission:
	uv run --locked python scripts/check_admission.py

check-spec:
	uv run --locked python scripts/check_spec.py

check-conformance:
	uv run --locked python scripts/check_conformance.py --corpus tests/vectors/v1/corpus.json --expected-corpus "$$(cat tests/vectors/v1/corpus.id)" --software-only --self-test

test:
	uv run --locked pytest

check-train:
	OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 uv run --locked --extra train pytest -m train --require-train

check-guard:
	OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 uv run --locked --extra guard python scripts/check_guard.py
	OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 uv run --locked --extra guard pytest tests/test_guard.py

check-comparison:
	OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 uv run --locked --extra train --extra guard python scripts/check_comparison_run.py
	OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 uv run --locked --extra train --extra guard pytest tests/test_comparison_run.py

smoke:
	uv run --locked hallmark validate-data fixtures/smoke.jsonl

package-check:
	uv run --locked python scripts/reproduce_package.py

package-check-train:
	uv run --locked python scripts/reproduce_package.py --train

package-check-guard:
	uv run --locked python scripts/reproduce_package.py --guard

package-check-comparison:
	uv run --locked python scripts/reproduce_package.py --train --guard
