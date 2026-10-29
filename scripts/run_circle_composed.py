"""Default all-Circle integrity composition; retained inputs require no paid work."""

import argparse
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

import circle_inputs
import classifier_comparison as comparison
import composed_input
import run_circle_e2e
import run_e2e
import run_llm_e2e
import verify_llm
from check_circle_composed import binding_negatives, joined_jobs
from check_circle_engine import encode

from hallmark._worker import RunBudget, invoke, read_regular, write_new

ROOT = Path(__file__).resolve().parents[1]


def run(*, llm_run=None, classifier_run=None, enrollment=None, trusted_key=None):
    required = 32 if llm_run is None else 12
    if shutil.disk_usage(ROOT).free < required * 1024**3:
        raise ValueError(f"Circle composition requires {required} GiB free storage")
    case = composed_input.case()
    signed, key = verify_llm.read_enrollment(enrollment, trusted_key)
    inventory = verify_llm.source_inventory()
    verifier_id = verify_llm.verifier_identity(inventory)
    (ROOT / "runs").mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="composed-circle-", dir=ROOT / "runs"))
    print(f"Composed evidence: {output}", flush=True)
    started = time.monotonic()
    sources = run_e2e.source_pins()
    run_e2e.write_json(
        output / "protocol.json",
        dict(
            schema_id="hallmark.circle-composed-protocol/1",
            sources=sources,
            fresh_llm_proving=llm_run is None,
            classifier_backend="circle",
            llm_case_sha256=composed_input.CASE_SHA256,
            circle_enrollment=circle_inputs.ENROLLMENT_PIN,
            host_join=True,
            recursion=False,
            qualified_backend=False,
        ),
    )

    def authority(stage):
        value = verify_llm.parameter_authority(
            signed,
            key,
            case_sha256=bytes.fromhex(composed_input.CASE_SHA256),
            verifier=verifier_id,
            stage=stage,
        )
        run_e2e.write_json(output / ("enrollment-" + stage + ".json"), value)
        return value

    try:
        initial = authority("before-preparation")
        frozen = None
        if signed is not None:
            frozen = output / "enrollment.cbor"
            write_new(frozen, signed)
        if llm_run is None:
            llm_run = run_llm_e2e.run("2.10")
        verified = verify_llm.run(
            Path(llm_run).resolve(), enrollment=frozen, trusted_key=trusted_key
        )
        llm = json.loads(read_regular(verified / "result.json", 1024**2))
        if (
            llm.get("passed") is not True
            or llm.get("proofs") != 23
            or llm.get("residual_links") != 22
            or llm.get("fresh_verifications") != 2
            or llm.get("response") != case["response"]
        ):
            raise ValueError("incomplete fresh LLM verification")
        observed = llm["parameter_authority"]
        if {k: v for k, v in observed.items() if k not in ("stage", "checked_at")} != {
            k: v for k, v in initial.items() if k not in ("stage", "checked_at")
        }:
            raise ValueError("LLM parameter authority changed")
        classifier = run_circle_e2e.run(classifier_run, llm=True)
        report = json.loads(read_regular(classifier / "result.json", 1024**2))
        _, originals, policy = circle_inputs.admit(classifier, report["native_preparation_pin"])
        proof_root = classifier / "proofs"
        opened, expected = comparison.request(proof_root, "llm-response")
        raw_enrollment = read_regular(proof_root / "caller-enrollment.json", 65536)
        bundle = json.loads(read_regular(proof_root / "llm-response-bundle.json", 32 * 1024**2))
        jobs = joined_jobs(
            raw_enrollment,
            circle_inputs.ENROLLMENT_PIN,
            originals,
            policy,
            opened,
            expected,
            bundle,
        )
        binary = (ROOT / "research/probes/circle/target/release/circle-verify").resolve()
        proof_protocol = json.loads(read_regular(proof_root / "protocol.json", 1024**2))
        if run_e2e.sha(binary) != proof_protocol["verifier_sha256"]:
            raise ValueError("caller verifier binary changed after proof creation")
        budget = RunBudget(
            output, time.monotonic() + 900, 240, 240, 900, 4 * 1024**3, 256 * 1024**2
        )
        for job in jobs:
            work = output / ("verify-" + job["kind"])
            work.mkdir()
            for name, data in {
                "enrollment.json": job["enrollment"],
                "public.json": encode(job["public"]),
                "proof.json": job["proof"],
            }.items():
                write_new(work / name, data)
            cost = invoke(
                binary,
                work,
                ["enrollment.json", job["enrollment_pin"], "public.json", "proof.json"],
                budget=budget,
                cpu_seconds=900,
                max_file=64 * 1024**2,
            )
            budget.inspect(cost)
            result = json.loads(read_regular(work / "stdout.txt", 65536))
            if cost["exit_code"] != 0 or result != dict(
                status="passed", cryptographic_verification=True, qualified_backend=False
            ):
                raise ValueError("fresh composed Circle verification failed")
        rejected = binding_negatives(
            raw_enrollment,
            circle_inputs.ENROLLMENT_PIN,
            originals,
            policy,
            opened,
            expected,
            bundle,
        )
        if (
            len(jobs) != 3
            or len(rejected) != 16
            or sources != run_e2e.source_pins()
            or inventory != verify_llm.source_inventory()
        ):
            raise ValueError("incomplete composition or changed source")
        final = authority("after-composition")
        verdicts = [p["public"][99] for p in bundle["proofs"]]
        run_e2e.write_json(
            output / "result.json",
            dict(
                schema_id="hallmark.circle-composed-request-result/1",
                status="passed",
                backend="circle",
                prompt=opened.prompt,
                response=opened.response,
                context=opened.context(expected).hex(),
                model=expected.model.hex(),
                llm_verification=str(verified),
                classifier_run=str(classifier),
                llm_result_sha256=run_e2e.sha(verified / "result.json"),
                classifier_result_sha256=run_e2e.sha(classifier / "result.json"),
                llm_proofs_verified=23,
                residual_links=22,
                fresh_llm_verifications=2,
                classifier_proofs_verified=3,
                classifier_verdicts=verdicts,
                policy_release=all(verdicts),
                binding_rejections=rejected,
                parameter_authority=final,
                elapsed_seconds=time.monotonic() - started,
                qualified_backend=False,
                hiding_claim=False,
                hardware_claim="not-accepted",
                classifier_scope="prompt",
                safety_quality_claim=False,
                host_join=True,
                recursion=False,
            ),
        )
        print(
            "INTEGRITY PASS: 23 SASH + 3 Circle classifier proofs. "
            f"Results: {output / 'result.json'}",
            flush=True,
        )
        return output
    except BaseException as error:
        run_e2e.write_json(
            output / "failure.json",
            dict(
                schema_id="hallmark.circle-composed-failure/1",
                status="failed",
                error_type=type(error).__name__,
                elapsed_seconds=time.monotonic() - started,
            ),
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm-run", type=Path)
    parser.add_argument("--classifier-run", type=Path)
    parser.add_argument("--enrollment", type=Path, default=os.environ.get("LLM_ENROLLMENT"))
    parser.add_argument("--trusted-key", default=os.environ.get("LLM_TRUST_KEY"))
    args = parser.parse_args()
    run(
        llm_run=args.llm_run,
        classifier_run=args.classifier_run,
        enrollment=args.enrollment,
        trusted_key=args.trusted_key,
    )
