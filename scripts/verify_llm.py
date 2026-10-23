"""Build a fixed-case Mac verifier and check a retained TinyLlama proof bundle."""

import argparse
import json
import os
import platform
import resource
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

from run_e2e import sha, write_json
from run_llm_e2e import fetch, require

from hallmark._gnark_probe import sandbox_profile, stream_regular

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "research/probes/sash"
TOOLCHAIN = "nightly-2025-07-14"
MEMORY_STOP = 4 * 1024**3


def process_group_rss(group):
    rows = subprocess.check_output(["/bin/ps", "-axo", "pgid=,rss="], text=True, timeout=5)
    total = 0
    for row in rows.splitlines():
        parts = row.split()
        require(len(parts) == 2, "invalid process monitor output")
        if int(parts[0]) == group:
            require(int(parts[1]) >= 0, "invalid process memory")
            total += int(parts[1]) * 1024
    return total


def bounded(args, folder, environment, seconds, *, cwd=None):
    """Bound compiler/worker descendants together; retain every failed attempt."""
    folder.mkdir()
    write_json(folder / "command.json", dict(argv=list(map(str, args)), seconds=seconds))
    start = time.monotonic()
    peak = 0
    failure = None
    with (folder / "output.log").open("x") as log:
        process = subprocess.Popen(
            list(map(str, args)),
            cwd=cwd,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            while process.poll() is None:
                peak = max(peak, process_group_rss(process.pid))
                require(peak <= MEMORY_STOP, "process-group memory limit")
                require(time.monotonic() - start <= seconds, "process-group time limit")
                time.sleep(0.25)
            require(process.returncode == 0, f"command exited {process.returncode}")
        except BaseException as error:
            failure = type(error).__name__
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            raise
        finally:
            write_json(
                folder / "cost.json",
                dict(
                    exit_code=process.returncode,
                    seconds=time.monotonic() - start,
                    sampled_process_group_peak_rss_bytes=peak,
                    failure=failure,
                    memory_stop_bytes=MEMORY_STOP,
                    sample_seconds=0.25,
                ),
            )


def enrolled_shapes(case):
    roots = {}
    for row in case["expected_roots"]:
        key, root = row["shape_key"], row["pre_root"]
        require(key not in roots or roots[key] == root, "conflicting shape enrollment")
        roots[key] = root
    require(len(case["expected_roots"]) == 23, "incomplete enrollment")
    return roots


def run(previous):
    require(
        (platform.system(), platform.machine()) == ("Darwin", "arm64"),
        "Native verification requires an Apple Silicon Mac",
    )
    require(shutil.which("cargo") is not None, "Install Rust and the pinned nightly toolchain")
    require(shutil.disk_usage(ROOT).free >= 8 * 1024**3, "At least 8 GiB free storage is required")
    previous = previous.resolve()
    require((previous / "proofs.tar.gz").is_file(), "Choose a retained make e2e-llm run directory")
    case = json.loads((PROBE / "response-case.json").read_text())
    shapes = enrolled_shapes(case)
    (ROOT / "runs").mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="llm-verify-", dir=ROOT / "runs"))
    print(f"Outputs: {output}", flush=True)
    started = time.monotonic()
    frozen = {
        str(p.relative_to(ROOT)): sha(p)
        for p in (
            Path(__file__),
            ROOT / "scripts/run_e2e.py",
            ROOT / "scripts/run_llm_e2e.py",
            ROOT / "src/hallmark/_gnark_probe.py",
            PROBE / "response-case.json",
            PROBE / "native-verifier.patch",
            PROBE / "verify_response.py",
            PROBE / "check_response.py",
        )
    }
    write_json(
        output / "protocol.json",
        dict(
            schema_id="hallmark.native-llm-verification/1",
            source_files=frozen,
            toolchain=TOOLCHAIN,
            shape_root_source="compiled-enrollment",
            source_dirty=True,
            memory_stop_bytes=MEMORY_STOP,
            build_seconds=1800,
            verification_seconds=600,
            threads=4,
            cloud_cost_usd=0,
            qualified_backend=False,
        ),
    )
    environment = {k: os.environ[k] for k in ("PATH", "HOME", "TMPDIR") if k in os.environ}
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        compressed = output / "source.tar.gz"
        source = case["source"]
        if (previous / "source.tar.gz").is_file():
            stream_regular(previous / "source.tar.gz", source["bytes"], destination=compressed)
            require(sha(compressed) == source["sha256"], "source archive mismatch")
        else:
            fetch(source["url"], compressed, source["sha256"], source["bytes"])
        with tarfile.open(compressed) as archive:
            archive.extractall(output / "source", filter="data")
        unpacked = list((output / "source").iterdir())
        require(len(unpacked) == 1 and unpacked[0].is_dir(), "unexpected source archive")
        source_dir = unpacked[0]
        environment["GIT_CEILING_DIRECTORIES"] = str(source_dir.parent)
        bounded(
            ["git", "apply", PROBE / "native-verifier.patch"],
            output / "patch",
            environment,
            30,
            cwd=source_dir,
        )
        write_json(source_dir / "prover/src/enrolled_shapes.json", shapes)
        (source_dir / ".source-commit").write_text(source["revision"] + " dirty\n")
        environment.update(
            CARGO_TARGET_DIR=str(output / "target"),
            CARGO_BUILD_JOBS="4",
            RAYON_NUM_THREADS="4",
            ZK_SOURCE_COMMIT=source["revision"],
            ZK_SOURCE_DIRTY="true",
        )
        print("Building the verifier for the compiled enrollment", flush=True)
        bounded(
            ["cargo", "+" + TOOLCHAIN, "build", "--release", "--locked", "-j", "4"],
            output / "build",
            environment,
            1800,
            cwd=source_dir,
        )
        binary = output / "target/release/zk-prover"
        require(binary.is_file() and binary.stat().st_size <= 128 * 1024**2, "missing verifier")
        worker = output / "verification"
        worker.mkdir()
        for name, limit in [("proofs.tar.gz", 512 * 1024**2), ("proof-inventory.json", 1024**2)]:
            stream_regular(previous / name, limit, destination=worker / name)
        for name in ("check_response.py", "verify_response.py"):
            shutil.copy2(PROBE / name, worker / name)
        shutil.copy2(binary, worker / "zk-prover")
        (worker / "zk-prover").chmod(0o700)
        write_json(
            worker / "expected.json",
            dict(
                schema_id="hallmark.sash-response-expectations/1",
                roots=case["expected_roots"],
                prompt_ids=case["prompt_ids"],
                answer_ids=case["answer_ids"],
                binary_sha256=sha(binary),
            ),
        )
        inputs = {p.name: sha(p) for p in worker.iterdir()}
        write_json(
            worker / "protocol.json",
            dict(
                schema_id="hallmark.native-llm-worker/1",
                source_commit=source["revision"],
                source_dirty=True,
                shape_root_source="compiled-enrollment",
                inputs=inputs,
                expected_sha256=inputs["expected.json"],
                max_single_file_bytes=2 * 1024**3,
            ),
        )
        require(all(sha(ROOT / name) == pin for name, pin in frozen.items()), "source changed")
        python = Path(sys.executable).resolve()
        profile = sandbox_profile(python, worker)
        profile += "\n(allow process-fork)\n(allow file-read* file-map-executable (subpath "
        profile += json.dumps(sys.base_prefix) + "))\n"
        (worker / "sandbox.sb").write_text(profile)
        canary = output / "sandbox-denied.txt"
        canary.write_text("harmless sandbox control\n")
        control = """
import json, pathlib, socket, subprocess, sys
p = subprocess.run([sys.argv[1]], capture_output=True)
assert p.returncode == 2 and b"requires boundary-grid --verify" in p.stderr
try:
    pathlib.Path(sys.argv[2]).read_bytes()
except PermissionError:
    pass
else:
    raise RuntimeError("sandbox allowed an outside file")
try:
    with socket.socket() as sock:
        sock.connect(("127.0.0.1", 9))
except PermissionError:
    pass
else:
    raise RuntimeError("sandbox allowed networking")
print(json.dumps(dict(fork=True, outside_file_denied=True, network_denied=True)))
"""
        restricted = {"PATH": "/usr/bin:/bin", "LANG": "C", "TZ": "UTC"}
        bounded(
            [
                "/usr/bin/sandbox-exec",
                "-f",
                worker / "sandbox.sb",
                python,
                "-I",
                "-B",
                "-c",
                control,
                worker / "zk-prover",
                canary,
            ],
            output / "sandbox-control",
            restricted,
            20,
            cwd=worker,
        )
        entry = (
            "import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); "
            "script=sys.argv.pop(1); runpy.run_path(script,run_name='__main__')"
        )
        args = [
            "/usr/bin/sandbox-exec",
            "-f",
            worker / "sandbox.sb",
            python,
            "-I",
            "-B",
            "-c",
            entry,
            worker,
            worker / "verify_response.py",
            "--root",
            worker,
            "--work",
            worker / "work",
        ]
        print("Verifying twice, then checking changed claims and unknown shapes", flush=True)
        bounded(
            args,
            output / "verify",
            restricted,
            600,
            cwd=worker,
        )
        report = json.loads((worker / "output/result.json").read_text())
        require(report["passed"] is True and len(report["cases"]) == 38, "incomplete suite")
        require(sum(c["accepted"] for c in report["cases"]) == 2, "incorrect suite outcomes")
        result = dict(
            passed=True,
            response=case["response"],
            proofs=23,
            residual_links=22,
            fresh_verifications=2,
            baseline_mutations_rejected=14,
            native_enrollment_mutations_rejected=2,
            native_boundary_mutations_rejected=20,
            seconds=time.monotonic() - started,
            verifier_sha256=sha(binary),
            shape_root_source="compiled-enrollment",
            cloud_cost_usd=0,
            qualified_backend=False,
            security_review=False,
        )
        write_json(output / "result.json", result)
        print(json.dumps(result, indent=2), flush=True)
        return output
    except BaseException as error:
        write_json(
            output / "failure.json",
            dict(type=type(error).__name__, seconds=time.monotonic() - started),
        )
        print(f"Failed; evidence retained at {output}", flush=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run", required=True, type=Path, help="retained make e2e-llm run directory"
    )
    run(parser.parse_args().run)
