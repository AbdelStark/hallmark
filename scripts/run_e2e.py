"""One-command reproduction of the frozen Mac classifier demo; no hardware claim."""

import hashlib
import json
import os
import platform
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GO_ARCHIVE = "go1.26.8.darwin-arm64.tar.gz"
GO_SHA256 = "a012b25b571bd0138a03dcd25375ceba866fe5ca822f426d2c66a4de56fd3f4b"
CNN_PROTOCOL = "3c47c07a5a3413f00814b957ae8752bcb3f786b0c6484becd6cab5290beb5394"
EXPORTS = {
    "mlp-training/seed-17/quantization.json": (
        "f8090161455ee56cdcd73eaab44437efa3b278a786d7c246491da5f1e1431a9c"
    ),
    "cnn-training/17/quantization.json": (
        "8de31ae0215178f5c74aa43e58dd63511bc3b6a881c2045cc96def9e149b8f0b"
    ),
}
CASES = [
    dict(name="allow", proofs_verified=3, release=True, verdicts=[1, 1, 1]),
    dict(name="cnn-block", proofs_verified=3, release=False, verdicts=[1, 1, 0]),
    dict(name="rule-block", proofs_verified=3, release=False, verdicts=[0, 1, 1]),
]


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


def check_proofs(output):
    result = json.loads((output / "proofs/result.json").read_text())
    rejections = [
        [t, s, k]
        for t in (c["name"] for c in CASES)
        for s in (c["name"] for c in CASES)
        if t != s
        for k in range(3)
    ]
    if (
        result["status"] != "passed"
        or result["qualified_backend"] is not False
        or result["hardware_claim"] != "not-accepted"
        or result["cases"] != CASES
        or result["cross_request_rejections"] != rejections
        or result["arithmetic_cases"] != dict(rule=135, mlp=135, encoder=135)
    ):
        raise ValueError("incomplete or unexpected proof campaign result")
    return result


def run():
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise ValueError("make e2e requires an Apple Silicon Mac; see docs/DEMO.md")
    uv_version = subprocess.check_output(["uv", "--version"], text=True, timeout=10).strip()
    if uv_version.split()[:2] != ["uv", "0.9.18"] or sys.version_info[:3] != (3, 12, 12):
        raise ValueError("use uv 0.9.18 and CPython 3.12.12 for the frozen reproduction")
    if shutil.disk_usage(ROOT).free < 12 * 1024**3:
        raise ValueError("make e2e requires at least 12 GiB free storage")
    (ROOT / "runs").mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="e2e-", dir=ROOT / "runs"))
    print(f"Evidence: {output}\nExpect about 20 minutes plus dependency/build time.", flush=True)
    started = time.monotonic()
    deadline = started + 7200
    stage = "source"
    env = os.environ | dict(
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        VECLIB_MAXIMUM_THREADS="1",
        PYTHONUNBUFFERED="1",
        GOROOT=str(output / "toolchain/go"),
        GOPATH=str(output / "gopath"),
        GOMODCACHE=str(output / "gomodcache"),
        GOCACHE=str(output / "gocache"),
        GOTOOLCHAIN="local",
        GOTELEMETRY="off",
        CGO_ENABLED="0",
        GOFLAGS="-p=2",
        GOMAXPROCS="2",
        GOMEMLIMIT="1GiB",
    )
    try:
        pins = source_pins()
        write_json(output / "source-pins.json", pins)
        write_json(
            output / "environment.json",
            dict(
                schema_id="hallmark.e2e-environment/1",
                uv=uv_version,
                python=sys.version,
                host=platform.platform(),
                seconds=7200,
                cloud_cost_minor=0,
                source_commit=subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=ROOT,
                    text=True,
                    timeout=10,
                ).strip(),
            ),
        )

        def step(name, args, cwd=ROOT):
            nonlocal stage
            stage = name
            command(args, output / (name + ".log"), env, deadline, cwd)

        step("python-packages", ["uv", "pip", "freeze", "--python", sys.executable])
        archive = output / "go.tar.gz"
        step(
            "download-go",
            [
                "curl",
                "--fail",
                "--silent",
                "--show-error",
                "--location",
                "--max-time",
                "120",
                "https://go.dev/dl/" + GO_ARCHIVE,
                "--output",
                archive,
            ],
        )
        stage = "check-go-archive"
        if sha(archive) != GO_SHA256:
            raise ValueError("Go archive checksum mismatch")
        with tarfile.open(archive) as source:
            source.extractall(output / "toolchain", filter="data")
        go = output / "toolchain/go/bin/go"
        probe = output / "probe"
        step("go-version", [go, "version"])
        for name, args in (
            ("download-modules", ["mod", "download"]),
            ("verify-modules", ["mod", "verify"]),
            (
                "build-circuits",
                [
                    "build",
                    "-trimpath",
                    "-buildvcs=false",
                    "-ldflags=-buildid=",
                    "-toolexec=" + shlex.join([sys.executable, str(ROOT / "scripts/go_tool.py")]),
                    "-mod=readonly",
                    "-o",
                    probe,
                    ".",
                ],
            ),
        ):
            step(name, [go, *args], ROOT / "research/probes/gnark")
        binary_pin = sha(probe)
        (output / "probe.sha256").write_text(binary_pin + "\n")
        verifier = output / "verifier-env/bin/python"
        step("verifier-env", ["uv", "venv", "--python", "3.12.12", verifier.parent.parent])
        step(
            "verifier-packages",
            [
                "uv",
                "pip",
                "install",
                "--python",
                verifier,
                "--require-hashes",
                "--only-binary",
                ":all:",
                "-r",
                "research/probes/py_ecc/requirements.txt",
            ],
        )
        step(
            "mlp-training",
            [
                sys.executable,
                "scripts/check_mlp_training.py",
                "fixtures/mlp-training.json",
                "--expected-fixture",
                (ROOT / "fixtures/mlp-training.sha256").read_text().strip(),
                "--output",
                output / "mlp-training",
            ],
        )
        step(
            "cnn-training",
            [
                sys.executable,
                "scripts/run_contextual_cnn.py",
                "--study",
                "v2",
                "--expected-protocol",
                CNN_PROTOCOL,
                "--output",
                output / "cnn-training",
            ],
        )
        stage = "check-training"
        check_training(output)
        step(
            "proofs",
            [
                sys.executable,
                "scripts/run_trained_common.py",
                "--binary",
                probe,
                "--expected-binary",
                binary_pin,
                "--verifier-python",
                verifier,
                "--mlp-quantization",
                output / "mlp-training/seed-17/quantization.json",
                "--cnn-quantization",
                output / "cnn-training/17/quantization.json",
                "--output",
                output / "proofs",
            ],
        )
        stage = "check-results"
        result = check_proofs(output)
        if source_pins() != pins:
            raise ValueError("pipeline source changed during the run")
        write_json(
            output / "result.json",
            dict(
                schema_id="hallmark.e2e-result/1",
                status="passed",
                cases=result["cases"],
                proofs_verified=9,
                cross_request_rejections=18,
                arithmetic_cases=405,
                proof_result_sha256=sha(output / "proofs/result.json"),
                elapsed_seconds=time.monotonic() - started,
                qualified_backend=False,
                hardware_claim="not-accepted",
            ),
        )
        print(
            "\nPASS: 9 proofs verified; 18 cross-request substitutions rejected; "
            "405 arithmetic cases matched.",
            flush=True,
        )
        for case in result["cases"]:
            print(f"  {case['name']}: {case['verdicts']} release={str(case['release']).lower()}")
        print(f"Results: {output / 'result.json'}\nProof meaning: docs/PROOFS.md")
        return output
    except BaseException as error:
        write_json(
            output / "failure.json",
            dict(
                schema_id="hallmark.e2e-failure/1",
                status="failed",
                stage=stage,
                error_type=type(error).__name__,
                elapsed_seconds=time.monotonic() - started,
            ),
        )
        print(f"FAILED at {stage}; evidence retained at {output}", file=sys.stderr, flush=True)
        raise


if __name__ == "__main__":
    run()
