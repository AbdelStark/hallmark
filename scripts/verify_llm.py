"""Build a fixed-case Mac verifier and check a retained TinyLlama proof bundle."""

import argparse
import hashlib
import json
import os
import platform
import re
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

from hallmark._gnark_probe import (
    MAX_OPEN_FILES,
    limit_open_files,
    read_regular,
    sandbox_profile,
    stream_regular,
)
from hallmark.integrity import parse_json
from hallmark.llm_enrollment import verify_llm_enrollment
from hallmark.wire import H

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "research/probes/sash"
TOOLCHAIN = "nightly-2025-07-14"
MEMORY_STOP = 4 * 1024**3


def source_inventory():
    paths = (
        Path(__file__),
        ROOT / "scripts/run_e2e.py",
        ROOT / "scripts/run_llm_e2e.py",
        *sorted((ROOT / "src/hallmark").glob("*.py")),
        ROOT / "uv.lock",
        PROBE / "response-case.json",
        PROBE / "native-verifier.patch",
        PROBE / "verify_response.py",
        PROBE / "check_response.py",
    )
    return {str(path.relative_to(ROOT)): sha(path) for path in paths}


def verifier_identity(inventory):
    return H("program", dict(schema_id="hallmark/llm-verifier-source/1", files=inventory))


def read_enrollment(enrollment, trusted_key):
    require(
        (enrollment is None) == (trusted_key is None), "Supply enrollment and trusted key together"
    )
    if enrollment is None:
        return None, None
    require(
        isinstance(trusted_key, str) and re.fullmatch(r"[0-9a-f]{64}", trusted_key),
        "Trusted Ed25519 key must be 64 lowercase hex characters",
    )
    return read_regular(enrollment, 16384), bytes.fromhex(trusted_key)


def parameter_authority(signed, key, *, case_sha256, verifier, stage):
    if signed is None:
        return dict(kind="checkout-case")
    checked_at = int(time.time())
    body = verify_llm_enrollment(
        signed,
        trusted_key=key,
        expected_case=case_sha256,
        expected_verifier=verifier,
        now=checked_at,
    )
    return dict(
        schema_id="hallmark.llm-parameter-authority/1",
        kind="ed25519",
        enrollment_sha256=hashlib.sha256(signed).hexdigest(),
        trusted_key_sha256=hashlib.sha256(key).hexdigest(),
        not_before=body.not_before,
        expires_at=body.expires_at,
        checked_at=checked_at,
        stage=stage,
    )


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
    write_json(
        folder / "command.json",
        dict(argv=list(map(str, args)), seconds=seconds, max_open_files=MAX_OPEN_FILES),
    )
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
            preexec_fn=limit_open_files,
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


def run(previous, *, enrollment=None, trusted_key=None):
    require(
        (platform.system(), platform.machine()) == ("Darwin", "arm64"),
        "Native verification requires an Apple Silicon Mac",
    )
    require(shutil.which("cargo") is not None, "Install Rust and the pinned nightly toolchain")
    require(shutil.disk_usage(ROOT).free >= 8 * 1024**3, "At least 8 GiB free storage is required")
    previous = previous.resolve()
    require((previous / "proofs.tar.gz").is_file(), "Choose a retained make e2e-llm run directory")
    case_raw = read_regular(PROBE / "response-case.json", 1024**2)
    case = parse_json(case_raw.decode("utf-8"))
    shapes = enrolled_shapes(case)
    (ROOT / "runs").mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="llm-verify-", dir=ROOT / "runs"))
    print(f"Outputs: {output}", flush=True)
    started = time.monotonic()
    frozen = source_inventory()
    verifier = verifier_identity(frozen)
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
            max_open_files=MAX_OPEN_FILES,
            verification_seconds=600,
            threads=4,
            cloud_cost_usd=0,
            qualified_backend=False,
            verifier_identity=verifier.hex(),
        ),
    )
    environment = {k: os.environ[k] for k in ("PATH", "HOME", "TMPDIR") if k in os.environ}
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        signed, key = read_enrollment(enrollment, trusted_key)

        def check_enrollment(stage):
            metadata = parameter_authority(
                signed,
                key,
                case_sha256=hashlib.sha256(case_raw).digest(),
                verifier=verifier,
                stage=stage,
            )
            if signed is not None:
                write_json(output / ("enrollment-" + stage + ".json"), metadata)
            return metadata

        check_enrollment("before-build")
        if signed is not None:
            (output / "enrollment.cbor").write_bytes(signed)
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
        check_enrollment("before-worker")
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
        require(all(sha(ROOT / name) == pin for name, pin in frozen.items()), "source changed")
        authority = check_enrollment("after-verification")
        result = dict(
            schema_id="hallmark.native-llm-result/1",
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
            parameter_authority=authority,
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
    parser.add_argument("--enrollment", type=Path, default=os.environ.get("LLM_ENROLLMENT"))
    parser.add_argument("--trusted-key", default=os.environ.get("LLM_TRUST_KEY"))
    args = parser.parse_args()
    run(args.run, enrollment=args.enrollment, trusted_key=args.trusted_key)
