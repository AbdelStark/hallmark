"""Frozen classifier inputs, exports and scalar conformance; no proof backend here."""

import json
from fractions import Fraction
from pathlib import Path

import contextual_proof as cnn
import trained_mlp as mlp
from run_e2e import EXPORTS

from hallmark._worker import digest, read_regular
from hallmark.classifier_manifest import _rescale
from hallmark.integrity import parse_json
from hallmark.mlp_training import MlpQuantization
from hallmark.openings import TranscriptOpening
from hallmark.policy import RequestExpectation
from hallmark.wire import decode

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/circle-classifiers"


sha = digest


def encoded(value):
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def documents():
    plan = parse_json(read_regular(CONFIG / "plan.json", 65536).decode())
    corpus = parse_json(read_regular(CONFIG / "corpus.json", 65536).decode())
    if (
        plan["schema_id"] != "hallmark.circle-classifier-plan/1"
        or corpus["schema_id"] != "hallmark.classifier-backend-corpus/1"
        or plan["capacity_bytes"] != 96
        or [r["id"] for r in corpus["requests"]] != plan["case_ids"]
        or plan["threads"] != 4
    ):
        raise ValueError("classifier plan or corpus changed without a new identity")
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
    # Static node ranges bound only post-rescale values; reject intermediate i32 overflow here.
    cnn_integer_bounds(values["encoder"])
    return values


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
