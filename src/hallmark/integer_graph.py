"""Bounded exact execution of the existing integer DAG contract, without proof claims."""

import itertools
import math
from collections.abc import Iterator

from hallmark.classifier_manifest import (
    PARAMETERS,
    ArithmeticProfile,
    GatherParameters,
    LookupParameters,
    MultiplyParameters,
    NodeSpec,
    OperatorParameters,
    ReductionParameters,
    TensorSpec,
    TransposeParameters,
    _rescale,
)
from hallmark.wire import WireError, decode

MAX_VALUES = 262_144
MAX_WORK = 2_097_152


def _i32(value: int) -> int:
    if not -(2**31) <= value < 2**31:
        raise WireError("INPUT_INVALID")
    return value


def _indices(shape: tuple[int, ...]) -> Iterator[tuple[int, ...]]:
    return itertools.product(*(range(size) for size in shape))


def _offset(shape: tuple[int, ...], coordinates: tuple[int, ...]) -> int:
    offset = 0
    for size, index in zip(shape, coordinates[-len(shape) :], strict=True):
        offset = offset * size + (0 if size == 1 else index)
    return offset


def _check(values: tuple[int, ...], spec: TensorSpec) -> None:
    if (
        type(values) is not tuple
        or len(values) != math.prod(spec.shape)
        or any(type(n) is not int or not spec.minimum <= n <= spec.maximum for n in values)
    ):
        raise WireError("INPUT_INVALID")


class IntegerGraph:
    """Validate once, then execute bounded root tensors with private intermediate traces.

    Constants and parameter bytes are caller supplied. This performs no I/O,
    enrollment or graph qualification; the caller owns the surrounding run budget.
    """

    def __init__(
        self,
        profile: ArithmeticProfile,
        *,
        parameters: dict[str, bytes],
        constants: dict[str, tuple[int, ...]],
    ) -> None:
        if (
            type(profile) is not ArithmeticProfile
            or type(constants) is not dict
            or type(parameters) is not dict
        ):
            raise WireError("INPUT_INVALID")
        constants, parameters = constants.copy(), parameters.copy()
        profile = profile._validated()
        tensors = {t.name: t for t in profile.tensors}
        if sum(math.prod(t.shape) for t in tensors.values()) > MAX_VALUES:
            raise WireError("LIMIT_EXCEEDED")
        profile.validate_parameters(parameters)
        roots = tensors.keys() - {n.output for n in profile.nodes}
        if not constants.keys() <= roots:
            raise WireError("INPUT_INVALID")
        for name, values in constants.items():
            _check(values, tensors[name])
        self._constants = constants
        self._inputs = {name: tensors[name] for name in roots - constants.keys()}
        self._nodes = []
        work = 0
        for node in profile.nodes:
            p = PARAMETERS.validate_python(decode(parameters[node.parameters.path]))
            inputs = tuple(tensors[name] for name in node.inputs)
            output = tensors[node.output]
            count = math.prod(output.shape)
            if node.op == "affine" or isinstance(p, MultiplyParameters) and p.mode == "matmul":
                count *= 2 * inputs[0].shape[-1] + 1
            elif isinstance(p, ReductionParameters):
                count = math.prod(inputs[0].shape)
            work += count
            self._nodes.append((node, p, inputs, output))
        if work > MAX_WORK:
            raise WireError("LIMIT_EXCEEDED")
        self.work = work

    def evaluate(self, inputs: dict[str, tuple[int, ...]]) -> dict[str, tuple[int, ...]]:
        """Return node outputs only; serializing these tensors can disclose private input."""
        if type(inputs) is not dict or inputs.keys() != self._inputs.keys():
            raise WireError("INPUT_INVALID")
        inputs = inputs.copy()
        for name, supplied in inputs.items():
            _check(supplied, self._inputs[name])
        values = self._constants | inputs
        trace = {}
        for node, parameters, specs, output in self._nodes:
            result = _node(node, parameters, specs, output, tuple(values[n] for n in node.inputs))
            _check(result, output)
            values[node.output] = trace[node.output] = result
        return trace


def _node(
    node: NodeSpec,
    p: OperatorParameters,
    specs: tuple[TensorSpec, ...],
    output: TensorSpec,
    data: tuple[tuple[int, ...], ...],
) -> tuple[int, ...]:
    a = specs[0]
    fraction = a.fractional_bits

    def at(which: int, coordinates: tuple[int, ...]) -> int:
        return data[which][_offset(specs[which].shape, coordinates)]

    if node.op == "reshape":
        return data[0]
    if isinstance(p, ReductionParameters):
        reduced: list[int | None] = [None] * math.prod(output.shape)
        for index in _indices(a.shape):
            if not at(1, index):
                continue
            target = tuple(
                0 if axis in p.axes else value
                for axis, value in enumerate(index)
                if p.keep_dims or axis not in p.axes
            ) or (0,)
            position = _offset(output.shape, target)
            value, previous = at(0, index), reduced[position]
            if p.reduction == "sum":
                reduced[position] = _i32((previous or 0) + value)
            else:
                reduced[position] = value if previous is None else max(previous, value)
        raw = [p.empty_value if n is None else n for n in reduced]
    else:
        raw = []
        for index in _indices(output.shape):
            if isinstance(p, GatherParameters):
                stop = p.axis + len(specs[1].shape)
                selected = at(1, index[p.axis : stop])
                source = index[: p.axis] + (selected,) + index[stop:]
                value = at(0, source)
            elif isinstance(p, LookupParameters):
                selected = at(1, index) + p.offset
                if not 0 <= selected < len(data[0]):
                    raise WireError("INPUT_INVALID")
                value = data[0][selected]
            elif isinstance(p, TransposeParameters):
                source = tuple(index[p.permutation.index(axis)] for axis in range(len(index)))
                value = at(0, source)
            elif node.op == "affine":
                fraction = a.fractional_bits + specs[1].fractional_bits
                value = at(2, (index[-1],))
                for k in range(a.shape[-1]):
                    product = _i32(at(0, index[:-1] + (k,)) * at(1, (index[-1], k)))
                    value = _i32(value + product)
            elif isinstance(p, MultiplyParameters) and p.mode == "matmul":
                fraction = a.fractional_bits + specs[1].fractional_bits
                value = 0
                for k in range(a.shape[-1]):
                    product = _i32(at(0, index[:-1] + (k,)) * at(1, index[:-2] + (k, index[-1])))
                    value = _i32(value + product)
            elif isinstance(p, MultiplyParameters):
                fraction = a.fractional_bits + specs[1].fractional_bits
                value = _i32(at(0, index) * at(1, index))
            elif node.op == "add":
                fraction = max(a.fractional_bits, specs[1].fractional_bits)
                left = _i32(at(0, index) << (fraction - a.fractional_bits))
                right = _i32(at(1, index) << (fraction - specs[1].fractional_bits))
                value = _i32(left + right)
            elif node.op == "relu":
                value = max(0, at(0, index))
            else:
                raise WireError("INPUT_INVALID")
            raw.append(value)
    return tuple(_i32(_rescale(value, fraction, output.fractional_bits)) for value in raw)
