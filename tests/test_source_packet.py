import hashlib
from pathlib import Path


def test_historical_source_packet_identity(root: Path) -> None:
    expected = {
        "product-requirements.txt": (
            "0b816dd5faac0f09fa353565a1f1445cfd6832333a0e144d7e93fa88f37f0ef7"
        ),
        "ml-engineering.txt": "5343f6d31f40f0aebc9a67adbeb66061b0622e304fe5b8a2eab88b8a170a40b1",
        "hybrid-specification.txt": (
            "cbb42270e5322f8859ed8db64577e38bba28888a60f15d44bc18777f6e22d1e5"
        ),
    }
    for name, digest in expected.items():
        assert hashlib.sha256((root / "research/source" / name).read_bytes()).hexdigest() == digest
