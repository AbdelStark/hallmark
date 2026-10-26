"""Matched SIMD/CUDA measurements; the portable worker needs one NVIDIA GPU."""

import argparse
import csv
import hashlib
import json
import os
import resource
import shlex
import shutil
import signal
import subprocess
import tarfile
import time
from pathlib import Path

from check_response import TAGS, bundle, read_json, require
from relation import closed

# Witness generation stays on the host; generated AIR constraints execute on CUDA.
HOST_MODES = (
    "DEVICE_WITNESS_GEN_DEQUANT",
    "DEVICE_WITNESS_GEN_ATTENTION_FREIVALDS",
    "DEVICE_WITNESS_GEN_KEY_TILE",
    "DEVICE_WITNESS_GEN_DIAGONAL_BLOCK",
    "DEVICE_WITNESS_GEN_RESIDUAL_STREAM",
    "DEVICE_RESIDUAL_STREAM_BINDING",
    "DEVICE_TABLES",
    "DEVICE_STAGING_POOL",
    "DEVICE_PREPROCESSED",
    "DEVICE_ACCUMULATORS",
    "GENERATED_LOGUP",
    "PIPELINE",
    "PREPROCESSED_TREE_CACHE",
    "LOWERING_CACHE",
    "LDE_ONLY",
)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_provenance(report, case, backend):
    p = report["provenance"]
    require(p["backend"] == backend, "wrong execution backend")
    expected_dirty = backend == "cuda"
    require(
        p["commit"] == case["source"]["revision"] and p["dirty"] is expected_dirty, "source changed"
    )
    require(p["unsound_skips"] == [], "unsound execution mode")
    require(all(report["modes"][k]["value"] == 0 for k in HOST_MODES), "changed path modes")
    if backend == "cuda":
        require(isinstance(p["gpu"], str) and p["gpu"], "no GPU reported")


def kernel_checked(report, backend):
    if backend == "cuda":
        detail = report["result"]["point"]["phases"]["detail"]
        for key in ("constraint_eval_cpu_fallback", "constraint_eval_cpu_autofallback"):
            require(
                detail[key]["calls"] == 0 and detail[key]["secs"] == 0, "CPU constraint fallback"
            )
        require(
            detail["constraint_eval_gpu"]["calls"] > 0
            and detail["constraint_eval_gpu"]["secs"] > 0,
            "no generated constraint execution",
        )


def checked(report, case, backend):
    check_provenance(report, case, backend)
    kernel_checked(report, backend)
    closed(report["result"]["point"])
    require(report["result"]["point"]["ref_mismatch"] == 0, "reference arithmetic differs")


def smoke_checked(report, case, backend):
    check_provenance(report, case, backend)
    kernel_checked(report, backend)
    point = report["result"]["point"]
    require(
        point["accepts"] is True
        and point["binding"]["all_bound"] is True
        and point["binding"]["unbound"] == [],
        "synthetic proof rejected",
    )
    require(
        point["verdict"]["stark_ok"] is True
        and point["verdict"]["error"] is None
        and point["verdict"]["shape_root_ok"] is None
        and point["ref_mismatch"] == 0,
        "wrong synthetic fixture",
    )
    require(point["proof_sha256"].startswith("db6d17a700c25457"), "smoke digest changed")


def unpack(root, work):
    inventory = read_json(root / "inventory.json")
    require(
        len(inventory) <= 3000 and sum(x["bytes"] for x in inventory.values()) <= 3 * 1024**3,
        "oversized input inventory",
    )
    seen = set()
    with tarfile.open(root / "inputs.tar.gz", "r|gz") as tar:
        for member in tar:
            name = Path(member.name)
            require(
                member.isfile()
                and member.name in inventory
                and member.name not in seen
                and not name.is_absolute()
                and ".." not in name.parts,
                "invalid input archive member",
            )
            pin = inventory[member.name]
            require(member.size == pin["bytes"], "wrong archive member size")
            target = work / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            require(sha(target) == pin["sha256"], "changed witness input")
            seen.add(member.name)
    require(seen == inventory.keys(), "incomplete witness archive")


def gpu_samples(path, offset):
    with path.open("rb") as stream:
        previous = b"\n"
        if offset:
            stream.seek(offset - 1)
            previous = stream.read(1)
        stream.seek(offset)
        data = stream.read()
    # nvidia-smi appends concurrently; only complete records belong to this window.
    if previous != b"\n":
        data = data.partition(b"\n")[2]
    rows = list(csv.reader(data.rpartition(b"\n")[0].decode().splitlines()))
    require(all(len(row) == 3 for row in rows), "malformed GPU telemetry")
    return [dict(timestamp=r[0], memory_mib=int(r[1]), utilization=int(r[2])) for r in rows]


def process_rss(pid):
    try:
        lines = Path(f"/proc/{pid}/status").read_text().splitlines()
    except (FileNotFoundError, ProcessLookupError):
        return 0
    return max(
        (int(line.split()[1]) * 1024 for line in lines if line.startswith("VmHWM:")), default=0
    )


def main(root, work):
    out = root / "output"
    out.mkdir(exist_ok=False)
    started = time.monotonic()
    job = read_json(root / "protocol.json")
    config = read_json(root / "benchmark.json")
    case = read_json(root / "response-case.json")
    expected = read_json(root / "expected.json")
    commands = []
    results = []
    monitor = None
    monitor_stream = None
    resource.setrlimit(resource.RLIMIT_FSIZE, (job["max_single_file_bytes"],) * 2)
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("ZK_") and k not in {"CUDA_CPU_FALLBACK", "CUDA_ONLY", "CUDA_EXCEPT"}
    }
    env.update({"ZK_" + name: "0" for name in HOST_MODES})
    env["RAYON_NUM_THREADS"] = str(job["threads"])
    telemetry = out / "gpu.csv"

    def run(name, args):
        require(time.monotonic() - started < config["worker_seconds"], "benchmark deadline")
        offset = telemetry.stat().st_size if telemetry.exists() else 0
        before = time.monotonic()
        peak = 0
        failure = None
        print("Starting " + name, flush=True)
        with (
            (out / (name + ".stdout")).open("xb") as so,
            (out / (name + ".stderr")).open("xb") as se,
        ):
            proc = subprocess.Popen(
                args, cwd=work, env=env, stdout=so, stderr=se, start_new_session=True
            )
            try:
                while proc.poll() is None:
                    require(time.monotonic() - before < 600, "command deadline")
                    require(
                        time.monotonic() - started < config["worker_seconds"], "benchmark deadline"
                    )
                    peak = max(peak, process_rss(proc.pid))
                    require(peak <= config["max_rss_bytes"], "RSS limit exceeded")
                    time.sleep(0.25)
            except BaseException as exc:
                failure = exc
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
        row = dict(
            name=name,
            args=args,
            seconds=time.monotonic() - before,
            exit_code=proc.returncode,
            sampled_peak_rss_bytes=peak,
            failure=type(failure).__name__ if failure is not None else None,
        )
        samples = gpu_samples(telemetry, offset)
        row["gpu_peak_memory_mib"] = max((r["memory_mib"] for r in samples), default=0)
        row["gpu_peak_utilization"] = max((r["utilization"] for r in samples), default=0)
        commands.append(row)
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if failure is not None:
            raise failure
        require(proc.returncode == 0, name + " failed")
        print(json.dumps(row), flush=True)
        return row

    try:
        require(
            type(config["repetitions"]) is int and 1 <= config["repetitions"] <= 3,
            "invalid repetitions",
        )
        require(
            type(config["max_rss_bytes"]) is int and 0 < config["max_rss_bytes"] <= 200 * 1024**3,
            "invalid RSS limit",
        )
        require(
            type(config["worker_seconds"]) is int and 0 < config["worker_seconds"] <= 2550,
            "invalid worker deadline",
        )
        for name, pin in job["inputs"].items():
            require(sha(root / name) == pin, "changed job input")
        kernels = read_json(root / "kernel-build.json")
        require(
            kernels["generated_constraint_kernels"] is True
            and kernels["source_dirty"] is True
            and kernels["source_commit"] == case["source"]["revision"]
            and kernels["kernel_count"] > 0,
            "missing generated constraint build",
        )
        require(
            all(
                kernels["binaries"][name] == sha(root / name)
                for name in ("zk-prover-simd", "zk-prover-cuda")
            ),
            "kernel build binary mismatch",
        )
        work.mkdir(exist_ok=False)
        unpack(root, work)
        for name in ("zk-prover-simd", "zk-prover-cuda"):
            shutil.copy2(root / name, work / name)
            (work / name).chmod(0o700)
        device = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=15,
        ).strip()
        require(len(device.splitlines()) == 1 and "H200" in device, "expected one H200")
        (out / "device.txt").write_text(device + "\n")
        monitor_stream = telemetry.open("wb")
        monitor = subprocess.Popen(
            [
                "nvidia-smi",
                "--query-gpu=timestamp,memory.used,utilization.gpu",
                "--format=csv,noheader,nounits",
                "--loop-ms=500",
            ],
            stdout=monitor_stream,
            stderr=subprocess.DEVNULL,
        )
        # Smallest real CUDA fixture before loading the full model witness.
        smoke = [
            "--round",
            "away",
            "--variants",
            "intsplit6",
            "--table-bits",
            "16",
            "--s",
            "32",
            "--ctx",
            "128",
            "--hd",
            "32",
            "--head-groups",
            "2,2",
            "--nin",
            "128",
            "--nout",
            "128",
            "--residual-stream-a",
            "32",
            "--kmax",
            "16",
            "--synth-residual-stream",
            "--diagonal-block",
        ]
        smoke_digests = []
        for backend in ("simd", "cuda"):
            run("smoke-" + backend, [str(work / ("zk-prover-" + backend)), "compose", *smoke])
            report = read_json(out / ("smoke-" + backend + ".stdout"))
            smoke_checked(report, case, backend)
            smoke_digests.append(report["result"]["point"]["proof_sha256"])
        require(smoke_digests[0] == smoke_digests[1], "CPU/CUDA synthetic proof differs")
        plan = [
            shlex.split(line)
            for line in (work / "plan.txt").read_text().splitlines()
            if line.strip()
        ]
        require([a[a.index("--ser-tag") + 1] for a in plan] == TAGS, "wrong segment roster")
        cpu = str(work / "zk-prover-simd")
        run(
            "roots",
            [
                cpu,
                "model-roots",
                "--plan",
                "plan.txt",
                "--pins",
                shlex.join(case["shared_flags"]),
                "--out",
                str(out / "roots.json"),
            ],
        )
        require(read_json(out / "roots.json") == expected["roots"], "caller-enrolled roots differ")
        for iteration in range(config["repetitions"]):
            paired = {}
            for backend in ("simd", "cuda") if iteration % 2 == 0 else ("cuda", "simd"):
                name = f"{backend}-{iteration}"
                proof = out / (name + "-proof")
                proving = 0.0
                rows = []
                for tag, args in zip(TAGS, plan, strict=True):
                    row = run(
                        name + "-" + tag,
                        [
                            str(work / ("zk-prover-" + backend)),
                            "compose",
                            *case["shared_flags"],
                            *args,
                            "--verify-calibration",
                            str(root / "expected-roots.json"),
                            "--ser-dir",
                            str(proof),
                        ],
                    )
                    report = read_json(out / (name + "-" + tag + ".stdout"))
                    checked(report, case, backend)
                    proving += report["result"]["point"]["prove_secs"]
                    rows.append(row)
                bundle(proof, expected)
                inventory = {
                    "proof/" + p.name: dict(bytes=p.stat().st_size, sha256=sha(p))
                    for p in sorted(proof.iterdir())
                }
                require(len(inventory) == 69, "incomplete proof bundle")
                paired[backend] = inventory
                verify = run(
                    name + "-verify",
                    [
                        cpu,
                        "boundary-grid",
                        "--dir",
                        str(proof),
                        "--tags",
                        ",".join(TAGS),
                        "--verify",
                        "--prompt",
                        str(work / "prompt_ids.json"),
                        "--verify-calibration",
                        str(root / "expected-roots.json"),
                        "--expect-model-roots",
                        str(root / "expected-roots.json"),
                        "--expect-pre-roots",
                        str(root / "expected-roots.json"),
                        "--expect-layer-links",
                        "22",
                        "--expect-token-links",
                        "0",
                    ],
                )
                verified = read_json(out / (name + "-verify.stdout"))["result"]
                require(
                    verified["all_chain"] is True and verified["verified"]["accepted"] == 23,
                    "full grid rejected",
                )
                (out / (name + "-inventory.json")).write_text(
                    json.dumps(inventory, indent=2) + "\n"
                )
                with tarfile.open(out / (name + "-proofs.tar.gz"), "w:gz", compresslevel=1) as tar:
                    for p in sorted(proof.iterdir()):
                        tar.add(p, arcname="proof/" + p.name)
                results.append(
                    dict(
                        backend=backend,
                        iteration=iteration,
                        prove_seconds=proving,
                        commands_seconds=sum(r["seconds"] for r in rows),
                        verify_seconds=verify["seconds"],
                        serialized_proof_bytes=sum(
                            v["bytes"] for k, v in inventory.items() if k.endswith(".proof.json")
                        ),
                        sampled_peak_rss_bytes=max(r["sampled_peak_rss_bytes"] for r in rows),
                        gpu_peak_memory_mib=max(r["gpu_peak_memory_mib"] for r in rows),
                        gpu_peak_utilization=max(r["gpu_peak_utilization"] for r in rows),
                    )
                )
                if backend == "cuda":
                    require(results[-1]["gpu_peak_utilization"] > 0, "no sampled GPU activity")
                shutil.rmtree(proof)  # The complete archive and inventory are retained first.
            require(paired["simd"] == paired["cuda"], "CPU/CUDA proof or statement bytes differ")
        require(monitor.poll() is None, "GPU telemetry stopped")
        (out / "result.json").write_text(
            json.dumps(
                dict(
                    passed=True,
                    profile="cuda-native-sm90-generated-constraints",
                    generated_kernels=True,
                    generated_witness_kernels=False,
                    kernel_build_sha256=sha(root / "kernel-build.json"),
                    cpu_constraint_fallback_allowed=False,
                    repetitions=config["repetitions"],
                    results=results,
                    same_host=True,
                    proof_bytes_equal=True,
                    seconds=time.monotonic() - started,
                    cache_policy="fresh processes; shared OS cache; order alternates by repetition",
                    memory_control="sampled Linux VmHWM, not RLIMIT_AS; GPU sampled at 500 ms",
                    full_response_proof_only_worker_verified=False,
                ),
                indent=2,
            )
            + "\n"
        )
    except BaseException as exc:
        (out / "failure.json").write_text(
            json.dumps(dict(type=type(exc).__name__, message=str(exc), results=results), indent=2)
            + "\n"
        )
        raise
    finally:
        if monitor is not None:
            monitor.terminate()
            monitor.wait(timeout=15)
        if monitor_stream is not None:
            monitor_stream.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/persist"))
    parser.add_argument("--work", type=Path, default=Path("/work"))
    args = parser.parse_args()
    main(args.root, args.work)
