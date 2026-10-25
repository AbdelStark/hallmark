"""Native orchestration and enrollment failures; real proof evidence is separate."""

import copy
import importlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "research/probes/sash"))
native = importlib.import_module("verify_llm")
worker = importlib.import_module("verify_response")


def inventory():
    return {
        f"proof/{t}.{k}.json": dict(bytes=1, sha256="a" * 64)
        for t in worker.TAGS
        for k in ("fixed", "claims", "proof")
    }


def test_inventory_requires_exact_bounded_regular_file_roster():
    rows = inventory()
    worker.check_inventory(rows)
    rows["../escape"] = rows.pop("proof/head.proof.json")
    with pytest.raises(AssertionError, match="inventory"):
        worker.check_inventory(rows)


@pytest.mark.parametrize("size", [True, 0, -1, 128 * 1024**2 + 1])
def test_inventory_rejects_bad_sizes(size):
    rows = inventory()
    rows["proof/head.proof.json"]["bytes"] = size
    with pytest.raises(AssertionError, match="size"):
        worker.check_inventory(rows)


def test_inventory_checks_total_size_and_hashes():
    rows = inventory()
    for row in rows.values():
        row["bytes"] = 20 * 1024**2
    with pytest.raises(AssertionError, match="oversized"):
        worker.check_inventory(rows)
    rows = inventory()
    rows["proof/head.proof.json"]["sha256"] = "not a digest"
    with pytest.raises(AssertionError):
        worker.check_inventory(rows)


@pytest.mark.parametrize("dirty,basis", [(False, None), (True, "compiled-enrollment")])
def test_provenance_is_bound_to_the_callers_build(dirty, basis):
    job = dict(source_commit="a" * 40, source_dirty=dirty, shape_root_source=basis)
    good = dict(commit="a" * 40, dirty=dirty, shape_root_source=basis, unsound_skips=[])
    worker.check_provenance(good, job)
    for key, value in [
        ("commit", "b" * 40),
        ("dirty", not dirty),
        ("unsound_skips", ["lookup"]),
        ("shape_root_source", "untrusted"),
    ]:
        bad = good | {key: value}
        with pytest.raises(AssertionError):
            worker.check_provenance(bad, job)
    with pytest.raises(AssertionError, match="status"):
        worker.check_provenance(good, job | {"source_dirty": int(dirty)})


def test_compiled_roots_come_from_the_public_case():
    case = json.loads((native.PROBE / "response-case.json").read_text())
    assert len(native.enrolled_shapes(case)) == 23
    bad = copy.deepcopy(case)
    bad["expected_roots"][1]["shape_key"] = bad["expected_roots"][0]["shape_key"]
    with pytest.raises(ValueError, match="conflicting"):
        native.enrolled_shapes(bad)


def test_group_memory_sums_descendants_and_fails_closed(monkeypatch):
    monkeypatch.setattr(native.subprocess, "check_output", lambda *a, **k: " 31 2\n 42 7\n31 3\n")
    assert native.process_group_rss(31) == 5 * 1024
    monkeypatch.setattr(native.subprocess, "check_output", lambda *a, **k: "monitor failed\n")
    with pytest.raises(ValueError):
        native.process_group_rss(31)


def test_bounded_command_retains_success_and_timeout(tmp_path):
    environment = {"PATH": os.environ["PATH"]}
    native.bounded(
        [sys.executable, "-I", "-c", "print('fixture')"], tmp_path / "good", environment, 5
    )
    assert json.loads((tmp_path / "good/cost.json").read_text())["exit_code"] == 0
    with pytest.raises(ValueError, match="time limit"):
        native.bounded(
            [sys.executable, "-I", "-c", "import time; time.sleep(10)"],
            tmp_path / "timeout",
            environment,
            0.3,
        )
    result = json.loads((tmp_path / "timeout/cost.json").read_text())
    assert result["exit_code"] != 0 and result["failure"] == "ValueError"


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS sandbox regression")
def test_sandbox_nested_spawn_with_large_inherited_descriptor_limit(tmp_path):
    import fcntl
    import resource

    work = tmp_path / "worker"
    work.mkdir()
    python = Path(sys.executable).resolve()
    profile = native.sandbox_profile(python, work)
    profile += "\n(allow process-fork)\n(allow file-read* file-map-executable (subpath "
    profile += json.dumps(sys.base_prefix) + "))\n"
    (work / "sandbox.sb").write_text(profile)
    canary = tmp_path / "outside.txt"
    canary.write_text("denied")
    control = """
import errno, json, os, pathlib, resource, socket, subprocess, sys
p = subprocess.run([sys.executable, "-I", "-c", "print('nested-ok')"], capture_output=True)
assert p.returncode == 0 and p.stdout == b"nested-ok\\n"
try:
    os.fstat(int(sys.argv[2]))
except OSError as error:
    assert error.errno == errno.EBADF
else:
    raise AssertionError("inherited descriptor leaked")
try:
    pathlib.Path(sys.argv[1]).read_bytes()
except PermissionError:
    pass
else:
    raise AssertionError("outside file allowed")
try:
    with socket.socket() as sock:
        sock.connect(("127.0.0.1", 9))
except PermissionError:
    pass
else:
    raise AssertionError("network allowed")
print(json.dumps(dict(limit=resource.getrlimit(resource.RLIMIT_NOFILE)[0])))
"""
    previous = resource.getrlimit(resource.RLIMIT_NOFILE)
    if previous[1] != resource.RLIM_INFINITY and previous[1] < 1_000_000:
        pytest.skip("host hard descriptor limit is already bounded")
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (previous[1], previous[1]))
        with canary.open("rb") as source:
            high_fd = fcntl.fcntl(source.fileno(), fcntl.F_DUPFD, 5000)
            try:
                os.set_inheritable(high_fd, True)
                native.bounded(
                    [
                        "/usr/bin/sandbox-exec",
                        "-f",
                        work / "sandbox.sb",
                        python,
                        "-I",
                        "-c",
                        control,
                        canary,
                        high_fd,
                    ],
                    tmp_path / "attempt",
                    {"PATH": "/usr/bin:/bin"},
                    5,
                    cwd=work,
                )
            finally:
                os.close(high_fd)
        assert resource.getrlimit(resource.RLIMIT_NOFILE) == (previous[1], previous[1])
    finally:
        resource.setrlimit(resource.RLIMIT_NOFILE, previous)
    report = json.loads((tmp_path / "attempt/output.log").read_text())
    assert report["limit"] <= 4096


def test_memory_monitor_failure_stops_the_command(tmp_path, monkeypatch):
    def fail(_):
        raise OSError("monitor unavailable")

    monkeypatch.setattr(native, "process_group_rss", fail)
    with pytest.raises(OSError, match="monitor unavailable"):
        native.bounded(
            [sys.executable, "-I", "-c", "import time; time.sleep(10)"],
            tmp_path / "failed",
            {"PATH": os.environ["PATH"]},
            5,
        )
    cost = json.loads((tmp_path / "failed/cost.json").read_text())
    assert cost["exit_code"] != 0 and cost["failure"] == "OSError"


@pytest.mark.parametrize(
    "operation,original,expected",
    [("alias", 2, 2147483649), ("empty", [3], []), ("zero", 100, 0), ("increment", 0, 1)],
)
def test_native_mutations_preserve_the_hardlinked_control(tmp_path, operation, original, expected):
    control = tmp_path / "control.json"
    control.write_text(json.dumps({"nested": [{"value": original}], "unchanged": 7}))
    changed = tmp_path / "changed.json"
    os.link(control, changed)
    worker.mutate_native(changed, ["nested", 0, "value"], operation)
    assert json.loads(changed.read_text()) == {"nested": [{"value": expected}], "unchanged": 7}
    assert json.loads(control.read_text()) == {"nested": [{"value": original}], "unchanged": 7}


def test_unknown_native_mutation_leaves_the_file_unchanged(tmp_path):
    path = tmp_path / "proof.json"
    original = b'{"value":2}'
    path.write_bytes(original)
    with pytest.raises(ValueError, match="unknown native mutation"):
        worker.mutate_native(path, ["value"], "unsupported")
    assert path.read_bytes() == original
