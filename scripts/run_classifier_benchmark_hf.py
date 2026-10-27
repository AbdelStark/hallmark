"""Run the frozen public classifier comparison in two bounded HF CPU jobs."""

import argparse
import json
import math
import shutil
import subprocess
import tarfile
import time
from pathlib import Path, PurePosixPath

import circle_backend as circle
import classifier_comparison as comparison
import composed_input
import trained_common_input as common
from run_e2e import sha, write_json
from run_llm_e2e import TERMINAL, archive, require, retain, token

ROOT = Path(__file__).resolve().parents[1]


def admission(config, hardware, active):
    item = hardware[config["flavor"]]
    require(
        item.cpu == config["expected_cpu"]
        and item.ram == config["expected_ram"]
        and item.unit_label == "minute"
        and item.unit_cost_micro_usd == config["rate_micro_usd_minute"],
        "hardware or price differs from frozen budget",
    )
    require(not active, "another HF job is active; do not overlap this campaign")
    estimate = config["storage_reserve_micro_usd"] + config.get(
        "prior_attempt_reserve_micro_usd", 0
    )
    for seconds in config["provider_seconds"].values():
        minutes = math.ceil((seconds + config["startup_reserve_seconds_per_job"]) / 60)
        estimate += math.ceil(minutes * item.unit_cost_micro_usd / 10000) * 10000
    require(estimate <= config["max_cost_micro_usd"], "campaign exceeds cost ceiling")
    return estimate


def public_archives(prepared, reference, enrollment_pin, output):
    _, originals, old_policy, _, _ = comparison.admitted(prepared, enrollment_pin)
    names = (
        subprocess.check_output(
            [
                "git",
                "ls-files",
                "-z",
                "src",
                "scripts",
                "research/probes",
                "configs",
                "fixtures",
                "pyproject.toml",
                "uv.lock",
                ".python-version",
                "README.md",
                "LICENSE.md",
                ".gitignore",
                ".gitattributes",
            ],
            cwd=ROOT,
        )
        .decode()
        .split("\0")[:-1]
    )
    sources = {"source/" + name: ROOT / name for name in names}
    require(sum(p.stat().st_size for p in sources.values()) <= 64 * 1024**2, "source size limit")
    inventory = archive(sources, output / "source.tar.gz")
    paths = [
        "mlp-training/seed-17/quantization.json",
        "cnn-training/17/quantization.json",
        "proofs/enrollment.json",
        "proofs/circuit-pins.json",
        *("proofs/" + k + "-request.json" for k in ("allow", "cnn-block", "rule-block")),
        *("proofs/setup-" + k + "/vk.bin" for k in ("rule", "mlp", "encoder")),
    ]
    inputs = {"prepared/" + name: prepared / name for name in paths}
    for kind in ("rule", "mlp", "encoder"):
        inputs["prepared/circle-reference/" + kind + ".json"] = (
            reference / ("enroll-" + kind) / "enrollment.json"
        )
    engines = {
        kind: inputs["prepared/circle-reference/" + kind + ".json"].read_bytes()
        for kind in circle.KINDS
    }
    enrollment = circle.enroll(engines, originals)
    records, policy, _ = circle.resolve(
        enrollment, comparison.sha(enrollment), originals, old_policy
    )
    expected, opening = composed_input.request(policy)
    request = dict(
        opening_cbor_hex=opening.encode().hex(),
        expected_cbor_hex=expected.encode().hex(),
        circle_enrollment_sha256=comparison.sha(enrollment),
        public=[row["public"] for row in common.evaluate(records, policy, opening, expected)],
    )
    write_json(output / "composed-request.json", request)
    inputs["prepared/composed-request.json"] = output / "composed-request.json"
    require(
        sum(p.stat().st_size for p in inputs.values()) <= 4 * 1024**2, "public input size limit"
    )
    input_inventory = archive(inputs, output / "inputs.tar.gz")
    write_json(output / "archive-inventory.json", dict(source=inventory, inputs=input_inventory))
    return inventory, input_inventory


def validate_retention(retained, maximum):
    receipt = json.loads((retained / "output-receipt.json").read_bytes())
    path = retained / "outputs.tar.gz"
    require(
        path.stat().st_size == receipt["bytes"] <= maximum and sha(path) == receipt["sha256"],
        "output archive differs from remote receipt",
    )
    with tarfile.open(path, "r:gz") as source:
        members = source.getmembers()
        require(len(members) <= 20000, "too many retained files")
        require(sum(m.size for m in members) <= 16 * 1024**3, "retained expansion exceeds bound")
        seen = set()
        for member in members:
            name = PurePosixPath(member.name)
            require(
                member.isfile()
                and not name.is_absolute()
                and ".." not in name.parts
                and member.name not in seen,
                "unsafe retained archive member",
            )
            seen.add(member.name)
        result = source.extractfile("runs/campaign/result.json")
        require(result is not None, "campaign result missing")
        value = json.load(result)
    return value


def launch(api, namespace, stage, config, output, commit, enrollment_pin):
    from huggingface_hub import Volume

    folder = output / stage
    folder.mkdir()
    bucket = f"{namespace}/hallmark-classifiers-{stage}-{time.time_ns()}"
    paths = {
        "source.tar.gz": output / "source.tar.gz",
        "inputs.tar.gz": output / "inputs.tar.gz",
        "hf-job.json": ROOT / "configs/circle-classifiers/hf-job.json",
        "hf_bootstrap.py": ROOT / "research/probes/circle/hf_bootstrap.py",
    }
    hashes = {name: sha(path) for name, path in paths.items()}
    protocol = dict(
        schema_id="hallmark.classifier-hf-job/1",
        stage=stage,
        bucket=bucket,
        source_commit=commit,
        inputs=hashes,
        original_enrollment=enrollment_pin,
        provider_seconds=config["provider_seconds"][stage],
        automatic_retries=0,
        public_inputs_only=True,
        config=config,
    )
    write_json(folder / "protocol.json", protocol)
    api.create_bucket(bucket, private=True, exist_ok=False)
    write_json(folder / "bucket.json", dict(bucket=bucket, deleted=False))
    job = None
    attempted = False
    interrupted = None
    try:
        api.batch_bucket_files(bucket, add=[(p, n) for n, p in paths.items()])
        write_json(folder / "creation-attempt.json", dict(bucket=bucket, attempts=1))
        attempted = True
        job = api.run_job(
            image=config["image"],
            command=["python", "-u", "/persist/hf_bootstrap.py"],
            env=dict(
                CLASSIFIER_STAGE=stage,
                SOURCE_SHA256=hashes["source.tar.gz"],
                INPUTS_SHA256=hashes["inputs.tar.gz"],
                SOURCE_COMMIT=commit,
                ORIGINAL_ENROLLMENT=enrollment_pin,
                CONFIG_SHA256=hashes["hf-job.json"],
            ),
            flavor=config["flavor"],
            timeout=config["provider_seconds"][stage],
            attempts=1,
            name=bucket.split("/")[1],
            labels={"project": "hallmark", "scope": "classifier-comparison"},
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
        deadline = time.monotonic() + config["provider_seconds"][stage] + 600
        while True:
            status = api.inspect_job(job_id=job.id, namespace=namespace)
            print(f"{stage}: {status.status.stage} ({job.id})", flush=True)
            if status.status.stage in TERMINAL:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("provider deadline exceeded")
            time.sleep(20)
    except BaseException as error:
        interrupted = error
        if job is not None:
            api.cancel_job(job_id=job.id, namespace=namespace)
            for _ in range(30):
                status = api.inspect_job(job_id=job.id, namespace=namespace)
                if status.status.stage in TERMINAL:
                    break
                time.sleep(2)
            require(status.status.stage in TERMINAL, "job remains live; bucket retained")
    if job is None:
        if attempted:
            raise RuntimeError(
                f"Creation response uncertain: inspect {bucket}; inputs retained"
            ) from interrupted
        api.delete_bucket(bucket)
        raise RuntimeError("job not created; empty bucket deleted") from interrupted
    (folder / "job.log").write_text(
        "\n".join(api.fetch_job_logs(job_id=job.id, namespace=namespace, follow=False)) + "\n"
    )
    require(
        shutil.disk_usage(output).free >= 4 * 1024**3, "retain outputs after freeing local space"
    )
    inventory = retain(api, bucket, paths, folder / "retained")
    running = (
        (status.finished_at - status.started_at).total_seconds()
        if status.started_at and status.finished_at
        else None
    )
    receipt = dict(
        job_id=job.id,
        stage=status.status.stage,
        outputs=inventory,
        all_outputs_retained=True,
        bucket_deleted=False,
        running_seconds=running,
        invoice=False,
    )
    write_json(folder / "retention.json", receipt)
    result = None
    if status.status.stage == "COMPLETED":
        result = validate_retention(folder / "retained", config["max_download_bytes"])
    # Retain terminal failures before cleanup as well; validation never deletes the local copy.
    api.delete_bucket(bucket)
    receipt["bucket_deleted"] = True
    (folder / "retention.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if interrupted is not None:
        raise interrupted
    require(status.status.stage == "COMPLETED", "job failed; inspect retained logs")
    require(result is not None, "missing completed result")
    require(
        result["status"] == ("fixture-passed" if stage == "fixture" else "passed"),
        "job result did not pass",
    )
    write_json(folder / "validated-result.json", result)
    return result


def main():
    from huggingface_hub import HfApi
    from huggingface_hub.utils import disable_progress_bars

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classifier-run", type=Path, required=True)
    parser.add_argument("--circle-reference", type=Path, required=True)
    parser.add_argument("--expected-enrollment", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=("fixture", "benchmark"), required=True)
    parser.add_argument("--fixture-receipt", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "runs"), "output must be under ignored runs")
    config = json.loads((ROOT / "configs/circle-classifiers/hf-job.json").read_bytes())
    require(config["automatic_retries"] == 0, "automatic retry is prohibited")
    if args.stage == "benchmark":
        require(args.fixture_receipt is not None, "pass a completed fixture receipt")
        fixture = json.loads(args.fixture_receipt.read_bytes())
        require(fixture["status"] == "fixture-passed", "fixture has not passed")
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT
    )
    require(not dirty, "commit the frozen candidate/protocol before launch")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    output.mkdir(mode=0o700)
    public_archives(
        args.classifier_run.resolve(),
        args.circle_reference.resolve(),
        args.expected_enrollment,
        output,
    )
    disable_progress_bars()
    api = HfApi(token=token())
    namespace = api.whoami()["name"]
    hardware = {item.name: item for item in api.list_jobs_hardware()}
    active = [j.id for j in api.list_jobs(namespace=namespace) if j.status.stage not in TERMINAL]
    estimate = admission(config, hardware, active)
    write_json(
        output / "admission.json",
        dict(
            estimate_micro_usd=estimate,
            invoice=False,
            source_commit=commit,
            stage=args.stage,
            config=config,
        ),
    )
    result = launch(api, namespace, args.stage, config, output, commit, args.expected_enrollment)
    print(json.dumps(dict(status=result["status"], output=str(output))))


if __name__ == "__main__":
    main()
