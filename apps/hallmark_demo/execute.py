"""Paid-workflow admission, executed inside the existing proof environment.

This adapter checks startup-inclusive prices, then calls the frozen driver.
It imports neither the TUI nor the app server into the proof environment.
"""

import argparse
import hashlib
import importlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

CREATION_SECONDS = 600


def inclusive_phases(phases):
    return {
        name: (flavor, seconds + CREATION_SECONDS, threads, memory)
        for name, (flavor, seconds, threads, memory) in phases.items()
    }


def admission(e2e, hardware, workflow, maximum, *, gpu=None, build_reused=False):
    phases = e2e.PHASES
    if workflow == "gpu":
        phases = {
            name: value for name, value in gpu.PHASES.items() if name != "build" or not build_reused
        }
    bound = e2e.planned_cost(hardware, maximum, inclusive_phases(phases))
    return dict(
        schema_id="hallmark.demo-hf-plan/1",
        observed_at=datetime.now(UTC).isoformat(),
        ceiling_usd=maximum,
        conservative_bound_micro_usd=bound,
        cost_basis="Worker timeout plus 600-second creation/cancellation window per phase, "
        "minute rounding and storage reserve at observed prices",
        automatic_retries=0,
        phases={
            name: dict(
                flavor=value[0],
                worker_seconds=value[1],
                creation_seconds=CREATION_SECONDS,
                threads=value[2],
                memory_gib=value[3],
                rate_micro_usd_minute=hardware[value[0]].unit_cost_micro_usd,
            )
            for name, value in phases.items()
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--workflow", choices=("llm", "gpu", "composed-circle"), required=True)
    parser.add_argument("--max-cost-usd", required=True)
    parser.add_argument("--monitor-dir", type=Path, required=True)
    parser.add_argument("--llm-run", type=Path)
    parser.add_argument("--classifier-run", type=Path)
    parser.add_argument("--build-run", type=Path)
    parser.add_argument("--credit-balance-usd")
    args = parser.parse_args()
    root = args.root.resolve()
    if Path.cwd().resolve() != root:
        raise ValueError("The proof adapter must run in its selected checkout")
    monitor = args.monitor_dir.resolve()
    if not monitor.is_relative_to(root / "runs/workbench") or not monitor.is_dir():
        raise ValueError("Unsafe monitoring directory")
    sys.path.insert(0, str(root / "scripts"))
    e2e = importlib.import_module("run_llm_e2e")
    gpu = importlib.import_module("run_llm_gpu") if args.workflow == "gpu" else None
    paid = args.workflow != "composed-circle" or args.llm_run is None
    if paid:
        from huggingface_hub import HfApi

        print("Checking startup-inclusive HF prices before launching paid work", flush=True)
        api = HfApi(token=e2e.token())
        hardware = {item.name: item for item in api.list_jobs_hardware()}
        plan = admission(
            e2e,
            hardware,
            args.workflow,
            args.max_cost_usd,
            gpu=gpu,
            build_reused=args.build_run is not None,
        )
        if gpu:
            gpu.credit_guard(args.credit_balance_usd, plan["conservative_bound_micro_usd"])
        plan["adapter_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        with (monitor / "resource-plan.json").open("x") as stream:
            json.dump(plan, stream, indent=2)
        print(
            f"Admitted resource bound: ${plan['conservative_bound_micro_usd'] / 1e6:.2f}; "
            f"ceiling ${args.max_cost_usd}",
            flush=True,
        )
    if args.workflow == "llm":
        e2e.run(args.max_cost_usd)
    elif args.workflow == "gpu":
        gpu.run(
            args.llm_run,
            balance=args.credit_balance_usd,
            maximum=args.max_cost_usd,
            build_run=args.build_run,
        )
    else:
        importlib.import_module("run_circle_composed").run(
            llm_run=args.llm_run,
            classifier_run=args.classifier_run,
            enrollment=os.environ.get("LLM_ENROLLMENT"),
            trusted_key=os.environ.get("LLM_TRUST_KEY"),
        )


if __name__ == "__main__":
    main()
