from pathlib import Path

import pytest

from hallmark.contracts import LinearArtifact

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def root() -> Path:
    return ROOT


@pytest.fixture
def model() -> LinearArtifact:
    weights = [0] * 256
    weights[ord("x")] = 3
    weights[ord("a")] = -1
    return LinearArtifact(
        schema_id="hallmark.integer-byte-linear/1",
        policy_id="fixture.marker",
        scope="response",
        chunk_bytes=4,
        weights=tuple(weights),
        bias=-1,
        threshold=2,
        scale=128,
    )
