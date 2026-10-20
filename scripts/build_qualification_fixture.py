"""Build a structural protocol marker; no executable or approval evidence."""

import hashlib
import json

from hallmark.manifests import FileRef, FileSHA256
from hallmark.qualification import INPUTS, QualificationLimits, QualificationProtocol


def build():
    refs = {}
    for name in INPUTS:
        raw = f"synthetic {name} marker; never execute".encode()
        refs[name] = FileRef(
            path=name, size=len(raw), sha256=FileSHA256(hashlib.sha256(raw).digest())
        )
    protocol = QualificationProtocol(
        schema_id="hallmark/qualification-protocol/1",
        host="macos-arm64",
        controller_sha256=FileSHA256(bytes(32)),
        **refs,
        limits=QualificationLimits(
            total_seconds=120,
            case_seconds=30,
            verify_seconds=5,
            case_cpu_seconds=30,
            threads=1,
            max_worker_rss_bytes=1024**3,
            max_output_bytes=1024**3,
        ),
    )
    return {
        "schema_id": "hallmark.qualification-contract-fixture/1",
        "fixture_only": True,
        "qualified_backend": False,
        "cbor_hex": protocol.encode().hex(),
        "identity_hex": protocol.identity().hex(),
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
