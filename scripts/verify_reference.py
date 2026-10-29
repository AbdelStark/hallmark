"""Verify downloaded reference artifacts against an externally obtained manifest digest."""

import argparse
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import circle_backend
import circle_inputs
import classifier_comparison as comparison
import composed_input
import reference_files
import verify_llm
from check_circle_engine import encode

from hallmark._worker import RunBudget, invoke, read_regular, write_new

ROOT = Path(__file__).resolve().parents[1]


def run(directory, expected_manifest):
    manifest_path = directory / "reference-manifest.json"
    if reference_files.sha(manifest_path) != expected_manifest:
        raise ValueError("external reference manifest pin mismatch")
    manifest = json.loads(read_regular(manifest_path, 2 * 1024**2))
    if manifest["schema_id"] != "hallmark.public-reference/1":
        raise ValueError("reference schema mismatch")
    if (
        circle_backend.source_identity()[0].hex() != manifest["circle_backend_identity"]
        or verify_llm.verifier_identity(verify_llm.source_inventory()).hex()
        != manifest["llm_verifier_identity"]
    ):
        raise ValueError("reference verifier source identity mismatch")
    for name, record in manifest["assets"].items():
        reference_files.relative(name)
        path = directory / name
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != record["bytes"]
            or reference_files.sha(path) != record["sha256"]
        ):
            raise ValueError("reference asset mismatch: " + name)
    (ROOT / "runs").mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="reference-verify-", dir=ROOT / "runs"))
    print(f"Reference verification: {output}", flush=True)
    started = time.monotonic()
    for name in ("reference-records.tar.gz", "llm-proofs.tar.gz"):
        reference_files.check_archive(directory / name, manifest["assets"][name]["members"])
    reference_files.check_archive(
        directory / "reference-records.tar.gz",
        manifest["assets"]["reference-records.tar.gz"]["members"],
        output / "records",
    )
    records = output / "records"
    llm = output / "llm"
    llm.mkdir()
    shutil.copyfile(directory / "llm-proofs.tar.gz", llm / "proofs.tar.gz")
    write_new(
        llm / "proof-inventory.json", read_regular(records / "llm/proof-inventory.json", 1024**2)
    )
    llm_result = verify_llm.run(llm)
    cargo = ROOT / "research/probes/circle/Cargo.toml"
    subprocess.run(
        [
            "cargo",
            "+nightly-2025-07-14",
            "build",
            "--manifest-path",
            str(cargo),
            "--locked",
            "--release",
            "--no-default-features",
            "--bin",
            "circle-verify",
            "-j",
            "4",
        ],
        check=True,
        timeout=1800,
    )
    binary = cargo.parent / "target/release/circle-verify"
    checks = output / "circle-checks"
    checks.mkdir()
    budget = RunBudget(checks, time.monotonic() + 900, 120, 120, 900, 4 * 1024**3, 128 * 1024**2)
    counts = {"controls": 0, "composed": 0}
    for group in manifest["classifiers"]:
        if group["id"] not in counts:
            raise ValueError("unknown reference classifier group")
        prepared = records / group["directory"]
        _, originals, policy = circle_inputs.admit(prepared, group["native_preparation_pin"])
        proof_root = prepared / "proofs"
        enrollment = read_regular(proof_root / "caller-enrollment.json", 65536)
        for name in group["cases"]:
            opening, expected = comparison.request(proof_root, name)
            if group["id"] == "composed":
                composed_input.check_request(opening, expected)
            bundle = json.loads(read_regular(proof_root / (name + "-bundle.json"), 32 * 1024**2))
            jobs = circle_backend.check_bundle(
                enrollment,
                circle_inputs.ENROLLMENT_PIN,
                originals,
                policy,
                opening,
                expected,
                bundle,
            )
            for job in jobs:
                work = checks / (group["id"] + "-" + name + "-" + job["kind"])
                work.mkdir()
                for file, data in {
                    "enrollment.json": job["enrollment"],
                    "public.json": encode(job["public"]),
                    "proof.json": job["proof"],
                }.items():
                    write_new(work / file, data)
                cost = invoke(
                    binary,
                    work,
                    ["enrollment.json", job["enrollment_pin"], "public.json", "proof.json"],
                    budget=budget,
                )
                budget.inspect(cost)
                result = json.loads(read_regular(work / "stdout.txt", 65536))
                if cost["exit_code"] != 0 or result != dict(
                    status="passed", cryptographic_verification=True, qualified_backend=False
                ):
                    raise ValueError("reference Circle proof failed")
                counts[group["id"]] += 1
    if counts != {"controls": 9, "composed": 3}:
        raise ValueError("reference proof count mismatch")
    result = dict(
        schema_id="hallmark.public-reference-verification/1",
        status="passed",
        manifest_sha256=expected_manifest,
        llm_result=str(llm_result),
        llm_distinct_proofs=23,
        llm_honest_verifications=2,
        circle_classifier_proofs=sum(counts.values()),
        composed_classifier_proofs=3,
        control_classifier_proofs=9,
        seconds=time.monotonic() - started,
        qualified_backend=False,
    )
    write_new(output / "result.json", comparison.encoded(result))
    print(json.dumps(result, indent=2), flush=True)
    return output


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--expected-manifest", required=True)
    args = p.parse_args()
    run(args.directory.resolve(), args.expected_manifest)
