"""Default local Circle STARK workflow, with native model preparation and no Groth16 setup."""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import circle_inputs
import classifier_comparison as comparison
import run_circle_classifiers
import run_e2e

from hallmark._gnark_probe import read_regular, write_new

ROOT = Path(__file__).resolve().parents[1]


def run(classifier_run=None, *, llm=False):
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise ValueError("Circle demo requires an Apple Silicon Mac; see docs/DEMO.md")
    uv = subprocess.check_output(["uv", "--version"], text=True, timeout=10).split()[:2]
    if uv != ["uv", "0.9.18"] or sys.version_info[:3] != (3, 12, 12):
        raise ValueError("use uv 0.9.18 and CPython 3.12.12")
    if shutil.disk_usage(ROOT).free < 12 * 1024**3:
        raise ValueError("Circle demo requires 12 GiB plus dependency/build cache headroom")
    (ROOT / "runs").mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="e2e-circle-", dir=ROOT / "runs"))
    print(f"Evidence: {output}", flush=True)
    started, stage = time.monotonic(), "source"
    deadline = started + 7200
    pins = run_e2e.source_pins()
    env = os.environ | dict(
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        VECLIB_MAXIMUM_THREADS="1",
        PYTHONUNBUFFERED="1",
        RAYON_NUM_THREADS="4",
    )
    run_e2e.write_json(
        output / "protocol.json",
        dict(
            schema_id="hallmark.circle-e2e-protocol/1",
            backend="circle",
            sources=pins,
            source_commit=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            uv=" ".join(uv),
            python=sys.version,
            host=platform.platform(),
            seconds=7200,
            fresh_training=classifier_run is None,
            composed=llm,
            groth16_setup=False,
            cloud_cost_minor=0,
        ),
    )

    def step(name, args):
        nonlocal stage
        stage = name
        run_e2e.command(args, output / (name + ".log"), env, deadline)

    try:
        if classifier_run is None:
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
                    run_e2e.CNN_PROTOCOL,
                    "--output",
                    output / "cnn-training",
                ],
            )
            run_e2e.check_training(output)
        else:
            retained = Path(classifier_run).resolve()
            comparison.exports(retained)
            for name in run_e2e.EXPORTS:
                target = output / name
                target.parent.mkdir(parents=True, exist_ok=True)
                write_new(target, read_regular(retained / name, 65536))
        stage = "native-preparation"
        preparation_pin = circle_inputs.create(output)
        circle_inputs.admit(output, preparation_pin)
        cargo = ROOT / "research/probes/circle"
        for name, features in [
            ("circle-prove", ["--features", "prover"]),
            ("circle-verify", ["--no-default-features"]),
        ]:
            step(
                name + "-build",
                [
                    "cargo",
                    "+nightly-2025-07-14",
                    "build",
                    "--manifest-path",
                    cargo / "Cargo.toml",
                    "--locked",
                    "--release",
                    *features,
                    "--bin",
                    name,
                    "-j",
                    "4",
                ],
            )
        prover, verifier = [
            cargo / "target/release" / name for name in ("circle-prove", "circle-verify")
        ]
        if time.monotonic() + 1800 > deadline:
            raise TimeoutError("not enough controller time left for the bounded proof workflow")
        stage = "circle-proofs"
        print("Running circle-proofs", flush=True)
        proof = run_circle_classifiers.run(
            output,
            preparation_pin,
            prover,
            run_e2e.sha(prover),
            verifier,
            run_e2e.sha(verifier),
            output / "proofs",
            native_preparation=True,
            llm=llm,
        )
        expected_count = 3 if llm else 9
        if (
            proof["status"] != "passed"
            or proof["fresh_proofs"] != expected_count
            or proof["fresh_proof_only_verifications"] != expected_count
            or proof["direct_public_mutations_rejected"] != expected_count * 7
            or len(proof["cross_request_rejections"]) != (0 if llm else 18)
            or proof["roster_rejections"] != 3
            or proof["intermediate_parity"] is not True
            or (llm and len(proof["binding_rejections"]) != 16)
        ):
            raise ValueError("incomplete Circle workflow result")
        if run_e2e.source_pins() != pins:
            raise ValueError("Circle pipeline source changed during execution")
        run_e2e.write_json(
            output / "result.json",
            dict(
                schema_id="hallmark.circle-e2e-result/1",
                status="passed",
                backend="circle",
                cases=proof["cases"],
                proofs_verified=expected_count,
                cross_request_rejections=len(proof["cross_request_rejections"]),
                direct_public_mutations_rejected=proof["direct_public_mutations_rejected"],
                roster_rejections=3,
                intermediate_parity=True,
                binding_rejections=proof["binding_rejections"],
                native_preparation_pin=preparation_pin,
                circle_enrollment_pin=proof["caller_enrollment_sha256"],
                proof_result_sha256=run_e2e.sha(output / "proofs/result.json"),
                elapsed_seconds=time.monotonic() - started,
                qualified_backend=False,
                hardware_claim="not-accepted",
                hiding_claim=False,
            ),
        )
        print(
            f"PASS: {expected_count} Circle proofs freshly verified. "
            f"Results: {output / 'result.json'}",
            flush=True,
        )
        return output
    except BaseException as error:
        run_e2e.write_json(
            output / "failure.json",
            dict(
                schema_id="hallmark.circle-e2e-failure/1",
                status="failed",
                stage=stage,
                error_type=type(error).__name__,
                elapsed_seconds=time.monotonic() - started,
            ),
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classifier-run", type=Path, help="reuse exact frozen model exports only")
    args = parser.parse_args()
    run(args.classifier_run)
