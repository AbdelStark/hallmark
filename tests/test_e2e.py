"""Fast orchestration helper failure checks; real proofs are exercised by make e2e."""

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
