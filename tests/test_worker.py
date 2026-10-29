"""Sandboxed worker boundaries, run offline against harmless fixtures."""

import errno
import json
import os
import platform
import shutil
import signal
import socket
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from hallmark import _worker as probe

mac = pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="the admitted OS worker is macOS arm64 only",
)


@pytest.mark.parametrize(
    "inherited,expected",
    [
        ((4096, 2**63 - 1), 4096),
        ((512, 1024), 512),
        ((probe.resource.RLIM_INFINITY, probe.resource.RLIM_INFINITY), 4096),
    ],
)
def test_descriptor_limit_preserves_stricter_limits(monkeypatch, inherited, expected):
    calls = []
    monkeypatch.setattr(probe.resource, "getrlimit", lambda kind: inherited)
    monkeypatch.setattr(probe.resource, "setrlimit", lambda *args: calls.append(args))
    probe.limit_open_files()
    assert calls == [(probe.resource.RLIMIT_NOFILE, (expected, expected))]


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


@pytest.mark.parametrize("kind", ["link", "hardlink", "directory", "fifo", "oversize"])
def test_stream_rejects_unsafe_file_before_creating_copy(tmp_path, kind):
    source, target = tmp_path / "source", tmp_path / "copy"
    original = tmp_path / "original"
    original.write_bytes(b"data")
    if kind == "link":
        source.symlink_to(original)
    elif kind == "hardlink":
        os.link(original, source)
    elif kind == "directory":
        source.mkdir()
    elif kind == "fifo":
        os.mkfifo(source)
    else:
        source.write_bytes(b"oversize")
    with pytest.raises((OSError, ValueError)):
        probe.stream_regular(source, 4, destination=target)
    assert not target.exists()


def test_stream_copy_bounds_memory_and_keeps_exclusive_private_output(tmp_path):
    import tracemalloc

    source, target = tmp_path / "source", tmp_path / "copy"
    source.write_bytes(b"a" * (8 * 1024**2))
    expected = {"bytes": source.stat().st_size, "sha256": probe.digest(source.read_bytes())}
    tracemalloc.start()
    try:
        actual = probe.stream_regular(source, expected["bytes"], destination=target)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 3 * 1024**2
    assert actual == expected == probe.stream_regular(target, expected["bytes"])
    assert target.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        probe.stream_regular(source, expected["bytes"], destination=target)


@pytest.mark.parametrize("fault", ["modified", "replaced", "sync"])
def test_stream_copy_retains_rejected_output(tmp_path, monkeypatch, fault):
    source, target = tmp_path / "source", tmp_path / "copy"
    source.write_bytes(b"data")
    if fault in {"modified", "replaced"}:
        original = probe.os.fstat
        calls = 0

        def changed(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                if fault == "replaced":
                    source.rename(source.with_suffix(".old"))
                    source.write_bytes(b"data")
                else:
                    source.write_bytes(b"evil")
            return original(fd)

        monkeypatch.setattr(probe.os, "fstat", changed)
    else:
        monkeypatch.setattr(probe.os, "fsync", lambda fd: (_ for _ in ()).throw(OSError("sync")))
    with pytest.raises((ValueError, OSError)):
        probe.stream_regular(source, 4, destination=target)
    assert target.is_file()
    assert not (tmp_path / "cost.json").exists()


def test_exclusive_private_write(tmp_path):
    binary = tmp_path / "probe"
    probe.write_new(binary, b"public fixture")
    assert binary.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        probe.write_new(binary, b"replacement")
    with pytest.raises(FileExistsError):
        probe.json_new(binary, {"replacement": True})
    assert binary.read_bytes() == b"public fixture"
    probe.json_new(tmp_path / "value.json", {"b": 1, "a": [2]})
    assert json.loads((tmp_path / "value.json").read_text()) == {"a": [2], "b": 1}
    with pytest.raises(ValueError):
        probe.json_new(tmp_path / "nan.json", float("nan"))
    assert not (tmp_path / "nan.json").exists()


def test_unsupported_platform_fails_before_file_access(tmp_path, monkeypatch):
    monkeypatch.setattr(probe.platform, "system", lambda: "Linux")
    with pytest.raises(ValueError, match="macOS arm64"):
        probe.invoke(Path("/bin/sh"), tmp_path, [])
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
def test_extra_read_paths_are_read_only_and_do_not_leak_to_next_worker(tmp_path):
    source = work(tmp_path, 'reviewed "environment"')
    text = source / "public.txt"
    text.write_text("harmless fixture")
    directory = work(tmp_path, "reader")
    result = probe.invoke(
        Path("/bin/cat"),
        directory,
        [str(text)],
        read_paths=(source,),
    )
    assert result["exit_code"] == 0
    assert (directory / "stdout.txt").read_text() == "harmless fixture"
    write_dir = work(tmp_path, "writer")
    denied_write = probe.invoke(
        Path("/bin/sh"),
        write_dir,
        ["-c", 'echo changed > "$1"', "sh", str(text)],
        read_paths=(source,),
    )
    assert denied_write["exit_code"] != 0
    assert b"Operation not permitted" in (write_dir / "stderr.txt").read_bytes()
    assert text.read_text() == "harmless fixture"
    denied = probe.invoke(Path("/bin/cat"), work(tmp_path, "next-worker"), [str(text)])
    assert denied["exit_code"] == 1


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
        probe.RunBudget(tmp_path, time.monotonic() + 10, 5, 1, 2, ceiling, 1024**2)
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


@mac
def test_signals_are_confined_to_the_sandbox(tmp_path):
    outside = subprocess.Popen(["/bin/sleep", "30"])
    try:
        directory = work(tmp_path, "signal")
        result = probe.invoke(Path("/bin/kill"), directory, ["-TERM", str(outside.pid)])
        assert result["exit_code"] != 0 and not result["timed_out"]
        assert b"Operation not permitted" in (directory / "stderr.txt").read_bytes()
        assert outside.poll() is None
    finally:
        outside.kill()
        outside.wait()
    itself = probe.invoke(Path("/bin/sh"), work(tmp_path, "self"), ["-c", "kill -TERM $$"])
    assert itself["exit_code"] == -signal.SIGTERM
    # Forking workers (the native LLM verifier) must still be able to stop their children.
    directory = work(tmp_path, "children")
    profile = directory / "fork.sb"
    profile.write_text(probe.sandbox_profile(Path("/bin/sh"), directory) + "(allow process-fork)\n")
    script = "/bin/sleep 30 & kill $!; wait $!"
    child = subprocess.run(
        ["/usr/bin/sandbox-exec", "-f", str(profile), "/bin/sh", "-c", script],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert child.returncode == 128 + signal.SIGTERM, child.stderr


@mac
@pytest.mark.parametrize(("name", "limit"), [("circle-verify", 3), ("circle-prove", 7)])
def test_verifier_limit_follows_binary_name(tmp_path, name, limit):
    binary = tmp_path.resolve() / name
    shutil.copy("/usr/bin/true", binary)
    budget = probe.RunBudget(tmp_path, time.monotonic() + 30, 7, 3, 10, 1024**3, 1024**2)
    directory = work(tmp_path, "case")
    assert probe.invoke(binary, directory, ["enrollment.json"], budget=budget)["exit_code"] == 0
    assert json.loads((directory / "plan.json").read_text())["wall_limit_seconds"] == limit


@mac
def test_inventory_records_directories_and_rejects_links(tmp_path):
    directory = work(tmp_path, "directory")
    result = probe.invoke(Path("/bin/mkdir"), directory, ["scratch"])
    assert result["exit_code"] == 0 and result["files"]["scratch"] is None
    assert result["files"]["stdout.txt"] == {"sha256": probe.digest(b""), "bytes": 0}
    assert json.loads((directory / "cost.json").read_text()) == result
    linked = work(tmp_path, "link")
    with pytest.raises(OSError):
        probe.invoke(Path("/bin/ln"), linked, ["-s", "stdout.txt", "alias"])
    assert not (linked / "cost.json").exists()
