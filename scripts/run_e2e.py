"""Shared end-to-end helpers: source pins, bounded stage commands and frozen exports."""

import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CNN_PROTOCOL = "3c47c07a5a3413f00814b957ae8752bcb3f786b0c6484becd6cab5290beb5394"
EXPORTS = {
    "mlp-training/seed-17/quantization.json": (
        "f8090161455ee56cdcd73eaab44437efa3b278a786d7c246491da5f1e1431a9c"
    ),
    "cnn-training/17/quantization.json": (
        "8de31ae0215178f5c74aa43e58dd63511bc3b6a881c2045cc96def9e149b8f0b"
    ),
}


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2) + "\n")


def source_pins():
    paths = (
        subprocess.check_output(
            [
                "git",
                "ls-files",
                "-z",
                "src",
                "scripts",
                "fixtures",
                "configs",
                "research/probes",
                "Makefile",
                "pyproject.toml",
                "uv.lock",
                ".python-version",
            ],
            cwd=ROOT,
            timeout=10,
        )
        .decode()
        .split("\0")
    )
    return {p: sha(ROOT / p) for p in paths if p}


def command(args, log, env, deadline, cwd=ROOT):
    """Keep child output local and terminate the entire stage on timeout/interruption."""
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("end-to-end deadline exceeded")
    print(f"Running {log.stem}; log: {log}", flush=True)
    with log.open("x") as stream:
        with subprocess.Popen(
            [str(a) for a in args],
            cwd=cwd,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        ) as process:
            try:
                code = process.wait(timeout=remaining)
            except BaseException:
                # Let the Python proof controller reap its separately grouped workers.
                try:
                    os.killpg(process.pid, signal.SIGINT)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                raise
            if code:
                raise RuntimeError(f"{log.stem} exited {code}; inspect {log}")
    print(f"Completed {log.stem}", flush=True)


def check_training(output):
    if json.loads((output / "cnn-training/results.json").read_text())["all_seeds_pass"] is not True:
        raise ValueError("CNN synthetic screen failed; retain this run, do not retune on test")
    for path, pin in EXPORTS.items():
        if sha(output / path) != pin:
            raise ValueError("selected quantization pin mismatch: " + path)
