"""Benchmark the frozen TinyLlama relation with SIMD and CUDA on one HF H200."""

import argparse
import json
import re
import shutil
import tempfile
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

import run_llm_e2e as e2e
import verify_llm
from run_e2e import sha, write_json

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "research/probes/sash"
PHASES = {
    "build": ("cpu-upgrade", 1800, 4, 28),
    "prove": ("h200", 2700, 4, 210),
    "verify": ("cpu-upgrade", 1800, 4, 28),
}


def planned_cost(hardware, maximum, phases=PHASES):
    # HF bills Starting too; reserve the full extra creation/cancellation window.
    bounds = {name: (p[0], p[1] + 600, p[2], p[3]) for name, p in phases.items()}
    return e2e.planned_cost(hardware, maximum, bounds)


def credit_guard(balance, ceiling):
    try:
        amount = Decimal(balance)
    except InvalidOperation:
        raise ValueError("invalid independently checked credit balance") from None
    e2e.require(
        amount.is_finite() and amount >= Decimal(ceiling) / 1_000_000,
        "insufficient verified credits",
    )


def admit_inputs(previous):
    baseline = json.loads(
        (ROOT / "research/evidence/llm-e2e-reproduction-2026-10-23.json").read_text()
    )
    pins = baseline["artifact_sha256"]
    for name in ("inputs.tar.gz", "inventory.json"):
        path = previous / name
        e2e.require(path.is_file() and not path.is_symlink(), "missing regular public input")
        e2e.require(sha(path) == pins[name], "input differs from reviewed public witness archive")
    e2e.require(sha(PROBE / "response-case.json") == baseline["case_sha256"], "LLM case changed")
    return {name: pins[name] for name in ("inputs.tar.gz", "inventory.json")}


def admit_build(previous):
    case_pin = sha(PROBE / "response-case.json")
    parent = json.loads((previous / "protocol.json").read_text())
    e2e.require(parent["case_sha256"] == case_pin, "cached build case changed")
    for name in ("build_gpu.sh", "build_prover.sh", "response-case.json"):
        key = "research/probes/sash/" + name
        e2e.require(parent["source_files"][key] == sha(PROBE / name), "cached build source changed")
    receipt = json.loads((previous / "build/retention.json").read_text())
    e2e.require(
        receipt["stage"] == "COMPLETED"
        and receipt["all_outputs_retained"] is True
        and receipt["bucket_deleted"] is True,
        "cached build incomplete",
    )
    folder = previous / "build/retained"
    for name in ("zk-prover-simd", "zk-prover-cuda"):
        path = folder / name
        e2e.require(
            path.is_file() and not path.is_symlink() and 0 < path.stat().st_size < 128 * 1024**2,
            "invalid cached binary",
        )
        e2e.require(sha(path) == receipt["outputs"][name]["sha256"], "cached binary changed")
    return folder


def run(previous, balance, maximum, build_run=None):
    from huggingface_hub import HfApi

    previous = previous.resolve()
    inputs = admit_inputs(previous)
    built = admit_build(build_run.resolve()) if build_run is not None else None
    phases = {name: p for name, p in PHASES.items() if name != "build" or built is None}
    e2e.require(
        shutil.disk_usage(ROOT).free >= 16 * 1024**3, "at least 16 GiB free storage required"
    )
    api = HfApi(token=e2e.token())
    namespace = api.whoami()["name"]
    e2e.require(re.fullmatch(r"[A-Za-z0-9-]+", namespace) is not None, "invalid HF namespace")
    hardware = {h.name: h for h in api.list_jobs_hardware()}
    ceiling = planned_cost(hardware, maximum, phases)
    credit_guard(balance, ceiling)
    e2e.require(hardware["h200"].ram == "256 GB", "review changed H200 host memory")
    e2e.require(
        not [j for j in api.list_jobs(namespace=namespace) if j.status.stage not in e2e.TERMINAL],
        "another HF job is active",
    )
    case = json.loads((PROBE / "response-case.json").read_text())
    (ROOT / "runs").mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="llm-gpu-", dir=ROOT / "runs"))
    started = time.monotonic()
    files = [
        Path(__file__),
        ROOT / "scripts/run_llm_e2e.py",
        ROOT / "scripts/run_e2e.py",
        ROOT / "scripts/verify_llm.py",
        ROOT / "Makefile",
        ROOT / "pyproject.toml",
        ROOT / "uv.lock",
        ROOT / "research/AUTHORITY.json",
        ROOT / "research/evidence/llm-e2e-reproduction-2026-10-23.json",
        *sorted(PROBE.glob("*")),
    ]
    write_json(
        output / "protocol.json",
        dict(
            schema_id="hallmark.llm-gpu-benchmark/1",
            profile="cuda-native-sm90-host-generation",
            case_sha256=sha(PROBE / "response-case.json"),
            inputs=inputs,
            phases={
                k: dict(flavor=v[0], seconds=v[1], threads=v[2], memory_gib=v[3])
                for k, v in phases.items()
            },
            cost_ceiling_micro_usd=ceiling,
            cost_basis="worker timeout plus 600-second creation window per job and storage reserve",
            caller_ceiling_usd=maximum,
            credit_check="caller-supplied live prepaid balance; separately checked before launch",
            balance_check_unix=int(time.time()),
            automatic_retries=0,
            source_files={str(p.relative_to(ROOT)): sha(p) for p in files if p.is_file()},
            preparation_reused=True,
            build_reused=built is not None,
            repetitions=1,
            generated_kernels=False,
            adoption=False,
            qualified_backend=False,
            hiding_claim=False,
            hardware_claim="not-accepted",
        ),
    )
    print(
        f"Outputs: {output}\nCPU build, paired SIMD/CUDA H200 run, fresh proof-only worker.\n"
        f"Timeout-based ceiling: ${ceiling / 1e6:.2f}; no retries.",
        flush=True,
    )
    try:
        # Snapshot only the hash-enrolled, previously reviewed public preparation.
        for name in inputs:
            shutil.copyfile(previous / name, output / name)
            e2e.require(sha(output / name) == inputs[name], "input changed while copying")
        if built is None:
            built = e2e.cloud_job(
                api,
                namespace,
                "build",
                {
                    "build_prover.sh": PROBE / "build_gpu.sh",
                    "build_cpu.sh": PROBE / "build_prover.sh",
                },
                case,
                hardware,
                output,
                env={
                    "SOURCE_URL": case["source"]["url"],
                    "SOURCE_SHA256": case["source"]["sha256"],
                    "SOURCE_COMMIT": case["source"]["revision"],
                },
                phases=phases,
            )
        else:
            write_json(
                output / "build-reused.json",
                dict(
                    case_sha256=sha(PROBE / "response-case.json"),
                    parent_protocol_sha256=sha(build_run / "protocol.json"),
                    receipt_sha256=sha(build_run / "build/retention.json"),
                    binaries={
                        name: sha(built / name) for name in ("zk-prover-simd", "zk-prover-cuda")
                    },
                ),
            )
        cpu, cuda = built / "zk-prover-simd", built / "zk-prover-cuda"
        for binary, pin in ((cpu, "binary.sha256"), (cuda, "cuda.sha256")):
            e2e.require(
                binary.is_file() and binary.stat().st_size < 128 * 1024**2, "missing prover binary"
            )
            e2e.require((built / pin).read_text().split()[0] == sha(binary), "binary hash mismatch")
        expected = dict(
            schema_id="hallmark.sash-response-expectations/1",
            roots=case["expected_roots"],
            prompt_ids=case["prompt_ids"],
            answer_ids=case["answer_ids"],
            binary_sha256=sha(cpu),
        )
        write_json(output / "expected.json", expected)
        write_json(output / "expected-roots.json", expected["roots"])
        write_json(
            output / "benchmark.json",
            dict(repetitions=1, worker_seconds=2550, max_rss_bytes=200 * 1024**3),
        )
        common = {
            "expected.json": output / "expected.json",
            "check_response.py": PROBE / "check_response.py",
        }
        measured = e2e.cloud_job(
            api,
            namespace,
            "prove",
            common
            | {
                "prove_response.py": PROBE / "benchmark_gpu.py",
                "relation.py": PROBE / "prove_response.py",
                "zk-prover-simd": cpu,
                "zk-prover-cuda": cuda,
                "inputs.tar.gz": output / "inputs.tar.gz",
                "inventory.json": output / "inventory.json",
                "response-case.json": PROBE / "response-case.json",
                "expected-roots.json": output / "expected-roots.json",
                "benchmark.json": output / "benchmark.json",
            },
            case,
            hardware,
            output,
            phases=phases,
        )
        report = json.loads((measured / "output/result.json").read_text())
        e2e.require(
            report["passed"] is True
            and report["proof_bytes_equal"] is True
            and len(report["results"]) == 2,
            "incomplete matched measurement",
        )
        for src, dst in (
            ("cuda-0-proofs.tar.gz", "proofs.tar.gz"),
            ("cuda-0-inventory.json", "proof-inventory.json"),
        ):
            shutil.copyfile(measured / "output" / src, output / dst)
        # This job receives only GPU-generated proof artifacts and the SIMD verifier.
        verified = e2e.cloud_job(
            api,
            namespace,
            "verify",
            common
            | {
                "zk-prover": cpu,
                "proofs.tar.gz": output / "proofs.tar.gz",
                "proof-inventory.json": output / "proof-inventory.json",
                "verify_response.py": PROBE / "verify_response.py",
            },
            case,
            hardware,
            output,
            phases=phases,
        )
        verification = json.loads((verified / "output/result.json").read_text())
        e2e.require(
            verification["passed"] is True
            and len(verification["cases"]) == 16
            and sum(c["accepted"] for c in verification["cases"]) == 2
            and verification["weights_present"] is False
            and verification["witness_present"] is False,
            "fresh proof-only verification failed",
        )
        native = verify_llm.run(output)
        receipts = [json.loads((output / phase / "retention.json").read_text()) for phase in phases]
        e2e.require(all(r["bucket_deleted"] for r in receipts), "bucket cleanup incomplete")
        result = dict(
            schema_id="hallmark.llm-gpu-result/1",
            passed=True,
            profile=report["profile"],
            measurements=report["results"],
            proof_bytes_equal=True,
            repetitions=1,
            preparation_reused=True,
            build_reused=build_run is not None,
            full_fresh_e2e_measured=False,
            native_verification=str(native),
            seconds=time.monotonic() - started,
            compute_bound_micro_usd=sum(r["compute_bound_micro_usd"] for r in receipts),
            invoice=False,
            all_buckets_deleted=True,
            qualified_backend=False,
            hiding_claim=False,
            hardware_claim="not-accepted",
        )
        write_json(output / "result.json", result)
        print(json.dumps(result, indent=2), flush=True)
        return output
    except BaseException as exc:
        write_json(
            output / "failure.json",
            dict(
                type=type(exc).__name__,
                seconds=time.monotonic() - started,
                completed=False,
                message="Inspect retained phase logs",
            ),
        )
        print(f"Failed; retained evidence: {output}", flush=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm-run", required=True, type=Path)
    parser.add_argument(
        "--credit-balance-usd", required=True, help="live prepaid balance checked independently"
    )
    parser.add_argument("--max-cost-usd", default="5.00")
    parser.add_argument(
        "--build-run",
        type=Path,
        help="reuse a completed caller-owned build with checked source/output hashes",
    )
    args = parser.parse_args()
    run(args.llm_run, args.credit_balance_usd, args.max_cost_usd, args.build_run)
