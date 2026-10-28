"""Bounded file/hash checks for the public reference collection; no proof acceptance here."""

import hashlib
import tarfile
from pathlib import Path, PurePosixPath

LIMIT = 2 * 1024**3


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def relative(name):
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or path.as_posix() != name
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise ValueError("unsafe reference path")
    return path


def inventory(root):
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("reference symlink")
        if path.is_file():
            files[path.relative_to(root).as_posix()] = dict(
                bytes=path.stat().st_size, sha256=sha(path)
            )
    return files


def check_archive(path, expected, destination=None):
    """Check all bytes before extracting only exact regular members to a new directory."""
    if sum(v["bytes"] for v in expected.values()) > LIMIT:
        raise ValueError("reference archive size limit")
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError("reference archive roster mismatch")
        for member in members:
            relative(member.name)
            record = expected[member.name]
            if not member.isfile() or member.size != record["bytes"] or member.size > LIMIT:
                raise ValueError("reference member type/size mismatch")
            with archive.extractfile(member) as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != record["sha256"]:
                    raise ValueError("reference member hash mismatch")
        if destination is not None:
            destination.mkdir(parents=True, exist_ok=False)
            archive.extractall(destination, filter="data")
    return len(members)
