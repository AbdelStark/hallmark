"""Archive checks are transport checks; real cryptographic acceptance is a separate run."""

import hashlib
import io
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from record_reference import measured
from reference_files import check_archive, relative
from verify_reference import run


def archive(path, names):
    with tarfile.open(path, "w:gz") as stream:
        for name, kind in names:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = 2 if kind == tarfile.REGTYPE else 0
            member.linkname = "../../outside"
            stream.addfile(member, io.BytesIO(b"ok") if member.size else None)
    return {"proof.json": dict(bytes=2, sha256=hashlib.sha256(b"ok").hexdigest())}


def test_archive_requires_exact_bytes_before_new_directory_extract(tmp_path):
    path = tmp_path / "a.tar.gz"
    expected = archive(path, [("proof.json", tarfile.REGTYPE)])
    target = tmp_path / "extracted"
    assert check_archive(path, expected, target) == 1
    assert (target / "proof.json").read_bytes() == b"ok"
    with pytest.raises(FileExistsError):
        check_archive(path, expected, target)
    expected["proof.json"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash mismatch"):
        check_archive(path, expected, tmp_path / "bad")
    assert not (tmp_path / "bad").exists()


@pytest.mark.parametrize(
    "members",
    [
        [("../proof.json", tarfile.REGTYPE)],
        [("proof.json", tarfile.SYMTYPE)],
        [("proof.json", tarfile.LNKTYPE)],
        [("proof.json", tarfile.REGTYPE)] * 2,
        [("proof.json", tarfile.REGTYPE), ("extra.json", tarfile.REGTYPE)],
    ],
)
def test_archive_rejects_changed_roster_or_links(tmp_path, members):
    path = tmp_path / "a.tar.gz"
    expected = archive(path, members)
    with pytest.raises(ValueError):
        check_archive(path, expected, tmp_path / "bad")
    assert not (tmp_path / "bad").exists()


@pytest.mark.parametrize("name", ["../proof", "/proof", "a/../proof", "a//proof", "./proof"])
def test_noncanonical_paths_reject(name):
    with pytest.raises(ValueError):
        relative(name)


def test_reference_rejects_wrong_external_pin_before_proof_build(tmp_path):
    (tmp_path / "reference-manifest.json").write_text("{}")
    with pytest.raises(ValueError, match="external reference manifest pin"):
        run(tmp_path, "0" * 64)


def test_observer_preserves_return_and_failure():
    events = []
    wrapped = measured("fixture", lambda x: x + 1, events)
    assert wrapped(1) == 2 and events[0]["status"] == "passed"

    def fail():
        raise RuntimeError("retained failure")

    with pytest.raises(RuntimeError, match="retained failure"):
        measured("failed", fail, events)()
    assert events[-1]["status"] == "failed" and events[-1]["seconds"] >= 0
