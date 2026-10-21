"""Build a synthetic backend declaration, not a qualified backend or proof result."""

import hashlib
import json
from pathlib import Path

from hallmark.backend import BackendQualification
from hallmark.manifests import ArtifactDigest, FileRef, FileSHA256
from hallmark.wire import H

ROOT = Path(__file__).resolve().parents[1]


def build():
    files = {
        "dependencies/source.txt": b"Hand-authored dependency marker; no backend source.\n",
        "metadata/security.json": b'{"fixture_only":true,"reviewed":false}\n',
        "metadata/public-input-layout.json": (
            ROOT / "docs/schemas/proof-input-layout-v1.json"
        ).read_bytes(),
    }

    def ref(path):
        raw = files[path]
        return FileRef(path=path, size=len(raw), sha256=FileSHA256(hashlib.sha256(raw).digest()))

    def marker(name):
        return ArtifactDigest(H("backend", ["synthetic-unqualified-marker", name]))

    backend = BackendQualification(
        schema_id="hallmark/backend/1",
        source=marker("source"),
        dependencies=(ref("dependencies/source.txt"),),
        build=marker("build"),
        proof_system="synthetic-fixture",
        security_parameters=ref("metadata/security.json"),
        zero_knowledge=False,
        setup=marker("setup"),
        supported_programs=tuple(sorted((marker("program-a"), marker("program-b")))),
        public_input_layout=ref("metadata/public-input-layout.json"),
        verifier=marker("verifier"),
        license_review=marker("licence-review"),
        security_review=marker("security-review"),
        conformance=marker("conformance"),
        costs=marker("costs"),
    )
    return {
        "schema_id": "hallmark/backend-contract-fixture/1",
        "fixture_only": True,
        "qualified_backend": False,
        "purpose": "Structural binding checks only; no real dependency, review or proof.",
        "cbor_hex": backend.encode().hex(),
        "identity_hex": backend.identity().hex(),
        "files": {path: raw.hex() for path, raw in files.items()},
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
