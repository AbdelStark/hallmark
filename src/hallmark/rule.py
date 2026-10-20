"""Complete-input literal byte rules; native execution, not policy or proof acceptance."""

import hashlib
from typing import Annotated, Literal, Self

from pydantic import Field, WithJsonSchema, model_validator

from hallmark.classifier_manifest import ArithmeticProfile, ClassifierManifest, InputProfile
from hallmark.manifests import Digest32, FileRef, _Artifact, _Record
from hallmark.openings import TranscriptOpening, input_commitment
from hallmark.wire import WireError

MAX_PATTERN_BYTES = 4096
MAX_PROVENANCE_BYTES = 16384
Bit = Annotated[int, Field(ge=0, le=1)]
Pattern = Annotated[
    bytes,
    Field(min_length=1, max_length=MAX_PATTERN_BYTES),
    WithJsonSchema(
        {
            "type": "string",
            "pattern": "^(?:[0-9a-fA-F]{2})+$",
            "minLength": 2,
            "maxLength": 2 * MAX_PATTERN_BYTES,
        }
    ),
]


class RuleProgram(_Artifact):
    _domain = "program"
    schema_id: Literal["hallmark/rule-program/1"]
    input_profile: Digest32
    arithmetic: Digest32
    patterns: Annotated[
        tuple[Pattern, ...], Field(strict=False, min_length=1, max_length=MAX_PATTERN_BYTES)
    ]
    provenance: FileRef

    @model_validator(mode="after")
    def bounded_patterns(self) -> Self:
        if (
            self.patterns != tuple(sorted(set(self.patterns)))
            or sum(map(len, self.patterns)) > MAX_PATTERN_BYTES
            or not 1 <= self.provenance.size <= MAX_PROVENANCE_BYTES
        ):
            raise ValueError("rule patterns or provenance are not canonical and bounded")
        return self


class RuleResult(_Record):
    """Private diagnostics: chunk scores disclose where literal matches end."""

    schema_id: Literal["hallmark/rule-result/1"]
    classifier: Digest32
    input_digest: Digest32
    unit_count: Annotated[int, Field(ge=0, le=32768)]
    chunk_size: Annotated[int, Field(ge=1, le=512)]
    chunk_scores: Annotated[
        tuple[Bit, ...], Field(strict=False, min_length=1, max_length=32768, repr=False)
    ]
    threshold: Annotated[int, Field(ge=1, le=1)]
    score: Bit
    verdict: bool

    @model_validator(mode="after")
    def complete(self) -> Self:
        if (
            len(self.chunk_scores)
            != max(1, (self.unit_count + self.chunk_size - 1) // self.chunk_size)
            or (self.unit_count == 0 and self.chunk_scores != (0,))
            or self.score != max(self.chunk_scores)
            or self.verdict != (self.score < self.threshold)
        ):
            raise ValueError("rule result omits chunks or disagrees with strict threshold")
        return self


def execute_rule(
    opening: TranscriptOpening,
    classifier: ClassifierManifest,
    program: RuleProgram,
    inputs: InputProfile,
    arithmetic: ArithmeticProfile,
    *,
    provenance: bytes,
    parameters: dict[str, bytes],
) -> RuleResult:
    """Bind exact inputs/program/files, carry suffix state and consume every chunk.

    No file access, normalization or regex. The literal feature extractor is part
    of RuleProgram; the arithmetic DAG is only its scalar Boolean score projection.
    Enrollment, source approval and full-program proof qualification are separate.
    """
    if (
        type(opening) is not TranscriptOpening
        or type(classifier) is not ClassifierManifest
        or type(program) is not RuleProgram
        or type(inputs) is not InputProfile
        or type(arithmetic) is not ArithmeticProfile
        or type(provenance) is not bytes
    ):
        raise WireError("INPUT_INVALID")
    if len(provenance) > MAX_PROVENANCE_BYTES:
        raise WireError("LIMIT_EXCEEDED")
    opening, classifier = opening._validated(), classifier._validated()
    program, inputs, arithmetic = program._validated(), inputs._validated(), arithmetic._validated()
    if (
        classifier.kind != "rule"
        or classifier.program != program.identity()
        or program.input_profile != inputs.identity()
        or program.arithmetic != arithmetic.identity()
        or len(provenance) != program.provenance.size
        or hashlib.sha256(provenance).digest() != program.provenance.sha256
        or len(arithmetic.nodes) != 1
        or len(arithmetic.tensors) != 2
        or program.provenance.path in {node.parameters.path for node in arithmetic.nodes}
    ):
        raise WireError("INPUT_INVALID")
    node = arithmetic.nodes[0]
    if (
        node.op != "relu"
        or node.output != arithmetic.output
        or any(
            (
                tensor.shape,
                tensor.signed_bits,
                tensor.fractional_bits,
                tensor.minimum,
                tensor.maximum,
            )
            != ((1,), 2, 0, 0, 1)
            for tensor in arithmetic.tensors
        )
    ):
        raise WireError("INPUT_INVALID")
    classifier.validate_profiles(inputs, arithmetic, parameters=parameters)
    raw = opening.prompt.encode("utf-8")
    if len(raw) > inputs.max_units:
        raise WireError("LIMIT_EXCEEDED")
    keep = max(map(len, program.patterns)) - 1
    suffix = b""
    scores = []
    for start in range(0, max(1, len(raw)), inputs.chunk_size):
        content = raw[start : start + inputs.chunk_size]
        window = suffix + content
        # A match belongs to the chunk containing its final byte, never padding.
        matched = bool(content) and any(
            window.find(pattern, max(0, len(suffix) - len(pattern) + 1)) >= 0
            for pattern in program.patterns
        )
        scores.append(max(0, int(matched)))
        suffix = window[-keep:] if keep else b""
    score = max(scores)
    return RuleResult(
        schema_id="hallmark/rule-result/1",
        classifier=classifier.identity(),
        input_digest=input_commitment(opening, classifier, inputs),
        unit_count=len(raw),
        chunk_size=inputs.chunk_size,
        chunk_scores=tuple(scores),
        threshold=classifier.threshold,
        score=score,
        verdict=score < classifier.threshold,
    )
