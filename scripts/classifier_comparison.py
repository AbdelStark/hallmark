"""Frozen classifier comparison inputs and conformance; no new proof backend here."""

import copy
import hashlib
import json
import time
from fractions import Fraction
from pathlib import Path

import run_contextual_proof as cnn
import run_trained_mlp as mlp
import trained_common_input as common
from run_e2e import EXPORTS

from hallmark._gnark_probe import read_regular
from hallmark.classifier_manifest import _rescale
from hallmark.integer_graph import IntegerGraph
from hallmark.integrity import parse_json
from hallmark.mlp_training import MlpQuantization
from hallmark.openings import TranscriptOpening
from hallmark.policy import RequestExpectation
from hallmark.wire import decode

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/circle-classifiers"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def documents():
    plan = parse_json(read_regular(CONFIG / "plan.json", 65536).decode())
    corpus = parse_json(read_regular(CONFIG / "corpus.json", 65536).decode())
    if (
        plan["schema_id"] != "hallmark.classifier-backend-plan/1"
        or corpus["schema_id"] != "hallmark.classifier-backend-corpus/1"
        or plan["capacity_bytes"] != 96
        or plan["repetitions"] != {"fresh": 3, "warm": 5}
        or [r["id"] for r in corpus["requests"]] != plan["case_ids"]
        or plan["threads"] != 4
    ):
        raise ValueError("comparison plan or corpus changed without a new identity")
    return plan, corpus


def exports(directory):
    values = {}
    for kind, relative in (("mlp", "mlp-training/seed-17"), ("encoder", "cnn-training/17")):
        name = relative + "/quantization.json"
        raw = read_regular(directory / name, 65536)
        if sha(raw) != EXPORTS[name]:
            raise ValueError("comparison requires the frozen published quantizations")
        values[kind] = (
            mlp.export(MlpQuantization.model_validate_json(raw))
            if kind == "mlp"
            else cnn.export(parse_json(raw.decode()))
        )
    return values


def admitted(directory, expected_enrollment):
    """Caller pins the original enrollment; a prover result flag is never consumed."""
    values = exports(directory)
    root = directory / "proofs"
    raw = read_regular(root / "enrollment.json", 65536)
    circuits = parse_json(read_regular(root / "circuit-pins.json", 65536).decode())
    records, policy = common.resolve(raw, expected_enrollment, values, circuits)
    for kind, record in zip(common.KINDS, records, strict=True):
        vk = read_regular(root / ("setup-" + kind) / "vk.bin", 65536)
        if vk != record["key"]:
            raise ValueError("enrolled key differs from retained preparation")
    return values, records, policy, circuits, raw


def request(root, name):
    value = parse_json(read_regular(root / (name + "-request.json"), 2 * 1024**2).decode())
    return (
        TranscriptOpening.decode(bytes.fromhex(value["opening_cbor_hex"])),
        RequestExpectation.decode(bytes.fromhex(value["expected_cbor_hex"])),
    )


def scalar_conformance(corpus):
    for row in corpus["rounding"]:
        value, shift = row["value"], row["shift"]
        actual = _rescale(value, shift, 0)
        if actual != row["expected"] or actual != round(Fraction(value, 2**shift)):
            raise ValueError("integer rounding contract mismatch")
    scalar = corpus["scalar_boundaries"]
    if scalar["int32_min"] != -(2**31) or scalar["int32_max"] != 2**31 - 1:
        raise ValueError("int32 bounds changed")
    if any(max(0, x) != y for x, y in scalar["relu"]):
        raise ValueError("ReLU boundary mismatch")
    if any(
        (score < threshold) is not expected
        for score, threshold, expected in scalar["strict_threshold"]
    ):
        raise ValueError("strict threshold boundary mismatch")
    return len(corpus["rounding"]) + len(scalar["relu"]) + len(scalar["strict_threshold"])


def native_scorer(values):
    """Inference without request admission, commitments or caller recomputation."""
    e = values["mlp"]
    model = e["model"]
    graph = IntegerGraph(
        e["arithmetic"],
        parameters=e["parameters"],
        constants={
            "w1": tuple(x for row in model["hidden_weights"] for x in row),
            "b1": tuple(model["hidden_bias"]),
            "w2": tuple(model["output_weights"]),
            "b2": (model["output_bias"],),
        },
    )

    def score(prompt):
        raw = prompt.encode("utf-8")
        if len(raw) > 96:
            raise ValueError("comparison capacity exceeded")
        mlp_score = graph.evaluate({"counts": tuple(raw.count(i) for i in range(256))})["score"][0]
        cnn_score = values["encoder"]["graph"].evaluate(
            {
                "tokens": tuple(raw) + (0,) * (96 - len(raw)),
                "mask": (1,) * len(raw) + (0,) * (96 - len(raw)),
            }
        )["score"][0]
        return [int(b"BAD" in raw), mlp_score, cnn_score]

    return score


def cnn_integer_bounds(exported):
    """Exhaust all 256 embeddings per kernel site, then bound every i32 affine step.

    Sites may choose different bytes: these are conservative interval bounds,
    not achievable-score claims or measurements on held-out examples.
    """
    constants = decode(exported["weights"])["tensors"]
    embedding, kernel = constants["embedding"], constants["convolution-w"]
    pooled_upper, convolution_peak = [], 0
    for channel in range(32):
        low = high = constants["convolution-b"][channel]
        independent_low = independent_high = low
        for offset in range(24):
            contributions = [
                sum(
                    embedding[token * 4 + dim] * kernel[channel * 96 + offset * 4 + dim]
                    for dim in range(4)
                )
                for token in range(256)
            ] + [0]
            low += min(contributions)
            high += max(contributions)
            for dim in range(4):
                products = [
                    embedding[token * 4 + dim] * kernel[channel * 96 + offset * 4 + dim]
                    for token in range(256)
                ] + [0]
                independent_low += min(products)
                independent_high += max(products)
                convolution_peak = max(
                    convolution_peak,
                    abs(independent_low),
                    abs(independent_high),
                    max(abs(v) for v in products),
                )
        pooled_upper.append(max(0, round(Fraction(high, 64))))
    low = high = constants["score-b"][0]
    head_peak = abs(low)
    for high_value, weight in zip(pooled_upper, constants["score-w"], strict=True):
        product = high_value * weight
        low += min(0, product)
        high += max(0, product)
        head_peak = max(head_peak, abs(low), abs(high), abs(product))
    if max(convolution_peak, head_peak) >= 2**31:
        raise ValueError("frozen CNN cannot establish all reachable native i32 bounds")
    return dict(
        pooled_upper=pooled_upper,
        convolution_max_absolute_partial_or_product=convolution_peak,
        head_minimum=low,
        head_maximum=high,
        head_max_absolute_partial_or_product=head_peak,
        method="Per-site vocabulary extrema; independent sites; conservative, not tight/reachable",
    )


def native_contract(directory, expected_enrollment):
    plan, corpus = documents()
    values, records, policy, circuits, enrollment = admitted(directory, expected_enrollment)
    proof_root = directory / "proofs"
    score = native_scorer(values)
    cases, bundles = [], {}
    elapsed = []
    for case in corpus["requests"]:
        name = case["id"]
        opening, expected = request(proof_root, name)
        if opening.prompt != case["prompt"]:
            raise ValueError("frozen caller prompt changed")
        started = time.perf_counter()
        native_scores = score(opening.prompt)
        inference_seconds = time.perf_counter() - started
        started = time.perf_counter()
        rows = common.evaluate(records, policy, opening, expected)
        elapsed.append(time.perf_counter() - started)
        if [r["public"][99] for r in rows] != case["verdicts"]:
            raise ValueError("frozen native verdict mismatch")
        if native_scores != [
            int(not case["verdicts"][0]),
            rows[1]["trace"][-1],
            rows[2]["trace"][-1],
        ]:
            raise ValueError("inference-only versus bound execution mismatch")
        raw = read_regular(proof_root / (name + "-bundle.json"), 65536)
        jobs = common.check_bundle(
            enrollment, expected_enrollment, values, circuits, opening, expected, raw
        )
        bundles[name] = raw
        cases.append(
            dict(
                id=name,
                verdicts=case["verdicts"],
                scores=native_scores,
                native_inference_seconds=inference_seconds,
                request=dict(
                    opening_cbor_hex=opening.encode().hex(),
                    expected_cbor_hex=expected.encode().hex(),
                ),
                public=[r["public"] for r in rows],
                jobs=jobs,
            )
        )
    opening, expected = request(proof_root, corpus["requests"][0]["id"])
    boundaries = []
    for case in corpus["input_boundaries"]:
        prompt = case["unit"] * case["repeat"] + case["suffix"]
        changed = opening.model_copy(update={"prompt": prompt})
        try:
            rows = common.evaluate(records, policy, changed, expected)
        except ValueError:
            if case["accepted"]:
                raise
            boundaries.append(dict(id=case["id"], admitted=False, byte_count=len(prompt.encode())))
        else:
            if not case["accepted"] or rows[0]["public"][99] != case["rule_verdict"]:
                raise ValueError("input boundary contract mismatch")
            boundaries.append(
                dict(
                    id=case["id"],
                    admitted=True,
                    byte_count=len(prompt.encode()),
                    verdicts=[r["public"][99] for r in rows],
                    trace_sha256=[sha(encoded(r["trace"])) for r in rows],
                )
            )
    cross = []
    for target in corpus["requests"]:
        opening, expected = request(proof_root, target["id"])
        for source in corpus["requests"]:
            if source["id"] == target["id"]:
                continue
            for family in range(3):
                changed = parse_json(bundles[target["id"]].decode())
                changed["proofs"][family] = parse_json(bundles[source["id"]].decode())["proofs"][
                    family
                ]
                try:
                    common.check_bundle(
                        enrollment,
                        expected_enrollment,
                        values,
                        circuits,
                        opening,
                        expected,
                        encoded(changed),
                    )
                except ValueError:
                    cross.append([target["id"], source["id"], family])
                else:
                    raise ValueError("cross-request classifier accepted")
    for roster in ([], ["rule", "mlp"], ["rule", "mlp", "mlp"]):
        original = parse_json(bundles[corpus["requests"][0]["id"]].decode())
        by_kind = {r["kind"]: r for r in original["proofs"]}
        changed = copy.deepcopy(original)
        changed["proofs"] = [by_kind[k] for k in roster]
        opening, expected = request(proof_root, corpus["requests"][0]["id"])
        try:
            common.check_bundle(
                enrollment,
                expected_enrollment,
                values,
                circuits,
                opening,
                expected,
                encoded(changed),
            )
        except ValueError:
            pass
        else:
            raise ValueError("incomplete/duplicate classifier roster accepted")
    return dict(
        schema_id="hallmark.classifier-comparison-contract/1",
        plan=plan,
        plan_sha256=sha((CONFIG / "plan.json").read_bytes()),
        corpus_sha256=sha((CONFIG / "corpus.json").read_bytes()),
        enrollment_sha256=expected_enrollment,
        model_pins={k: sha(encoded(v["model"])) for k, v in values.items()},
        program_identities={k: v["program"].identity().hex() for k, v in values.items()},
        cases=cases,
        boundaries=boundaries,
        cnn_integer_bounds=cnn_integer_bounds(values["encoder"]),
        scalar_cases=scalar_conformance(corpus),
        cross_request_rejections=cross,
        roster_rejections=3,
        exploratory_native_binding_seconds=elapsed,
        qualified_backend=False,
    )
