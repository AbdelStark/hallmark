"""Fresh Mac proof-only verification and host join for a retained Circle/LLM run.

No native LLM build or proof is reused as an acceptance flag. The caller supplies
its retained request hash and executable pins, independently of the remote job.
"""

import argparse
import copy
import json
import sys
import time
from pathlib import Path

import circle_backend as circle
import classifier_comparison as comparison
import composed_input
import verify_llm
from check_circle_engine import encode

from hallmark._gnark_probe import RunBudget, invoke, json_new, read_regular, write_new
from hallmark.openings import TranscriptOpening
from hallmark.policy import RequestExpectation

ROOT = Path(__file__).resolve().parents[1]
SOURCE_IDENTITY = "8567c911d686b13b09032b75e1fc041e6bbcc9407cb2755b60746112102b342a"


def joined_jobs(enrollment, pin, originals, old_policy, opening, expected, bundle):
    composed_input.check_request(opening, expected)
    return circle.check_bundle(enrollment, pin, originals, old_policy, opening, expected, bundle)


def binding_negatives(enrollment, pin, originals, policy, opening, expected, bundle):
    rejected = []
    for field in (
        "prompt",
        "response",
        "system_ref",
        "salt",
        "model",
        "nonce",
        "interaction_id",
        "policy",
    ):
        opened, request = opening, expected
        if field in ("prompt", "response", "system_ref", "salt"):
            value = getattr(opening, field)
            value = value + "!" if type(value) is str else bytes([value[0] ^ 1]) + value[1:]
            opened = opening.model_copy(update={field: value})
        else:
            value = getattr(expected, field)
            request = expected.model_copy(update={field: bytes([value[0] ^ 1]) + value[1:]})
        try:
            joined_jobs(enrollment, pin, originals, policy, opened, request, bundle)
        except ValueError:
            rejected.append(field)
        else:
            raise ValueError("changed composed request accepted: " + field)
    variants = []
    for index in range(3):
        changed = copy.deepcopy(bundle)
        changed["proofs"][index]["public"][32] ^= 1
        variants.append(("classifier-" + str(index), changed))
    variants += [
        ("missing", dict(bundle, proofs=bundle["proofs"][:-1])),
        ("duplicate", dict(bundle, proofs=[bundle["proofs"][0]] * 3)),
        ("reordered", dict(bundle, proofs=list(reversed(bundle["proofs"])))),
    ]
    for name, changed in variants:
        try:
            joined_jobs(enrollment, pin, originals, policy, opening, expected, changed)
        except ValueError:
            rejected.append(name)
        else:
            raise ValueError("changed composed roster accepted: " + name)
    return rejected


def fresh_llm(binary, binary_pin, proof_directory, output, budget):
    inventory = verify_llm.source_inventory()
    if verify_llm.verifier_identity(inventory).hex() != SOURCE_IDENTITY:
        raise ValueError("native verifier source identity changed")
    if comparison.sha(read_regular(binary, 128 * 1024**2)) != binary_pin:
        raise ValueError("caller LLM executable pin mismatch")
    sys.path.insert(0, str(ROOT / "research/probes/sash"))
    from check_response import TAGS, bundle
    from verify_response import check_provenance

    case = composed_input.case()
    expected = dict(
        prompt_ids=case["prompt_ids"], answer_ids=case["answer_ids"], roots=case["expected_roots"]
    )
    bundle(proof_directory, expected)
    work = output / "llm-verify"
    work.mkdir()
    write_new(work / "prompt.json", encode(expected["prompt_ids"]))
    write_new(work / "roots.json", encode(expected["roots"]))
    cost = invoke(
        binary,
        work,
        [
            "boundary-grid",
            "--dir",
            str(proof_directory),
            "--tags",
            ",".join(TAGS),
            "--verify",
            "--prompt",
            "prompt.json",
            "--verify-calibration",
            "roots.json",
            "--expect-model-roots",
            "roots.json",
            "--expect-pre-roots",
            "roots.json",
            "--expect-layer-links",
            "22",
            "--expect-token-links",
            "0",
        ],
        budget=budget,
        cpu_seconds=1800,
        max_file=64 * 1024**2,
        read_paths=(proof_directory,),
    )
    doc = json.loads(read_regular(work / "stdout.txt", 8 * 1024**2))
    check_provenance(
        doc["provenance"],
        dict(
            source_commit=case["source"]["revision"],
            source_dirty=True,
            shape_root_source="compiled-enrollment",
        ),
    )
    value = doc["result"]
    if not (
        cost["exit_code"] == 0
        and value["all_chain"] is True
        and value["verified"]["accepted"] == 23
        and value["shape_roots"]["matched"] == 23
        and value["gaps"] == []
        and value["failures"] == []
        and value["tokens"]["all"] is True
        and value["tokens"]["prompt_positions"] == 25
        and value["tokens"]["generated_positions"] == 7
        and value["links_passed"] == 22
    ):
        raise ValueError("fresh LLM cryptographic verification failed")
    if inventory != verify_llm.source_inventory():
        raise ValueError("native verifier sources changed during verification")
    return dict(
        cost=cost,
        proofs_verified=23,
        residual_links=22,
        source_identity=SOURCE_IDENTITY,
        binary_sha256=binary_pin,
        parameter_authority="checkout-case",
    )


def run(args):
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "runs"):
        raise ValueError("keep composition output under ignored runs")
    output.mkdir(mode=0o700)
    started = time.monotonic()
    budget = RunBudget(output, started + 900, 600, 600, 1800, 4, 4 * 1024**3, 256 * 1024**2)
    raw = read_regular(args.owner_request, 65536)
    if comparison.sha(raw) != args.expected_request:
        raise ValueError("caller request pin mismatch")
    request = json.loads(raw)
    opening = TranscriptOpening.decode(bytes.fromhex(request["opening_cbor_hex"]))
    expected = RequestExpectation.decode(bytes.fromhex(request["expected_cbor_hex"]))
    _, originals, old_policy, _, _ = comparison.admitted(
        args.classifier_run, args.expected_enrollment
    )
    enrollment = read_regular(args.campaign / "fresh-00-circle/caller-enrollment.json", 65536)
    bundle = json.loads(
        read_regular(args.campaign / "composition-00-circle/llm-response-bundle.json", 32 * 1024**2)
    )
    jobs = joined_jobs(
        enrollment,
        request["circle_enrollment_sha256"],
        originals,
        old_policy,
        opening,
        expected,
        bundle,
    )
    if [p["public"] for p in bundle["proofs"]] != request["public"]:
        raise ValueError("remote public inputs differ from caller freeze")
    if (
        comparison.sha(read_regular(args.circle_verifier, 128 * 1024**2))
        != args.expected_circle_verifier
    ):
        raise ValueError("caller Circle executable pin mismatch")
    json_new(
        output / "protocol.json",
        dict(
            owner_request_sha256=args.expected_request,
            enrollment_sha256=request["circle_enrollment_sha256"],
            circle_verifier=args.expected_circle_verifier,
            llm_verifier=args.expected_llm_verifier,
            llm_source_identity=SOURCE_IDENTITY,
            source_sha256=comparison.sha(Path(__file__).read_bytes()),
            host_join=True,
            recursion=False,
        ),
    )
    costs = []
    for job in jobs:
        work = output / ("circle-verify-" + job["kind"])
        work.mkdir()
        for name, raw in {
            "enrollment.json": job["enrollment"],
            "public.json": encode(job["public"]),
            "proof.json": job["proof"],
        }.items():
            write_new(work / name, raw)
        cost = invoke(
            args.circle_verifier,
            work,
            ["enrollment.json", job["enrollment_pin"], "public.json", "proof.json"],
            budget=budget,
            cpu_seconds=1800,
            max_file=64 * 1024**2,
        )
        report = json.loads(read_regular(work / "stdout.txt", 65536))
        if (
            cost["exit_code"] != 0
            or report.get("cryptographic_verification") is not True
            or report.get("qualified_backend") is not False
        ):
            raise ValueError("fresh Circle verifier rejected")
        costs.append(cost)
    llm = fresh_llm(
        args.llm_verifier, args.expected_llm_verifier, args.llm_proof_directory, output, budget
    )
    rejected = binding_negatives(
        enrollment,
        request["circle_enrollment_sha256"],
        originals,
        old_policy,
        opening,
        expected,
        bundle,
    )
    verdicts = [p["public"][99] for p in bundle["proofs"]]
    result = dict(
        schema_id="hallmark.circle-composed-result/1",
        status="passed",
        llm=llm,
        classifier_proofs_verified=3,
        classifier_costs=costs,
        binding_rejections=rejected,
        prompt=opening.prompt,
        response=opening.response,
        context=opening.context(expected).hex(),
        classifier_verdicts=verdicts,
        policy_release=all(v == 1 for v in verdicts),
        qualified_backend=False,
        hiding_claim=False,
        hardware_claim="not-accepted",
        host_join=True,
        recursion=False,
        fresh_llm_proving=False,
        fresh_verification=True,
        elapsed_seconds=time.monotonic() - started,
    )
    json_new(output / "result.json", result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in (
        "classifier-run",
        "owner-request",
        "campaign",
        "circle-verifier",
        "llm-verifier",
        "llm-proof-directory",
        "output",
    ):
        p.add_argument("--" + name, type=Path, required=True)
    for name in (
        "expected-enrollment",
        "expected-request",
        "expected-circle-verifier",
        "expected-llm-verifier",
    ):
        p.add_argument("--" + name, required=True)
    print(json.dumps(run(p.parse_args())))
