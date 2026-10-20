"""Bounded native byte-count MLP execution; no learned quality or proof claim."""

import hashlib
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from hallmark.classifier_manifest import (
    ArithmeticProfile,
    ClassifierManifest,
    InputProfile,
    TensorSpec,
    _rescale,
)
from hallmark.contracts import Int32
from hallmark.manifests import ArtifactDigest, Digest32, FileRef, _Artifact, _Record
from hallmark.openings import TranscriptOpening, input_commitment
from hallmark.wire import WireError, WireLimits

MAX_WEIGHTS_BYTES = 65536
MAX_CHUNKS = 1024
MAX_PRODUCTS = 2_097_152
I32_MIN, I32_MAX = -(2**31), 2**31 - 1
Int8 = Annotated[int, Field(ge=-128, le=127)]
Hidden = Annotated[tuple[Int32, ...], Field(strict=False, min_length=1, max_length=64)]
WeightRow = Annotated[tuple[Int8, ...], Field(strict=False, min_length=256, max_length=256)]


class MlpWeights(_Record):
    schema_id: Literal["hallmark/mlp-weights/1"]
    hidden_weights: Annotated[
        tuple[WeightRow, ...], Field(strict=False, min_length=1, max_length=64, repr=False)
    ]
    hidden_bias: Annotated[Hidden, Field(repr=False)]
    output_weights: Annotated[
        tuple[Int8, ...], Field(strict=False, min_length=1, max_length=64, repr=False)
    ]
    output_bias: Annotated[Int32, Field(repr=False)]

    @model_validator(mode="after")
    def dimensions(self) -> Self:
        if not len(self.hidden_weights) == len(self.hidden_bias) == len(self.output_weights):
            raise ValueError("MLP hidden dimensions disagree")
        return self


class MlpProgram(_Artifact):
    _domain = "program"
    schema_id: Literal["hallmark/mlp-program/1"]
    input_profile: Digest32
    arithmetic: Digest32
    weights: FileRef


class MlpChunk(_Record):
    index: Annotated[int, Field(ge=0, lt=MAX_CHUNKS)]
    unit_count: Annotated[int, Field(ge=0, le=512)]
    counts: Annotated[
        tuple[Annotated[int, Field(ge=0, le=512)], ...],
        Field(strict=False, min_length=256, max_length=256, repr=False),
    ]
    hidden_accumulators: Annotated[Hidden, Field(repr=False)]
    hidden: Annotated[Hidden, Field(repr=False)]
    activated: Annotated[Hidden, Field(repr=False)]
    output_accumulator: Int32
    score: Int32

    @model_validator(mode="after")
    def dimensions(self) -> Self:
        if (
            sum(self.counts) != self.unit_count
            or not len(self.hidden_accumulators) == len(self.hidden) == len(self.activated)
            or self.activated != tuple(max(0, value) for value in self.hidden)
        ):
            raise ValueError("MLP intermediate dimensions or counts disagree")
        return self


class MlpResult(_Record):
    """Private diagnostic trace: serialization discloses byte counts and activations."""

    schema_id: Literal["hallmark/mlp-result/1"]
    classifier: Digest32
    input_digest: Digest32
    unit_count: Annotated[int, Field(ge=0, le=32768)]
    chunk_size: Annotated[int, Field(ge=1, le=512)]
    chunks: Annotated[
        tuple[MlpChunk, ...], Field(strict=False, min_length=1, max_length=MAX_CHUNKS, repr=False)
    ]
    threshold: Int32
    score: Int32
    verdict: bool

    @model_validator(mode="after")
    def complete(self) -> Self:
        count = max(1, (self.unit_count + self.chunk_size - 1) // self.chunk_size)
        if (
            len(self.chunks) != count
            or any(
                chunk.index != index
                or chunk.unit_count
                != min(self.chunk_size, self.unit_count - index * self.chunk_size)
                or len(chunk.hidden) != len(self.chunks[0].hidden)
                for index, chunk in enumerate(self.chunks)
            )
            or self.score != max(chunk.score for chunk in self.chunks)
            or self.verdict != (self.score < self.threshold)
        ):
            raise ValueError("MLP result omits chunks or disagrees with strict threshold")
        return self


def _values(values: tuple[int, ...], spec: TensorSpec) -> None:
    if any(not spec.minimum <= value <= spec.maximum for value in values):
        raise WireError("INPUT_INVALID")


def _accumulator_bounds(
    rows: tuple[tuple[int, ...], ...], biases: tuple[int, ...], inputs: TensorSpec
) -> None:
    # Bound every bias-first partial sum before any rescaling can hide overflow.
    for row, bias in zip(rows, biases, strict=True):
        low = high = bias
        for weight in row:
            a, b = inputs.minimum * weight, inputs.maximum * weight
            low += min(a, b)
            high += max(a, b)
            if low < I32_MIN or high > I32_MAX:
                raise WireError("INPUT_INVALID")


def _affine(
    values: tuple[int, ...],
    rows: tuple[tuple[int, ...], ...],
    biases: tuple[int, ...],
    source_fraction: int,
    output: TensorSpec,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    accumulators = []
    for row, bias in zip(rows, biases, strict=True):
        total = bias
        for value, weight in zip(values, row, strict=True):
            total += value * weight
            if not I32_MIN <= total <= I32_MAX:
                raise WireError("INPUT_INVALID")
        accumulators.append(total)
    scaled = tuple(
        _rescale(value, source_fraction, output.fractional_bits) for value in accumulators
    )
    _values(scaled, output)
    return tuple(accumulators), scaled


def execute_mlp(
    opening: TranscriptOpening,
    classifier: ClassifierManifest,
    program: MlpProgram,
    inputs: InputProfile,
    arithmetic: ArithmeticProfile,
    *,
    weights: bytes,
    parameters: dict[str, bytes],
) -> MlpResult:
    """Validate exact exports, then evaluate all prompt bytes with bounded private traces.

    File references never trigger I/O. Caller enrollment, proof/hardware verification,
    training and calibration are separate. Returned traces must stay on private channels.
    """
    if (
        type(opening) is not TranscriptOpening
        or type(classifier) is not ClassifierManifest
        or type(program) is not MlpProgram
        or type(inputs) is not InputProfile
        or type(arithmetic) is not ArithmeticProfile
        or type(weights) is not bytes
    ):
        raise WireError("INPUT_INVALID")
    if len(weights) > MAX_WEIGHTS_BYTES:
        raise WireError("LIMIT_EXCEEDED")
    opening, classifier = opening._validated(), classifier._validated()
    program, inputs, arithmetic = program._validated(), inputs._validated(), arithmetic._validated()
    if (
        classifier.kind != "mlp"
        or classifier.program != program.identity()
        or classifier.weights != ArtifactDigest(program.weights.sha256)
        or program.input_profile != inputs.identity()
        or program.arithmetic != arithmetic.identity()
        or len(weights) != program.weights.size
        or hashlib.sha256(weights).digest() != program.weights.sha256
        or len(arithmetic.nodes) != 3
        or len(arithmetic.tensors) != 8
        or program.weights.path in {node.parameters.path for node in arithmetic.nodes}
    ):
        raise WireError("INPUT_INVALID")
    values = MlpWeights.decode(
        weights, limits=WireLimits(max_bytes=MAX_WEIGHTS_BYTES, max_items=20000)
    )
    first, relu, last = arithmetic.nodes
    if (
        (first.op, relu.op, last.op) != ("affine", "relu", "affine")
        or relu.inputs != (first.output,)
        or last.inputs[0] != relu.output
        or arithmetic.output != last.output
    ):
        raise WireError("INPUT_INVALID")
    names = (*first.inputs, first.output, relu.output, *last.inputs[1:], last.output)
    if len(set(names)) != 8:
        raise WireError("INPUT_INVALID")
    tensors = {tensor.name: tensor for tensor in arithmetic.tensors}
    x, w1, b1, z, h, w2, b2, y = (tensors[name] for name in names)
    width = len(values.hidden_bias)
    shapes = ((256,), (width, 256), (width,), (width,), (width,), (1, width), (1,), (1,))
    if (
        tuple(t.shape for t in (x, w1, b1, z, h, w2, b2, y)) != shapes
        or (x.minimum, x.maximum, x.fractional_bits) != (0, inputs.chunk_size, 0)
        or any(t.signed_bits != 32 for t in (x, b1, z, h, b2, y))
        or any(t.signed_bits != 8 for t in (w1, w2))
        or h.fractional_bits != z.fractional_bits
    ):
        raise WireError("INPUT_INVALID")
    classifier.validate_profiles(inputs, arithmetic, parameters=parameters)
    _values(tuple(v for row in values.hidden_weights for v in row), w1)
    _values(values.hidden_bias, b1)
    _values(values.output_weights, w2)
    _values((values.output_bias,), b2)
    _accumulator_bounds(values.hidden_weights, values.hidden_bias, x)
    output_rows, output_biases = (values.output_weights,), (values.output_bias,)
    _accumulator_bounds(output_rows, output_biases, h)
    raw = opening.prompt.encode("utf-8")
    chunk_count = max(1, (len(raw) + inputs.chunk_size - 1) // inputs.chunk_size)
    if (
        len(raw) > inputs.max_units
        or chunk_count > MAX_CHUNKS
        or chunk_count * width * 257 > MAX_PRODUCTS
    ):
        raise WireError("LIMIT_EXCEEDED")
    traces = []
    for index in range(chunk_count):
        content = raw[index * inputs.chunk_size : (index + 1) * inputs.chunk_size]
        counts = [0] * 256
        # Masked right-padding contributes zero, including when padding_id is a real byte.
        for value in content:
            counts[value] += 1
        accumulators, hidden = _affine(
            tuple(counts), values.hidden_weights, values.hidden_bias, w1.fractional_bits, z
        )
        activated = tuple(max(0, value) for value in hidden)
        _values(activated, h)
        output_accumulators, scores = _affine(
            activated, output_rows, output_biases, h.fractional_bits + w2.fractional_bits, y
        )
        traces.append(
            MlpChunk(
                index=index,
                unit_count=len(content),
                counts=tuple(counts),
                hidden_accumulators=accumulators,
                hidden=hidden,
                activated=activated,
                output_accumulator=output_accumulators[0],
                score=scores[0],
            )
        )
    score = max(trace.score for trace in traces)
    return MlpResult(
        schema_id="hallmark/mlp-result/1",
        classifier=classifier.identity(),
        input_digest=input_commitment(opening, classifier, inputs),
        unit_count=len(raw),
        chunk_size=inputs.chunk_size,
        chunks=tuple(traces),
        threshold=classifier.threshold,
        score=score,
        verdict=score < classifier.threshold,
    )
