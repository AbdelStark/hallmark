"""Measure the exact published classifier cases on one H200, CPU and CUDA."""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import circle_backend
import circle_inputs
import classifier_comparison as comparison
import run_llm_e2e as cloud
import trained_common_input as common
from check_circle_engine import encode
from prepare_classifier_gpu import PROBE
from run_e2e import sha, write_json
from run_llm_gpu import credit_guard

ROOT = Path(__file__).resolve().parents[1]
PHASES = {"build": ("cpu-upgrade", 1800, 4, 28), "prove": ("h200", 1800, 4, 210)}
VERIFIER = ROOT / "research/probes/circle/target/release/circle-verify"
BINARIES = {"circle-prove-cpu", "circle-prove-cuda", "circle-verify"}
ROSTER = {
    f"{case}-{kind}"
    for case in ("allow", "rule-block", "cnn-block")
    for kind in circle_backend.KINDS
}


def measurement_roster(rows):
    expected = {
        (i, backend, name) for i in range(3) for backend in ("cpu", "cuda") for name in ROSTER
    }
    cloud.require(
        len(rows) == len(expected)
        and {(r["iteration"], r["backend"], r["case"]) for r in rows} == expected,
        "GPU measurement roster changed",
    )


def admit_source(source):
    pins = json.loads((source / "source.json").read_text())
    cloud.require(
        sha(source / "source.tar.gz") == pins["source_archive_sha256"]
        and sha(source / "source-inventory.json") == pins["source_inventory_sha256"],
        "source archive changed",
    )
    overlays = {p.name: sha(p) for p in PROBE.iterdir() if p.is_file()}
    cloud.require(overlays == pins["overlays"], "source overlay changed; prepare a fresh tree")
    return pins


def inputs(prepared, pin, destination):
    exported, originals, old_policy = circle_inputs.admit(prepared, pin)
    proof_root = prepared / "proofs"
    enrollment = (proof_root / "caller-enrollment.json").read_bytes()
    records, policy, engines = circle_backend.resolve(
        enrollment, circle_inputs.ENROLLMENT_PIN, originals, old_policy
    )
    files, roster = {}, []
    reconstruction = []
    for name in ("allow", "rule-block", "cnn-block"):
        opening, expected = comparison.request(proof_root, name)
        rows = common.evaluate(records, policy, opening, expected)
        for kind, row in zip(circle_backend.KINDS, rows, strict=True):
            folder = proof_root / (name + "-prove-" + kind)
            circuit, trace = circle_backend.compile_case(
                kind, row, opening.prompt.encode(), exported
            )
            frozen = {
                "program.json": encode(circuit.program()),
                "witness.json": encode(circuit.witness()),
                "public.json": encode([w.value for w in circuit.wires[: circuit.external]]),
                "enrollment.json": engines[kind],
            }
            cloud.require(circuit.check_witness(), "native witness failed")
            del circuit, trace
            case = name + "-" + kind
            roster.append(case)
            for file, raw in frozen.items():
                cloud.require(
                    (folder / file).read_bytes() == raw, "C1 native reconstruction differs"
                )
                files[case + "/" + file] = folder / file
            for field in (
                "classifier",
                "context",
                "digest",
                "length",
                "chunks",
                "threshold",
                "verdict",
            ):
                files[case + "/reject-" + field + ".json"] = (
                    proof_root / (name + "-reject-" + kind + "-" + field) / "public.json"
                )
            reconstruction.append(
                dict(
                    case=case,
                    files={k: comparison.sha(v) for k, v in frozen.items()},
                    reference_proof_sha256=sha(folder / "proof.json"),
                )
            )
    # The fixed arithmetic control exercises a genuine proof before large inputs.
    fixture = destination / "fixture"
    fixture.mkdir()
    program = dict(
        schema="hallmark.gate-program/1",
        external=5,
        gates=[
            dict(mode=1, a=2, b=3, qa=1, qb=1, qm=0, qk=0),
            dict(mode=2, a=5, b=4, qa=1, qb=2**31 - 2, qm=0, qk=0),
        ],
    )
    for file, value in {
        "program.json": program,
        "public.json": [0, 1, 3, 4, 7],
        "witness.json": [0, 1, 3, 4, 7, 7, 0],
        "bad-witness.json": [0, 1, 3, 4, 7, 8, 0],
    }.items():
        (fixture / file).write_bytes(encode(value))
    subprocess.run(
        [
            ROOT / "research/probes/circle/target/release/circle-prove",
            "enroll",
            fixture / "program.json",
            fixture / "enrollment.json",
        ],
        check=True,
        timeout=60,
        stdout=(destination / "fixture-enroll.stdout").open("xb"),
        stderr=(destination / "fixture-enroll.stderr").open("xb"),
    )
    files |= {"fixture/" + p.name: p for p in fixture.iterdir()}
    inventory = cloud.archive(files, destination / "inputs.tar.gz")
    write_json(destination / "inputs-inventory.json", inventory)
    write_json(destination / "cases.json", roster)
    write_json(destination / "native-reconstruction.json", reconstruction)
    return inventory


def run(
    prepared,
    native_pin,
    source,
    balance,
    *,
    gpu_flavor="h200",
    build_run=None,
):
    from huggingface_hub import HfApi

    cloud.require(shutil.disk_usage(ROOT).free >= 16 * 1024**3, "16 GiB free storage required")
    # The proofs are only checked after the paid jobs; build the verifier before starting them.
    cloud.require(
        VERIFIER.is_file() and not VERIFIER.is_symlink(),
        "Build circle-verify (make circle-build) before starting paid jobs",
    )
    api = HfApi(token=cloud.token())
    namespace = api.whoami()["name"]
    hardware = {h.name: h for h in api.list_jobs_hardware()}
    cloud.require(gpu_flavor in ("h200", "a100-large"), "unadmitted GPU flavor")
    phases = PHASES | {"prove": (gpu_flavor, 1800, 4, 210 if gpu_flavor == "h200" else 120)}
    expected = ("23 vCPU", "256 GB") if gpu_flavor == "h200" else ("12 vCPU", "142 GB")
    cloud.require(
        (hardware[gpu_flavor].cpu, hardware[gpu_flavor].ram) == expected
        and hardware["cpu-upgrade"].ram == "32 GB",
        "hardware allocation changed",
    )
    ceiling = cloud.planned_cost(hardware, "5.00", phases)
    credit_guard(balance, ceiling)
    cloud.require(
        not [j for j in api.list_jobs(namespace=namespace) if j.status.stage not in cloud.TERMINAL],
        "another HF job is active",
    )
    source_pins = admit_source(source)
    output = Path(tempfile.mkdtemp(prefix="classifier-gpu-", dir=ROOT / "runs"))
    print("Outputs: " + str(output), flush=True)
    sources = [
        Path(__file__),
        ROOT / "scripts/reference_files.py",
        ROOT / "scripts/prepare_classifier_gpu.py",
        ROOT / "scripts/run_llm_e2e.py",
        ROOT / "scripts/run_llm_gpu.py",
        ROOT / "scripts/run_e2e.py",
        ROOT / "scripts/circle_inputs.py",
        ROOT / "scripts/classifier_comparison.py",
        ROOT / "scripts/trained_common_input.py",
        *PROBE.iterdir(),
    ]
    write_json(
        output / "protocol.json",
        dict(
            schema_id="hallmark.classifier-cuda-study/1",
            source_files={str(p.relative_to(ROOT)): sha(p) for p in sources if p.is_file()},
            phases=phases,
            gpu_flavor=gpu_flavor,
            balance_check_usd=balance,
            cost_ceiling_micro_usd=ceiling,
            source=source_pins,
            native_preparation_pin=native_pin,
            cpu_backend_identity=circle_backend.source_identity()[0].hex(),
            repetitions=3,
            baseline="published C1 Mac observation",
            automatic_retries=0,
            qualified_backend=False,
        ),
    )
    started = time.monotonic()
    try:
        os.environ.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1")
        prepared_at = time.monotonic()
        inputs(prepared, native_pin, output)
        preparation_seconds = time.monotonic() - prepared_at
        write_json(
            output / "input-preparation.json",
            dict(
                seconds=preparation_seconds,
                training_reused=True,
                source_preparation_reused=True,
                native_reconstruction_cases=9,
                input_archive_bytes=(output / "inputs.tar.gz").stat().st_size,
            ),
        )
        # Hardware transport and retention use the existing foreground job controller.
        case = json.loads((ROOT / "research/probes/sash/response-case.json").read_text())
        case["source"] = {
            "revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip()
        }
        if build_run is not None:
            parent = json.loads((build_run / "protocol.json").read_text())
            cloud.require(
                parent["source"]["source_inventory_sha256"]
                == source_pins["source_inventory_sha256"]
                and parent.get("gpu_flavor", "h200") == gpu_flavor,
                "cached build source or native target changed",
            )
            retained = json.loads((build_run / "build/retention.json").read_text())
            cloud.require(retained["stage"] == "COMPLETED", "cached build incomplete")
            built = build_run / "build/retained"
            for name in BINARIES | {"binaries.json"}:
                cloud.require(
                    sha(built / name) == retained["outputs"][name]["sha256"],
                    "cached build bytes changed",
                )
            write_json(
                output / "reused-build.json",
                dict(
                    path=str(build_run),
                    protocol_sha256=sha(build_run / "protocol.json"),
                    retention_sha256=sha(build_run / "build/retention.json"),
                ),
            )
        else:
            built = cloud.cloud_job(
                api,
                namespace,
                "build",
                {
                    "build_prover.sh": PROBE / "build.sh",
                    "source.tar.gz": source / "source.tar.gz",
                    "source-inventory.json": source / "source-inventory.json",
                    "reference_files.py": ROOT / "scripts/reference_files.py",
                },
                case,
                hardware,
                output,
                phases=phases,
                env={"HALLMARK_CUDA_ARCH": "90" if gpu_flavor == "h200" else "80"},
            )
        binaries = json.loads((built / "binaries.json").read_text())
        cloud.require(set(binaries) == BINARIES, "built binary roster changed")
        for name in BINARIES:
            cloud.require(sha(built / name) == binaries[name], "built binary changed")
        measured = cloud.cloud_job(
            api,
            namespace,
            "prove",
            {
                **{name: built / name for name in binaries},
                "prove_response.py": PROBE / "benchmark.py",
                "reference_files.py": ROOT / "scripts/reference_files.py",
                **{
                    name: output / name
                    for name in ("inputs.tar.gz", "inputs-inventory.json", "cases.json")
                },
            },
            case,
            hardware,
            output,
            phases=phases,
            env={"HALLMARK_EXPECTED_GPU": "H200" if gpu_flavor == "h200" else "A100"},
        )
        result = json.loads((measured / "output/result.json").read_text())
        cloud.require(
            result["passed"] and len(result["measurements"]) == 54, "GPU campaign incomplete"
        )
        measurement_roster(result["measurements"])
        for row in result["measurements"]:
            stem = f"{row['iteration']}-{row['backend']}-{row['case']}"
            case_name, kind = row["case"].rsplit("-", 1)
            folder = prepared / "proofs" / (case_name + "-prove-" + kind)
            cloud.require(
                sha(folder / "enrollment.json") == row["enrollment_sha256"]
                and sha(folder / "public.json") == row["public_sha256"],
                "caller input substitution",
            )
            proof = measured / "output" / (stem + ".json")
            cloud.require(sha(proof) == row["proof_sha256"], "retained proof changed")
            begin = time.monotonic()
            checked = subprocess.run(
                [
                    VERIFIER,
                    folder / "enrollment.json",
                    row["enrollment_sha256"],
                    folder / "public.json",
                    proof,
                ],
                capture_output=True,
                timeout=30,
            )
            cloud.require(checked.returncode == 0, "fresh stock Mac verifier rejected")
            row["mac_verify_seconds"] = time.monotonic() - begin
        result |= dict(
            seconds=time.monotonic() - started,
            input_preparation_seconds=preparation_seconds,
            fresh_mac_verifications=54,
            all_buckets_deleted=True,
            source=source_pins,
            invoice=False,
        )
        write_json(output / "result.json", result)
        print(json.dumps({k: v for k, v in result.items() if k != "measurements"}), flush=True)
        return output
    except BaseException as exc:
        write_json(
            output / "failure.json",
            dict(type=type(exc).__name__, seconds=time.monotonic() - started, passed=False),
        )
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prepared", type=Path, required=True)
    p.add_argument("--native-preparation-pin", required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--credit-balance-usd", required=True)
    p.add_argument("--gpu-flavor", choices=("h200", "a100-large"), default="h200")
    p.add_argument("--build-run", type=Path)
    a = p.parse_args()
    run(
        a.prepared.resolve(),
        a.native_preparation_pin,
        a.source.resolve(),
        a.credit_balance_usd,
        gpu_flavor=a.gpu_flavor,
        build_run=a.build_run.resolve() if a.build_run else None,
    )
