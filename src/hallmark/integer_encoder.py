"""Native integer graph and lossless byte-token preparation; no encoder qualification."""

import hashlib
import math
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from hallmark.classifier_manifest import ArithmeticProfile, ClassifierManifest, InputProfile
from hallmark.contracts import Identifier, Int32
from hallmark.integer_graph import MAX_VALUES, IntegerGraph
from hallmark.manifests import ArtifactDigest, Digest32, FileRef, _Artifact, _Record
from hallmark.openings import TranscriptOpening, input_commitment
from hallmark.wire import WireError, WireLimits

BYTE_TOKENIZER = (
    b'{"schema_id":"hallmark/byte-tokenizer/1","encoding":"utf-8","ids":"byte-values"}\n'
)
MAX_CONSTANT_BYTES = 4 * 1024 * 1024
MAX_EXECUTION_WORK = 33_554_432
MAX_TRACE_VALUES = 8_388_608
Byte = Annotated[int, Field(ge=0, le=255)]
Mask = Annotated[int, Field(ge=0, le=1)]


class EncoderProgram(_Artifact):
    _domain = "program"
    schema_id: Literal["hallmark/encoder-program/1"]
    input_profile: Digest32
    arithmetic: Digest32
    weights: FileRef
    tokenizer: FileRef
    token_input: Identifier
    mask_input: Identifier


class EncoderConstants(_Record):
    schema_id: Literal["hallmark/encoder-constants/1"]
    tensors: Annotated[
        dict[Identifier, Annotated[tuple[Int32, ...], Field(strict=False, min_length=1)]],
        Field(min_length=1, max_length=4096, repr=False),
    ]

    @model_validator(mode="after")
    def bounded(self) -> Self:
        if sum(map(len, self.tensors.values())) > MAX_VALUES:
            raise ValueError("too many constant values")
        return self


class EncoderChunk(_Record):
    index: Annotated[int, Field(ge=0, lt=32768)]
    unit_count: Annotated[int, Field(ge=0, le=512)]
    tokens: Annotated[
        tuple[Byte, ...], Field(strict=False, min_length=1, max_length=512, repr=False)
    ]
    mask: Annotated[tuple[Mask, ...], Field(strict=False, min_length=1, max_length=512, repr=False)]
    tensors: Annotated[
        dict[Identifier, Annotated[tuple[Int32, ...], Field(strict=False, min_length=1)]],
        Field(min_length=1, max_length=4096, repr=False),
    ]
    score: Int32


class EncoderResult(_Record):
    """Private software trace. Parsing this record does not authenticate its computation."""

    schema_id: Literal["hallmark/encoder-result/1"]
    classifier: Digest32
    input_digest: Digest32
    unit_count: Annotated[int, Field(ge=0, le=32768)]
    chunk_size: Annotated[int, Field(ge=1, le=512)]
    content_capacity: Annotated[int, Field(ge=1, le=512)]
    chunks: Annotated[
        tuple[EncoderChunk, ...], Field(strict=False, min_length=1, max_length=32768, repr=False)
    ]
    threshold: Int32
    score: Int32
    verdict: bool

    @model_validator(mode="after")
    def complete(self) -> Self:
        capacity = self.content_capacity
        special = self.chunk_size - capacity
        if (
            special < 0
            or len(self.chunks) != max(1, (self.unit_count + capacity - 1) // capacity)
            or any(
                c.index != i
                or c.unit_count != min(capacity, self.unit_count - i * capacity)
                or len(c.tokens) != self.chunk_size
                or c.mask != (1,) * (c.unit_count + special) + (0,) * (capacity - c.unit_count)
                for i, c in enumerate(self.chunks)
            )
            or self.score != max(c.score for c in self.chunks)
            or self.verdict != (self.score < self.threshold)
        ):
            raise ValueError("incomplete encoder chunks or inconsistent threshold")
        return self


def execute_encoder(
    opening: TranscriptOpening,
    classifier: ClassifierManifest,
    program: EncoderProgram,
    inputs: InputProfile,
    arithmetic: ArithmeticProfile,
    *,
    weights: bytes,
    tokenizer: bytes,
    parameters: dict[str, bytes],
) -> EncoderResult:
    """Check exact files/identities, tokenize locally and execute every content chunk.

    Only the explicit byte-tokenizer recipe is implemented. No download, optional
    framework, truncation, implicit approximation or enrollment occurs here.
    """
    if (
        type(opening) is not TranscriptOpening
        or type(classifier) is not ClassifierManifest
        or type(program) is not EncoderProgram
        or type(inputs) is not InputProfile
        or type(arithmetic) is not ArithmeticProfile
        or type(weights) is not bytes
        or type(tokenizer) is not bytes
    ):
        raise WireError("INPUT_INVALID")
    if len(weights) > MAX_CONSTANT_BYTES:
        raise WireError("LIMIT_EXCEEDED")
    opening, classifier = opening._validated(), classifier._validated()
    program, inputs, arithmetic = program._validated(), inputs._validated(), arithmetic._validated()
    paths = {node.parameters.path for node in arithmetic.nodes}
    if (
        classifier.kind != "encoder"
        or classifier.program != program.identity()
        or classifier.weights != ArtifactDigest(program.weights.sha256)
        or classifier.tokenizer != ArtifactDigest(program.tokenizer.sha256)
        or program.input_profile != inputs.identity()
        or program.arithmetic != arithmetic.identity()
        or inputs.tokenizer_files != (program.tokenizer,)
        or program.token_input == program.mask_input
        or program.weights.path == program.tokenizer.path
        or bool(paths & {program.weights.path, program.tokenizer.path})
        or tokenizer != BYTE_TOKENIZER
        or max((*inputs.prefix_tokens, *inputs.suffix_tokens, inputs.padding_id)) > 255
    ):
        raise WireError("INPUT_INVALID")
    for ref, raw in ((program.weights, weights), (program.tokenizer, tokenizer)):
        if len(raw) != ref.size or hashlib.sha256(raw).digest() != ref.sha256:
            raise WireError("INPUT_INVALID")
    classifier.validate_profiles(inputs, arithmetic, parameters=parameters)
    specs = {t.name: t for t in arithmetic.tensors}
    roots = specs.keys() - {node.output for node in arithmetic.nodes}
    for name, high in ((program.token_input, 255), (program.mask_input, 1)):
        if name not in roots or (
            specs[name].shape,
            specs[name].fractional_bits,
            specs[name].minimum,
            specs[name].maximum,
        ) != ((inputs.chunk_size,), 0, 0, high):
            raise WireError("INPUT_INVALID")
    constants = EncoderConstants.decode(
        weights, limits=WireLimits(max_bytes=MAX_CONSTANT_BYTES, max_items=MAX_VALUES + 16384)
    )
    if constants.tensors.keys() != roots - {program.token_input, program.mask_input}:
        raise WireError("INPUT_INVALID")
    graph = IntegerGraph(arithmetic, parameters=parameters, constants=constants.tensors)
    units = tuple(opening.prompt.encode("utf-8"))
    capacity = inputs.chunk_size - len(inputs.prefix_tokens) - len(inputs.suffix_tokens)
    count = max(1, (len(units) + capacity - 1) // capacity)
    trace_size = sum(math.prod(specs[node.output].shape) for node in arithmetic.nodes)
    if (
        len(units) > inputs.max_units
        or count * graph.work > MAX_EXECUTION_WORK
        or count * trace_size > MAX_TRACE_VALUES
    ):
        raise WireError("LIMIT_EXCEEDED")
    chunks = []
    for index in range(count):
        content = units[index * capacity : (index + 1) * capacity]
        active = inputs.prefix_tokens + content + inputs.suffix_tokens
        tokens = active + (inputs.padding_id,) * (inputs.chunk_size - len(active))
        mask = (1,) * len(active) + (0,) * (inputs.chunk_size - len(active))
        tensors = graph.evaluate({program.token_input: tokens, program.mask_input: mask})
        chunks.append(
            EncoderChunk(
                index=index,
                unit_count=len(content),
                tokens=tokens,
                mask=mask,
                tensors=tensors,
                score=tensors[arithmetic.output][0],
            )
        )
    score = max(c.score for c in chunks)
    return EncoderResult(
        schema_id="hallmark/encoder-result/1",
        classifier=classifier.identity(),
        input_digest=input_commitment(
            opening, classifier, inputs, token_units=units, vocabulary_size=256
        ),
        unit_count=len(units),
        chunk_size=inputs.chunk_size,
        content_capacity=capacity,
        chunks=tuple(chunks),
        threshold=classifier.threshold,
        score=score,
        verdict=score < classifier.threshold,
    )
