"""Controller/contract tests use marker workers; these are not proof evidence."""

import hashlib
import json
import os
import time
from pathlib import Path

import pytest

from hallmark import _gnark_probe as worker
from hallmark import qualification as q
from hallmark.cli import main
from hallmark.errors import HallmarkError
from hallmark.manifests import FileRef, FileSHA256

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(q.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(q.platform, "machine", lambda: "arm64")
    refs = {}
    for name in q.INPUTS:
        data = (
            (
                ROOT / f"research/probes/gnark/{name.removesuffix('_fixture')}-fixture.json"
            ).read_bytes()
            if name.endswith("_fixture")
            else f"public {name} marker; never execute".encode()
        )
        (tmp_path / name).write_bytes(data)
        refs[name] = FileRef(
            path=name, size=len(data), sha256=FileSHA256(hashlib.sha256(data).digest())
        )
    protocol = q.QualificationProtocol(
        schema_id="hallmark/qualification-protocol/1",
        host="macos-arm64",
        controller_sha256=FileSHA256(q.controller_sha256()),
        **refs,
        limits=q.QualificationLimits(
            total_seconds=120,
            case_seconds=30,
            verify_seconds=5,
            case_cpu_seconds=20,
            threads=2,
            max_worker_rss_bytes=1024**3,
            max_output_bytes=1024**3,
        ),
    )
    path = tmp_path / "protocol.json"
    path.write_text(protocol.model_dump_json())
    return path, protocol, tmp_path / "output"


def call(prepared):
    path, protocol, output = prepared
    return q.qualify(path, protocol.identity().hex(), output)


@pytest.mark.parametrize(
    "fault",
    [
        "pin",
        "controller",
        "file",
        "symlink",
        "parent-link",
        "hardlink",
        "fifo",
        "duplicate-json",
        "nan",
        "duplicate-path",
        "wrong-fixture",
        "platform",
    ],
)
def test_preflight_rejects_before_output(prepared, monkeypatch, fault):
    path, protocol, output = prepared
    if fault == "pin":
        prepared = (path, protocol.model_copy(update={"controller_sha256": b"x" * 32}), output)
    elif fault == "controller":
        monkeypatch.setattr(q, "controller_sha256", lambda: b"x" * 32)
    elif fault == "file":
        (path.parent / "binary").write_bytes(b"changed")
    elif fault in {"symlink", "hardlink", "fifo"}:
        binary = path.parent / "binary"
        original = path.parent / "original"
        binary.rename(original)
        if fault == "symlink":
            binary.symlink_to(original)
        elif fault == "hardlink":
            os.link(original, binary)
        else:
            os.mkfifo(binary)
    elif fault == "parent-link":
        source = path.parent / "directory"
        source.mkdir()
        (path.parent / "binary").rename(source / "binary")
        (path.parent / "link").symlink_to(source, target_is_directory=True)
        protocol = protocol.model_copy(
            update={"binary": protocol.binary.model_copy(update={"path": "link/binary"})}
        )
        path.write_text(protocol.model_dump_json())
        prepared = (path, protocol, output)
    elif fault == "duplicate-json":
        path.write_text(path.read_text().replace("{", '{"host":"macos-arm64",', 1))
    elif fault == "nan":
        path.write_text(path.read_text().replace('"total_seconds":120', '"total_seconds":NaN'))
    elif fault == "duplicate-path":
        value = json.loads(path.read_text())
        value["source_review"] = value["binary"]
        path.write_text(json.dumps(value))
    elif fault == "wrong-fixture":
        data = (path.parent / "mlp_fixture").read_bytes()
        (path.parent / "rule_fixture").write_bytes(data)
        protocol = protocol.model_copy(
            update={
                "rule_fixture": FileRef(
                    path="rule_fixture",
                    size=len(data),
                    sha256=FileSHA256(hashlib.sha256(data).digest()),
                )
            }
        )
        path.write_text(protocol.model_dump_json())
        prepared = (path, protocol, output)
    else:
        monkeypatch.setattr(q.platform, "system", lambda: "Linux")
    with pytest.raises((ValueError, HallmarkError, OSError)):
        call(prepared)
    assert not output.exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("total_seconds", 7201),
        ("case_seconds", 121),
        ("verify_seconds", 31),
        ("threads", 5),
        ("threads", True),
        ("case_cpu_seconds", 0),
        ("max_worker_rss_bytes", 17 * 1024**3),
        ("max_output_bytes", 21 * 1024**3),
    ],
)
def test_protocol_budget_bounds(prepared, field, value):
    _, protocol, _ = prepared
    document = protocol.model_dump(mode="json")
    document["limits"][field] = value
    with pytest.raises(ValueError):
        q.QualificationProtocol.model_validate_json(json.dumps(document))


def fake_stages(monkeypatch, calls, *, fault=None):
    def check(*args, budget):
        output = args[-1]
        stage = output.name
        calls.append(stage)
        output.mkdir(mode=0o700)
        if fault == "interrupt":
            raise KeyboardInterrupt
        if fault == stage:
            raise RuntimeError("private-file-secret")
        count = dict(q.STAGES)[stage]
        report = {"status": "passed", "qualified_backend": False, "cases": [None] * count}
        worker.json_new(output / "result.json", report)
        return report

    monkeypatch.setattr(q.worker, "check", check)
    monkeypatch.setattr(q.graph, "check", check)
    monkeypatch.setattr(q.block, "check", check)


def test_passing_marker_stages_never_qualify(prepared, monkeypatch):
    calls = []
    fake_stages(monkeypatch, calls)
    result = call(prepared)
    assert calls == [name for name, _ in q.STAGES]
    assert result["status"] == "incomplete" and result["qualified_backend"] is False
    assert result["missing"] == list(q.MISSING)
    assert sum(row["cases"] for row in result["completed"]) == 541
    assert json.loads((prepared[2] / "result.json").read_bytes()) == result
    assert not (prepared[2] / "failure.json").exists()
    for entry in prepared[2].rglob("*"):
        assert entry.stat().st_mode & 0o077 == 0
    with pytest.raises(FileExistsError):
        call(prepared)


@pytest.mark.parametrize(
    "fault,expected", [("mlp", ["installation", "rule", "mlp"]), ("interrupt", ["installation"])]
)
def test_failure_retained_without_false_result(prepared, monkeypatch, fault, expected):
    calls = []
    fake_stages(monkeypatch, calls, fault=fault)
    with pytest.raises(HallmarkError):
        call(prepared)
    assert calls == expected
    assert not (prepared[2] / "result.json").exists()
    failure = (prepared[2] / "failure.json").read_text()
    assert "private-file-secret" not in failure
    assert json.loads(failure)["status"] == "failed"


def test_snapshots_are_used_after_source_change(prepared, monkeypatch):
    original = q.block.validate_fixture

    def mutate(raw):
        result = original(raw)
        (prepared[0].parent / "binary").write_bytes(b"replaced after read")
        return result

    monkeypatch.setattr(q.block, "validate_fixture", mutate)
    calls = []
    fake_stages(monkeypatch, calls)
    call(prepared)
    snapshot = (prepared[2] / "inputs/binary").read_bytes()
    assert hashlib.sha256(snapshot).digest() == prepared[1].binary.sha256


def test_global_budget_stops_before_next_stage(prepared, monkeypatch):
    calls = []
    fake_stages(monkeypatch, calls)
    original = worker.RunBudget.inspect

    def stop(budget, cost=None):
        if calls:
            raise TimeoutError("deadline")
        return original(budget, cost)

    monkeypatch.setattr(worker.RunBudget, "inspect", stop)
    with pytest.raises(HallmarkError):
        call(prepared)
    assert calls == ["installation"]
    assert not (prepared[2] / "result.json").exists()


@pytest.mark.parametrize(
    "fault",
    [
        "deadline",
        "storage",
        "symlink",
        "hardlink",
        "rss",
        "cpu",
        "timeout",
        "memory_limit_exceeded",
        "memory_monitor_failed",
    ],
)
def test_measured_budget_rejects(tmp_path, fault):
    budget = worker.RunBudget(tmp_path, time.monotonic() + 10, 3, 1, 2, 1, 1024, 10)
    cost = {"timed_out": False, "max_rss_bytes": 1, "user_seconds": 1, "system_seconds": 0}
    if fault == "deadline":
        budget.deadline = time.monotonic() - 1
    elif fault == "storage":
        (tmp_path / "large").write_bytes(b"0" * 11)
    elif fault in {"symlink", "hardlink"}:
        (tmp_path / "file").write_bytes(b"0")
        if fault == "symlink":
            (tmp_path / "link").symlink_to(tmp_path / "file")
        else:
            os.link(tmp_path / "file", tmp_path / "link")
    elif fault == "rss":
        cost["max_rss_bytes"] = 1025
    elif fault == "cpu":
        cost["system_seconds"] = 2
    elif fault in {"memory_limit_exceeded", "memory_monitor_failed"}:
        cost[fault] = True
    else:
        cost["timed_out"] = True
    with pytest.raises((TimeoutError, MemoryError, ValueError)):
        budget.inspect(cost)


def test_cli_returns_incomplete_as_nonzero(prepared, monkeypatch, capsys):
    fake_stages(monkeypatch, [])
    path, protocol, output = prepared
    assert (
        main(
            [
                "qualify",
                str(path),
                "--expected-protocol",
                protocol.identity().hex(),
                "--output",
                str(output),
            ]
        )
        == 3
    )
    assert json.loads(capsys.readouterr().out)["status"] == "incomplete"


def test_cli_preflight_and_parser_are_private(tmp_path, capsys):
    secret = str(tmp_path / "private-path-secret")
    assert main(["qualify", secret, "--expected-protocol", "bad", "--output", secret]) == 2
    capture = capsys.readouterr()
    assert secret not in capture.err + capture.out
    assert main(["qualify", "--private-secret"]) == 2
    assert "private-secret" not in capsys.readouterr().err


def test_schema_snapshot():
    expected = json.loads((ROOT / "docs/schemas/qualification-protocol-v1.json").read_bytes())
    assert q.QualificationProtocol.model_json_schema() == expected


@pytest.mark.skipif(os.uname().sysname != "Darwin", reason="macOS sandbox boundary")
def test_shared_deadline_reaps_live_worker_and_keeps_cost(tmp_path):
    directory = tmp_path / "case"
    directory.mkdir()
    budget = worker.RunBudget(tmp_path, time.monotonic() + 0.2, 30, 1, 10, 1, 1024**3, 1024**2)
    with pytest.raises(TimeoutError):
        worker.invoke(Path("/bin/sleep"), directory, ["10"], budget=budget)
    cost = json.loads((directory / "cost.json").read_bytes())
    assert cost["timed_out"] and cost["exit_code"] == -9
    assert cost["elapsed_seconds"] < 2
    plan = json.loads((directory / "plan.json").read_bytes())
    assert plan["environment"]["GOMAXPROCS"] == "1"
    assert plan["wall_limit_seconds"] < 0.2


@pytest.mark.parametrize(
    "script", ["check_gnark_probe.py", "check_gnark_rule_probe.py", "check_gnark_block_probe.py"]
)
def test_compatibility_cli_parser_is_private(script):
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), "--private-secret"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 3 and not result.stderr
    assert "private-secret" not in result.stdout


def test_marker_fixture_reproduces():
    import subprocess
    import sys

    actual = subprocess.check_output(
        [sys.executable, str(ROOT / "scripts/build_qualification_fixture.py")], timeout=5
    )
    assert json.loads(actual) == json.loads(
        (ROOT / "fixtures/wire/qualification-protocol-v1.json").read_bytes()
    )


@pytest.mark.parametrize("kind", ["rule", "mlp", "block"])
def test_duplicate_fixture_keys_reject(kind):
    raw = (ROOT / f"research/probes/gnark/{kind}-fixture.json").read_bytes()
    altered = raw.replace(b"{", b'{"qualified_backend":false,', 1)
    controller = q.block if kind == "block" else q.graph
    with pytest.raises(ValueError, match="duplicate"):
        controller.validate_fixture(altered)
