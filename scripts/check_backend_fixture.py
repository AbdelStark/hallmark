"""Check installed backend contracts without executing or qualifying a backend."""

import json
import sys
from pathlib import Path

from hallmark.backend import BackendQualification, validate_backend_files
from hallmark.errors import HallmarkError
from hallmark.manifests import ArtifactDigest


def check(path):
    fixture = json.loads(path.read_text())
    backend = BackendQualification.decode(bytes.fromhex(fixture["cbor_hex"]))
    expected = ArtifactDigest(bytes.fromhex(fixture["identity_hex"]))
    assert backend.identity() == expected
    files = {name: bytes.fromhex(raw) for name, raw in fixture["files"].items()}
    args = dict(
        expected_backend=expected,
        required_programs=backend.supported_programs,
        require_zero_knowledge=False,
        files=files,
        max_bytes=sum(map(len, files.values())),
    )
    validate_backend_files(backend, **args)
    for mutation in (
        {"expected_backend": b"x" * 32},
        {"required_programs": (b"x" * 32,)},
        {"require_zero_knowledge": True},
        {"files": {}},
        {"max_bytes": 0},
    ):
        try:
            validate_backend_files(backend, **(args | mutation))
        except HallmarkError:
            continue
        raise AssertionError("backend boundary failure accepted")
    print(
        json.dumps(
            {
                "schema_id": "hallmark/backend-contract-result/1",
                "status": "matched",
                "backend": expected.hex(),
                "negative_checks": 5,
                "qualified_backend": False,
            }
        )
    )


if __name__ == "__main__":
    check(Path(sys.argv[1]))
