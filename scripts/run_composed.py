"""Prove classifier decisions over the exact opened, proved TinyLlama request."""

import argparse
import shutil
import tempfile
import time
from pathlib import Path

import composed_input
import run_e2e
import run_llm_e2e
import run_trained_common
import verify_llm

from hallmark._gnark_probe import read_regular
from hallmark.integrity import parse_json
from hallmark.openings import TranscriptOpening
from hallmark.policy import RequestExpectation

ROOT = Path(__file__).resolve().parents[1]
CLASSIFIER_BINARIES = {
    "376c9aea1c28e5656099b8248d449323268670d77a67196f501301ab8d80a377",
    "ad40c57319d370d16e9f75b19f98291ae748d661b7c509375e7f7997a597e43a",
}
BINDINGS = [
    "prompt",
    "response",
    "system_ref",
    "model",
    "nonce",
    "interaction_id",
    "policy",
    "salt",
    "classifier-0",
    "classifier-1",
    "classifier-2",
]


def classifier_inputs(directory):
    """Retained preparation is caller-owned; no saved proof verdict is consumed."""
    run_e2e.check_training(directory)
    binary = directory / "probe"
    binary_pin = run_e2e.sha(binary)
    if binary_pin not in CLASSIFIER_BINARIES:
        raise ValueError("composed classifier binary pin mismatch")
    return (
        binary,
        binary_pin,
        directory / "verifier-env/bin/python",
        directory / "mlp-training/seed-17/quantization.json",
        directory / "cnn-training/17/quantization.json",
    )


def check_classifiers(output):
    report = parse_json(read_regular(output / "result.json", 1024**2).decode())
    request = parse_json(read_regular(output / "llm-response-request.json", 1024**2).decode())
    opening = TranscriptOpening.decode(bytes.fromhex(request["opening_cbor_hex"]))
    expected = RequestExpectation.decode(bytes.fromhex(request["expected_cbor_hex"]))
    composed_input.check_request(opening, expected)
    cases = report["cases"]
    if (
        report["schema_id"] != "hallmark.trained-common-result/1"
        or report["status"] != "passed"
        or report["qualified_backend"] is not False
        or report["hardware_claim"] != "not-accepted"
        or report["composed_binding_rejections"] != BINDINGS
        or report["arithmetic_cases"] != dict(rule=133, mlp=133, encoder=133)
        or len(cases) != 1
        or cases[0]["name"] != "llm-response"
        or cases[0]["proofs_verified"] != 3
        or len(cases[0]["verdicts"]) != 3
        or any(type(v) is not int or v not in (0, 1) for v in cases[0]["verdicts"])
        or cases[0]["release"] is not all(v == 1 for v in cases[0]["verdicts"])
    ):
        raise ValueError("incomplete composed classifier checks")
    return report, opening, expected


def run(*, llm_run=None, classifier_run=None):
    case = composed_input.case()
    if shutil.disk_usage(ROOT).free < 32 * 1024**3:
        raise ValueError("composed workflow requires at least 32 GiB free storage")
    inputs = classifier_inputs(classifier_run.resolve()) if classifier_run is not None else None
    (ROOT / "runs").mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="composed-", dir=ROOT / "runs"))
    print(f"Composed evidence: {output}", flush=True)
    started = time.monotonic()
    pins = run_e2e.source_pins()
    run_e2e.write_json(
        output / "protocol.json",
        dict(
            schema_id="hallmark.composed-request-protocol/1",
            sources=pins,
            llm_case_sha256=composed_input.CASE_SHA256,
            fresh_llm_proving=llm_run is None,
            fresh_classifier_preparation=classifier_run is None,
            fresh_classifier_setups=True,
            fresh_classifier_proofs=True,
            hardware_claim="not-accepted",
            qualified_backend=False,
        ),
    )
    try:
        if llm_run is None:
            llm_run = run_llm_e2e.run("2.10")
        verified = verify_llm.run(llm_run.resolve())
        llm = parse_json(read_regular(verified / "result.json", 1024**2).decode())
        if (
            llm["passed"] is not True
            or llm["proofs"] != 23
            or llm["residual_links"] != 22
            or llm["fresh_verifications"] != 2
            or llm["response"] != case["response"]
        ):
            raise ValueError("incomplete fresh LLM verification")
        if inputs is None:
            classifier_run = run_e2e.run()
            inputs = classifier_inputs(classifier_run)
        run_trained_common.run(*inputs, output / "classifiers", llm=True)
        classifiers, opening, expected = check_classifiers(output / "classifiers")
        if run_e2e.source_pins() != pins:
            raise ValueError("composed pipeline source changed")
        run_e2e.write_json(
            output / "result.json",
            dict(
                schema_id="hallmark.composed-request-result/1",
                status="passed",
                prompt=opening.prompt,
                response=opening.response,
                context=opening.context(expected).hex(),
                model=expected.model.hex(),
                llm_case_sha256=composed_input.CASE_SHA256,
                llm_verification=str(verified),
                llm_result_sha256=run_e2e.sha(verified / "result.json"),
                classifier_result_sha256=run_e2e.sha(output / "classifiers/result.json"),
                llm_proofs_verified=23,
                classifier_proofs_verified=3,
                classifier_verdicts=classifiers["cases"][0]["verdicts"],
                policy_release=classifiers["cases"][0]["release"],
                binding_rejections=BINDINGS,
                arithmetic_cases=399,
                elapsed_seconds=time.monotonic() - started,
                qualified_backend=False,
                hardware_claim="not-accepted",
                hiding_claim=False,
                classifier_scope="prompt",
                safety_quality_claim=False,
            ),
        )
        print(
            "INTEGRITY PASS: 23 LLM proofs and 3 classifier proofs. "
            f"Synthetic policy release={classifiers['cases'][0]['release']}. "
            f"Results: {output / 'result.json'}"
        )
        return output
    except BaseException as error:
        run_e2e.write_json(
            output / "failure.json",
            dict(
                schema_id="hallmark.composed-request-failure/1",
                error_type=type(error).__name__,
                elapsed_seconds=time.monotonic() - started,
            ),
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm-run", type=Path, help="retained proof archive; freshly reverified")
    parser.add_argument("--classifier-run", type=Path, help="caller-owned make e2e preparation")
    args = parser.parse_args()
    run(llm_run=args.llm_run, classifier_run=args.classifier_run)
