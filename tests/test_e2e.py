"""Fast orchestration failure checks; real proofs are exercised by make e2e."""

import copy
import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_e2e as e2e


def test_command_retains_failure_and_stops_at_deadline(tmp_path):
    log = tmp_path / "failed.log"
    with pytest.raises(RuntimeError, match="exited 7"):
        e2e.command(
            [sys.executable, "-c", "print('retained');exit(7)"],
            log,
            os.environ,
            time.monotonic() + 10,
        )
    assert "retained" in log.read_text()
    with pytest.raises(TimeoutError):
        e2e.command(["never-executed"], tmp_path / "timeout.log", os.environ, 0)
    assert not (tmp_path / "timeout.log").exists()
    with pytest.raises(FileExistsError):
        e2e.command(["never-executed"], log, os.environ, time.monotonic() + 10)


def test_command_timeout_kills_stage(tmp_path):
    with pytest.raises(e2e.subprocess.TimeoutExpired):
        e2e.command(
            [sys.executable, "-c", "import time;time.sleep(30)"],
            tmp_path / "timeout.log",
            os.environ,
            time.monotonic() + 0.1,
        )


def test_training_screen_and_export_failure(tmp_path, monkeypatch):
    (tmp_path / "cnn-training").mkdir()
    result = tmp_path / "cnn-training/results.json"
    result.write_text('{"all_seeds_pass":false}')
    with pytest.raises(ValueError, match="screen failed"):
        e2e.check_training(tmp_path)
    result.write_text('{"all_seeds_pass":true}')
    monkeypatch.setattr(e2e, "sha", lambda _: "wrong")
    with pytest.raises(ValueError, match="quantization pin mismatch"):
        e2e.check_training(tmp_path)


def proof_result():
    return dict(
        status="passed",
        qualified_backend=False,
        hardware_claim="not-accepted",
        cases=copy.deepcopy(e2e.CASES),
        cross_request_rejections=[
            [t, s, k]
            for t in ["allow", "cnn-block", "rule-block"]
            for s in ["allow", "cnn-block", "rule-block"]
            if t != s
            for k in range(3)
        ],
        arithmetic_cases=dict(rule=135, mlp=135, encoder=135),
    )


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r.update(status="failed"),
        lambda r: r["cases"].pop(),
        lambda r: r["cases"][1].update(release=True),
        lambda r: r["cases"][0].update(proofs_verified=2),
        lambda r: r["cross_request_rejections"].pop(),
        lambda r: r["arithmetic_cases"].update(encoder=134),
        lambda r: r.update(qualified_backend=True),
        lambda r: r.update(hardware_claim="accepted"),
    ],
)
def test_reject_incomplete_or_overclaimed_result(tmp_path, change):
    (tmp_path / "proofs").mkdir()
    path = tmp_path / "proofs/result.json"
    result = proof_result()
    path.write_text(json.dumps(result))
    assert e2e.check_proofs(tmp_path) == result
    change(result)
    path.write_text(json.dumps(result))
    with pytest.raises(ValueError, match="unexpected proof"):
        e2e.check_proofs(tmp_path)


def test_unsupported_host_stops_before_acquisition(monkeypatch):
    monkeypatch.setattr(e2e.platform, "system", lambda: "Linux")
    with pytest.raises(ValueError, match="Apple Silicon"):
        e2e.run()


def test_failed_runs_are_separate_and_retained(tmp_path, monkeypatch):
    monkeypatch.setattr(e2e, "ROOT", tmp_path)
    monkeypatch.setattr(e2e.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(e2e.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(e2e.platform, "platform", lambda: "fixture-host")
    monkeypatch.setattr(e2e.sys, "version_info", (3, 12, 12))
    monkeypatch.setattr(e2e.subprocess, "check_output", lambda *a, **k: "uv 0.9.18")
    monkeypatch.setattr(e2e, "source_pins", lambda: {"fixture": "pin"})
    monkeypatch.setattr(e2e.shutil, "disk_usage", lambda _: type("Disk", (), {"free": 2**40})())

    def fail(*args, **kwargs):
        raise RuntimeError("fixture-stage-failure")

    monkeypatch.setattr(e2e, "command", fail)
    for _ in range(2):
        with pytest.raises(RuntimeError, match="fixture-stage-failure"):
            e2e.run()
    runs = list((tmp_path / "runs").iterdir())
    assert len(runs) == 2
    for run in runs:
        assert json.loads((run / "failure.json").read_text())["stage"] == "python-packages"
        assert not (run / "result.json").exists()
        assert run.stat().st_mode & 0o777 == 0o700


def test_timeout_allows_controller_to_reap_separate_worker(tmp_path):
    marker = tmp_path / "reaped"
    controller = """
import os, signal, subprocess, sys
worker = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(60)'],
                          start_new_session=True)
try:
    worker.wait()
except KeyboardInterrupt:
    os.killpg(worker.pid, signal.SIGKILL)
    worker.wait()
    from pathlib import Path
    Path(sys.argv[1]).write_text('reaped')
    raise
"""
    with pytest.raises(e2e.subprocess.TimeoutExpired):
        e2e.command(
            [sys.executable, "-c", controller, marker],
            tmp_path / "controller.log",
            os.environ,
            time.monotonic() + 2,
        )
    assert marker.read_text() == "reaped"


def test_make_keeps_validation_as_default():
    default = e2e.subprocess.check_output(
        ["make", "--no-print-directory", "-n"], cwd=e2e.ROOT, text=True
    )
    assert default.splitlines()[0] == "uv lock --check"
    explicit = e2e.subprocess.check_output(
        ["make", "--no-print-directory", "-n", "e2e"], cwd=e2e.ROOT, text=True
    )
    assert "scripts/run_circle_e2e.py" in explicit
    assert "scripts/run_e2e.py" not in explicit
