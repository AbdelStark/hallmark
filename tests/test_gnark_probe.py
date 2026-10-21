"""Probe boundaries run offline; actual proofs require the separately admitted build."""

import errno
import json
import os
import platform
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from hallmark import _gnark_graph_probe as rule_probe
from hallmark import _gnark_probe as probe

ROOT = Path(__file__).resolve().parents[1]
mac = pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="the admitted OS worker is macOS arm64 only",
)


@pytest.mark.parametrize("kind", ["link", "directory", "fifo", "oversize"])
def test_regular_file_boundary(tmp_path, kind):
    target = tmp_path / "input"
    if kind == "link":
        original = tmp_path / "original"
        original.write_bytes(b"ok")
        target.symlink_to(original)
    elif kind == "directory":
        target.mkdir()
    elif kind == "fifo":
        os.mkfifo(target)
    else:
        target.write_bytes(b"too long")
    with pytest.raises((OSError, ValueError)):
        probe.read_regular(target, 2)


def test_changed_file_rejects(tmp_path, monkeypatch):
    target = tmp_path / "input"
    target.write_bytes(b"ok")
    original = probe.os.fstat
    calls = 0

    def changed(fd):
        nonlocal calls
        info = original(fd)
        calls += 1
        return SimpleNamespace(
            st_mode=info.st_mode,
            st_size=info.st_size,
            st_mtime_ns=info.st_mtime_ns + (calls > 1),
            st_ctime_ns=info.st_ctime_ns,
        )

    monkeypatch.setattr(probe.os, "fstat", changed)
    with pytest.raises(ValueError, match="changed"):
        probe.read_regular(target, 2)


def test_exclusive_private_write_and_pin(tmp_path, monkeypatch):
    monkeypatch.setattr(probe.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(probe.platform, "machine", lambda: "arm64")
    binary = tmp_path / "probe"
    probe.write_new(binary, b"public fixture")
    assert binary.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        probe.write_new(binary, b"replacement")
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="identity"):
        probe.check(binary, "0" * 64, output)
    assert not output.exists()
    output.mkdir()
    with pytest.raises(FileExistsError):
        probe.check(binary, probe.digest(binary.read_bytes()), output)
    assert list(output.iterdir()) == []
    assert binary.read_bytes() == b"public fixture"


def test_unsupported_platform_fails_before_file_access(tmp_path, monkeypatch):
    monkeypatch.setattr(probe.platform, "system", lambda: "Linux")
    with pytest.raises(ValueError, match="macOS arm64"):
        probe.check(tmp_path / "absent", "0" * 64, tmp_path / "output")
    assert list(tmp_path.iterdir()) == []


def work(tmp_path, name):
    path = (tmp_path / name).resolve()
    path.mkdir(mode=0o700)
    return path


@mac
def test_environment_does_not_inherit_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("HALLMARK_SYNTHETIC_SECRET", "public-test-sentinel")
    directory = work(tmp_path, "environment")
    result = probe.invoke(Path("/usr/bin/env"), directory, [])
    assert result["exit_code"] == 0 and not result["timed_out"]
    environment = dict(
        line.split("=", 1) for line in (directory / "stdout.txt").read_text().splitlines()
    )
    assert environment == {
        "PATH": "/usr/bin:/bin",
        "GOMAXPROCS": "4",
        "GOMEMLIMIT": "1GiB",
        "LANG": "C",
        "TZ": "UTC",
        "TMPDIR": str(directory),
    }
    assert "public-test-sentinel" not in (directory / "plan.json").read_text()


@mac
def test_assigned_file_reads_and_external_file_denial(tmp_path):
    inside = work(tmp_path, "inside")
    (inside / "public.txt").write_text("harmless fixture")
    passed = probe.invoke(Path("/bin/cat"), inside, [str(inside / "public.txt")])
    assert passed["exit_code"] == 0
    assert (inside / "stdout.txt").read_text() == "harmless fixture"
    outside = work(tmp_path, "outside")
    failed = probe.invoke(Path("/bin/cat"), outside, [str(inside / "public.txt")])
    assert failed["exit_code"] == 1 and not failed["timed_out"]
    assert (outside / "stdout.txt").read_bytes() == b""
    assert b"Operation not permitted" in (outside / "stderr.txt").read_bytes()


@mac
def test_network_denied_with_live_loopback_control(tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(0.2)
        port = listener.getsockname()[1]
        args = ["-v", "-z", "-G", "2", "127.0.0.1", str(port)]
        control = subprocess.run(
            ["/usr/bin/nc", *args], capture_output=True, timeout=3, check=False
        )
        assert control.returncode == 0
        connection, _ = listener.accept()
        connection.close()
        directory = work(tmp_path, "network")
        result = probe.invoke(Path("/usr/bin/nc"), directory, args)
        assert result["exit_code"] == 1 and not result["timed_out"]
        assert b"Operation not permitted" in (directory / "stderr.txt").read_bytes()
        with pytest.raises(TimeoutError):
            listener.accept()


@mac
def test_timeout_reaps_worker_and_preserves_costs(tmp_path):
    directory = work(tmp_path, "timeout")
    result = probe.invoke(Path("/bin/sleep"), directory, ["10"], seconds=0.1)
    assert result["timed_out"] and result["exit_code"] == -signal.SIGKILL
    assert result["elapsed_seconds"] < 5
    assert json.loads((directory / "cost.json").read_text()) == result


@mac
def test_native_memory_sample():
    assert 0 < probe._rss_reader()(os.getpid()) < 16 * 1024**3


@pytest.mark.parametrize("returned", [-1, 0, 95, 96, 97])
def test_native_memory_sample_requires_complete_abi(monkeypatch, returned):
    monkeypatch.setattr(probe.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(probe.platform, "machine", lambda: "arm64")

    def read(pid, flavor, arg, buffer, size):
        assert (pid, flavor, arg, size) == (123, 4, 0, 96)
        probe.ctypes.c_uint64.from_buffer(buffer, 8).value = 4321
        return returned

    monkeypatch.setattr(probe.ctypes, "CDLL", lambda *a, **kw: SimpleNamespace(proc_pidinfo=read))
    reader = probe._rss_reader()
    if returned == 96:
        assert reader(123) == 4321
    else:
        with pytest.raises(OSError, match="sample unavailable"):
            reader(123)


@pytest.mark.parametrize(
    "fault",
    [
        "below",
        "cutoff",
        "above",
        "monitor",
        "exit-race",
        "signal-exit-race",
        "peak",
        "exit-transition",
        "missing-live",
        "monitor-normal-exit",
    ],
)
@pytest.mark.parametrize("use_budget", [False, True])
def test_live_memory_stop_reaps_and_retains_cost(tmp_path, monkeypatch, fault, use_budget):
    process = SimpleNamespace(pid=123, returncode=None)
    monkeypatch.setattr(probe.subprocess, "Popen", lambda *_a, **_kw: process)
    reads = []
    signals = []
    single_signals = []
    ceiling = 8000 if use_budget else 16 * 1024**3
    cutoff = ceiling * 7 // 8

    def sample(pid):
        reads.append(pid)
        if fault in {"monitor", "exit-race", "monitor-normal-exit"}:
            raise OSError("private error detail")
        if fault in {"exit-transition", "missing-live"}:
            raise ProcessLookupError("private error detail")
        return {
            "below": cutoff - 1,
            "cutoff": cutoff,
            "above": ceiling + 1,
            "signal-exit-race": cutoff,
            "peak": 0,
        }[fault]

    monkeypatch.setattr(probe, "_rss_reader", lambda: sample)
    killed = fault in {"cutoff", "above", "monitor", "missing-live"}
    usage = SimpleNamespace(
        ru_utime=0, ru_stime=0, ru_maxrss=ceiling + 1 if fault == "peak" else cutoff
    )
    waits = iter(
        [
            0,
            *(
                [0]
                if fault in {"monitor", "exit-transition", "missing-live", "monitor-normal-exit"}
                else []
            ),
            123,
        ]
    )
    reaps = []

    def wait(pid, flags):
        reaps.append((pid, flags))
        return next(waits), signal.SIGKILL if killed else 0, usage

    monkeypatch.setattr(probe.os, "wait4", wait)

    def kill(pid, sig):
        signals.append((pid, sig))
        if fault == "signal-exit-race":
            raise PermissionError("exited child")

    monkeypatch.setattr(probe.os, "killpg", kill)
    monkeypatch.setattr(probe.os, "kill", lambda pid, sig: single_signals.append((pid, sig)))
    directory = work(tmp_path, "worker")
    budget = (
        probe.RunBudget(tmp_path, time.monotonic() + 10, 5, 1, 2, 1, ceiling, 1024**2)
        if use_budget
        else None
    )
    if killed or fault in {"peak", "signal-exit-race", "monitor-normal-exit"}:
        with pytest.raises(MemoryError):
            probe.invoke(Path("/bin/sleep"), directory, ["10"], budget=budget)
    else:
        probe.invoke(Path("/bin/sleep"), directory, ["10"], budget=budget)
    cost = json.loads((directory / "cost.json").read_text())
    assert cost["memory_limit_exceeded"] == (fault in {"cutoff", "above", "signal-exit-race"})
    assert cost["memory_monitor_failed"] == (
        fault in {"monitor", "missing-live", "monitor-normal-exit"}
    )
    assert cost["memory_sample_process_missing"] == (fault in {"exit-transition", "missing-live"})
    assert not cost["timed_out"]
    assert cost["exit_code"] == (-signal.SIGKILL if killed else 0)
    stopped = killed or fault in {"signal-exit-race", "exit-transition", "monitor-normal-exit"}
    assert signals == ([(123, signal.SIGKILL)] if stopped else [])
    assert single_signals == ([(123, signal.SIGKILL)] if fault == "signal-exit-race" else [])
    assert reaps[-1] == (123, 0 if stopped else os.WNOHANG)
    assert reads == [123]
    assert "private error detail" not in (directory / "cost.json").read_text()
    plan = json.loads((directory / "plan.json").read_text())
    assert plan["memory_cutoff_bytes"] == cutoff
    assert plan["max_rss_bytes"] == ceiling


def test_signal_permission_failure_is_not_ignored_for_live_child(monkeypatch):
    def denied(*_):
        raise PermissionError("signal denied")

    monkeypatch.setattr(probe.os, "killpg", denied)
    monkeypatch.setattr(probe.os, "kill", denied)
    with pytest.raises(PermissionError, match="signal denied"):
        probe._stop_worker(123)


@pytest.mark.parametrize("code", [0, errno.ESRCH, errno.EACCES])
def test_native_sampler_preserves_error_kind_and_clears_stale_errno(monkeypatch, code):
    monkeypatch.setattr(probe.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(probe.platform, "machine", lambda: "arm64")

    def read(*_):
        assert probe.ctypes.get_errno() == 0
        probe.ctypes.set_errno(code)
        return 0

    monkeypatch.setattr(probe.ctypes, "CDLL", lambda *a, **kw: SimpleNamespace(proc_pidinfo=read))
    probe.ctypes.set_errno(errno.ESRCH)
    with pytest.raises(OSError) as error:
        probe._rss_reader()(123)
    assert error.value.errno == code
    assert isinstance(error.value, ProcessLookupError) == (code == errno.ESRCH)


@mac
def test_fork_is_denied(tmp_path):
    directory = work(tmp_path, "fork")
    result = probe.invoke(Path("/bin/sh"), directory, ["-c", "(echo child) >child.txt"])
    assert result["exit_code"] != 0 and not result["timed_out"]
    assert not (directory / "child.txt").exists()
    assert b"fork" in (directory / "stderr.txt").read_bytes()


@pytest.mark.parametrize(
    "fault",
    [
        "crash",
        "timeout",
        "unexpected-file",
        "rss",
        "cpu",
        "wrong-status",
        "bool-count",
        "negative-time",
    ],
)
def test_failed_worker_cannot_publish_success(tmp_path, monkeypatch, fault):
    monkeypatch.setattr(probe.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(probe.platform, "machine", lambda: "arm64")
    original = probe.read_regular
    monkeypatch.setattr(
        probe,
        "read_regular",
        lambda path, limit: (
            b"public dyld fixture" if path.name == "dyld-support.sb" else original(path, limit)
        ),
    )
    binary = tmp_path / "binary"
    binary.write_bytes(b"not an executable")

    def failed_worker(_binary, directory, _args, **_kwargs):
        report = {
            "schema_id": "hallmark.gnark-installation-probe/1",
            "status": "passed",
            "constraints": 45,
            "elapsed_ns": 1,
        }
        if fault == "wrong-status":
            report["status"] = "failed"
        elif fault == "bool-count":
            report["constraints"] = True
        elif fault == "negative-time":
            report["elapsed_ns"] = -1
        names = ["sandbox.sb", "plan.json", "stderr.txt", "circuit.r1cs", "pk.bin", "vk.bin"]
        for name in names:
            probe.write_new(directory / name, b"fixture")
        probe.json_new(directory / "stdout.txt", report)
        return {
            "exit_code": -6 if fault == "crash" else 0,
            "timed_out": fault == "timeout",
            "max_rss_bytes": 17 * 1024**3 if fault == "rss" else 1,
            "user_seconds": 41 if fault == "cpu" else 0,
            "system_seconds": 0,
            "files": dict.fromkeys(
                [*names, "stdout.txt", *(["extra"] if fault == "unexpected-file" else [])]
            ),
        }

    monkeypatch.setattr(probe, "invoke", failed_worker)
    output = tmp_path / "result"
    with pytest.raises(ValueError):
        probe.check(binary, probe.digest(binary.read_bytes()), output)
    assert (output / "failure.json").exists()
    assert not (output / "result.json").exists()


@pytest.mark.parametrize("kind", ["rule", "mlp"])
def test_frozen_graph_fixture_reproduces_and_matches_source_constants(kind):
    fixture = ROOT / f"research/probes/gnark/{kind}-fixture.json"
    reproduced = subprocess.run(
        [sys.executable, str(ROOT / f"scripts/build_gnark_{kind}_fixture.py")],
        cwd=ROOT,
        capture_output=True,
        check=True,
        timeout=20,
    )
    assert reproduced.stdout == fixture.read_bytes()
    value = rule_probe.validate_fixture(reproduced.stdout)
    source = (ROOT / f"research/probes/gnark/{kind}.go").read_text()
    for record in ("classifier", "input_profile"):
        assert value["records"][record]["identity_hex"] in source
    for case in value["cases"]:
        private = rule_probe.assignment(case, True).splitlines()
        public = rule_probe.assignment(case, False).splitlines()
        assert len(private) == (162 if kind == "mlp" else 140) and len(public) == 100
        assert private[:100] == public
        assert list(map(int, public)) == case["public"]
        assert all(str(int(line)).encode() == line for line in private)
        if kind == "mlp":
            assert [int(n) - 2**31 for n in private[140:]] == case["trace"]


@pytest.mark.parametrize("fault", ["missing", "length", "bool", "low", "high", "rule-trace"])
def test_graph_fixture_rejects_invalid_layer_traces(fault):
    value = json.loads((ROOT / "research/probes/gnark/mlp-fixture.json").read_text())
    case = value["cases"][0]
    if fault == "missing":
        del case["trace"]
    elif fault == "length":
        case["trace"].pop()
    elif fault == "rule-trace":
        value["schema_id"] = "hallmark.gnark-rule-fixture/1"
    else:
        case["trace"][0] = {"bool": False, "low": -(2**31) - 1, "high": 2**31}[fault]
    with pytest.raises(ValueError):
        rule_probe.validate_fixture(json.dumps(value).encode())


@pytest.mark.parametrize(
    "fault", ["qualified", "name", "duplicate", "count", "boolean", "negative", "oversize"]
)
def test_rule_fixture_rejects_unsafe_assignments(fault):
    value = json.loads((ROOT / "research/probes/gnark/rule-fixture.json").read_bytes())
    if fault == "qualified":
        value["qualified_backend"] = True
    elif fault == "name":
        value["cases"][0]["name"] = "../escape"
    elif fault == "duplicate":
        value["cases"][0]["name"] = value["cases"][1]["name"]
    elif fault == "count":
        value["cases"][0]["public"].pop()
    else:
        value["cases"][0]["public"][0] = {
            "boolean": True,
            "negative": -1,
            "oversize": 2**32,
        }[fault]
    with pytest.raises(ValueError):
        rule_probe.validate_fixture(json.dumps(value).encode())


def test_rule_identity_before_write_and_failed_attempt_retained(tmp_path, monkeypatch):
    monkeypatch.setattr(rule_probe.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(rule_probe.platform, "machine", lambda: "arm64")
    binary = tmp_path / "binary"
    binary.write_bytes(b"public fixture")
    fixture = ROOT / "research/probes/gnark/rule-fixture.json"
    binary_pin, fixture_pin = probe.digest(binary.read_bytes()), probe.digest(fixture.read_bytes())
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="identity"):
        rule_probe.check(binary, binary_pin, fixture, "0" * 64, output)
    assert not output.exists()
    monkeypatch.setattr(
        rule_probe,
        "invoke",
        lambda *_args, **_kw: {
            "exit_code": -6,
            "timed_out": False,
            "max_rss_bytes": 1,
            "files": {},
        },
    )
    with pytest.raises(ValueError, match="process"):
        rule_probe.check(binary, binary_pin, fixture, fixture_pin, output)
    assert len(json.loads((output / "failure.json").read_text())["cases"]) == 1
    assert not (output / "result.json").exists()
    with pytest.raises(FileExistsError):
        rule_probe.check(binary, binary_pin, fixture, fixture_pin, output)


@pytest.mark.parametrize("script", ["check_gnark_probe.py", "check_gnark_rule_probe.py"])
def test_probe_cli_sanitizes_failures(tmp_path, script):
    secret_path = tmp_path / "harmless-private-path-marker"
    args = [
        sys.executable,
        str(ROOT / "scripts" / script),
        "--binary",
        str(secret_path),
        "--expected-binary",
        "0" * 64,
        "--output",
        str(tmp_path / "out"),
    ]
    if "rule" in script:
        args += ["--fixture", str(secret_path), "--expected-fixture", "0" * 64]
    result = subprocess.run(args, capture_output=True, timeout=5, check=False)
    assert result.returncode == 3 and result.stderr == b""
    assert json.loads(result.stdout) == {"status": "failed", "qualified_backend": False}
    assert b"harmless-private-path-marker" not in result.stdout
