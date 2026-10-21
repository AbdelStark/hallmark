"""Frozen finite numerical coverage; no exhaustive proof or transcript claim."""

import itertools
import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


def test_all_numerical_chunk_classes_reproduce(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    builder = runpy.run_path(str(ROOT / "scripts/build_encoder_classes_fixture.py"))
    fixture = builder["build"](builder["NATIVE_PIN"])
    raw = (json.dumps(fixture, sort_keys=True, separators=(",", ":")) + "\n").encode()
    assert raw == (ROOT / "research/probes/gnark/encoder-classes-fixture.json").read_bytes()
    classes = fixture["embedding_classes"]
    assert sorted(token for c in classes for token in c["tokens"]) == list(range(256))
    assert len({tuple(c["embedding"]) for c in classes}) == 4
    expected = {()} | {(i,) for i in range(4)} | set(itertools.product(range(4), repeat=2))
    actual = {tuple(c["units"][: sum(c["unit_active"])]) for c in fixture["cases"]}
    assert actual == expected and len(fixture["cases"]) == 21
    assert all(len(c["trace"]) == 484 and len(c["public"]) == 100 for c in fixture["cases"])
    with pytest.raises(ValueError, match="pin"):
        builder["build"]("0" * 64)
