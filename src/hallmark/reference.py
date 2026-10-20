"""Normative integer baseline: UTF-8 byte counts, complete chunk coverage, strict threshold."""

from hallmark.contracts import LinearArtifact


def chunks(content: bytes, chunk_bytes: int) -> tuple[bytes, ...]:
    if type(chunk_bytes) is not int or not 1 <= chunk_bytes <= 4096:
        raise ValueError("chunk_bytes must be an integer in [1,4096]")
    return tuple(content[i : i + chunk_bytes] for i in range(0, len(content), chunk_bytes)) or (
        b"",
    )


def byte_counts(content: bytes) -> tuple[int, ...]:
    counts = [0] * 256
    for byte in content:
        counts[byte] += 1
    return tuple(counts)


def score(artifact: LinearArtifact, text: str) -> int:
    return max(
        artifact.bias + sum(artifact.weights[b] for b in chunk)
        for chunk in chunks(text.encode("utf-8"), artifact.chunk_bytes)
    )


def decision(artifact: LinearArtifact, text: str) -> dict[str, int | bool]:
    value = score(artifact, text)
    return {"score": value, "pass": value < artifact.threshold}
