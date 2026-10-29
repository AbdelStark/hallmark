"""V1 classifier contracts and parameter-bound static graph checks, not execution."""

import hashlib
import math
from fractions import Fraction
from typing import Annotated, Literal, Self

from pydantic import Field, TypeAdapter, ValidationError, model_validator

from hallmark.contracts import Identifier, Int32
from hallmark.manifests import Digest32, FileRef, _Artifact, _Record
from hallmark.wire import WireError, decode

U64 = Annotated[int, Field(ge=0, le=2**64 - 1)]
Dimension = Annotated[int, Field(ge=1, le=2**64 - 1)]
Axis = Annotated[int, Field(ge=0, le=3)]
type Operation = Literal[
    "gather", "affine", "add", "multiply", "reshape", "transpose", "masked-reduce", "relu", "lookup"
]


class InputProfile(_Artifact):
    _domain = "input-profile"
    schema_id: Literal["hallmark/input-profile/1"]
    encoding: Literal["utf8-bytes", "token-ids"]
    tokenizer_files: Annotated[tuple[FileRef, ...], Field(strict=False, max_length=64)]
    prefix_tokens: Annotated[tuple[U64, ...], Field(strict=False, max_length=8)]
    suffix_tokens: Annotated[tuple[U64, ...], Field(strict=False, max_length=8)]
    chunk_size: Annotated[int, Field(ge=1, le=512)]
    overlap: Annotated[int, Field(ge=0, le=0)]
    max_units: Annotated[int, Field(ge=1, le=32768)]
    padding_id: U64
    padding_side: Literal["right"]

    @model_validator(mode="after")
    def recipe(self) -> Self:
        if len(self.prefix_tokens) + len(self.suffix_tokens) >= self.chunk_size:
            raise ValueError("special tokens leave no content capacity")
        paths = [ref.path for ref in self.tokenizer_files]
        if paths != sorted(set(paths)):
            raise ValueError("tokenizer paths must be sorted and unique")
        if self.encoding == "utf8-bytes":
            if (
                self.tokenizer_files
                or self.prefix_tokens
                or self.suffix_tokens
                or self.padding_id > 255
            ):
                raise ValueError("byte profiles have no tokenizer or special tokens")
        elif not self.tokenizer_files:
            raise ValueError("token profiles require pinned tokenizer files")
        return self


class TensorSpec(_Record):
    name: Identifier
    shape: Annotated[tuple[Dimension, ...], Field(strict=False, min_length=1, max_length=4)]
    signed_bits: Annotated[int, Field(ge=2, le=32)]
    fractional_bits: Annotated[int, Field(ge=0, le=30)]
    minimum: Int32
    maximum: Int32

    @model_validator(mode="after")
    def representable(self) -> Self:
        radius = 1 << (self.signed_bits - 1)
        if not -radius <= self.minimum <= self.maximum < radius:
            raise ValueError("tensor bounds exceed its signed representation")
        return self


class NodeSpec(_Record):
    id: Identifier
    op: Operation
    inputs: Annotated[tuple[Identifier, ...], Field(strict=False, min_length=1, max_length=3)]
    output: Identifier
    parameters: FileRef

    @model_validator(mode="after")
    def arity(self) -> Self:
        count = {"affine": 3, "reshape": 1, "transpose": 1, "relu": 1}.get(self.op, 2)
        if len(self.inputs) != count:
            raise ValueError("incorrect operator arity")
        return self


class _Parameters(_Record):
    schema_id: Literal["hallmark/operator-parameters/1"]


class PlainParameters(_Parameters):
    op: Literal["affine", "add", "reshape", "relu"]


class GatherParameters(_Parameters):
    op: Literal["gather"]
    axis: Axis


class MultiplyParameters(_Parameters):
    op: Literal["multiply"]
    mode: Literal["elementwise", "matmul"]


class TransposeParameters(_Parameters):
    op: Literal["transpose"]
    permutation: Annotated[tuple[Axis, ...], Field(strict=False, min_length=1, max_length=4)]


class ReductionParameters(_Parameters):
    op: Literal["masked-reduce"]
    axes: Annotated[tuple[Axis, ...], Field(strict=False, min_length=1, max_length=4)]
    keep_dims: bool
    reduction: Literal["sum", "max"]
    empty_value: Int32

    @model_validator(mode="after")
    def reduction_contract(self) -> Self:
        if tuple(sorted(set(self.axes))) != self.axes:
            raise ValueError("reduction axes must be sorted and unique")
        if self.reduction == "sum" and self.empty_value != 0:
            raise ValueError("an empty sum must be zero")
        return self


class LookupParameters(_Parameters):
    op: Literal["lookup"]
    offset: Int32


type OperatorParameters = Annotated[
    PlainParameters
    | GatherParameters
    | MultiplyParameters
    | TransposeParameters
    | ReductionParameters
    | LookupParameters,
    Field(discriminator="op"),
]
PARAMETERS: TypeAdapter[OperatorParameters] = TypeAdapter(OperatorParameters)


def _broadcast(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...]:
    width = max(len(a), len(b))
    pairs = zip((1,) * (width - len(a)) + a, (1,) * (width - len(b)) + b, strict=True)
    result = []
    for x, y in pairs:
        if x != y and x != 1 and y != 1:
            raise ValueError("incompatible broadcast shapes")
        result.append(max(x, y))
    return tuple(result)


def _product_bounds(a: TensorSpec, b: TensorSpec) -> tuple[int, int]:
    products = [x * y for x in (a.minimum, a.maximum) for y in (b.minimum, b.maximum)]
    return min(products), max(products)


def _rescale(value: int, source: int, target: int) -> int:
    shift = source - target
    return round(Fraction(value, 1 << shift)) if shift > 0 else value << -shift


def _node_contract(
    node: NodeSpec, tensors: dict[str, TensorSpec], parameters: OperatorParameters
) -> None:
    """Bound post-rescale ranges only; intermediate int32 overflow fails closed at runtime."""
    inputs = [tensors[name] for name in node.inputs]
    a = inputs[0]
    out = tensors[node.output]
    shape = a.shape
    low, high, fraction = a.minimum, a.maximum, a.fractional_bits
    preserve_scale = False
    if isinstance(parameters, GatherParameters):
        indices = inputs[1]
        axis = parameters.axis
        if (
            axis >= len(a.shape)
            or indices.fractional_bits != 0
            or not 0 <= indices.minimum <= indices.maximum < a.shape[axis]
        ):
            raise ValueError("invalid gather index or axis")
        shape = a.shape[:axis] + indices.shape + a.shape[axis + 1 :]
        preserve_scale = True
    elif isinstance(parameters, LookupParameters):
        indices = inputs[1]
        if len(a.shape) != 1 or not (
            0
            <= indices.minimum + parameters.offset
            <= indices.maximum + parameters.offset
            < a.shape[0]
        ):
            raise ValueError("lookup index exceeds the table")
        shape = indices.shape
        preserve_scale = True
    elif isinstance(parameters, TransposeParameters):
        if sorted(parameters.permutation) != list(range(len(a.shape))):
            raise ValueError("invalid transpose permutation")
        shape = tuple(a.shape[index] for index in parameters.permutation)
        preserve_scale = True
    elif isinstance(parameters, ReductionParameters):
        mask = inputs[1]
        if (
            parameters.axes[-1] >= len(a.shape)
            or mask.fractional_bits != 0
            or not 0 <= mask.minimum <= mask.maximum <= 1
            or _broadcast(a.shape, mask.shape) != a.shape
        ):
            raise ValueError("invalid reduction mask or axes")
        shape = tuple(
            1 if index in parameters.axes else size
            for index, size in enumerate(a.shape)
            if parameters.keep_dims or index not in parameters.axes
        ) or (1,)
        if parameters.reduction == "sum":
            count = math.prod(a.shape[index] for index in parameters.axes)
            low, high = min(0, low) * count, max(0, high) * count
        else:
            low, high = min(low, parameters.empty_value), max(high, parameters.empty_value)
    elif node.op == "reshape":
        if math.prod(a.shape) != math.prod(out.shape):
            raise ValueError("reshape changes element count")
        shape = out.shape
        preserve_scale = True
    elif node.op == "relu":
        low, high = max(0, low), max(0, high)
    elif node.op == "add":
        b = inputs[1]
        shape = _broadcast(a.shape, b.shape)
        fraction = max(a.fractional_bits, b.fractional_bits)
        low = (a.minimum << (fraction - a.fractional_bits)) + (
            b.minimum << (fraction - b.fractional_bits)
        )
        high = (a.maximum << (fraction - a.fractional_bits)) + (
            b.maximum << (fraction - b.fractional_bits)
        )
    elif isinstance(parameters, MultiplyParameters):
        b = inputs[1]
        low, high = _product_bounds(a, b)
        fraction = a.fractional_bits + b.fractional_bits
        if parameters.mode == "matmul":
            if len(a.shape) < 2 or len(b.shape) < 2 or a.shape[-1] != b.shape[-2]:
                raise ValueError("incompatible matrix shapes")
            shape = _broadcast(a.shape[:-2], b.shape[:-2]) + (a.shape[-2], b.shape[-1])
            low, high = low * a.shape[-1], high * a.shape[-1]
        else:
            shape = _broadcast(a.shape, b.shape)
    elif node.op == "affine":
        weights, bias = inputs[1:]
        if len(weights.shape) != 2 or a.shape[-1] != weights.shape[1]:
            raise ValueError("incompatible affine weights")
        fraction = a.fractional_bits + weights.fractional_bits
        if bias.shape != (weights.shape[0],) or bias.fractional_bits != fraction:
            raise ValueError("incompatible affine bias")
        shape = a.shape[:-1] + (weights.shape[0],)
        low, high = _product_bounds(a, weights)
        low, high = low * a.shape[-1] + bias.minimum, high * a.shape[-1] + bias.maximum
    else:
        raise ValueError("unsupported operator parameters")
    if shape != out.shape or (preserve_scale and fraction != out.fractional_bits):
        raise ValueError("incorrect output shape or scale")
    low = _rescale(low, fraction, out.fractional_bits)
    high = _rescale(high, fraction, out.fractional_bits)
    if not out.minimum <= low <= high <= out.maximum:
        raise ValueError("declared output range does not cover the operation")


class ArithmeticProfile(_Artifact):
    _domain = "arithmetic"
    schema_id: Literal["hallmark/arithmetic/1"]
    tensors: Annotated[tuple[TensorSpec, ...], Field(strict=False, min_length=1, max_length=4096)]
    nodes: Annotated[tuple[NodeSpec, ...], Field(strict=False, min_length=1, max_length=4096)]
    output: Identifier

    @model_validator(mode="after")
    def topology(self) -> Self:
        tensors = {tensor.name for tensor in self.tensors}
        producers = {node.output: node for node in self.nodes}
        if (
            len(tensors) != len(self.tensors)
            or len(producers) != len(self.nodes)
            or len({node.id for node in self.nodes}) != len(self.nodes)
            or self.output not in producers
            or not producers.keys() <= tensors
        ):
            raise ValueError("duplicate or missing tensor/node/output")
        available = tensors - producers.keys()
        refs: dict[str, FileRef] = {}
        for node in self.nodes:
            if not set(node.inputs) <= available:
                raise ValueError("graph must be topologically ordered")
            available.add(node.output)
            ref = node.parameters
            if ref.path in refs and refs[ref.path] != ref:
                raise ValueError("conflicting parameter file references")
            refs[ref.path] = ref
        needed = {self.output}
        for node in reversed(self.nodes):
            if node.output not in needed:
                raise ValueError("unused graph node")
            needed.update(node.inputs)
        if needed != tensors:
            raise ValueError("unused tensor declaration")
        return self

    def validate_parameters(self, files: dict[str, bytes]) -> None:
        """Check exact parameter bytes, then every node's shapes, scales and ranges.

        External tensor contents and backend qualification are separate obligations.
        No file is opened and no tensor data is allocated or executed here.
        """
        profile = self._validated()
        refs = {node.parameters.path: node.parameters for node in profile.nodes}
        if (
            type(files) is not dict
            or files.keys() != refs.keys()
            or any(type(raw) is not bytes for raw in files.values())
        ):
            raise WireError("INPUT_INVALID")
        if sum(len(raw) for raw in files.values()) > 64 * 1024 * 1024:
            raise WireError("LIMIT_EXCEEDED")
        try:
            parsed = {}
            for path, ref in refs.items():
                raw = files[path]
                if len(raw) != ref.size or hashlib.sha256(raw).digest() != ref.sha256:
                    raise ValueError("parameter file mismatch")
                parsed[path] = PARAMETERS.validate_python(decode(raw))
            tensors = {tensor.name: tensor for tensor in profile.tensors}
            for node in profile.nodes:
                parameters = parsed[node.parameters.path]
                if parameters.op != node.op:
                    raise ValueError("operator and parameters disagree")
                _node_contract(node, tensors, parameters)
            return
        except WireError:
            raise
        except (ValidationError, ValueError):
            pass
        raise WireError("INPUT_INVALID")


class ClassifierManifest(_Artifact):
    _domain = "classifier"
    schema_id: Literal["hallmark/classifier/1"]
    kind: Literal["rule", "mlp", "encoder"]
    program: Digest32
    weights: Digest32 | None
    tokenizer: Digest32 | None
    input_profile: Digest32
    arithmetic: Digest32
    threshold: Int32
    scope: Literal["prompt"]
    labels: Annotated[tuple[Identifier, Identifier], Field(strict=False)]
    backend: Digest32
    verifier_key: Digest32
    setup: Digest32

    @model_validator(mode="after")
    def classifier_contract(self) -> Self:
        if self.labels[0] == self.labels[1]:
            raise ValueError("label roles must be distinct")
        if (self.kind == "rule") != (self.weights is None):
            raise ValueError("weights are required for learned classifiers only")
        if (self.kind == "encoder") != (self.tokenizer is not None):
            raise ValueError("only encoders use tokenizer identities")
        if self.kind == "rule" and self.threshold != 1:
            raise ValueError("rule threshold must be one")
        return self

    def validate_profiles(
        self, inputs: InputProfile, arithmetic: ArithmeticProfile, *, parameters: dict[str, bytes]
    ) -> None:
        """Bind supplied profiles and fully check their parameter-dependent contracts."""
        classifier = self._validated()
        inputs = inputs._validated()
        arithmetic = arithmetic._validated()
        if (
            classifier.input_profile != inputs.identity()
            or classifier.arithmetic != arithmetic.identity()
        ):
            raise WireError("INPUT_INVALID")
        expected = "token-ids" if classifier.kind == "encoder" else "utf8-bytes"
        output = next(t for t in arithmetic.tensors if t.name == arithmetic.output)
        if inputs.encoding != expected or output.shape != (1,) or output.fractional_bits != 0:
            raise WireError("INPUT_INVALID")
        if classifier.kind == "rule" and (output.minimum, output.maximum) != (0, 1):
            raise WireError("INPUT_INVALID")
        arithmetic.validate_parameters(parameters)
