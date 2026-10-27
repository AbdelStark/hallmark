"""Maximum-length proofs, invalid witnesses and fixed-program conformance.

Expected invalid-witness failures must reach STWO's constraint check, rather
than merely fail an input parser or a native inference preflight.
"""

import argparse
import json
import time
from pathlib import Path

import circle_backend as backend
import classifier_comparison as comparison
import trained_common_input as common
from check_circle_engine import encode
from run_circle_classifiers import trace_parity

from hallmark._gnark_probe import RunBudget, invoke, json_new, read_regular, write_new

ROOT = Path(__file__).resolve().parents[1]


def run(prepared, original_pin, circle_run, circle_pin, prover, verifier, output):
    protocol = json.loads(read_regular(circle_run / "protocol.json", 1024**2))
    for binary, key in ((prover, "prover_sha256"), (verifier, "verifier_sha256")):
        if comparison.sha(read_regular(binary, 128 * 1024**2)) != protocol[key]:
            raise ValueError("acceptance binary pin mismatch")
    exported, originals, old_policy, _, _ = comparison.admitted(prepared, original_pin)
    enrollment = read_regular(circle_run / "caller-enrollment.json", 65536)
    records, policy, engines = backend.resolve(enrollment, circle_pin, originals, old_policy)
    opening, original_expected = comparison.request(prepared / "proofs", "allow")
    expected = backend.expected_request(original_expected, policy)
    _, corpus = comparison.documents()
    output.mkdir(mode=0o700)
    output = output.resolve()
    started = time.monotonic()
    budget = RunBudget(output, started + 1800, 600, 180, 1800, 4, 30 * 1024**3, 1024**3)
    identity, sources = backend.source_identity()
    json_new(
        output / "protocol.json",
        dict(
            schema_id="hallmark.circle-constraint-conformance-plan/1",
            backend=identity.hex(),
            sources=sources,
            script_sha256=comparison.sha(Path(__file__).read_bytes()),
            original_enrollment=original_pin,
            circle_enrollment=circle_pin,
            prover_sha256=protocol["prover_sha256"],
            verifier_sha256=protocol["verifier_sha256"],
            seconds=1800,
            threads=4,
            max_rss_bytes=budget.max_rss_bytes,
            max_storage_bytes=budget.max_output_bytes,
            automatic_retries=0,
            benchmark_sample=False,
        ),
    )
    costs, boundary_results = [], []

    def attempt(name, binary, args, inputs, reason=None, read_paths=()):
        work = output / name
        work.mkdir()
        for name, raw in inputs.items():
            write_new(work / name, raw)
        cost = invoke(
            binary,
            work,
            args,
            budget=budget,
            cpu_seconds=600,
            max_file=256 * 1024**2,
            read_paths=read_paths,
        )
        costs.append(dict(name=work.name, **cost))
        budget.inspect(cost)
        if reason is None:
            if cost["exit_code"] != 0:
                raise ValueError("honest conformance worker failed: " + work.name)
        elif (
            cost["exit_code"] == 0
            or reason not in read_regular(work / "stderr.txt", 65536).decode()
        ):
            raise ValueError("invalid witness did not reach expected rejection: " + work.name)
        return work

    try:
        for case in corpus["input_boundaries"]:
            prompt = case["unit"] * case["repeat"] + case["suffix"]
            changed = opening.model_copy(update=dict(prompt=prompt))
            if not case["accepted"]:
                try:
                    common.evaluate(records, policy, changed, expected)
                except ValueError:
                    boundary_results.append(dict(id=case["id"], rejected=True))
                    continue
                raise ValueError("over-capacity input admitted")
            rows = common.evaluate(records, policy, changed, expected)
            for kind, row in zip(backend.KINDS, rows, strict=True):
                c, trace = backend.compile_case(kind, row, prompt.encode(), exported)
                engine = json.loads(engines[kind])
                if (
                    comparison.sha(encode(c.program())) != engine["program_sha256"]
                    or not c.check_witness()
                ):
                    raise ValueError("witness-dependent program or failed boundary: " + case["id"])
                trace_parity(kind, trace, row)
                del c, trace
            boundary_results.append(
                dict(id=case["id"], all_three_constraints_and_native_parity=True)
            )
            print("Boundary passed: " + case["id"], flush=True)
        maximum = opening.model_copy(update=dict(prompt="x" * 93 + "BAD"))
        rows = common.evaluate(records, policy, maximum, expected)
        invalid = []
        for kind, row in zip(backend.KINDS, rows, strict=True):
            c, trace = backend.compile_case(kind, row, maximum.prompt.encode(), exported)
            trace_parity(kind, trace, row)
            values = c.witness()
            public = [w.value for w in c.wires[: c.external]]
            program = (circle_run / ("enroll-" + kind) / "program.json").resolve()
            if comparison.sha(read_regular(program, 256 * 1024**2)) != comparison.sha(
                encode(c.program())
            ):
                raise ValueError("maximum input changed the enrolled program")
            args = [
                "prove",
                str(program),
                "enrollment.json",
                "public.json",
                "witness.json",
                "proof.json",
            ]
            inputs = {
                "enrollment.json": engines[kind],
                "public.json": encode(public),
                "witness.json": encode(values),
            }
            honest = attempt(
                "maximum-prove-" + kind, prover, args, inputs, read_paths=(program.parent,)
            )
            proof = read_regular(honest / "proof.json", 64 * 1024**2)
            attempt(
                "maximum-verify-" + kind,
                verifier,
                ["enrollment.json", comparison.sha(engines[kind]), "public.json", "proof.json"],
                {
                    "enrollment.json": engines[kind],
                    "public.json": encode(public),
                    "proof.json": proof,
                },
            )
            private_bytes = [
                i
                for i, g in enumerate(c.gates, c.external)
                if g["mode"] == 0 and c.wires[i].low == 0 and c.wires[i].high == 255
            ]
            targets = {
                "late-input": private_bytes[95],
                "salt": private_bytes[-32],
                "encoded-padding": private_bytes[96 + 197],
                "active-mask": private_bytes[95] + 96,
                "verdict": 102,
            }
            if kind == "mlp":
                targets.update(
                    count=trace["counts"][ord("x")].index,
                    rounded_hidden=trace["hidden"][0].index,
                    score=trace["score"].index,
                )
            elif kind == "encoder":
                targets.update(
                    late_convolution=trace["convolution"][-1].index,
                    pooled_maximum=trace["pooled"][0].index,
                    head_bit=trace["head_twos"][0].index,
                )
            for label, index in targets.items():
                mutated = values.copy()
                mutated[index] = (mutated[index] + 1) % (2**31 - 1)
                if label in ("verdict", "active-mask", "head_bit"):
                    mutated[index] = 1 - values[index]
                elif label in ("late-input", "salt", "encoded-padding"):
                    mutated[index] = values[index] ^ 1
                if c.check_witness(mutated):
                    raise ValueError("negative witness still satisfies fixed gates: " + label)
                supplied = dict(
                    inputs,
                    **{
                        "witness.json": encode(mutated),
                        "public.json": encode(mutated[: c.external]),
                    },
                )
                attempt(
                    kind + "-reject-" + label,
                    prover,
                    args,
                    supplied,
                    "ConstraintsNotSatisfied",
                    (program.parent,),
                )
                invalid.append(
                    dict(kind=kind, mutation=label, rejection="STWO ConstraintsNotSatisfied")
                )
                print("Constraint rejection: " + kind + "/" + label, flush=True)
            if kind == "encoder":
                altered = c.program()
                # The last convolution accumulator includes an actual nonzero dense coefficient.
                gate = altered["gates"][trace["accumulators"][-1].index - c.external]
                if gate["qb"] == 0:
                    raise ValueError("dense-edge negative lacks its expected coefficient")
                gate["qb"] = 0
                changed_inputs = dict(inputs, **{"program.json": encode(altered)})
                changed_args = ["prove", "program.json", *args[2:]]
                attempt(
                    "encoder-reject-omitted-dense-edge",
                    prover,
                    changed_args,
                    changed_inputs,
                    "program pin mismatch",
                )
                invalid.append(
                    dict(
                        kind=kind,
                        mutation="omitted-dense-edge",
                        rejection="caller-enrolled program pin",
                    )
                )
            del c, trace, values
        if backend.source_identity() != (identity, sources):
            raise ValueError("backend sources changed during conformance")
        result = dict(
            schema_id="hallmark.circle-constraint-conformance/1",
            status="passed",
            boundaries=boundary_results,
            maximum_input_fresh_proofs=3,
            maximum_input_fresh_verifications=3,
            invalid_witnesses=invalid,
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
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("classifier-run", "circle-run", "prover", "verifier", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    for name in ("expected-enrollment", "expected-circle-enrollment"):
        p.add_argument("--" + name, required=True)
    a = p.parse_args()
    result = run(
        a.classifier_run.resolve(),
        a.expected_enrollment,
        a.circle_run.resolve(),
        a.expected_circle_enrollment,
        a.prover.resolve(),
        a.verifier.resolve(),
        a.output,
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in ("costs", "boundaries", "invalid_witnesses")
            }
        )
    )


if __name__ == "__main__":
    main()
