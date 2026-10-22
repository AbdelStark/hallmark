"""Prove the preselected contextual CNN; dedicated relation, no VM or qualification."""

import argparse
import json
import platform
import subprocess
import time
from fractions import Fraction
from pathlib import Path

import contextual_cnn as cnn
from check_gnark_encoder import assignment
from check_gnark_input_scale import vector
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
from hallmark.data import load_records
from hallmark.integer_encoder import execute_encoder
from hallmark.openings import TranscriptOpening, derive_input_salt
from hallmark.policy import RequestExpectation
from hallmark.receipts import ProofInputs
from hallmark.wire import H

ROOT = Path(__file__).resolve().parents[1]
QUANTIZATION = "8de31ae0215178f5c74aa43e58dd63511bc3b6a881c2045cc96def9e149b8f0b"
PROGRAM = "ef90bf45331d2f9287090ab48c4eb9166a7d9c712efc1c2f5cf92b797640cc16"
DATASET = "c28358a88348f954449203d72eb723a8a7b8c2e1faed3d390cce345706c11e67"
THRESHOLD = -3733
MAX_FILE = 2 * 1024**3


def export(q):
    e = cnn.export(q, threshold=THRESHOLD)
    if len(q["values"]["bias"]) != 32:
        raise ValueError("proof requires the 32-channel CNN")
    p, f = q["values"], q["fractions"]
    e["model"] = dict(
        schema_id="hallmark.contextual-cnn-graph/1",
        program=e["program"].identity().hex(),
        input_profile=e["profile"].identity().hex(),
        arithmetic=e["arithmetic"].identity().hex(),
        weights_sha256=digest(e["weights"]),
        embedding_fraction=f["embedding"],
        kernel_fraction=f["kernel"],
        head_fraction=f["head"],
        embedding=p["embedding"],
        kernel=p["kernel"],
        bias=p["bias"],
        head=p["head"][0],
        output_bias=p["out"][0],
    )
    return e


def classifier(e, key, circuit_pin):
    if len(key) != 5536 or len(bytes.fromhex(circuit_pin)) != 32:
        raise ValueError("invalid enrollment")
    return e["classifier"].model_copy(
        update=dict(
            backend=H("backend", "contextual-cnn-research/1"),
            verifier_key=H("key", key),
            setup=H("setup", [digest(encoded(e["model"])), circuit_pin, digest(key)]),
        )
    )


def native_row(e, c, capacity, prompt, index):
    if type(capacity) is not int or capacity not in (8, 96) or len(prompt.encode()) > capacity:
        raise ValueError("proof capacity exceeded")
    expected = RequestExpectation(
        schema_id="hallmark/request-expectation/1",
        audience="local-contextual-cnn",
        nonce=bytes([index + 1]) * 32,
        interaction_id=bytes([index + 10]) * 32,
        model=b"m" * 32,
        policy=H("policy", [c.identity(), c.threshold]),
        continuity=None,
    )
    opening = TranscriptOpening(
        schema_id="hallmark/transcript-opening/1",
        system_ref=b"s" * 32,
        prompt=prompt,
        response="Synthetic response; no inference provenance claim.",
        salt=b"t" * 32,
    )
    result = execute_encoder(
        opening,
        c,
        e["program"],
        e["profile"],
        e["arithmetic"],
        **{k: e[k] for k in ("weights", "tokenizer", "parameters")},
    )
    public = ProofInputs(
        schema_id="hallmark/proof-inputs/1",
        context=opening.context(expected),
        classifier=c.identity(),
        input_digest=result.input_digest,
        unit_count=result.unit_count,
        chunk_count=1,
        threshold=c.threshold,
        verdict=result.verdict,
    )
    public.validate_profile(c, e["profile"])
    row = vector(256, prompt.encode())
    for field in ("units", "unit_active"):
        row[field] = row[field][:capacity]
    row["positions"] = row["positions"][: capacity + 1]
    for field in ("encoded", "encoded_active"):
        row[field] = row[field][: 2 * capacity + 6]
    row["public"] = list(public.to_fields())
    row["salt"] = list(derive_input_salt(opening.salt, c.identity()))
    tensors = result.chunks[0].tensors
    trace, model = [], e["model"]
    for pos in range(96):
        values = tensors["flat"][pos * 96 : (pos + 1) * 96]
        for h in range(32):
            acc = model["bias"][h] + sum(
                x * w for x, w in zip(values, model["kernel"][h], strict=True)
            )
            z = tensors["convolution"][pos * 32 + h]
            assert z == round(
                Fraction(acc, 2 ** (model["embedding_fraction"] + model["kernel_fraction"])) * 256
            )
            trace.extend((acc, z, tensors["relu"][pos * 32 + h]))
    pooled = tensors["pooled"]
    output = model["output_bias"] + sum(x * w for x, w in zip(pooled, model["head"], strict=True))
    assert result.score == round(Fraction(output, 2 ** model["head_fraction"]))
    row["trace"] = trace + list(pooled) + [output, result.score]
    return row, dict(
        expected_cbor_hex=expected.encode().hex(),
        opening_cbor_hex=opening.encode().hex(),
        public_cbor_hex=public.encode().hex(),
        native_score=result.score,
        verdict=result.verdict,
    )


def mutations(e, c, capacity, prompt, row):
    roster = {}
    for name, field, offset in (
        ("late-unit", "units", capacity - 1),
        ("mask", "unit_active", capacity - 1),
        ("convolution", "trace", 0),
        ("rounded", "trace", 1),
        ("relu", "trace", 2),
        ("pooled", "trace", 96 * 32 * 3),
        ("score", "trace", -1),
        ("threshold", "public", 98),
    ):
        changed = {k: list(v) for k, v in row.items()}
        if name == "threshold":
            changed[field][offset] = 2**31 + row["trace"][-1] + int(not row["public"][-1])
        else:
            changed[field][offset] ^= 1
        roster[name] = changed
    altered = ("B" if prompt[:1] != "B" else "A") + prompt[1:]
    fresh, _ = native_row(e, c, capacity, altered, 2)
    if fresh["trace"] == row["trace"]:
        raise ValueError("changed input has no trace contrast")
    fresh["trace"] = row["trace"]
    roster["reencoded-input-stale-trace"] = fresh
    return roster


def run(binary, binary_pin, verifier_python, quantization, output):
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise ValueError("requires admitted Mac host")
    binary_raw = read_regular(binary, 32 * 1024**2)
    q_raw = read_regular(quantization, 65536)
    if digest(binary_raw) != binary_pin or digest(q_raw) != QUANTIZATION:
        raise ValueError("binary or selected model pin mismatch")
    e = export(json.loads(q_raw))
    if e["program"].identity().hex() != PROGRAM:
        raise ValueError("selected program changed")
    data = ROOT / "fixtures/contextual-scope-v2.jsonl"
    if digest(read_regular(data, 1024**2)) != DATASET:
        raise ValueError("case source changed")
    test = sorted((r for r in load_records(data) if r.split == "test"), key=lambda r: r.record_id)
    benign, positive = test[:2]
    if benign.group_id != positive.group_id or (benign.label, positive.label) != (0, 1):
        raise ValueError("invalid fixed case pair")
    cases = {
        8: ("", "\x00", "é"),
        96: (
            benign.prompt,
            positive.prompt,
            " " * (96 - len(positive.prompt.encode())) + positive.prompt,
        ),
    }
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
    binary = output / "probe"
    write_new(binary, binary_raw, 0o500)
    write_new(output / "quantization.json", q_raw)
    started = time.monotonic()
    budget = RunBudget(output, started + 7200, 900, 240, 3600, 4, 8 * 1024**3, 8 * 1024**3)
    json_new(
        output / "protocol.json",
        dict(
            schema_id="hallmark.contextual-proof-run/1",
            binary_sha256=binary_pin,
            quantization_sha256=QUANTIZATION,
            program=PROGRAM,
            threshold=THRESHOLD,
            cases={str(k): list(v) for k, v in cases.items()},
            controller_sha256=digest(Path(__file__).read_bytes()),
            verifier_sha256=digest((ROOT / "research/probes/py_ecc/check.py").read_bytes()),
            qualified_backend=False,
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
            worker.sandbox_profile = lambda binary, work: (
                original(binary, work)
                + "\n(allow file-read* file-map-executable "
                + " ".join(
                    "(subpath " + json.dumps(str(p)) + ")"
                    for p in (verifier_python.parent.parent, prefix, ROOT)
                )
                + ")\n"
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
        if report.get("status") != "passed" or set(cost["files"]) != set(inputs) | set(produced) | {
            "sandbox.sb",
            "plan.json",
            "stdout.txt",
            "stderr.txt",
        }:
            raise ValueError("unexpected worker result/inventory")
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
        for capacity, prompts in cases.items():
            tag = f"n{capacity}"
            preflight = classifier(e, bytes(5536), "0" * 64)
            decisions = [native_row(e, preflight, capacity, p, i)[1] for i, p in enumerate(prompts)]
            json_new(output / (tag + "-preflight.json"), decisions)
            if capacity == 96 and [r["verdict"] for r in decisions[:2]] != [True, False]:
                raise ValueError("selected contextual pair lost its decision contrast")
            model = encoded(e["model"])
            setup, _ = invoke(
                tag + "-setup",
                binary,
                ["contextual-setup", str(capacity)],
                {"model.json": model},
                ("circuit.r1cs", "pk.bin", "vk.bin"),
            )

            def artifact(name, setup=setup, tag=tag):
                pin = setup["files"][name]
                return PinnedArtifact(output / (tag + "-setup") / name, pin["sha256"], pin["bytes"])

            key = read_regular(output / (tag + "-setup/vk.bin"), 65536)
            c = classifier(e, key, setup["files"]["circuit.r1cs"]["sha256"])
            json_new(
                output / (tag + "-enrollment.json"),
                dict(
                    model_sha256=digest(model),
                    key_sha256=digest(key),
                    circuit=setup["files"]["circuit.r1cs"],
                    classifier_cbor_hex=c.encode().hex(),
                ),
            )
            inputs = {
                "model.json": model,
                **{name: artifact(name) for name in ("circuit.r1cs", "pk.bin", "vk.bin")},
            }
            rows, roster = [], []
            for i, prompt in enumerate(prompts):
                row, request = native_row(e, c, capacity, prompt, i)
                rows.append(row)
                json_new(output / f"{tag}-case-{i}-request.json", dict(**request, native_row=row))
                inputs[f"case-{i}.txt"] = assignment(row, True)
                roster.append(dict(name=f"case-{i}", valid=True))
            negative = mutations(e, c, capacity, prompts[-1], rows[-1])
            for name, row in negative.items():
                inputs["reject-" + name + ".txt"] = assignment(row, True)
                roster.append(dict(name="reject-" + name, valid=False))
            inputs["cases.json"] = encoded(roster)
            produced = [r["name"] + ".json" for r in roster] + [f"case-{i}.proof" for i in range(3)]
            invoke(tag + "-batch", binary, ["contextual-batch", str(capacity)], inputs, produced)
            fixtures = [
                dict(
                    name=str(i),
                    proof_hex=read_regular(output / f"{tag}-batch/case-{i}.proof", 292).hex(),
                    public=row["public"],
                )
                for i, row in enumerate(rows)
            ]
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
                capacity=capacity,
                actual_proofs=3,
                witness_rejections=list(negative),
                arithmetic_cases=len(report["cases"]),
                scores=[r["trace"][-1] for r in rows],
                verdicts=[r["public"][-1] for r in rows],
            )
            json_new(output / (tag + "-result.json"), completed)
            results.append(completed)
            print(json.dumps(completed), flush=True)
        result = dict(
            status="passed",
            qualified_backend=False,
            synthetic_only=True,
            results=results,
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--expected-binary", required=True)
    parser.add_argument("--verifier-python", type=Path, required=True)
    parser.add_argument("--quantization", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(
        args.binary.resolve(),
        args.expected_binary,
        args.verifier_python.absolute(),
        args.quantization,
        args.output,
    )
