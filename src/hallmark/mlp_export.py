"""Compile explicit MLP integer weights/profiles without inventing backend enrollment."""

import hashlib
from typing import cast

from hallmark.classifier_manifest import (
    ArithmeticProfile,
    InputProfile,
    NodeSpec,
    Operation,
    TensorSpec,
    _rescale,
)
from hallmark.integer_mlp import MlpProgram, MlpWeights
from hallmark.manifests import FileRef, FileSHA256
from hallmark.wire import WireError, encode


def compile_mlp(
    weights: MlpWeights,
    inputs: InputProfile,
    *,
    first_fraction: int,
    hidden_fraction: int,
    last_fraction: int,
) -> tuple[MlpProgram, ArithmeticProfile, bytes, dict[str, bytes]]:
    """Build conservative range envelopes; caller separately supplies classifier trust fields."""
    if type(weights) is not MlpWeights or type(inputs) is not InputProfile:
        raise WireError("INPUT_INVALID")
    weights, inputs = weights._validated(), inputs._validated()
    if inputs.encoding != "utf8-bytes" or any(
        type(n) is not int or not 0 <= n <= 30
        for n in (first_fraction, hidden_fraction, last_fraction)
    ):
        raise WireError("INPUT_INVALID")
    width = len(weights.hidden_bias)
    parameters = {
        f"params/{op}.cbor": encode({"schema_id": "hallmark/operator-parameters/1", "op": op})
        for op in ("affine", "relu")
    }

    def ref(path: str, raw: bytes) -> FileRef:
        return FileRef(path=path, size=len(raw), sha256=FileSHA256(hashlib.sha256(raw).digest()))

    def tensor(
        name: str, shape: tuple[int, ...], low: int, high: int, fraction: int, bits: int = 32
    ) -> TensorSpec:
        return TensorSpec(
            name=name,
            shape=shape,
            signed_bits=bits,
            fractional_bits=fraction,
            minimum=low,
            maximum=high,
        )

    flat = [value for row in weights.hidden_weights for value in row]
    low = min(0, min(flat) * inputs.chunk_size) * 256 + min(weights.hidden_bias)
    high = max(0, max(flat) * inputs.chunk_size) * 256 + max(weights.hidden_bias)
    zl, zh = (
        _rescale(low, first_fraction, hidden_fraction),
        _rescale(high, first_fraction, hidden_fraction),
    )
    hl, hh = max(0, zl), max(0, zh)
    endpoints = [
        value * weight
        for value in (hl, hh)
        for weight in (min(weights.output_weights), max(weights.output_weights))
    ]
    ol = min(endpoints) * width + weights.output_bias
    oh = max(endpoints) * width + weights.output_bias
    tensors = (
        tensor("counts", (256,), 0, inputs.chunk_size, 0),
        tensor("w1", (width, 256), min(flat), max(flat), first_fraction, 8),
        tensor("b1", (width,), min(weights.hidden_bias), max(weights.hidden_bias), first_fraction),
        tensor("hidden", (width,), zl, zh, hidden_fraction),
        tensor("relu", (width,), hl, hh, hidden_fraction),
        tensor(
            "w2",
            (1, width),
            min(weights.output_weights),
            max(weights.output_weights),
            last_fraction,
            8,
        ),
        tensor(
            "b2", (1,), weights.output_bias, weights.output_bias, hidden_fraction + last_fraction
        ),
        tensor(
            "score",
            (1,),
            _rescale(ol, hidden_fraction + last_fraction, 0),
            _rescale(oh, hidden_fraction + last_fraction, 0),
            0,
        ),
    )
    arithmetic = ArithmeticProfile(
        schema_id="hallmark/arithmetic/1",
        tensors=tensors,
        output="score",
        nodes=tuple(
            NodeSpec(
                id=name,
                op=cast(Operation, op),
                inputs=names,
                output=out,
                parameters=ref(f"params/{op}.cbor", parameters[f"params/{op}.cbor"]),
            )
            for name, op, names, out in (
                ("hidden-affine", "affine", ("counts", "w1", "b1"), "hidden"),
                ("activation", "relu", ("hidden",), "relu"),
                ("output-affine", "affine", ("relu", "w2", "b2"), "score"),
            )
        ),
    )
    raw = weights.encode()
    program = MlpProgram(
        schema_id="hallmark/mlp-program/1",
        input_profile=inputs.identity(),
        arithmetic=arithmetic.identity(),
        weights=ref("weights/mlp.cbor", raw),
    )
    return program, arithmetic, raw, parameters
