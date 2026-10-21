"""Offline codec/orchestration boundaries; actual proofs live in run evidence."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "input_scale", ROOT / "scripts/check_gnark_input_scale.py"
)
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


@pytest.mark.parametrize("count", [0, 1, 8, 23, 24, 255, 256, 32767, 32768])
def test_canonical_header_and_complete_byte_encoding(count):
    size = next(size for size in probe.SIZES if size >= count)
    value = probe.vector(size, bytes(i % 256 for i in range(count)))
    width = 1 if count < 24 else 2 if count < 256 else 3
    positions = value["positions"]
    assert positions[0] == 2 * width
    assert positions[-1] == 2 * width + count + sum(i % 256 >= 24 for i in range(count))
    assert all(n == 0 for n in value["encoded"][positions[-1] :])
    for i in range(size):
        if i < count:
            unit = i % 256
            expected = [unit] if unit < 24 else [24, unit]
            assert value["encoded"][positions[i] : positions[i + 1]] == expected
        else:
            assert positions[i] == positions[i + 1] and value["units"][i] == 0
    fields = probe.assignment(value).splitlines()
    assert len(fields) == 72 + 4 * size
    assert fields[:33] == probe.assignment(value, False).splitlines()
    assert all(str(int(n)).encode() == n for n in fields)


def test_salt_profile_units_and_final_byte_affect_digest():
    from hallmark.wire import H

    value = probe.vector(8, b"\0" * 8)
    pin = bytes(value["public"][1:])
    assert pin != bytes(probe.vector(8, b"\0" * 7 + b"\1")["public"][1:])
    assert pin != H("input", [b"t" * 32, b"p" * 32, 8, [0] * 8])
    assert pin != H("input", [b"s" * 32, b"q" * 32, 8, [0] * 8])
    assert pin != bytes(probe.vector(8, b"\0" * 7)["public"][1:])


@pytest.mark.parametrize("size,units", [(7, b""), (8, b"x" * 9), (8, []), (32769, b"")])
def test_invalid_fixture_boundary(size, units):
    with pytest.raises(ValueError):
        probe.vector(size, units)


def test_stale_binary_and_wrong_host_reject_without_output(tmp_path, monkeypatch):
    binary = tmp_path / "probe"
    binary.write_bytes(b"not executed")
    output = tmp_path / "output"
    monkeypatch.setattr(probe.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(probe.platform, "machine", lambda: "arm64")
    with pytest.raises(ValueError, match="pin"):
        probe.check(binary, "0" * 64, output)
    monkeypatch.setattr(probe.platform, "machine", lambda: "x86_64")
    with pytest.raises(ValueError, match="host"):
        probe.check(binary, probe.digest(binary.read_bytes()), output)
    assert not output.exists()


def test_worker_failure_preserves_failure_and_never_publishes_result(tmp_path, monkeypatch):
    binary = tmp_path / "probe"
    binary.write_bytes(b"not executed")
    output = tmp_path / "output"
    monkeypatch.setattr(probe.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(probe.platform, "machine", lambda: "arm64")

    def fail(*args, **kwargs):
        raise OSError("private path must not enter failure record")

    monkeypatch.setattr(probe, "invoke", fail)
    with pytest.raises(OSError):
        probe.check(binary, probe.digest(binary.read_bytes()), output)
    assert (output / "failure.json").is_file()
    assert "private path" not in (output / "failure.json").read_text()
    assert not (output / "result.json").exists()


def test_cli_errors_do_not_echo_sensitive_arguments():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_gnark_input_scale.py"), "private-marker"],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 3
    assert result.stderr == b""
    assert json.loads(result.stdout) == {"status": "failed", "qualified_backend": False}
