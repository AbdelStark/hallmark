.PHONY: check check-train check-guard check-conformance check-spec check-admission test package-check package-check-train package-check-guard smoke

check:
	uv lock --check
	uv run --locked ruff check .
	uv run --locked ruff format --check .
	uv run --locked mypy
	uv run --locked pytest
	$(MAKE) check-spec
	$(MAKE) check-conformance
	$(MAKE) check-admission

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

smoke:
	uv run --locked hallmark validate-data fixtures/smoke.jsonl

package-check:
	uv run --locked python scripts/reproduce_package.py

package-check-train:
	uv run --locked python scripts/reproduce_package.py --train

package-check-guard:
	uv run --locked python scripts/reproduce_package.py --guard
