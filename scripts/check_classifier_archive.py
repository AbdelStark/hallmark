"""Fresh local verification of all 144 retained benchmark proofs; not new timings."""

import argparse
import json
import subprocess
import time
from pathlib import Path, PurePosixPath

import circle_backend as circle
import classifier_comparison as comparison
import trained_common_input as common
from benchmark_classifiers import summarize
from check_circle_engine import encode
from report_classifier_benchmark import PREFIX
from run_llm_e2e import require

from hallmark._gnark_probe import RunBudget, invoke, json_new, read_regular, write_new

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    prepared = args.classifier_run.resolve()
    audited = args.audit_run.resolve()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "runs"), "keep local evidence under ignored runs")
    output.mkdir(mode=0o700)
    started = time.monotonic()
    budget = RunBudget(output, started + 1800, 240, 240, 900, 4, 4 * 1024**3, 1024**3)
    raw = read_regular(audited / "report.json", 64 * 1024**2)
    audit = json.loads(raw)
    require(
        audit["status"] == "passed"
        and audit["measured_proofs"] == 144
        and len(audit["raw_samples"]) == 16,
        "incomplete byte audit",
    )
    require(audit["source_commit"] == args.expected_commit, "caller campaign commit mismatch")
    plan, _ = comparison.documents()
    require(
        summarize(audit["raw_samples"], plan) == audit["campaign"]["summary"],
        "raw matrix differs from frozen repetitions/cases",
    )
    for sample in audit["raw_samples"]:
        require(
            type(sample["repetition"]) is int
            and sample["sample_id"]
            == f"{sample['phase']}-{sample['repetition']:02d}-{sample['backend']}",
            "invalid sample identity",
        )
        expected_prep = (
            sample["sample_id"] if sample["phase"] == "fresh" else "fresh-00-" + sample["backend"]
        )
        require(sample["preparation_reference"] == expected_prep, "unexpected preparation reuse")
    exported, originals, old_policy, circuits, _ = comparison.admitted(
        prepared, args.expected_enrollment
    )
    binary = args.circle_verifier.resolve()
    require(
        comparison.sha(read_regular(binary, 128 * 1024**2)) == args.expected_verifier,
        "caller Circle binary pin",
    )
    python = prepared / "verifier-env/bin/python"
    prefix = Path(
        subprocess.check_output(
            [python, "-I", "-c", "import sys;print(sys.base_prefix)"], text=True, timeout=10
        ).strip()
    )
    crypto_helper = ROOT / "research/probes/py_ecc/verify_set.py"
    proof_root = audited / "campaign"

    def artifact(relative, maximum):
        name = PurePosixPath(relative)
        require(not name.is_absolute() and ".." not in name.parts, "unsafe proof input path")
        path = proof_root / relative
        require(
            path.resolve().is_relative_to(proof_root.resolve()), "proof input escapes audit root"
        )
        value = read_regular(path, maximum)
        require(
            comparison.sha(value) == audit["artifact_inventory"][PREFIX + relative]["sha256"],
            "extracted proof input differs from audited bytes",
        )
        return value

    json_new(
        output / "protocol.json",
        dict(
            schema_id="hallmark.classifier-local-verification/1",
            source_commit=args.expected_commit,
            audit_sha256=comparison.sha(raw),
            archive_sha256=audit["archive_sha256"],
            original_enrollment=args.expected_enrollment,
            circle_enrollment=args.expected_circle_enrollment,
            circle_verifier_sha256=args.expected_verifier,
            interpreter_sha256=comparison.sha(read_regular(python.resolve(), 128 * 1024**2)),
            pairing_helper_sha256=comparison.sha(crypto_helper.read_bytes()),
            source_sha256=comparison.sha(Path(__file__).read_bytes()),
            timing_scope="postflight Mac verification; excluded from matched Linux measurements",
            groth16_setup_trust="owner pre-proof setup; no reviewed ceremony or hardware claim",
        ),
    )
    counts = dict(circle=0, gnark=0)
    costs = []
    preparations = {}
    for sample in audit["raw_samples"]:
        backend = sample["backend"]
        prep = sample["preparation_reference"]
        if prep not in preparations:
            enrollment = artifact(prep + "/caller-enrollment.json", 65536)
            if backend == "circle":
                pin = args.expected_circle_enrollment
                records, policy, _ = circle.resolve(enrollment, pin, originals, old_policy)
            else:
                keys = {
                    kind: artifact(prep + "/setup-" + kind + "/vk.bin", 65536)
                    for kind in circle.KINDS
                }
                setup = next(s for s in audit["raw_samples"] if s["sample_id"] == prep)
                for kind, stage in zip(circle.KINDS, setup["shared_stages"]["setup"], strict=True):
                    require(
                        stage["kind"] == kind
                        and stage["setup"]["files"]["circuit.r1cs"]["sha256"] == circuits[kind]
                        and audit["artifact_inventory"][
                            PREFIX + prep + "/setup-" + kind + "/circuit.r1cs"
                        ]["sha256"]
                        == circuits[kind]
                        and stage["setup"]["files"]["vk.bin"]["sha256"]
                        == comparison.sha(keys[kind]),
                        "pre-proof setup record differs from admitted circuit/key",
                    )
                require(
                    enrollment == comparison.encoded(common.enroll(exported, keys, circuits)),
                    "captured setup/model enrollment differs from owner reconstruction",
                )
                pin = comparison.sha(enrollment)
                records, policy = common.resolve(enrollment, pin, exported, circuits)
            preparations[prep] = enrollment, pin, records, policy
        enrollment, pin, records, policy = preparations[prep]
        for case in sample["cases"]:
            opening, original_expected = comparison.request(prepared / "proofs", case["case_id"])
            expected = circle.expected_request(original_expected, policy)
            rows = common.evaluate(records, policy, opening, expected)
            proofs = []
            for kind, row, record in zip(circle.KINDS, rows, case["proofs"], strict=True):
                require(
                    record["kind"] == kind and record["public"] == row["public"],
                    "reported public inputs differ from caller expectations",
                )
                filename = "proof.json" if backend == "circle" else "proof.bin"
                proof = artifact(
                    sample["sample_id"] + "/" + case["case_id"] + "-prove-" + kind + "/" + filename,
                    64 * 1024**2,
                )
                require(
                    comparison.sha(proof) == record["proof_sha256"], "proof sample hash mismatch"
                )
                proofs.append(proof)
            if backend == "circle":
                bundle = dict(
                    schema_id="hallmark.circle-classifier-bundle/1",
                    proofs=[
                        dict(kind=k, public=r["public"], proof_hex=p.hex())
                        for k, r, p in zip(circle.KINDS, rows, proofs, strict=True)
                    ],
                )
                jobs = circle.check_bundle(
                    enrollment, pin, originals, old_policy, opening, expected, bundle
                )
                for job in jobs:
                    work = output / (
                        sample["sample_id"] + "-" + case["case_id"] + "-" + job["kind"]
                    )
                    work.mkdir()
                    for name, value in {
                        "enrollment.json": job["enrollment"],
                        "public.json": encode(job["public"]),
                        "proof.json": job["proof"],
                    }.items():
                        write_new(work / name, value)
                    cost = invoke(
                        binary,
                        work,
                        ["enrollment.json", job["enrollment_pin"], "public.json", "proof.json"],
                        budget=budget,
                        cpu_seconds=900,
                        max_file=64 * 1024**2,
                    )
                    doc = json.loads(read_regular(work / "stdout.txt", 65536))
                    require(
                        cost["exit_code"] == 0
                        and doc.get("status") == "passed"
                        and doc.get("cryptographic_verification") is True
                        and doc.get("qualified_backend") is False,
                        "local Circle verification failed",
                    )
                    costs.append(cost)
                    counts["circle"] += 1
            else:
                bundle = common.bundle(records, policy, opening, expected, rows, proofs)
                jobs = common.check_bundle(
                    enrollment,
                    pin,
                    exported,
                    circuits,
                    opening,
                    expected,
                    comparison.encoded(bundle),
                )
                job_bytes = comparison.encoded(jobs)
                work = output / (sample["sample_id"] + "-" + case["case_id"])
                work.mkdir()
                write_new(work / "jobs.json", job_bytes)
                cost = invoke(
                    python,
                    work,
                    [
                        "-I",
                        "-B",
                        str(crypto_helper),
                        "--jobs",
                        "jobs.json",
                        "--expected-jobs",
                        comparison.sha(job_bytes),
                    ],
                    budget=budget,
                    cpu_seconds=900,
                    max_file=64 * 1024**2,
                    read_paths=(python.parent.parent, prefix, ROOT / "src", crypto_helper.parent),
                )
                doc = json.loads(read_regular(work / "stdout.txt", 65536))
                require(
                    cost["exit_code"] == 0
                    and doc.get("status") == "passed"
                    and doc.get("proofs_verified") == 3
                    and doc.get("qualified_backend") is False,
                    "local pairing verification failed",
                )
                costs.append(cost)
                counts["gnark"] += 3
            print(sample["sample_id"] + ": locally verified " + case["case_id"], flush=True)
    require(counts == dict(circle=72, gnark=72), "incomplete local cryptographic verification")
    result = dict(
        schema_id="hallmark.classifier-local-verification-result/1",
        status="passed",
        fresh_proofs_verified=counts,
        total=144,
        verifier_processes=len(costs),
        costs=costs,
        elapsed_seconds=time.monotonic() - started,
        benchmark_sample=False,
        qualified_backend=False,
        hardware_claim="not-accepted",
    )
    json_new(output / "result.json", result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("audit-run", "classifier-run", "circle-verifier", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    for name in (
        "expected-commit",
        "expected-enrollment",
        "expected-circle-enrollment",
        "expected-verifier",
    ):
        p.add_argument("--" + name, required=True)
    result = run(p.parse_args())
    print(json.dumps({k: v for k, v in result.items() if k != "costs"}))
