"""Reproduce the fixed TinyLlama response with local preparation and bounded HF jobs."""

import argparse
import ast
import gzip
import json
import math
import os
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath

from run_e2e import command, sha, write_json

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "research/probes/sash"
TERMINAL = {"COMPLETED", "ERROR", "CANCELED", "CANCELLED"}
PHASES = {
    "build": ("cpu-upgrade", 1800, 4, 28),
    "prove": ("cpu-performance", 3600, 16, 210),
    "verify": ("cpu-upgrade", 1800, 4, 28),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def token():
    if os.environ.get("HF_TOKEN"):
        return os.environ["HF_TOKEN"]
    path = ROOT / ".env"
    if path.is_file():
        for line in path.read_text().splitlines():
            match = re.fullmatch(r"\s*(?:export\s+)?HF_TOKEN\s*=\s*(.*?)\s*", line)
            if match:
                try:
                    raw = match[1]
                    value = ast.literal_eval(raw) if raw[:1] in ('"', "'") else raw
                    require(isinstance(value, str) and value.startswith("hf_"), "invalid token")
                    return value
                except (ValueError, SyntaxError):
                    raise ValueError("Malformed HF_TOKEN in .env") from None
    raise ValueError("Set HF_TOKEN in the environment or ignored .env file")


def planned_cost(hardware, maximum, phases=None):
    try:
        cap = Decimal(maximum)
    except InvalidOperation:
        raise ValueError("invalid cost ceiling") from None
    require(cap.is_finite() and cap > 0, "invalid cost ceiling")
    micros = 10_000  # Reserve one cent for short-lived bucket storage.
    for flavor, seconds, _, _ in (PHASES if phases is None else phases).values():
        item = hardware[flavor]
        require(
            item.unit_label == "minute"
            and type(item.unit_cost_micro_usd) is int
            and item.unit_cost_micro_usd > 0,
            "unsupported provider pricing",
        )
        micros += ((math.ceil(seconds / 60) * item.unit_cost_micro_usd + 9999) // 10000) * 10000
    require(Decimal(micros) / 1_000_000 <= cap, "provider timeouts exceed the cost ceiling")
    return micros


def fetch(url, destination, expected, size):
    with urllib.request.urlopen(url, timeout=120) as source, destination.open("xb") as target:
        copied = 0
        while chunk := source.read(1024**2):
            copied += len(chunk)
            require(copied <= size, "download exceeds frozen size")
            target.write(chunk)
    require(copied == size and sha(destination) == expected, "download identity mismatch")


def patch_source(source, output, environment, deadline):
    # An enclosing checkout makes git apply silently skip the extracted source.
    environment = environment | {"GIT_CEILING_DIRECTORIES": str(source.parent)}
    for flags, log in [(["--check"], "patch-check.log"), ([], "patch.log")]:
        command(
            ["git", "apply", *flags, PROBE / "exact-gemm.patch"],
            output / log,
            environment,
            deadline,
            cwd=source,
        )


def archive(files, destination):
    inventory = {}
    with (
        destination.open("xb") as output,
        gzip.GzipFile(fileobj=output, mode="wb", mtime=0) as zipped,
        tarfile.open(fileobj=zipped, mode="w|") as tar,
    ):
        for name, path in sorted(files.items()):
            relative = PurePosixPath(name)
            require(
                not relative.is_absolute() and ".." not in relative.parts, "unsafe archive path"
            )
            require(path.is_file() and not path.is_symlink(), "nonregular archive input")
            inventory[name] = dict(bytes=path.stat().st_size, sha256=sha(path))
            info = tar.gettarinfo(str(path), arcname=name)
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ""
            with path.open("rb") as stream:
                tar.addfile(info, stream)
    require(sum(x["bytes"] for x in inventory.values()) <= 3 * 1024**3, "archive exceeds run bound")
    return inventory


def witness_archive(native, case, output):
    portable = output / "portable"
    portable.mkdir()
    files = {
        "plan.txt": PROBE / "response-plan.txt",
        "prompt_ids.json": native / "prompt_ids.json",
        "answer_ids.json": native / "answer_ids.json",
        "input_ids.json": native / "input_ids.json",
        "attn-ranges.json": native / "attn-ranges.json",
    }
    for name in [f"witness_B0_L{i}" for i in range(22)] + ["head_B0"]:
        folder = native / name
        manifest = json.loads((folder / "manifest.json").read_text())
        require(
            manifest["spec"] == case["spec"]
            and manifest["attn_ranges"]["sha256"] == case["calibration_sha256"],
            "changed witness profile",
        )
        manifest["model"] = case["model"]["id"] + "@" + case["model"]["revision"]
        manifest["ids_from"]["path"] = "input_ids.json"
        manifest["attn_ranges"]["path"] = "attn-ranges.json"
        text = json.dumps(manifest, indent=2) + "\n"
        require("/Users/" not in text and str(native) not in text, "local path in upload manifest")
        path = portable / name / "manifest.json"
        path.parent.mkdir()
        path.write_text(text)
        files[name + "/manifest.json"] = path
        for filename, record in manifest["files"].items():
            require(
                Path(filename).name == filename and filename not in (".", ".."),
                "unsafe witness filename",
            )
            if record.get("written") is False:
                continue
            path = folder / filename
            require(sha(path).startswith(record["sha256"]), "changed witness array")
            files[name + "/" + filename] = path
    target = output / "inputs.tar.gz"
    inventory = archive(files, target)
    write_json(output / "inventory.json", inventory)
    return target


def retain(api, bucket, inputs, destination):
    files = [
        item
        for item in api.list_bucket_tree(bucket, recursive=True)
        if hasattr(item, "size") and item.path not in {*inputs, "protocol.json"}
    ]
    require(
        sum(item.size for item in files) <= 4 * 1024**3, "remote outputs exceed retention bound"
    )
    destination.mkdir()
    transfers = []
    for item in files:
        relative = PurePosixPath(item.path)
        require(
            not relative.is_absolute() and ".." not in relative.parts, "unsafe remote output path"
        )
        transfers.append((item, str(destination / relative)))
    api.download_bucket_files(bucket, transfers, raise_on_missing_files=True)
    inventory = {}
    for item in files:
        path = destination / item.path
        require(path.stat().st_size == item.size, "incomplete output download")
        inventory[item.path] = dict(bytes=item.size, sha256=sha(path))
    return inventory


def cloud_job(api, namespace, phase, inputs, case, hardware, output, env=None, *, phases=None):
    from huggingface_hub import Volume

    frozen = json.loads((output / "protocol.json").read_text())["source_files"]
    require(all(sha(ROOT / name) == pin for name, pin in frozen.items()), "workflow source changed")
    folder = output / phase
    folder.mkdir()
    flavor, seconds, threads, gib = (PHASES if phases is None else phases)[phase]
    rate = hardware[flavor].unit_cost_micro_usd
    bucket = f"{namespace}/hallmark-llm-{phase}-{time.time_ns()}"
    hashes = {name: sha(path) for name, path in inputs.items()}
    require(all(Path(name).name == name for name in inputs), "invalid cloud input name")
    protocol = dict(
        schema_id="hallmark.llm-e2e-job/1",
        phase=phase,
        source_commit=case["source"]["revision"],
        inputs=hashes,
        expected_sha256=hashes.get("expected.json"),
        max_address_space_bytes=gib * 1024**3,
        max_single_file_bytes=2 * 1024**3,
        threads=threads,
        provider_seconds=seconds,
        rate_micro_usd_minute=rate,
        automatic_retries=0,
        public_inputs_only=True,
        bucket=bucket,
    )
    write_json(folder / "protocol.json", protocol)
    api.create_bucket(bucket, private=True, exist_ok=False)
    write_json(folder / "bucket.json", dict(bucket=bucket))
    job = None
    creation_attempted = False
    status = None
    interrupted = None
    try:
        print(f"{phase}: uploading frozen public inputs", flush=True)
        api.batch_bucket_files(
            bucket,
            add=[(path, name) for name, path in inputs.items()]
            + [(folder / "protocol.json", "protocol.json")],
        )
        if phase == "build":
            argv = ["bash", "/persist/build_prover.sh"]
        else:
            script = "prove_response.py" if phase == "prove" else "verify_response.py"
            argv = [
                "bash",
                "-lc",
                "apt-get update -qq && apt-get install -y -qq python3 >/tmp/apt.log "
                f"&& python3 -B -u /persist/{script}",
            ]
        creation_attempted = True
        job = api.run_job(
            image=case["image"],
            command=argv,
            env=env,
            flavor=flavor,
            timeout=seconds,
            attempts=1,
            name=bucket.split("/")[1],
            labels={"project": "hallmark", "scope": "public-llm-reproduction"},
            namespace=namespace,
            volumes=[Volume(type="bucket", source=bucket, mount_path="/persist", read_only=False)],
        )
        write_json(
            folder / "job.json",
            dict(
                id=job.id,
                namespace=namespace,
                url=f"https://huggingface.co/jobs/{namespace}/{job.id}",
            ),
        )
        deadline = time.monotonic() + seconds + 600
        failures = 0
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{phase} creation deadline exceeded")
            try:
                status = api.inspect_job(job_id=job.id, namespace=namespace)
            except Exception:
                failures += 1
                if failures >= 3:
                    raise
                print(f"{phase}: status unavailable; retrying the same job", flush=True)
                time.sleep(2)
                continue
            failures = 0
            print(f"{phase}: {status.status.stage} ({job.id})", flush=True)
            if status.status.stage in TERMINAL:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{phase} creation deadline exceeded")
            time.sleep(20)
    except BaseException as exc:
        interrupted = exc
        if job is not None:
            api.cancel_job(job_id=job.id, namespace=namespace)
            for _ in range(30):
                status = api.inspect_job(job_id=job.id, namespace=namespace)
                if status.status.stage in TERMINAL:
                    break
                time.sleep(2)
            require(status.status.stage in TERMINAL, f"job {job.id} remains live; bucket retained")
    if job is None:
        if creation_attempted:
            raise RuntimeError(
                f"Job creation uncertain; inspect jobs for {bucket}; bucket retained"
            ) from interrupted
        api.delete_bucket(bucket)
        if interrupted is not None:
            raise interrupted
        raise RuntimeError("provider did not create a job")
    (folder / "job.log").write_text(
        "\n".join(api.fetch_job_logs(job_id=job.id, namespace=namespace, follow=False))
    )
    inventory = retain(api, bucket, inputs, folder / "retained")
    running = (
        (status.finished_at - status.started_at).total_seconds()
        if status.started_at and status.finished_at
        else 0
    )
    receipt = dict(
        job_id=job.id,
        stage=status.status.stage,
        running_seconds=running,
        compute_bound_micro_usd=((math.ceil(running / 60) * rate + 9999) // 10000) * 10000,
        invoice=False,
        outputs=inventory,
        all_outputs_retained=True,
        bucket_deleted=False,
    )
    write_json(folder / "retention.json", receipt)
    api.delete_bucket(bucket)
    receipt["bucket_deleted"] = True
    (folder / "retention.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if interrupted is not None:
        raise interrupted
    require(status.status.stage == "COMPLETED", f"{phase} failed; inspect {folder}")
    return folder / "retained"


def run(maximum):
    from huggingface_hub import HfApi, hf_hub_download
    from huggingface_hub.utils import disable_progress_bars

    disable_progress_bars()
    require(
        (platform.system(), platform.machine()) == ("Darwin", "arm64"),
        "The recorded preparation path requires an Apple Silicon Mac",
    )
    require(
        subprocess.check_output(["uv", "--version"], text=True).split()[:2] == ["uv", "0.9.18"],
        "Use uv 0.9.18",
    )
    require(
        shutil.disk_usage(ROOT).free >= 16 * 1024**3, "At least 16 GiB free storage is required"
    )
    case = json.loads((PROBE / "response-case.json").read_text())
    require(
        sha(PROBE / "exact-gemm.patch") == case["witness_patch_sha256"], "witness patch changed"
    )
    api = HfApi(token=token())
    namespace = api.whoami()["name"]
    require(re.fullmatch(r"[A-Za-z0-9-]+", namespace) is not None, "invalid HF namespace")
    hardware = {item.name: item for item in api.list_jobs_hardware()}
    ceiling = planned_cost(hardware, maximum)
    require(hardware["cpu-upgrade"].ram == "32 GB", "review changed CPU Upgrade hardware")
    require(hardware["cpu-performance"].ram == "256 GB", "review changed CPU Performance hardware")
    require(
        not [j for j in api.list_jobs(namespace=namespace) if j.status.stage not in TERMINAL],
        "Finish existing HF jobs before starting this foreground workflow",
    )
    (ROOT / "runs").mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="llm-e2e-", dir=ROOT / "runs"))
    print(
        f"Outputs: {output}\nThree CPU jobs; "
        f"provider timeouts plus storage reserve: ${ceiling / 1e6:.5f}",
        flush=True,
    )
    write_json(
        output / "protocol.json",
        dict(
            schema_id="hallmark.llm-e2e/1",
            case_sha256=sha(PROBE / "response-case.json"),
            limits={
                name: dict(flavor=p[0], seconds=p[1], threads=p[2], memory_gib=p[3])
                for name, p in PHASES.items()
            },
            cost_ceiling_micro_usd=ceiling,
            owner_ceiling_usd=maximum,
            automatic_retries=0,
            local_seconds=1800,
            source_files={
                str(p.relative_to(ROOT)): sha(p)
                for p in [
                    Path(__file__),
                    ROOT / "scripts/run_e2e.py",
                    ROOT / "pyproject.toml",
                    ROOT / "uv.lock",
                    ROOT / "Makefile",
                    *sorted(PROBE.glob("*")),
                ]
                if p.is_file()
            },
        ),
    )
    environment = {
        key: os.environ[key] for key in ("PATH", "HOME", "TMPDIR", "LANG") if key in os.environ
    }
    started = time.monotonic()
    try:
        source = case["source"]
        compressed = output / "source.tar.gz"
        fetch(source["url"], compressed, source["sha256"], source["bytes"])
        unpacked = output / "source"
        unpacked.mkdir()
        with tarfile.open(compressed, "r:gz") as tar:
            tar.extractall(unpacked, filter="data")
        roots = list(unpacked.iterdir())
        require(len(roots) == 1 and roots[0].is_dir(), "unexpected source archive layout")
        source_dir = roots[0]
        deadline = time.monotonic() + 1800
        patch_source(source_dir, output, environment, deadline)
        python_env = output / "witness-env"
        command(
            ["uv", "sync", "--project", source_dir / "harness", "--locked", "--python", "3.12.12"],
            output / "python.log",
            environment | {"UV_PROJECT_ENVIRONMENT": str(python_env)},
            deadline,
        )
        model = output / "model"
        print("Downloading and checking the pinned public checkpoint", flush=True)
        for name, pin in case["model"]["files"].items():
            path = Path(
                hf_hub_download(
                    case["model"]["id"],
                    name,
                    revision=case["model"]["revision"],
                    local_dir=model,
                    token=False,
                )
            )
            require(
                path.stat().st_size == pin["bytes"] and sha(path) == pin["sha256"],
                "model download mismatch: " + name,
            )
        native = output / "native"
        local_env = environment | {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "OMP_NUM_THREADS": "4",
            "ZK_THREADS": "4",
            "ZK_DEVICE": "cpu",
            "ZK_MODEL": str(model),
            "PYTHONPATH": str(source_dir),
        }
        command(
            [python_env / "bin/python", PROBE / "check_exact_gemm.py"],
            output / "exact-gemm.log",
            local_env,
            deadline,
        )
        command(
            [
                python_env / "bin/python",
                PROBE / "prepare_native.py",
                model,
                native,
                PROBE / "response-case.json",
            ],
            output / "prepare.log",
            local_env,
            deadline,
        )
        generated = json.loads((native / "generation.json").read_text())
        require(
            generated["passed"] is True and generated["answer_ids"] == case["answer_ids"],
            "native generation failed",
        )
        witness_archive(native, case, output)
        build = cloud_job(
            api,
            namespace,
            "build",
            {"build_prover.sh": PROBE / "build_prover.sh"},
            case,
            hardware,
            output,
            env={
                "SOURCE_URL": source["url"],
                "SOURCE_SHA256": source["sha256"],
                "SOURCE_COMMIT": source["revision"],
            },
        )
        binary = build / "zk-prover-simd"
        require(
            binary.is_file() and 0 < binary.stat().st_size < 128 * 1024**2, "missing prover binary"
        )
        require(
            (build / "binary.sha256").read_text().split()[0] == sha(binary),
            "binary digest mismatch",
        )
        expected = dict(
            schema_id="hallmark.sash-response-expectations/1",
            roots=case["expected_roots"],
            prompt_ids=case["prompt_ids"],
            answer_ids=case["answer_ids"],
            binary_sha256=sha(binary),
        )
        write_json(output / "expected.json", expected)
        write_json(output / "expected-roots.json", expected["roots"])
        common = {
            "expected.json": output / "expected.json",
            "zk-prover": binary,
            "check_response.py": PROBE / "check_response.py",
        }
        proved = cloud_job(
            api,
            namespace,
            "prove",
            common
            | {
                "inputs.tar.gz": output / "inputs.tar.gz",
                "inventory.json": output / "inventory.json",
                "response-case.json": PROBE / "response-case.json",
                "expected-roots.json": output / "expected-roots.json",
                "prove_response.py": PROBE / "prove_response.py",
            },
            case,
            hardware,
            output,
        )
        proof = proved / "output/proof"
        require(
            json.loads((proved / "output/result.json").read_text())["proofs_produced"] == 23,
            "incomplete proving stage",
        )
        # This archive is the verifier's entire data input; no weights or witness directories.
        inventory = archive(
            {f"proof/{p.name}": p for p in proof.iterdir()}, output / "proofs.tar.gz"
        )
        require(len(inventory) == 69, "incomplete proof bundle")
        write_json(output / "proof-inventory.json", inventory)
        verified = cloud_job(
            api,
            namespace,
            "verify",
            common
            | {
                "proofs.tar.gz": output / "proofs.tar.gz",
                "proof-inventory.json": output / "proof-inventory.json",
                "verify_response.py": PROBE / "verify_response.py",
            },
            case,
            hardware,
            output,
        )
        report = json.loads((verified / "output/result.json").read_text())
        cases = report["cases"]
        require(
            report["passed"] is True
            and len(cases) == 16
            and sum(row["accepted"] for row in cases) == 2,
            "incomplete verification suite",
        )
        require(
            report["weights_present"] is False and report["witness_present"] is False,
            "unexpected verifier inputs",
        )
        receipts = [json.loads((output / name / "retention.json").read_text()) for name in PHASES]
        require(
            all(row["bucket_deleted"] for row in receipts), "temporary bucket cleanup incomplete"
        )
        result = dict(
            schema_id="hallmark.llm-e2e-result/1",
            passed=True,
            model=case["model"]["id"],
            revision=case["model"]["revision"],
            quantized_profile=case["spec"],
            prompt=case["prompt"],
            response=case["response"],
            answer_ids=case["answer_ids"],
            proofs=23,
            residual_links=22,
            fresh_verifications=2,
            mutations_rejected=14,
            seconds=time.monotonic() - started,
            compute_bound_micro_usd=sum(row["compute_bound_micro_usd"] for row in receipts),
            invoice=False,
            qualified_backend=False,
            hardware_claim="not-accepted",
            hiding_claim=False,
            all_buckets_deleted=True,
        )
        write_json(output / "result.json", result)
        print(json.dumps(result, indent=2), flush=True)
        return output
    except BaseException as exc:
        write_json(
            output / "failure.json",
            dict(type=type(exc).__name__, seconds=time.monotonic() - started, completed=False),
        )
        print(f"Workflow failed. Evidence retained at {output}", flush=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-cost-usd",
        required=True,
        help="ceiling for the three bounded HF CPU jobs and storage reserve",
    )
    run(parser.parse_args().max_cost_usd)
