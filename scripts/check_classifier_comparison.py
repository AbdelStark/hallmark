"""Freeze/replay the classifier comparison with native and real gnark verification."""

import argparse
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import classifier_comparison as comparison

from hallmark._gnark_probe import RunBudget, digest, invoke, json_new, read_regular, write_new

ROOT = Path(__file__).resolve().parents[1]


def run(prepared, enrollment_pin, output):
    output.mkdir(mode=0o700)
    output = output.resolve()
    started = time.monotonic()
    budget = RunBudget(output, started + 600, 180, 180, 600, 4, 4 * 1024**3, 512 * 1024**2)
    source_paths = [
        *sorted((ROOT / "src/hallmark").glob("*.py")),
        *(
            ROOT / "scripts" / name
            for name in (
                "classifier_comparison.py",
                "check_classifier_comparison.py",
                "trained_common_input.py",
                "run_trained_mlp.py",
                "run_contextual_proof.py",
                "common_input.py",
                "contextual_cnn.py",
                "run_e2e.py",
                "check_gnark_input_scale.py",
            )
        ),
        ROOT / "research/probes/py_ecc/verify.py",
        ROOT / "research/probes/py_ecc/verify_set.py",
        ROOT / "uv.lock",
        ROOT / "configs/circle-classifiers/plan.json",
        ROOT / "configs/circle-classifiers/corpus.json",
    ]
    sources = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in source_paths}
    environment = dict(
        python=sys.version,
        platform=platform.platform(),
        machine=platform.machine(),
        packages={k: importlib.metadata.version(k) for k in ("numpy", "pydantic")},
        threads={
            k: os.environ.get(k)
            for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
        },
    )
    json_new(
        output / "protocol.json",
        dict(
            schema_id="hallmark.classifier-contract-replay-plan/1",
            sources=sources,
            environment=environment,
            environment_sha256=digest(comparison.encoded(environment)),
            expected_enrollment=enrollment_pin,
            seconds=600,
            threads=4,
            max_rss_bytes=budget.max_rss_bytes,
            max_storage_bytes=budget.max_output_bytes,
            command=sys.argv,
            benchmark_sample=False,
            new_proof_generation=False,
        ),
    )
    try:
        contract = comparison.native_contract(prepared, enrollment_pin)
        json_new(output / "contract.json", contract)
        python = prepared / "verifier-env/bin/python"
        prefix = Path(
            subprocess.check_output(
                [str(python), "-I", "-c", "import sys;print(sys.base_prefix)"],
                text=True,
                timeout=10,
                env={"PATH": "/usr/bin:/bin"},
            ).strip()
        )
        costs = []
        for case in contract["cases"]:
            work = output / case["id"]
            work.mkdir()
            raw = comparison.encoded(case["jobs"])
            write_new(work / "jobs.json", raw)
            cost = invoke(
                python,
                work,
                [
                    "-I",
                    "-B",
                    str(ROOT / "research/probes/py_ecc/verify_set.py"),
                    "--jobs",
                    "jobs.json",
                    "--expected-jobs",
                    digest(raw),
                ],
                budget=budget,
                cpu_seconds=180,
                read_paths=(python.parent.parent, prefix, ROOT),
            )
            budget.inspect(cost)
            if cost["exit_code"] != 0:
                raise ValueError("fresh separate gnark verifier failed; inspect retained logs")
            report = json.loads(read_regular(work / "stdout.txt", 65536))
            if report != {"status": "passed", "proofs_verified": 3, "qualified_backend": False}:
                raise ValueError("unexpected fresh verifier report")
            costs.append(dict(case=case["id"], **cost))
        if sources != {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in source_paths}:
            raise ValueError("comparison source changed during replay")
        result = dict(
            schema_id="hallmark.classifier-contract-replay/1",
            status="passed",
            gnark_proofs_freshly_verified=9,
            new_proofs_generated=0,
            native_input_boundaries=len(contract["boundaries"]),
            scalar_cases=contract["scalar_cases"],
            cross_request_rejections=len(contract["cross_request_rejections"]),
            roster_rejections=contract["roster_rejections"],
            contract_sha256=digest((output / "contract.json").read_bytes()),
            costs=costs,
            elapsed_seconds=time.monotonic() - started,
            qualified_backend=False,
            circle_classifier_support=False,
            benchmark_sample=False,
        )
        json_new(output / "result.json", result)
        return result
    except BaseException as error:
        json_new(
            output / "failure.json",
            dict(
                schema_id="hallmark.classifier-contract-replay-failure/1",
                error_type=type(error).__name__,
                error=str(error),
                elapsed_seconds=time.monotonic() - started,
            ),
        )
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classifier-run", required=True, type=Path)
    parser.add_argument("--expected-enrollment", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[key] = "4"
    if args.output is None:
        (ROOT / "runs").mkdir(exist_ok=True)
        args.output = Path(tempfile.mkdtemp(prefix="classifier-contract-", dir=ROOT / "runs"))
        args.output.rmdir()
    print("Evidence: " + str(args.output.resolve()), flush=True)
    result = run(args.classifier_run.resolve(), args.expected_enrollment, args.output)
    print(json.dumps({k: v for k, v in result.items() if k != "costs"}), flush=True)


if __name__ == "__main__":
    main()
