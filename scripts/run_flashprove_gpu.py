"""Build FlashProve, commit to and prove its small synthetic kit on an HF H200; recheck here.

Two paid jobs, one attempt each: upstream `verifier/build.sh` and `prover/build.sh` on a CPU host,
then upstream `run_target_example.sh` on the sm_90 GPU. Only public files return: the secret key
directory stays on the worker. The local verifier, built first from the same pinned source, must
accept the fresh proof against caller-held kit files and reject altered copies.
"""

import argparse
import json
import re
import shutil
import struct
import subprocess
import tempfile
import time
from pathlib import Path

import flashprove as fp
import run_llm_e2e as cloud
from run_e2e import sha, write_json
from run_llm_gpu import credit_guard

ROOT = fp.ROOT
PHASES = {"build": ("cpu-xl", 3600, 16, 100), "prove": ("h200", 900, 23, 200)}
JOB = fp.PROBE / "job.sh"


def caller_case(tree, case, worker_log):
    """Everything the client brings is taken from the pinned kit, not from the worker."""
    kit = tree / "prover/examples" / fp.PIN["gpu_kit"]["name"]
    for name in ("policy.txt", "KL.bin", "layout.txt"):
        cloud.require(
            (case / "config" / name).read_bytes() == (kit / name).read_bytes(),
            f"worker configuration {name} differs from the pinned kit",
        )
    cloud.require(
        (case / "example.req").read_bytes() == (kit / "own_choices.req").read_bytes(),
        "worker request differs from the pinned kit request",
    )
    ids = [
        line.split(":", 1)[1].replace(" ", "")
        for line in worker_log.read_text().splitlines()
        if line.startswith("commitment ID:")
    ]
    cloud.require(
        len(set(ids)) == 1 and re.fullmatch("[0-9a-f]{64}", ids[0]),
        "cp_commit printed no single commitment ID",
    )
    raw = (case / "example.y").read_bytes()
    cloud.require(len(raw) == 4, "token file is not one token")
    return ids[0], struct.unpack("<I", raw)[0]


def flip(path, offset):
    data = bytearray(path.read_bytes())
    data[offset] ^= 1
    path.write_bytes(bytes(data))


def mutations(verifier, case, commitment_id, output):
    """Each altered copy must end `NO: ...` with exit 1; returns the rows."""
    other = ("0" if commitment_id[0] != "0" else "1") + commitment_id[1:]
    altered = {
        "proof-middle-bit": ("example.proof", lambda p: flip(p, p.stat().st_size // 2), None),
        "proof-last-bit": ("example.proof", lambda p: flip(p, p.stat().st_size - 1), None),
        "next-token": ("example.y", lambda p: flip(p, 0), None),
        "request-first-token": ("example.req", lambda p: flip(p, 0), None),
        "key-bit": ("ivk/key.bin", lambda p: flip(p, p.stat().st_size // 2), None),
        "commitment-id": (None, None, other),
    }
    rows = []
    for name, (file, change, cid) in altered.items():
        copy = output / "altered" / name
        shutil.copytree(case, copy)
        if file:
            change(copy / file)
        code, last = fp.direct(verifier, copy, cid or commitment_id, output / f"altered-{name}.log")
        rows.append(dict(mutation=name, exit_code=code, last_line=last))
        cloud.require(code == 1 and last.startswith("NO:"), f"altered copy {name} not rejected")
    return rows


def run(balance, maximum):
    from huggingface_hub import HfApi

    cloud.require(shutil.disk_usage(ROOT).free >= 8 * 1024**3, "8 GiB free storage required")
    (ROOT / "runs").mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="flashprove-gpu-", dir=ROOT / "runs"))
    print("Outputs: " + str(output), flush=True)
    started = time.monotonic()
    try:
        # Free local checks first: the verifier that will judge the paid proof must already work.
        local = output / "local"
        local.mkdir()
        tree, verifier, stored = fp.verify_stored(local)
        api = HfApi(token=cloud.token())
        namespace = api.whoami()["name"]
        hardware = {h.name: h for h in api.list_jobs_hardware()}
        cloud.require(
            (hardware["h200"].cpu, hardware["h200"].ram) == ("23 vCPU", "256 GB")
            and (hardware["cpu-xl"].cpu, hardware["cpu-xl"].ram) == ("16 vCPU", "124 GB"),
            "hardware allocation changed",
        )
        ceiling = cloud.planned_cost(hardware, maximum, PHASES)
        credit_guard(balance, ceiling)
        live = [
            j for j in api.list_jobs(namespace=namespace) if j.status.stage not in cloud.TERMINAL
        ]
        cloud.require(not live, "another HF job is active")
        sources = [Path(__file__), ROOT / "scripts/flashprove.py", *fp.PROBE.iterdir()]
        write_json(
            output / "protocol.json",
            dict(
                schema_id="hallmark.flashprove-gpu/1",
                source_files={
                    str(p.relative_to(ROOT)): sha(p)
                    for p in sources
                    if p.is_file() and "__pycache__" not in p.parts
                },
                phases=PHASES,
                cost_ceiling_micro_usd=ceiling,
                balance_check_usd=balance,
                source=fp.PIN,
                automatic_retries=0,
                synthetic_weights_only=True,
                qualified_backend=False,
            ),
        )
        case = dict(
            image=fp.PIN["image"],
            source=dict(
                revision=subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip()
            ),
        )
        shared = {"build_prover.sh": JOB, "source.json": fp.PROBE / "source.json"}
        built = cloud.cloud_job(
            api,
            namespace,
            "build",
            shared,
            case,
            hardware,
            output,
            {"HALLMARK_FLASHPROVE_PHASE": "build"},
            phases=PHASES,
        )
        cloud.require(
            json.loads((built / "exit.json").read_text())["exit_code"] == 0, "build failed"
        )
        proved = cloud.cloud_job(
            api,
            namespace,
            "prove",
            shared
            | {"prove_response.py": fp.PROBE / "launch.py", "hc.tar.gz": built / "hc.tar.gz"},
            case,
            hardware,
            output,
            {
                "HALLMARK_FLASHPROVE_PHASE": "prove",
                "HALLMARK_FLASHPROVE_KIT": fp.PIN["gpu_kit"]["name"],
            },
            phases=PHASES,
        )
        cloud.require(
            json.loads((proved / "exit.json").read_text())["exit_code"] == 0, "proving failed"
        )
        worker_last = (proved / "cp_verify.log").read_text().strip().splitlines()[-1]
        cloud.require(worker_last == "YES", "the worker's own cp_verify did not accept")
        case_dir = proved / "case"
        commitment_id, next_token = caller_case(tree, case_dir, proved / "cp_commit.log")
        ok, check = fp.check_proof(
            tree,
            verifier,
            case_dir,
            commitment_id,
            fp.PIN["gpu_kit"]["range"],
            next_token,
            output / "check-fresh.log",
        )
        cloud.require(ok, "the local verifier did not accept the fresh proof")
        rejected = mutations(verifier, case_dir, commitment_id, output)
        retained = {n: json.loads((output / n / "retention.json").read_text()) for n in PHASES}
        result = dict(
            passed=True,
            schema_id="hallmark.flashprove-gpu-result/1",
            commitment_id=commitment_id,
            next_token=next_token,
            proof_bytes=(case_dir / "example.proof").stat().st_size,
            proof_sha256=sha(case_dir / "example.proof"),
            worker_verdict=worker_last,
            local_check=check,
            local_verifier=stored["build"],
            stored=stored,
            mutations_rejected=len(rejected),
            mutations=rejected,
            jobs={
                n: dict(
                    job_id=r["job_id"],
                    running_seconds=r["running_seconds"],
                    compute_bound_micro_usd=r["compute_bound_micro_usd"],
                )
                for n, r in retained.items()
            },
            gpu=(proved / "gpu.txt").read_text().strip(),
            seconds=time.monotonic() - started,
            invoice=False,
            synthetic_weights_only=True,
            qualified_backend=False,
            hiding_claim=False,
        )
        write_json(output / "result.json", result)
        print(json.dumps({k: result[k] for k in ("passed", "commitment_id", "mutations_rejected")}))
        return output
    except BaseException as exc:
        write_json(
            output / "failure.json",
            dict(type=type(exc).__name__, message=str(exc), seconds=time.monotonic() - started),
        )
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--credit-balance-usd", required=True)
    p.add_argument("--max-cost-usd", required=True)
    a = p.parse_args()
    run(a.credit_balance_usd, a.max_cost_usd)
