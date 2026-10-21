"""Offline admission checks and actual Linux process-boundary fixtures."""

import errno
import json
import os
import platform
import sys
from pathlib import Path

import pytest

from hallmark import _gnark_linux_compile as probe

linux = pytest.mark.skipif(
    platform.system() != "Linux" or platform.machine() != "x86_64",
    reason="actual kernel checks require Linux x86-64",
)


@pytest.mark.parametrize(
    "arch,number,expected",
    [
        (0xC000003E, 39, 0x7FFF0000),
        *((0xC000003E, n, 0x50000 | errno.EPERM) for n in [41, 53, 101, 425, 438]),
        (0xC000003E, 0x40000000 | 41, 0x80000000),
        (0x40000003, 102, 0x80000000),
    ],
)
def test_filter_rejects_network_and_abi_bypasses(arch, number, expected):
    rules = probe.network_filter()
    pc = value = 0
    for _ in range(len(rules)):
        code, yes, no, operand = rules[pc]
        if code == 0x06:
            assert operand == expected
            return
        if code == 0x20:
            value = {0: number, 4: arch}[operand]
        elif code == 0x15:
            pc += yes if value == operand else no
        elif code == 0x45:
            pc += yes if value & operand else no
        else:
            pytest.fail("unexpected filter instruction")
        pc += 1
    pytest.fail("filter did not return")


@pytest.mark.parametrize("text", ["", "1 2", "1 -2 3 4 5 6 7", "1 ² 3 4 5 6 7"])
def test_invalid_memory_sample_rejects(monkeypatch, text):
    monkeypatch.setattr(Path, "read_text", lambda self: text)
    with pytest.raises(ValueError):
        probe.resident_bytes(123)


def test_memory_units(monkeypatch):
    monkeypatch.setattr(Path, "read_text", lambda self: "123 27 0 0 0 0 0\n")
    monkeypatch.setattr(os, "sysconf", lambda _: 4096)
    assert probe.resident_bytes(123) == 27 * 4096


@pytest.mark.parametrize("value", ["max", "-1", "1000000000", "invalid"])
def test_container_budget_rejects_unknown_or_small_limit(monkeypatch, value):
    monkeypatch.setattr(Path, "read_text", lambda self: value)
    with pytest.raises(ValueError):
        probe.container_memory_limit()


@pytest.mark.parametrize("failure", ["none", "small", "maximum", "mismatch", "bad-report"])
def test_compile_roster_and_incomplete_scope(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(probe.platform, "system", lambda: "Linux")
    monkeypatch.setattr(probe.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(probe, "container_memory_limit", lambda: 30_000_000_000)
    binary = tmp_path / "binary"
    binary.write_bytes(b"pinned test input")
    names = []

    def invoke(command, work, **kwargs):
        names.append(work.name)
        work.mkdir()
        count = 205547 if work.name == "small" else 1234567
        if failure == "mismatch" and work.name == "confirmation":
            count += 1
        report = {
            "schema_id": "hallmark.gnark-installation-probe/1",
            "status": "passed",
            "constraints": count,
            "elapsed_ns": 100,
        }
        if failure == "bad-report" and work.name == "small":
            report["constraints"] = True
        (work / "stdout.txt").write_text(json.dumps(report))
        return {"exit_code": 0, "within_limits": work.name != failure}

    monkeypatch.setattr(probe, "invoke", invoke)
    result = probe.check(binary, probe.digest(binary.read_bytes()), tmp_path / "out")
    assert result["maximum_compile_reproduced"] == (failure == "none")
    assert result["qualified_backend"] is False and result["full_input_proof"] is False
    assert (tmp_path / "out/result.json").is_file()
    if failure in ["small", "bad-report"]:
        assert names == ["network-smoke", "small"]
    elif failure == "maximum":
        assert names == ["network-smoke", "small", "maximum"]
    else:
        assert names == ["network-smoke", "small", "maximum", "confirmation"]


@linux
def test_kernel_filter_and_no_inherited_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("HALLMARK_SENTINEL_SECRET", "not-a-real-secret")
    code = """import errno,os,socket
assert 'HALLMARK_SENTINEL_SECRET' not in os.environ
for make in (socket.socket, socket.socketpair):
 try: make()
 except OSError as error: assert error.errno == errno.EPERM
 else: raise AssertionError('network socket available')
"""
    cost = probe.invoke([sys.executable, "-c", code], tmp_path / "network", seconds=5)
    assert cost["exit_code"] == 0 and cost["within_limits"]
    assert 0 < cost["max_rss_bytes"] < probe.MAX_RSS


@linux
def test_timeout_stops_worker(tmp_path):
    cost = probe.invoke(
        [sys.executable, "-c", "import time;time.sleep(10)"], tmp_path / "timeout", seconds=0.1
    )
    assert cost["exit_code"] < 0 and cost["timed_out"] and not cost["within_limits"]


@linux
def test_live_memory_cutoff(tmp_path):
    cost = probe.invoke(
        [sys.executable, "-c", "import time;x=bytearray(128*1024**2);time.sleep(10)"],
        tmp_path / "memory",
        seconds=5,
        max_rss=200 * 1024**2,
        cutoff=64 * 1024**2,
    )
    assert cost["exit_code"] < 0 and cost["memory_limit_exceeded"] and not cost["within_limits"]


@linux
def test_lost_sample_fails_closed(tmp_path, monkeypatch):
    def unavailable(pid):
        raise OSError("unavailable")

    monkeypatch.setattr(probe, "resident_bytes", unavailable)
    cost = probe.invoke(
        [sys.executable, "-c", "import time;time.sleep(10)"], tmp_path / "monitor", seconds=5
    )
    assert cost["exit_code"] < 0 and cost["memory_monitor_failed"] and not cost["within_limits"]


@pytest.mark.parametrize("mutation", ["revision", "files", "toolchain", "builder"])
def test_bootstrap_rejects_unapproved_manifest(mutation):
    import base64
    import runpy

    bootstrap = runpy.run_path(str(Path(__file__).parents[1] / "scripts/gnark_hf_bootstrap.py"))
    names = [
        "block.go",
        "cache_test.go",
        "go.mod",
        "go.sum",
        "graph.go",
        "input.go",
        "input_scale.go",
        "input_scale_test.go",
        "main.go",
        "mlp.go",
        "rule.go",
    ]
    files = {"research/probes/gnark/" + name: {} for name in names}
    files.update(
        {
            "src/hallmark/" + name: {}
            for name in [
                "__init__.py",
                "_gnark_probe.py",
                "_gnark_linux_compile.py",
            ]
        }
    )
    plan = {
        "schema_id": "hallmark.hf-compile-inputs/1",
        "source_commit": "a" * 40,
        "files": files,
        "go_archive": {"filename": "go1.26.8.linux-amd64.tar.gz", "size": 66897291},
        "patched_builder": base64.b64encode(b"unreviewed").decode(),
    }
    if mutation == "revision":
        plan["source_commit"] = "../main"
    elif mutation == "files":
        plan["files"] = {"../../.env": {}}
    elif mutation == "toolchain":
        plan["go_archive"]["filename"] = "unreviewed.tar.gz"
    else:
        plan["patched_builder"] = "!"
    with pytest.raises(ValueError):
        bootstrap["validate"](plan)
