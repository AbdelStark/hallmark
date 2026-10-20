"""Pinned backend declarations and file bindings; no proof or qualification verdict."""

import hashlib
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from hallmark.contracts import Identifier
from hallmark.errors import HallmarkError
from hallmark.manifests import ArtifactDigest, Digest32, FileRef, _Artifact
from hallmark.wire import WireError

MAX_DEPENDENCIES = 1024
MAX_PROGRAMS = 4096
MAX_METADATA_BYTES = 1024 * 1024


class BackendQualification(_Artifact):
    """RFC-0005 record of claims, not evidence that those claims have been verified."""

    _domain = "backend"
    schema_id: Literal["hallmark/backend/1"]
    source: Digest32
    dependencies: Annotated[
        tuple[FileRef, ...], Field(strict=False, min_length=1, max_length=MAX_DEPENDENCIES)
    ]
    build: Digest32
    proof_system: Identifier
    security_parameters: FileRef
    zero_knowledge: bool
    setup: Digest32
    supported_programs: Annotated[
        tuple[Digest32, ...], Field(strict=False, min_length=1, max_length=MAX_PROGRAMS)
    ]
    public_input_layout: FileRef
    verifier: Digest32
    license_review: Digest32
    security_review: Digest32
    conformance: Digest32
    costs: Digest32

    @model_validator(mode="after")
    def canonical_inventory(self) -> Self:
        paths = tuple(ref.path for ref in self.dependencies)
        if paths != tuple(sorted(set(paths))):
            raise ValueError("dependencies must have sorted unique paths")
        if self.supported_programs != tuple(sorted(set(self.supported_programs))):
            raise ValueError("supported programs must be sorted and unique")
        metadata = (self.security_parameters, self.public_input_layout)
        if any(not 1 <= ref.size <= MAX_METADATA_BYTES for ref in metadata):
            raise ValueError("backend metadata size outside bounds")
        refs = (*self.dependencies, *metadata)
        if len({ref.path for ref in refs}) != len(refs):
            raise ValueError("metadata and dependency paths must be distinct")
        return self


def validate_backend_files(
    backend: BackendQualification,
    *,
    expected_backend: ArtifactDigest,
    required_programs: tuple[ArtifactDigest, ...],
    require_zero_knowledge: bool,
    files: dict[str, bytes],
    max_bytes: int,
) -> None:
    """Check a caller-enrolled record, declared program coverage and exact file bytes.

    The caller authenticates its backend pin outside the supplied record. Opaque
    source/build/setup/review/conformance/cost identities are bound by that pin,
    not resolved here. No executable is loaded, proof checked, review authenticated
    or hiding/security claim established. Files stay in caller-owned memory.
    """
    if type(backend) is not BackendQualification:
        raise WireError("INPUT_INVALID")
    backend = backend._validated()
    if (
        type(expected_backend) is not bytes
        or len(expected_backend) != 32
        or expected_backend != backend.identity()
    ):
        raise HallmarkError("TRUST_MISSING", "enroll")
    if (
        type(required_programs) is not tuple
        or not 1 <= len(required_programs) <= MAX_PROGRAMS
        or any(type(p) is not bytes or len(p) != 32 for p in required_programs)
        or required_programs != tuple(sorted(set(required_programs)))
        or type(require_zero_knowledge) is not bool
        or type(max_bytes) is not int
        or not 0 <= max_bytes <= 2**64 - 1
    ):
        raise WireError("INPUT_INVALID")
    if not set(required_programs) <= set(backend.supported_programs):
        raise HallmarkError("REQUEST_MISMATCH", "bind")
    if require_zero_knowledge and not backend.zero_knowledge:
        raise HallmarkError("TRUST_MISSING", "enroll")
    refs = (*backend.dependencies, backend.security_parameters, backend.public_input_layout)
    if sum(ref.size for ref in refs) > max_bytes:
        raise HallmarkError("LIMIT_EXCEEDED", "verify")
    if (
        type(files) is not dict
        or any(type(path) is not str for path in files)
        or set(files) != {ref.path for ref in refs}
        or any(type(raw) is not bytes for raw in files.values())
    ):
        raise WireError("INPUT_INVALID")
    if sum(map(len, files.values())) > max_bytes:
        raise HallmarkError("LIMIT_EXCEEDED", "verify")
    for ref in refs:
        raw = files[ref.path]
        if len(raw) != ref.size or hashlib.sha256(raw).digest() != ref.sha256:
            raise WireError("INPUT_INVALID")
