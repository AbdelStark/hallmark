"""Compose frozen trained classifier proofs on one opened request; no hardware acceptance."""

import argparse
import copy
import json
import platform
import subprocess
import time
from pathlib import Path

import composed_input
import run_contextual_proof as cnn
import run_trained_mlp as mlp
import trained_common_input as common
from check_gnark_encoder import assignment as encoder_assignment

from hallmark import _gnark_probe as worker
from hallmark._gnark_probe import (
    PinnedArtifact,
    RunBudget,
    digest,
    json_new,
    read_regular,
    write_new,
)
from hallmark.data import load_records
from hallmark.mlp_training import MlpQuantization
from hallmark.openings import TranscriptOpening
from hallmark.policy import RequestExpectation

MAX_FILE = 2 * 1024**3
MLP_QUANTIZATION = "f8090161455ee56cdcd73eaab44437efa3b278a786d7c246491da5f1e1431a9c"


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def run(
    binary, binary_pin, verifier_python, mlp_quantization, cnn_quantization, output, *, llm=False
):
    exports = {}
    for kind, path, pin in (
        ("mlp", mlp_quantization, MLP_QUANTIZATION),
        ("encoder", cnn_quantization, cnn.QUANTIZATION),
    ):
        raw = read_regular(path, 65536)
        if digest(raw) != pin:
            raise ValueError("selected quantization pin mismatch")
        exports[kind] = (
            mlp.export(MlpQuantization.model_validate_json(raw))
            if kind == "mlp"
            else cnn.export(json.loads(raw))
        )
    if llm:
        cases = {"llm-response": composed_input.case()["prompt"]}
    else:
        data = common.ROOT / "fixtures/contextual-scope-v2.jsonl"
        if digest(read_regular(data, 1024**2)) != cnn.DATASET:
            raise ValueError("case source changed")
        test = sorted(
            (r for r in load_records(data) if r.split == "test"), key=lambda r: r.record_id
        )
        benign, positive = test[:2]
        if benign.group_id != positive.group_id or (benign.label, positive.label) != (0, 1):
            raise ValueError("invalid fixed pair")
        cases = {
            "allow": benign.prompt,
            "cnn-block": positive.prompt,
            "rule-block": "BAD; " + benign.prompt,
        }
    circuits = {}

    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise ValueError("this controller requires the approved Mac host")
    if digest(read_regular(binary, 32 * 1024**2)) != binary_pin:
        raise ValueError("binary enrollment mismatch")
    prefix = Path(
        subprocess.check_output(
            [str(verifier_python), "-I", "-c", "import sys;print(sys.base_prefix)"],
            timeout=10,
            env={"PATH": "/usr/bin:/bin"},
            text=True,
        ).strip()
    )
    output.mkdir(mode=0o700)
    output = output.resolve()
    started = time.monotonic()
    budget = RunBudget(output, started + 7200, 900, 240, 3600, 4, 8 * 1024**3, 8 * 1024**3)
    sources = [
        Path(__file__),
        common.ROOT / "scripts/trained_common_input.py",
        common.ROOT / "scripts/composed_input.py",
        common.ROOT / "scripts/common_input.py",
        Path(mlp.__file__),
        Path(cnn.__file__),
        common.ROOT / "research/probes/py_ecc/verify.py",
        common.ROOT / "research/probes/py_ecc/verify_set.py",
        common.ROOT / "research/probes/py_ecc/check.py",
    ]
    json_new(
        output / "protocol.json",
        dict(
            schema_id="hallmark.trained-common-run/1",
            quantizations={"mlp": MLP_QUANTIZATION, "encoder": cnn.QUANTIZATION},
            dataset_sha256=cnn.DATASET,
            cases=cases,
            llm_case_sha256=composed_input.CASE_SHA256 if llm else None,
            capacity=common.CAPACITY,
            binary_sha256=binary_pin,
            verifier_python=str(verifier_python),
            verifier_python_sha256=digest(verifier_python.resolve().read_bytes()),
            sources={str(p.relative_to(common.ROOT)): digest(p.read_bytes()) for p in sources},
            seconds=7200,
            threads=4,
            max_rss_bytes=budget.max_rss_bytes,
            max_output_bytes=budget.max_output_bytes,
            worker_sha256=digest(Path(worker.__file__).read_bytes()),
            qualified_backend=False,
            hardware_claim="not-accepted",
        ),
    )
    costs = []

    def invoke(name, executable, args, inputs, produced, *, python=False):
        return worker.run_case(
            executable,
            output / name,
            args,
            inputs,
            produced,
            budget=budget,
            max_file=MAX_FILE,
            costs=costs,
            read_paths=(verifier_python.parent.parent, prefix, common.ROOT) if python else (),
        )

    def args(kind, action):
        return [
            {"rule": "scaled-rule-", "mlp": "trained-mlp-", "encoder": "contextual-"}[kind]
            + action,
            "96",
        ]

    try:
        setups, keys, models = {}, {}, {}
        for kind in common.KINDS:
            models[kind] = {} if kind == "rule" else {"model.json": encoded(exports[kind]["model"])}
            cost, _ = invoke(
                "setup-" + kind,
                binary,
                args(kind, "setup"),
                models[kind],
                ("circuit.r1cs", "pk.bin", "vk.bin"),
            )
            circuits[kind] = cost["files"]["circuit.r1cs"]["sha256"]
            setups[kind] = cost["files"]
            keys[kind] = read_regular(output / ("setup-" + kind) / "vk.bin", 65536)
        json_new(output / "circuit-pins.json", circuits)
        enrollment_raw = encoded(common.enroll(exports, keys, circuits))
        enrollment_pin = digest(enrollment_raw)
        write_new(output / "enrollment.json", enrollment_raw)
        # The enrollment record exists before any proof; subsequent code uses this external pin.
        json_new(output / "enrollment-pin.json", dict(sha256=enrollment_pin, before_proving=True))
        records, policy = common.resolve(enrollment_raw, enrollment_pin, exports, circuits)
        expectations, openings, bundles, results = {}, {}, {}, []
        grouped = {kind: dict(key_hex=keys[kind].hex(), records=[]) for kind in common.KINDS}
        for index, (name, prompt) in enumerate(cases.items()):
            expected = RequestExpectation(
                schema_id="hallmark/request-expectation/1",
                audience="local-common-input",
                nonce=bytes([index + 1]) * 32,
                interaction_id=bytes([index + 10]) * 32,
                model=b"m" * 32,
                policy=policy.identity(),
                continuity=None,
            )
            opening = TranscriptOpening(
                schema_id="hallmark/transcript-opening/1",
                system_ref=b"s" * 32,
                prompt=prompt,
                response="Synthetic response; no inference claim.",
                salt=bytes([index + 20]) * 32,
            )
            if llm:
                expected, opening = composed_input.request(policy)
                composed_input.check_request(opening, expected)
            expectations[name], openings[name] = expected, opening
            rows = common.evaluate(records, policy, opening, expected)
            verdicts = [row["public"][99] for row in rows]
            if not llm and (
                (name == "allow" and verdicts != [1, 1, 1])
                or (name == "cnn-block" and verdicts[2] != 0)
                or (name == "rule-block" and verdicts[0] != 0)
            ):
                raise ValueError("frozen decision roster failed")
            json_new(
                output / (name + "-request.json"),
                dict(
                    expected_cbor_hex=expected.encode().hex(),
                    opening_cbor_hex=opening.encode().hex(),
                    native_rows=rows,
                ),
            )
            proofs = []
            for kind, row in zip(common.KINDS, rows, strict=True):
                assignment = encoder_assignment(row, True)
                inputs = dict(models[kind], **{"assignment.txt": assignment})
                for filename in ("circuit.r1cs", "pk.bin"):
                    pin = setups[kind][filename]
                    inputs[filename] = PinnedArtifact(
                        output / ("setup-" + kind) / filename, pin["sha256"], pin["bytes"]
                    )
                invoke(name + "-" + kind, binary, args(kind, "prove"), inputs, ("proof.bin",))
                proofs.append(read_regular(output / (name + "-" + kind) / "proof.bin", 292))
            value = common.bundle(records, policy, opening, expected, rows, proofs)
            bundles[name] = value
            raw = encoded(value)
            write_new(output / (name + "-bundle.json"), raw)
            jobs = common.check_bundle(
                enrollment_raw, enrollment_pin, exports, circuits, opening, expected, raw
            )
            for kind, job in zip(common.KINDS, jobs, strict=True):
                grouped[kind]["records"].append(
                    dict(name=name, proof_hex=job["proof_hex"], public=job["public"])
                )
            job_raw = encoded(jobs)
            _, report = invoke(
                name + "-separate-verifier",
                verifier_python,
                [
                    "-I",
                    "-B",
                    str(common.ROOT / "research/probes/py_ecc/verify_set.py"),
                    "--jobs",
                    "jobs.json",
                    "--expected-jobs",
                    digest(job_raw),
                ],
                {"jobs.json": job_raw},
                (),
                python=True,
            )
            results.append(
                dict(
                    name=name,
                    proofs_verified=report["proofs_verified"],
                    release=value["release"],
                    verdicts=[row["public"][99] for row in rows],
                )
            )
            print(json.dumps(results[-1]), flush=True)
        rejected = []
        for target in cases:
            for source in cases:
                if target == source:
                    continue
                for family in range(3):
                    changed = dict(bundles[target], proofs=bundles[target]["proofs"].copy())
                    changed["proofs"][family] = bundles[source]["proofs"][family]
                    try:
                        common.check_bundle(
                            enrollment_raw,
                            enrollment_pin,
                            exports,
                            circuits,
                            openings[target],
                            expectations[target],
                            encoded(changed),
                        )
                    except ValueError:
                        rejected.append([target, source, family])
                    else:
                        raise AssertionError("cross-request proof accepted")
        binding_rejections = []
        if llm:
            name = "llm-response"
            for field, replacement in (
                ("prompt", openings[name].prompt + "!"),
                ("response", openings[name].response + "!"),
                ("system_ref", b"s" * 32),
                ("model", b"m" * 32),
                ("nonce", b"n" * 32),
                ("interaction_id", b"i" * 32),
                ("policy", b"p" * 32),
                ("salt", b"t" * 32),
            ):
                opening, expected = openings[name], expectations[name]
                if field in ("prompt", "response", "system_ref", "salt"):
                    opening = opening.model_copy(update={field: replacement})
                else:
                    expected = expected.model_copy(update={field: replacement})
                try:
                    composed_input.check_request(opening, expected)
                    common.check_bundle(
                        enrollment_raw,
                        enrollment_pin,
                        exports,
                        circuits,
                        opening,
                        expected,
                        encoded(bundles[name]),
                    )
                except ValueError:
                    binding_rejections.append(field)
                else:
                    raise AssertionError("changed composed request accepted: " + field)
            for family in range(3):
                changed = copy.deepcopy(bundles[name])
                changed["proofs"][family]["artifact_cbor_hex"] = "00"
                try:
                    common.check_bundle(
                        enrollment_raw,
                        enrollment_pin,
                        exports,
                        circuits,
                        openings[name],
                        expectations[name],
                        encoded(changed),
                    )
                except ValueError:
                    binding_rejections.append("classifier-" + str(family))
                else:
                    raise AssertionError("changed classifier evidence accepted")
        negative_reports = {}
        for kind, fixture in grouped.items():
            raw = encoded(fixture)
            _, report = invoke(
                "arithmetic-negatives-" + kind,
                verifier_python,
                [
                    "-I",
                    "-B",
                    str(common.ROOT / "research/probes/py_ecc/check.py"),
                    "--fixture",
                    "fixture.json",
                    "--expected-fixture",
                    digest(raw),
                    "--expected-key",
                    digest(keys[kind]),
                ],
                {"fixture.json": raw},
                (),
                python=True,
            )
            negative_reports[kind] = len(report["cases"])
        result = dict(
            schema_id="hallmark.trained-common-result/1",
            status="passed",
            qualified_backend=False,
            hardware_claim="not-accepted",
            enrollment_sha256=enrollment_pin,
            circuits=circuits,
            model_sha256={k: digest(encoded(v["model"])) for k, v in exports.items()},
            cases=results,
            cross_request_rejections=rejected,
            composed_binding_rejections=binding_rejections,
            arithmetic_cases=negative_reports,
            elapsed_seconds=time.monotonic() - started,
            retained_bytes=budget.inspect(),
            peak_worker_rss_bytes=max(c["max_rss_bytes"] for c in costs),
        )
        json_new(output / "result.json", result)
        return result
    except BaseException as error:
        json_new(
            output / "failure.json",
            dict(
                status="failed",
                error_type=type(error).__name__,
                qualified_backend=False,
                completed_workers=len(costs),
            ),
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--expected-binary", required=True)
    parser.add_argument("--verifier-python", type=Path, required=True)
    parser.add_argument("--mlp-quantization", type=Path, required=True)
    parser.add_argument("--cnn-quantization", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--llm", action="store_true", help="bind the fixed proved LLM response")
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.binary.absolute(),
                args.expected_binary,
                args.verifier_python.absolute(),
                args.mlp_quantization.absolute(),
                args.cnn_quantization.absolute(),
                args.output,
                llm=args.llm,
            )
        )
    )
