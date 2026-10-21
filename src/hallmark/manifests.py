"""V1 model identities and explicit local file checks; no model loading or trust."""

import hashlib
import os
import stat
from pathlib import Path
from typing import Annotated, Any, ClassVar, Literal, NewType, Self, cast

from pydantic import ConfigDict, Field, ValidationError, WithJsonSchema, field_validator

from hallmark.contracts import Contract, Identifier
from hallmark.errors import HallmarkError
from hallmark.wire import (
    DEFAULT_LIMITS,
    Domain,
    H,
    WireError,
    WireLimits,
    WireValue,
    decode,
    encode,
)

ArtifactDigest = NewType("ArtifactDigest", bytes)
FileSHA256 = NewType("FileSHA256", bytes)
_DIGEST_JSON = WithJsonSchema(
    {"type": "string", "pattern": "^[0-9a-fA-F]{64}$", "minLength": 64, "maxLength": 64}
)
Digest32 = Annotated[ArtifactDigest, Field(min_length=32, max_length=32), _DIGEST_JSON]
FileHash32 = Annotated[FileSHA256, Field(min_length=32, max_length=32), _DIGEST_JSON]


def _wire_value(value: Any) -> WireValue:
    if isinstance(value, dict):
        return {key: _wire_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_wire_value(item) for item in value]
    return cast(WireValue, value)


class _Record(Contract):
    model_config = ConfigDict(
        revalidate_instances="always",
        hide_input_in_errors=True,
        ser_json_bytes="hex",
        val_json_bytes="hex",
    )

    def _validated(self) -> Self:
        try:
            return type(self).model_validate(self)
        except ValidationError:
            pass
        raise WireError("INPUT_INVALID")

    def _wire(self) -> WireValue:
        # Recheck instances because Pydantic's construct/copy APIs bypass validation.
        return _wire_value(self._validated().model_dump(mode="python"))

    def encode(self, *, limits: WireLimits = DEFAULT_LIMITS) -> bytes:
        """Return canonical CBOR after full schema revalidation."""
        return encode(self._wire(), limits=limits)

    @classmethod
    def decode(cls, raw: bytes, *, limits: WireLimits = DEFAULT_LIMITS) -> Self:
        """Validate canonical CBOR and this exact schema, without accessing files."""
        value = decode(raw, limits=limits)
        try:
            return cls.model_validate(value)
        except ValidationError:
            pass
        raise WireError("INPUT_INVALID")


class _Artifact(_Record):
    _domain: ClassVar[Domain]

    def identity(self) -> ArtifactDigest:
        """Hash the complete validated artifact in its fixed v1 domain."""
        return ArtifactDigest(H(self._domain, self._wire()))


class FileRef(_Record):
    """Exact bytes at a normalized relative POSIX path; parsing performs no I/O."""

    path: Annotated[
        str,
        Field(
            min_length=1,
            max_length=4096,
            description="Relative POSIX path, at most 4096 UTF-8 bytes; no normalization or links.",
        ),
    ]
    size: Annotated[int, Field(ge=0, le=2**64 - 1)]
    sha256: FileHash32

    @field_validator("path")
    @classmethod
    def normalized_path(cls, path: str) -> str:
        if (
            len(path.encode("utf-8")) > 4096
            or any(part in ("", ".", "..") for part in path.split("/"))
            or any(c in "\\:" or ord(c) < 32 or ord(c) == 127 for c in path)
        ):
            raise ValueError("invalid artifact path")
        return path


class GenerationConfig(_Record):
    """Only deterministic greedy generation is specified by v1."""

    max_new_tokens: Annotated[int, Field(ge=1, le=4096)]
    sampling: Literal["greedy"]
    seed: Annotated[int, Field(ge=0, le=0)]


class ModelManifest(_Artifact):
    """Frozen v1 model record; its identity binds every field, not its provenance."""

    _domain = "model"
    schema_id: Literal["hallmark/model/1"]
    files: Annotated[
        tuple[FileRef, ...],
        Field(
            strict=False,
            min_length=1,
            max_length=4096,
            description="Strictly increasing, unique path order.",
        ),
    ]
    architecture: Digest32
    tokenizer: Digest32
    chat_template: Digest32
    runtime: Digest32
    numerical_mode: Identifier
    generation: GenerationConfig

    @field_validator("files")
    @classmethod
    def ordered_files(cls, files: tuple[FileRef, ...]) -> tuple[FileRef, ...]:
        if any(a.path >= b.path for a, b in zip(files, files[1:], strict=False)):
            raise ValueError("file paths must be sorted and unique")
        return files


def _verify_file(
    root_fd: int, ref: FileRef, seen: set[tuple[int, int]], *, retain: bool = False
) -> bytes:
    parent_fd = os.dup(root_fd)
    try:
        parts = ref.path.split("/")
        for part in parts[:-1]:
            child_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = child_fd
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
        try:
            before = os.fstat(fd)
            inode = (before.st_dev, before.st_ino)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_size != ref.size
                or inode in seen
            ):
                raise HallmarkError("INPUT_INVALID", "verify")
            seen.add(inode)
            digest = hashlib.sha256()
            chunks = []
            size = 0
            while size < ref.size:
                block = os.read(fd, min(65536, ref.size - size))
                if not block:
                    break
                size += len(block)
                digest.update(block)
                if retain:
                    chunks.append(block)
            after = os.fstat(fd)
            if (
                size != ref.size
                or digest.digest() != ref.sha256
                or after.st_nlink != 1
                or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
            ):
                raise HallmarkError("INPUT_INVALID", "verify")
            return b"".join(chunks)
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def verify_model_files(model: ModelManifest, root: Path, *, max_bytes: int) -> None:
    """Check opened files beneath a trusted root within an explicit total read budget.

    Requires POSIX descriptor-relative, no-follow opens. A pass describes these
    reads only; a later loader must independently protect the files it actually uses.
    """
    model = model._validated()
    if type(max_bytes) is not int or not 0 <= max_bytes <= 2**64 - 1:
        raise HallmarkError("INPUT_INVALID", "parse")
    if sum(ref.size for ref in model.files) > max_bytes:
        raise HallmarkError("LIMIT_EXCEEDED", "verify")
    if os.name != "posix" or os.open not in os.supports_dir_fd:
        raise HallmarkError("INPUT_INVALID", "verify")
    try:
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            seen: set[tuple[int, int]] = set()
            for ref in model.files:
                _verify_file(root_fd, ref, seen)
        finally:
            os.close(root_fd)
        return
    except OSError:
        pass
    raise HallmarkError("INPUT_INVALID", "verify")
