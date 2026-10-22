"""Prove freshly trained synthetic MLP exports through a dedicated lookup circuit."""

import argparse
import json
import platform
import re
import subprocess
import time
from pathlib import Path

from check_gnark_encoder import assignment
from check_gnark_input_scale import vector
from check_mlp_training import check as train_fixture
from run_common_input import encoded

from hallmark import _gnark_probe as worker
from hallmark._gnark_probe import (
    PinnedArtifact,
    RunBudget,
    digest,
    json_new,
    read_regular,
    write_new,
)
from hallmark.classifier_manifest import ClassifierManifest, InputProfile
from hallmark.integer_mlp import execute_mlp
from hallmark.mlp_export import compile_mlp
from hallmark.mlp_training import MlpQuantization
from hallmark.openings import TranscriptOpening, derive_input_salt
from hallmark.policy import RequestExpectation
from hallmark.receipts import ProofInputs
from hallmark.wire import H

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/mlp-training.json"
FIXTURE_PIN = (ROOT / "fixtures/mlp-training.sha256").read_text().strip()
CASES = {8: ("", "A", "B"), 1024: ("A" * 512, "B" * 512, "A" * 512 + "B" * 512)}
MAX_FILE = 2 * 1024**3


def export(quantization):
    q = quantization._validated()
    if len(q.weights.hidden_bias) != 4:
        raise ValueError("unsupported trained MLP width")
    profile = InputProfile(
        schema_id="hallmark/input-profile/1",
        encoding="utf8-bytes",
        tokenizer_files=(),
        prefix_tokens=(),
        suffix_tokens=(),
        chunk_size=512,
        overlap=0,
        max_units=32768,
        padding_id=0,
        padding_side="right",
    )
    program, arithmetic, weights, parameters = compile_mlp(
        q.weights,
        profile,
        first_fraction=q.first_fraction,
        hidden_fraction=0,
        last_fraction=q.last_fraction,
    )
    model = dict(
        schema_id="hallmark.trained-mlp-graph/1",
        program=program.identity().hex(),
        input_profile=profile.identity().hex(),
        arithmetic=arithmetic.identity().hex(),
        weights_sha256=digest(weights),
        first_fraction=q.first_fraction,
        last_fraction=q.last_fraction,
        **q.weights.model_dump(mode="json", exclude={"schema_id"}),
    )
    return dict(
        model=model,
        program=program,
        profile=profile,
        arithmetic=arithmetic,
        weights=weights,
        parameters=parameters,
    )


def classifier(exported, key, circuit_pin):
    if (
        type(key) is not bytes
        or len(key) != 5536
        or not isinstance(circuit_pin, str)
        or not re.fullmatch("[a-f0-9]{64}", circuit_pin)
    ):
        raise ValueError("unsupported key")
    return ClassifierManifest(
        schema_id="hallmark/classifier/1",
        kind="mlp",
        program=exported["program"].identity(),
        weights=exported["program"].weights.sha256,
        tokenizer=None,
        input_profile=exported["profile"].identity(),
        arithmetic=exported["arithmetic"].identity(),
        threshold=0,
        scope="prompt",
        labels=("fixture-benign", "fixture-marker"),
        backend=H("backend", "trained-mlp-research/1"),
        verifier_key=H("key", key),
        setup=H("setup", [digest(encoded(exported["model"])), circuit_pin, digest(key)]),
    )


def native_row(exported, c, capacity, prompt, index):
    if type(capacity) is not int or capacity not in CASES or len(prompt.encode()) > capacity:
        raise ValueError("proof capacity exceeded")
    expected = RequestExpectation(
        schema_id="hallmark/request-expectation/1",
        audience="local-trained-mlp",
        nonce=bytes([index + 1]) * 32,
        interaction_id=bytes([index + 10]) * 32,
        model=b"m" * 32,
        policy=H("policy", [c.identity(), 0]),
        continuity=None,
    )
    opening = TranscriptOpening(
        schema_id="hallmark/transcript-opening/1",
        system_ref=b"s" * 32,
        prompt=prompt,
        response="Synthetic response; no inference claim.",
        salt=b"t" * 32,
    )

    def execute(o):
        return execute_mlp(
            o,
            c,
            exported["program"],
            exported["profile"],
            exported["arithmetic"],
            weights=exported["weights"],
            parameters=exported["parameters"],
        )

    result = execute(opening)
    row = vector(32768, prompt.encode())
    for name in ("units", "unit_active"):
        row[name] = row[name][:capacity]
    row["positions"] = row["positions"][: capacity + 1]
    for name in ("encoded", "encoded_active"):
        row[name] = row[name][: 2 * capacity + 6]
    public = ProofInputs(
        schema_id="hallmark/proof-inputs/1",
        context=opening.context(expected),
        classifier=c.identity(),
        input_digest=result.input_digest,
        unit_count=result.unit_count,
        chunk_count=len(result.chunks),
        threshold=c.threshold,
        verdict=result.verdict,
    )
    public.validate_profile(c, exported["profile"])
    row["public"] = list(public.to_fields())
    row["salt"] = list(derive_input_salt(opening.salt, c.identity()))
    chunks = list(result.chunks)
    if len(chunks) < (capacity + 511) // 512:
        chunks += list(execute(opening.model_copy(update={"prompt": ""})).chunks)
    row["trace"] = [
        v
        for chunk in chunks
        for v in (
            *chunk.hidden_accumulators,
            *chunk.hidden,
            *chunk.activated,
            chunk.output_accumulator,
            chunk.score,
        )
    ]
    return row, dict(
        opening_cbor_hex=opening.encode().hex(),
        expected_cbor_hex=expected.encode().hex(),
        classifier_cbor_hex=c.encode().hex(),
        native_score=result.score,
        verdict=result.verdict,
    )


def run(binary, binary_pin, verifier_python, output):
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise ValueError("requires the approved Mac host")
    if digest(read_regular(binary, 32 * 1024**2)) != binary_pin:
        raise ValueError("binary pin mismatch")
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
    json_new(
        output / "protocol.json",
        dict(
            schema_id="hallmark.trained-mlp-run/1",
            binary_sha256=binary_pin,
            fixture_sha256=FIXTURE_PIN,
            cases={str(k): list(v) for k, v in CASES.items()},
            seeds=[17, 29, 43],
            threshold=0,
            seconds=7200,
            max_rss_bytes=budget.max_rss_bytes,
            max_output_bytes=budget.max_output_bytes,
            qualified_backend=False,
            controller_sha256=digest(Path(__file__).read_bytes()),
            verifier_sha256=digest((ROOT / "research/probes/py_ecc/check.py").read_bytes()),
        ),
    )
    costs, results = [], []

    def invoke(name, executable, args, inputs, produced, *, python=False):
        work = output / name
        work.mkdir(mode=0o700)
        for filename, value in inputs.items():
            if isinstance(value, PinnedArtifact):
                value.copy_to(work / filename, MAX_FILE)
            else:
                write_new(work / filename, value)
        original = worker.sandbox_profile
        if python:
            roots = (verifier_python.parent.parent, prefix, ROOT)
            worker.sandbox_profile = lambda binary, work: (
                original(binary, work)
                + (
                    "\n(allow file-read* file-map-executable "
                    + " ".join("(subpath " + json.dumps(str(p)) + ")" for p in roots)
                    + ")\n"
                )
            )
        try:
            cost = worker.invoke(
                executable,
                work,
                args,
                seconds=900,
                cpu_seconds=3600,
                max_file=MAX_FILE,
                budget=budget,
            )
        finally:
            worker.sandbox_profile = original
        costs.append(dict(name=name, **cost))
        if cost["exit_code"] != 0:
            raise ValueError("worker failed: " + name)
        report = json.loads(read_regular(work / "stdout.txt", 1024**2).splitlines()[-1])
        if report.get("status") != "passed":
            raise ValueError("worker failed: " + name)
        allowed = (
            set(inputs) | set(produced) | {"sandbox.sb", "plan.json", "stdout.txt", "stderr.txt"}
        )
        if set(cost["files"]) != allowed:
            raise ValueError("unexpected artifact inventory")
        for filename, value in inputs.items():
            pin = (
                dict(bytes=value.size, sha256=value.sha256)
                if isinstance(value, PinnedArtifact)
                else dict(bytes=len(value), sha256=digest(value))
            )
            if cost["files"][filename] != pin:
                raise ValueError("worker changed an input")
        return cost, report

    try:
        training = train_fixture(FIXTURE, FIXTURE_PIN, output / "training")
        budget.inspect()
        exports = {}
        for seed in (17, 29, 43):
            q = MlpQuantization.model_validate_json(
                read_regular(output / f"training/seed-{seed}/quantization.json", 1024**2)
            )
            exports[seed] = export(q)
            recorded = json.loads(read_regular(output / f"training/seed-{seed}/result.json", 65536))
            if exports[seed]["program"].identity().hex() != recorded["program"]:
                raise ValueError("trained export changed")
        # Every small trained model passes before any larger circuit is attempted.
        for capacity in (8, 1024):
            for seed in (17, 29, 43):
                e = exports[seed]
                model = encoded(e["model"])
                tag = f"s{seed}-n{capacity}"
                if capacity == 1024:
                    preflight = classifier(e, bytes(5536), "0" * 64)
                    decisions = [
                        native_row(e, preflight, capacity, p, i)[1]
                        for i, p in enumerate(CASES[capacity])
                    ]
                    json_new(
                        output / (tag + "-native-preflight.json"),
                        dict(
                            software_only=True,
                            scores=[r["native_score"] for r in decisions],
                            verdicts=[r["verdict"] for r in decisions],
                        ),
                    )
                    if {r["verdict"] for r in decisions} != {False, True}:
                        raise ValueError(
                            "trained fixture has no decision contrast at fixed threshold"
                        )
                setup, _ = invoke(
                    tag + "-setup",
                    binary,
                    ["trained-mlp-setup", str(capacity)],
                    {"model.json": model},
                    ("circuit.r1cs", "pk.bin", "vk.bin"),
                )

                def artifact(name, setup=setup, tag=tag):
                    pin = setup["files"][name]
                    return PinnedArtifact(
                        output / (tag + "-setup") / name, pin["sha256"], pin["bytes"]
                    )

                key = read_regular(output / (tag + "-setup") / "vk.bin", 65536)
                c = classifier(e, key, setup["files"]["circuit.r1cs"]["sha256"])
                enrollment = dict(
                    model_sha256=digest(model),
                    key_sha256=digest(key),
                    circuit=setup["files"]["circuit.r1cs"],
                    classifier_cbor_hex=c.encode().hex(),
                )
                json_new(output / (tag + "-enrollment.json"), enrollment)
                fixtures, rows, requests, roster = [], [], [], []
                inputs = {
                    "model.json": model,
                    "circuit.r1cs": artifact("circuit.r1cs"),
                    "pk.bin": artifact("pk.bin"),
                }
                for index, prompt in enumerate(CASES[capacity]):
                    row, request = native_row(e, c, capacity, prompt, index)
                    rows.append(row)
                    requests.append(request)
                    name = f"case-{index}"
                    json_new(
                        output / (tag + "-" + name + "-request.json"),
                        dict(**request, native_row=row),
                    )
                    inputs[name + ".txt"] = assignment(row, True)
                    roster.append(dict(name=name, valid=True))
                    results.append(
                        dict(
                            seed=seed,
                            capacity=capacity,
                            case=index,
                            score=request["native_score"],
                            verdict=request["verdict"],
                        )
                    )
                if capacity == 1024 and {r["verdict"] for r in requests} != {False, True}:
                    raise ValueError("trained fixture has no decision contrast at fixed threshold")
                negative = []
                for label, field, offset in (
                    ("last-unit", "units", capacity - 1),
                    ("hidden", "trace", 4),
                    ("threshold", "public", 98),
                ):
                    changed = {k: list(v) for k, v in rows[-1].items()}
                    if field == "public":
                        changed[field][offset] = (
                            2**31 + requests[-1]["native_score"] + int(not requests[-1]["verdict"])
                        )
                    else:
                        changed[field][offset] ^= 1
                    name = "reject-" + label
                    inputs[name + ".txt"] = assignment(changed, True)
                    roster.append(dict(name=name, valid=False))
                    negative.append(label)
                inputs["cases.json"] = encoded(roster)
                produced = [r["name"] + ".json" for r in roster]
                produced += [r["name"] + ".proof" for r in roster if r["valid"]]
                invoke(
                    tag + "-batch", binary, ["trained-mlp-batch", str(capacity)], inputs, produced
                )
                for index, row in enumerate(rows):
                    proof = read_regular(output / (tag + "-batch") / f"case-{index}.proof", 292)
                    if len(proof) != 292:
                        raise ValueError("unexpected proof format")
                    fixtures.append(
                        dict(name=str(index), proof_hex=proof.hex(), public=row["public"])
                    )
                raw = encoded(dict(key_hex=key.hex(), records=fixtures))
                _, report = invoke(
                    tag + "-independent",
                    verifier_python,
                    [
                        "-I",
                        "-B",
                        str(ROOT / "research/probes/py_ecc/check.py"),
                        "--fixture",
                        "fixture.json",
                        "--expected-fixture",
                        digest(raw),
                        "--expected-key",
                        digest(key),
                    ],
                    {"fixture.json": raw},
                    (),
                    python=True,
                )
                completed = dict(
                    seed=seed,
                    capacity=capacity,
                    actual_proofs=len(fixtures),
                    arithmetic_cases=len(report["cases"]),
                    witness_rejections=negative,
                )
                json_new(output / (tag + "-result.json"), completed)
                print(json.dumps(completed), flush=True)
        result = dict(
            status="passed",
            qualified_backend=False,
            synthetic_only=True,
            training_seeds=training["seeds"],
            decisions=results,
            workers=len(costs),
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
                completed_workers=len(costs),
                qualified_backend=False,
            ),
        )
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--expected-binary", required=True)
    parser.add_argument("--verifier-python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            run(
                args.binary.resolve(),
                args.expected_binary,
                args.verifier_python.absolute(),
                args.output,
            )
        )
    )


if __name__ == "__main__":
    main()
