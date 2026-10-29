"""Prove three frozen requests with all three experimental Circle STARK circuits.

This is an acceptance workflow, not a repeated matched performance campaign.
Caller enrollment precedes proving; each proof uses a fresh proof-only verifier.
"""

import argparse
import copy
import json
import math
import platform
import shutil
import sys
import tempfile
import time
from pathlib import Path

import circle_backend as backend
import circle_inputs
import classifier_comparison as comparison
import trained_common_input as common
from check_circle_engine import encode

from hallmark._worker import RunBudget, invoke, json_new, read_regular, write_new

ROOT = Path(__file__).resolve().parents[1]


def trace_parity(kind, trace, row):
    if kind == "rule":
        return
    if kind == "mlp":
        actual = [w.value for group in ("accumulators", "hidden", "relu") for w in trace[group]]
        actual += [trace["output"].value, trace["score"].value]
    else:
        actual = [
            w.value
            for group in zip(
                trace["accumulators"], trace["convolution"], trace["relu"], strict=True
            )
            for w in group
        ]
        actual += [w.value for w in trace["pooled"]]
        head = (
            sum(w.value << i for i, w in enumerate(trace["head_twos"]))
            - trace["head_sign"].value * 2**32
        )
        if head % 256:
            raise ValueError("CNN head scaling differs from the frozen native export")
        actual += [head // 256, trace["score"][0].value]
    if actual != row["trace"]:
        raise ValueError("compiled/native intermediate parity failed: " + kind)


def run(
    prepared,
    original_pin,
    prover,
    prover_pin,
    verifier,
    verifier_pin,
    output,
    *,
    llm=False,
):
    for binary, pin in ((prover, prover_pin), (verifier, verifier_pin)):
        if comparison.sha(read_regular(binary, 128 * 1024**2)) != pin:
            raise ValueError("caller binary pin mismatch")
    output.mkdir(mode=0o700)
    output = output.resolve()
    started = time.monotonic()
    plan, corpus = comparison.documents()
    if shutil.disk_usage(ROOT).free < plan["limits"]["min_free_storage_bytes"]:
        raise ValueError("classifier acceptance requires at least 8 GiB free storage")
    budget = RunBudget(output, started + 1800, 600, 180, 1800, 4, 30 * 1024**3, 4 * 1024**3)
    source_paths = [
        *sorted((ROOT / "src/hallmark").glob("*.py")),
        *sorted((ROOT / "scripts").glob("*circle*.py")),
        ROOT / "scripts/classifier_comparison.py",
        ROOT / "scripts/trained_common_input.py",
        ROOT / "scripts/contextual_proof.py",
        ROOT / "scripts/trained_mlp.py",
        ROOT / "scripts/contextual_cnn.py",
        ROOT / "configs/circle-classifiers/plan.json",
        ROOT / "configs/circle-classifiers/corpus.json",
    ]
    source_hashes = {str(p.relative_to(ROOT)): comparison.sha(p.read_bytes()) for p in source_paths}
    backend_id, engine_sources = backend.source_identity()
    json_new(
        output / "protocol.json",
        dict(
            schema_id="hallmark.circle-classifier-acceptance-plan/1",
            sources=source_hashes,
            engine_sources=engine_sources,
            backend=backend_id.hex(),
            original_enrollment_pin=original_pin,
            preparation_kind="native-only",
            composed=llm,
            prover_sha256=prover_pin,
            verifier_sha256=verifier_pin,
            python=sys.version,
            platform=platform.platform(),
            command=sys.argv,
            benchmark_sample=False,
            seconds=1800,
            threads=4,
            max_rss_bytes=budget.max_rss_bytes,
            max_storage_bytes=budget.max_output_bytes,
            automatic_retries=0,
            comparison_plan_sha256=comparison.sha(comparison.encoded(plan)),
        ),
    )
    costs = []

    def attempt(name, binary, args, inputs, accept=True):
        if shutil.disk_usage(ROOT).free < plan["limits"]["min_free_storage_bytes"]:
            raise ValueError("free storage below the frozen stop boundary")
        work = output / name
        work.mkdir()
        for name, raw in inputs.items():
            write_new(work / name, raw)
        cost = invoke(binary, work, args, budget=budget, cpu_seconds=600, max_file=256 * 1024**2)
        costs.append(dict(name=work.name, **cost))
        budget.inspect(cost)
        if (cost["exit_code"] == 0) is not accept:
            raise ValueError("unexpected Circle worker outcome: " + work.name)
        if accept and binary == prover:
            cli = json.loads(read_regular(work / "stdout.txt", 65536))
            engine = json.loads(read_regular(work / "stderr.txt", 65536))
            if (
                cli.get("schema_id") != "hallmark.circle-cli-timing/1"
                or engine.get("schema_id") != "hallmark.circle-engine-timing/1"
            ):
                raise ValueError("missing Circle worker timing record")
            values = [cli["input_parse_seconds"], cli["serialize_write_seconds"]]
            values += (
                list(engine["stages_seconds"].values())
                if "stages_seconds" in engine
                else [engine["preprocessing_seconds"]]
            )
            if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
                raise ValueError("invalid Circle worker timing value")
            costs[-1]["cli_timing"] = cli
            costs[-1]["engine_timing"] = engine
        return work

    try:
        exported, originals, old_policy = circle_inputs.admit(prepared, original_pin)
        originals_by_case = {}
        if llm:
            import composed_input

            expected, opening = composed_input.request(old_policy)
            composed_input.check_request(opening, expected)
            originals_by_case["llm-response"] = (opening, expected)
            initial = common.evaluate(originals, old_policy, opening, expected)
            requested_cases = [dict(id="llm-response", verdicts=[r["public"][99] for r in initial])]
        else:
            requested_cases = corpus["requests"]
            for case in requested_cases:
                opening, expected = comparison.request(prepared / "requests", case["id"])
                originals_by_case[case["id"]] = (opening, expected)
        opening, expected = next(iter(originals_by_case.values()))
        baseline_rows = common.evaluate(originals, old_policy, opening, expected)
        programs, engines = {}, {}
        for kind, row in zip(backend.KINDS, baseline_rows, strict=True):
            circuit, trace = backend.compile_case(kind, row, opening.prompt.encode(), exported)
            trace_parity(kind, trace, row)
            if not circuit.check_witness():
                raise ValueError("baseline circuit constraints failed")
            programs[kind] = encode(circuit.program())
            work = attempt(
                "enroll-" + kind,
                prover,
                ["enroll", "program.json", "enrollment.json"],
                {"program.json": programs[kind]},
            )
            engines[kind] = read_regular(work / "enrollment.json", 65536)
            del circuit, trace
        enrollment = backend.enroll(engines, originals)
        enrollment_pin = comparison.sha(enrollment)
        if enrollment_pin != circle_inputs.ENROLLMENT_PIN:
            raise ValueError("Circle enrollment differs from the independently admitted default")
        write_new(output / "caller-enrollment.json", enrollment)
        json_new(output / "caller-pin.json", dict(sha256=enrollment_pin, before_proving=True))
        records, policy, _ = backend.resolve(enrollment, enrollment_pin, originals, old_policy)
        cases = {}
        for case in requested_cases:
            name = case["id"]
            opening, original_expected = originals_by_case[name]
            expected = backend.expected_request(original_expected, policy)
            rows = common.evaluate(records, policy, opening, expected)
            if [row["public"][99] for row in rows] != case["verdicts"]:
                raise ValueError("frozen native verdict mismatch")
            json_new(
                output / (name + "-request.json"),
                dict(
                    opening_cbor_hex=opening.encode().hex(),
                    expected_cbor_hex=expected.encode().hex(),
                ),
            )
            bundle = dict(schema_id="hallmark.circle-classifier-bundle/1", proofs=[])
            for kind, row in zip(backend.KINDS, rows, strict=True):
                begin = time.monotonic()
                circuit, trace = backend.compile_case(kind, row, opening.prompt.encode(), exported)
                trace_parity(kind, trace, row)
                if encode(circuit.program()) != programs[kind] or not circuit.check_witness():
                    raise ValueError("witness-dependent program or unsatisfied constraints")
                witness = encode(circuit.witness())
                external = encode([w.value for w in circuit.wires[: circuit.external]])
                witness_seconds = time.monotonic() - begin
                del circuit, trace
                work = attempt(
                    name + "-prove-" + kind,
                    prover,
                    [
                        "prove",
                        "program.json",
                        "enrollment.json",
                        "public.json",
                        "witness.json",
                        "proof.json",
                    ],
                    {
                        "program.json": programs[kind],
                        "enrollment.json": engines[kind],
                        "public.json": external,
                        "witness.json": witness,
                    },
                )
                proof = read_regular(work / "proof.json", 64 * 1024**2)
                bundle["proofs"].append(
                    dict(kind=kind, public=row["public"], proof_hex=proof.hex())
                )
                costs[-1]["python_witness_seconds"] = witness_seconds
                print(name + ": generated " + kind + " proof", flush=True)
            jobs = backend.check_bundle(
                enrollment, enrollment_pin, originals, old_policy, opening, expected, bundle
            )
            for job in jobs:
                args = ["enrollment.json", job["enrollment_pin"], "public.json", "proof.json"]
                inputs = {
                    "enrollment.json": job["enrollment"],
                    "public.json": encode(job["public"]),
                    "proof.json": job["proof"],
                }
                work = attempt(name + "-verify-" + job["kind"], verifier, args, inputs)
                report = json.loads(read_regular(work / "stdout.txt", 65536))
                if report != dict(
                    status="passed", cryptographic_verification=True, qualified_backend=False
                ):
                    raise ValueError("unexpected fresh verifier report")
                for index, label in (
                    (2, "context"),
                    (34, "classifier"),
                    (66, "digest"),
                    (98, "length"),
                    (99, "chunks"),
                    (100, "threshold"),
                    (102, "verdict"),
                ):
                    changed = job["public"].copy()
                    changed[index] = (
                        1 - changed[index] if label == "verdict" else changed[index] + 1
                    )
                    attempt(
                        name + "-reject-" + job["kind"] + "-" + label,
                        verifier,
                        args,
                        dict(inputs, **{"public.json": encode(changed)}),
                        False,
                    )
            json_new(output / (name + "-bundle.json"), bundle)
            cases[name] = (opening, expected, bundle)
        rejected = []
        for name, (opening, expected, bundle) in cases.items():
            for other, (_, _, wrong_bundle) in cases.items():
                if name == other:
                    continue
                for i, kind in enumerate(backend.KINDS):
                    altered = copy.deepcopy(bundle)
                    altered["proofs"][i] = wrong_bundle["proofs"][i]
                    try:
                        backend.check_bundle(
                            enrollment,
                            enrollment_pin,
                            originals,
                            old_policy,
                            opening,
                            expected,
                            altered,
                        )
                    except ValueError:
                        rejected.append(name + ":" + other + ":" + kind)
                    else:
                        raise ValueError("accepted cross-request classifier substitution")
        opening, expected, bundle = next(iter(cases.values()))
        for label, proofs in (
            ("missing", bundle["proofs"][:2]),
            ("duplicate", [bundle["proofs"][0]] * 3),
            ("reordered", list(reversed(bundle["proofs"]))),
        ):
            try:
                backend.check_bundle(
                    enrollment,
                    enrollment_pin,
                    originals,
                    old_policy,
                    opening,
                    expected,
                    dict(bundle, proofs=proofs),
                )
            except ValueError:
                pass
            else:
                raise ValueError("accepted invalid classifier roster: " + label)
        if (
            source_hashes
            != {str(p.relative_to(ROOT)): comparison.sha(p.read_bytes()) for p in source_paths}
            or engine_sources != backend.source_identity()[1]
        ):
            raise ValueError("source changed during classifier acceptance")
        binding_rejections = []
        if llm:
            from check_circle_composed import binding_negatives

            binding_rejections = binding_negatives(
                enrollment, enrollment_pin, originals, old_policy, opening, expected, bundle
            )
        result = dict(
            schema_id="hallmark.circle-classifier-acceptance/1",
            status="passed",
            fresh_proofs=len(cases) * 3,
            fresh_proof_only_verifications=len(cases) * 3,
            direct_public_mutations_rejected=len(cases) * 21,
            binding_rejections=binding_rejections,
            cases=[
                dict(
                    name=name,
                    verdicts=[p["public"][99] for p in b["proofs"]],
                    release=all(p["public"][99] == 1 for p in b["proofs"]),
                    proofs_verified=3,
                )
                for name, (_, _, b) in cases.items()
            ],
            cross_request_rejections=rejected,
            roster_rejections=3,
            intermediate_parity=True,
            caller_enrollment_sha256=enrollment_pin,
            costs=costs,
            elapsed_seconds=time.monotonic() - started,
            benchmark_sample=False,
            qualified_backend=False,
        )
        json_new(output / "result.json", result)
        return result
    except BaseException as error:
        json_new(
            output / "failure.json",
            dict(
                error=str(error),
                error_type=type(error).__name__,
                costs=costs,
                elapsed_seconds=time.monotonic() - started,
            ),
        )
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("classifier-run", "prover", "verifier"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--output", type=Path)
    for name in ("expected-preparation", "expected-prover", "expected-verifier"):
        parser.add_argument("--" + name, required=True)
    a = parser.parse_args()
    if a.output is None:
        (ROOT / "runs").mkdir(exist_ok=True)
        a.output = Path(tempfile.mkdtemp(prefix="circle-e2e-", dir=ROOT / "runs"))
        a.output.rmdir()
    print("Evidence: " + str(a.output.resolve()), flush=True)
    result = run(
        a.classifier_run.resolve(),
        a.expected_preparation,
        a.prover.resolve(),
        a.expected_prover,
        a.verifier.resolve(),
        a.expected_verifier,
        a.output,
    )
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("costs", "cross_request_rejections")}
        )
    )


if __name__ == "__main__":
    main()
