"""Frozen native-vector checks and fail-closed scheduling; stubs are not proof evidence."""

import json
import runpy
from pathlib import Path

import pytest

from hallmark import _gnark_maximum as maximum
from hallmark._gnark_probe import PinnedArtifact, digest, stream_regular


def test_retention_copies_failed_and_complete_outputs_with_source_pins(tmp_path):
    source, target = tmp_path / "local", tmp_path / "bucket"
    (source / "failed").mkdir(parents=True)
    (source / "failed" / "partial.bin").write_bytes(b"partial circuit")
    (source / "result.json").write_bytes(b'{"status":"incomplete"}')
    maximum.retain_outputs(source, target)
    receipt = json.loads((target / "retention.json").read_text())
    assert receipt["total_bytes"] == 38
    assert set(receipt["files"]) == {"failed/partial.bin", "result.json"}
    for name, pin in receipt["files"].items():
        assert (target / name).read_bytes() == (source / name).read_bytes()
        assert stream_regular(target / name, 100) == pin
    with pytest.raises(FileExistsError):
        maximum.retain_outputs(source, target)


@pytest.mark.parametrize("kind", ["file-link", "directory-link", "oversize"])
def test_retention_rejects_unsafe_source_without_completion_record(tmp_path, monkeypatch, kind):
    source, target = tmp_path / "local", tmp_path / "bucket"
    source.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "private").write_bytes(b"must not copy")
    if kind == "file-link":
        (source / "linked").symlink_to(outside / "private")
    elif kind == "directory-link":
        (source / "linked").symlink_to(outside, target_is_directory=True)
    else:
        monkeypatch.setattr(maximum, "MAX_FILE", 1)
        (source / "large").write_bytes(b"xx")
    with pytest.raises((OSError, ValueError)):
        maximum.retain_outputs(source, target)
    assert not (target / "retention.json").exists()
    assert not list(target.rglob("private"))


@pytest.mark.parametrize("count", [0, 1, 23, 24, 255, 256, 32767, 32768])
def test_maximum_fixture_matches_existing_canonical_native_vectors(count):
    reference = runpy.run_path(
        str(Path(__file__).parents[1] / "scripts/check_gnark_input_scale.py")
    )
    units = bytes(i % 256 for i in range(count))
    expected = reference["vector"](32768, units)
    actual = maximum.vector(units)
    assert actual == expected
    assert maximum.assignment(actual) == reference["assignment"](expected)
    assert maximum.assignment(actual, False) == reference["assignment"](expected, False)


def test_negative_roster_changes_exactly_one_witness_field():
    rows = maximum.fixtures()
    assert len(rows) == 12
    assert sum(valid for _, valid in rows.values()) == 3
    for name, (row, valid) in rows.items():
        if valid:
            continue
        original = rows["empty" if name == "empty-padding" else "maximum"][0]
        assert sum(a != b for key in row for a, b in zip(row[key], original[key], strict=True)) == 1


@pytest.mark.parametrize(
    "failure", [None, "network-smoke", "maximum-export", "maximum-setup", "changed-public-32"]
)
def test_failure_cannot_complete_maximum_campaign(tmp_path, monkeypatch, failure):
    binary = tmp_path / "probe"
    binary.write_bytes(b"fixture worker identity")
    circuit = b"fixture circuit"
    monkeypatch.setattr(maximum, "CIRCUIT_SHA", digest(circuit))
    monkeypatch.setattr(maximum, "container_memory_limit", lambda required: 186_000_000_000)
    names = []

    def invoke(command, work, **kwargs):
        names.append(work.name)
        work.mkdir()
        for name, value in (kwargs.get("inputs") or {}).items():
            if isinstance(value, PinnedArtifact):
                value.copy_to(work / name, maximum.MAX_FILE)
            else:
                (work / name).write_bytes(value)
        if work.name in ("tiny-setup", "other-key", "maximum-setup"):
            for name in ["circuit.r1cs", "pk.bin", "vk.bin"]:
                if not (work / name).exists():
                    (work / name).write_bytes(circuit if name == "circuit.r1cs" else b"fixture-key")
        if work.name == "maximum-export":
            (work / "circuit.r1cs").write_bytes(circuit if failure != work.name else b"changed")
        if work.name == "tiny-prove":
            (work / "proof.bin").write_bytes(b"fixture-proof")
        if work.name == "maximum-batch":
            for name in ["empty", "near", "maximum"]:
                (work / (name + ".proof")).write_bytes(b"fixture-proof")
        negative = work.name in (
            "tiny-changed",
            "field-alias",
            "changed-proof",
            "wrong-key",
        ) or work.name.startswith("changed-public-")
        code = int(negative)
        if failure == work.name and work.name != "maximum-export":
            code = 1 - code
        (work / "stdout.txt").write_text(
            json.dumps({"status": "passed" if code == 0 else "failed"})
        )
        return {
            "exit_code": code,
            "within_limits": True,
            "files": {p.name: stream_regular(p, maximum.MAX_FILE) for p in work.iterdir()},
        }

    monkeypatch.setattr(maximum, "invoke", invoke)
    output = tmp_path / "out"
    if failure:
        with pytest.raises(ValueError):
            maximum.check(binary, digest(binary.read_bytes()), output)
    else:
        maximum.check(binary, digest(binary.read_bytes()), output)
        assert len([name for name in names if name.startswith("changed-public-")]) == 33
        assert names[-1] == "wrong-key"
    report = json.loads((output / "result.json").read_text())
    assert report["full_input_proof"] == (failure is None)
    assert report["qualified_backend"] is False
    if failure:
        assert names[-1] == failure
        assert report["status"] == "incomplete"
