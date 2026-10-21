"""Offline codec/orchestration boundaries; actual proofs live in run evidence."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

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
    assert len(fields) == 78 + 7 * size
    assert value["unit_active"] == [1] * count + [0] * (size - count)
    assert value["encoded_active"] == [1] * positions[-1] + [0] * (
        len(value["encoded"]) - positions[-1]
    )
    assert sum(value["unit_active"]) == value["public"][0]
    assert sum(value["encoded_active"]) == positions[-1]
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


@pytest.mark.parametrize("changed", [False, True])
def test_scaling_streams_pinned_setup_files_before_next_worker(tmp_path, monkeypatch, changed):
    binary, output = tmp_path / "probe", tmp_path / "output"
    binary.write_bytes(b"not executed")
    monkeypatch.setattr(probe.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(probe.platform, "machine", lambda: "arm64")
    read = probe.read_regular
    keys = {"circuit.r1cs", "pk.bin", "vk.bin"}

    def small_reads_only(path, limit):
        assert path.name not in keys, "setup artifact materialized as bytes"
        return read(path, limit)

    monkeypatch.setattr(probe, "read_regular", small_reads_only)
    calls = []

    def worker(binary, directory, args, **kwargs):
        calls.append(args[0])
        if args[0] == "input-batch":
            for name in ["circuit.r1cs", "pk.bin"]:
                assert (directory / name).read_bytes() == name.encode()
            raise RuntimeError("copied before worker")
        for name in keys | {"sandbox.sb", "plan.json", "stderr.txt"}:
            (directory / name).write_bytes(name.encode())
        (directory / "stdout.txt").write_text(json.dumps({"status": "passed", "constraints": 1}))
        files = {
            f.name: {"sha256": probe.digest(f.read_bytes()), "bytes": f.stat().st_size}
            for f in directory.iterdir()
        }
        if changed:
            (directory / "circuit.r1cs").write_bytes(b"X" * len("circuit.r1cs"))
        return {"exit_code": 0, "timed_out": False, "files": files}

    monkeypatch.setattr(probe, "invoke", worker)
    with pytest.raises((RuntimeError, ValueError), match="pin mismatch|copied before worker"):
        probe.check(binary, probe.digest(binary.read_bytes()), output)
    assert calls == (["input-setup"] if changed else ["input-setup", "input-batch"])
    assert (output / "failure.json").is_file()
    assert not (output / "result.json").exists()
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


@pytest.mark.parametrize("exit_code", [0, -9])
@pytest.mark.parametrize("flag", [None, "memory_limit_exceeded", "memory_monitor_failed"])
def test_cutoff_classification_keeps_monitor_failures_distinct(exit_code, flag):
    cost = {
        "exit_code": exit_code,
        "timed_out": False,
        "max_rss_bytes": 700,
        "user_seconds": 1,
        "system_seconds": 0,
    }
    if flag:
        cost[flag] = True
    budget = SimpleNamespace(max_rss_bytes=800, cpu_seconds=2)
    if flag == "memory_monitor_failed":
        with pytest.raises(ValueError, match="monitor failed"):
            probe.resource_limited(cost, budget)
    else:
        assert probe.resource_limited(cost, budget) == (exit_code < 0 or flag is not None)
