.PHONY: check test package-check smoke

check:
	uv lock --check
	uv run --locked ruff check .
	uv run --locked ruff format --check .
	uv run --locked mypy
	uv run --locked pytest
	uv run --locked python scripts/check_docs.py

test:
	uv run --locked pytest

smoke:
	uv run --locked hallmark validate-data fixtures/smoke.jsonl

package-check:
	uv build
	uv run --locked python scripts/check_package.py
