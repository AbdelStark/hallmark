import random

from hallmark.contracts import LinearArtifact
from hallmark.reference import byte_counts, chunks, decision, score


def test_strict_threshold_equality_blocks(model: LinearArtifact) -> None:
    assert score(model, "x") == model.threshold
    assert decision(model, "x")["pass"] is False
    assert decision(model, "a")["pass"] is True


def test_complete_coverage_tail_and_empty(model: LinearArtifact) -> None:
    assert score(model, "aaaax") == 2
    assert score(model, "") == model.bias
    for size in (1, 3, 256, 4096):
        assert b"".join(chunks(bytes(range(256)) * 4, size)) == bytes(range(256)) * 4


def test_integer_runtime_against_separate_histogram_formula(model: LinearArtifact) -> None:
    rng = random.Random(20261020)
    for _ in range(300):
        content = bytes(rng.randrange(128) for _ in range(rng.randrange(80)))
        expected = max(
            model.bias + sum(w * n for w, n in zip(model.weights, byte_counts(c), strict=True))
            for c in chunks(content, model.chunk_bytes)
        )
        assert score(model, content.decode("ascii")) == expected
