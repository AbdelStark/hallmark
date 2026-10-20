.PHONY: check check-train check-conformance test package-check smoke

check:
	uv lock --check
	uv run --locked ruff check .
	uv run --locked ruff format --check .
	uv run --locked mypy
	uv run --locked pytest
	uv run --locked python scripts/check_docs.py
	$(MAKE) check-conformance

check-conformance:
	uv run --locked python scripts/check_conformance.py --corpus tests/vectors/v1/corpus.json --expected-corpus "$$(cat tests/vectors/v1/corpus.id)" --software-only --self-test

test:
	uv run --locked pytest

check-train:
	OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 uv run --locked --extra train pytest -m train --require-train

smoke:
	uv run --locked hallmark validate-data fixtures/smoke.jsonl

package-check:
	uv build
	uv run --locked python scripts/check_package.py
