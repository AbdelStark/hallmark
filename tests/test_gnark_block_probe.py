"""Offline operator-block boundaries; real proof results are separate evidence."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from hallmark import _gnark_block_probe as probe

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "research/probes/gnark/block-fixture.json"


def test_frozen_exhaustive_fixture_and_signed_transport():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_gnark_block_fixture.py")],
        capture_output=True,
        check=True,
        timeout=10,
    )
    assert result.stdout == FIXTURE.read_bytes()
    value = probe.validate_fixture(result.stdout)
    cases = {tuple(c["public"][:4]): c for c in value["cases"]}
    for inputs, case in cases.items():
        private = probe.assignment(case, True).splitlines()
        public = probe.assignment(case, False).splitlines()
        assert len(public) == 5 and len(private) == 94 and private[:5] == public
        assert [int(n) - 2**31 for n in private[5:]] == case["trace"]
        assert all(str(int(n)).encode() == n for n in private)
        a, b, x, y = inputs
        assert case["score"] == cases[b, a, y, x]["score"]
        for replacement in range(4):
            if not x:
                assert case["score"] == cases[replacement, b, x, y]["score"]
            if not y:
                assert case["score"] == cases[a, replacement, x, y]["score"]
        if x == y == 0:
            assert case["score"] == 0
        trace = [
            n for name in value["graph"]["trace_order"] for row in case["layers"][name] for n in row
        ]
        assert trace == case["trace"]
    # Hand-derived single-token results exercise negative max pooling and signed half ties.
    assert cases[1, 0, 1, 0]["score"] == -6
    assert cases[2, 0, 1, 0]["score"] == 8
    assert cases[2, 0, 1, 0]["layers"]["pool_max"] == [[-2, 1]]


@pytest.mark.parametrize(
    "fault",
    [
        "schema",
        "qualified",
        "missing-case",
        "duplicate",
        "name",
        "graph",
        "token",
        "mask",
        "score",
        "public-length",
        "trace-length",
        "bool",
        "negative",
        "overflow",
    ],
)
def test_invalid_or_incomplete_fixture_rejects(fault):
    value = json.loads(FIXTURE.read_text())
    case = value["cases"][0]
    if fault == "schema":
        value["schema_id"] = "unknown"
    elif fault == "qualified":
        value["qualified_backend"] = True
    elif fault == "missing-case":
        value["cases"].pop()
    elif fault == "duplicate":
        value["cases"][-1] = case
    elif fault == "name":
        case["name"] = "../escape"
    elif fault == "graph":
        value["graph"]["inverse"][0] = 1
    elif fault in ("token", "mask", "score"):
        case["public"][{"token": 0, "mask": 2, "score": 4}[fault]] = {
            "token": 4,
            "mask": 2,
            "score": 0,
        }[fault]
    elif fault in ("public-length", "trace-length"):
        case[fault.split("-")[0]].pop()
    else:
        case["trace"][0] = {"bool": False, "negative": -(2**31) - 1, "overflow": 2**31}[fault]
    with pytest.raises(ValueError):
        probe.validate_fixture(json.dumps(value).encode())


def test_stale_pins_reject_before_writing_and_crashes_are_retained(tmp_path, monkeypatch):
    monkeypatch.setattr(probe.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(probe.platform, "machine", lambda: "arm64")
    binary = tmp_path / "binary"
    binary.write_bytes(b"harmless fixture, never executed")
    binary_pin, fixture_pin = probe.digest(binary.read_bytes()), probe.digest(FIXTURE.read_bytes())
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="identity"):
        probe.check(binary, binary_pin, FIXTURE, "0" * 64, output)
    assert not output.exists()
    monkeypatch.setattr(
        probe,
        "invoke",
        lambda *_args, **_kw: {
            "exit_code": -6,
            "timed_out": False,
            "max_rss_bytes": 1,
            "files": {},
        },
    )
    with pytest.raises(ValueError, match="process"):
        probe.check(binary, binary_pin, FIXTURE, fixture_pin, output)
    assert len(json.loads((output / "failure.json").read_text())["cases"]) == 1
    assert not (output / "result.json").exists()
    with pytest.raises(FileExistsError):
        probe.check(binary, binary_pin, FIXTURE, fixture_pin, output)


def test_cli_does_not_leak_a_failed_input_path(tmp_path):
    private_path = tmp_path / "private-path-marker"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_gnark_block_probe.py"),
            "--binary",
            str(private_path),
            "--expected-binary",
            "0" * 64,
            "--fixture",
            str(private_path),
            "--expected-fixture",
            "0" * 64,
            "--output",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        timeout=5,
    )
    assert result.returncode == 3 and result.stderr == b""
    assert json.loads(result.stdout) == {"status": "failed", "qualified_backend": False}
