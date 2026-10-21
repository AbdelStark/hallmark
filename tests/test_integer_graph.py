"""Exact operator execution, resource limits and unscaled overflow boundaries."""

import hashlib
import itertools
import random
from fractions import Fraction

import pytest

from hallmark.classifier_manifest import ArithmeticProfile, NodeSpec, TensorSpec
from hallmark.integer_graph import IntegerGraph
from hallmark.manifests import FileRef
from hallmark.wire import WireError, encode


def tensor(name, shape, low=-100, high=100, fraction=0):
    return TensorSpec(
        name=name, shape=shape, signed_bits=32, fractional_bits=fraction, minimum=low, maximum=high
    )


def graph(op, specs, output, **options):
    raw = encode({"schema_id": "hallmark/operator-parameters/1", "op": op, **options})
    ref = FileRef(path="params.cbor", size=len(raw), sha256=hashlib.sha256(raw).digest())
    profile = ArithmeticProfile(
        schema_id="hallmark/arithmetic/1",
        tensors=(*specs, output),
        nodes=(
            NodeSpec(
                id="test",
                op=op,
                inputs=tuple(t.name for t in specs),
                output=output.name,
                parameters=ref,
            ),
        ),
        output=output.name,
    )
    return IntegerGraph(profile, constants={}, parameters={"params.cbor": raw})


def test_seeded_batched_matmul_broadcast():
    rng = random.Random(20261021)
    g = graph(
        "multiply",
        (tensor("a", (2, 2, 3), -4, 4), tensor("b", (1, 3, 2), -4, 4)),
        tensor("out", (2, 2, 2), -48, 48),
        mode="matmul",
    )
    for _ in range(50):
        a = tuple(rng.randrange(-4, 5) for _ in range(12))
        b = tuple(rng.randrange(-4, 5) for _ in range(6))
        expected = tuple(
            sum(a[batch * 6 + row * 3 + k] * b[k * 2 + col] for k in range(3))
            for batch in range(2)
            for row in range(2)
            for col in range(2)
        )
        assert g.evaluate({"a": a, "b": b})["out"] == expected


def test_gather_middle_axis_and_multidimensional_indices():
    g = graph(
        "gather",
        (tensor("a", (2, 3, 2), 0, 11), tensor("indices", (2, 1), 0, 2)),
        tensor("out", (2, 2, 1, 2), 0, 11),
        axis=1,
    )
    assert g.evaluate({"a": tuple(range(12)), "indices": (2, 0)})["out"] == (
        4,
        5,
        0,
        1,
        10,
        11,
        6,
        7,
    )


def test_transpose_four_dimensions():
    g = graph(
        "transpose",
        (tensor("a", (2, 1, 3, 2), 0, 11),),
        tensor("out", (2, 3, 2, 1), 0, 11),
        permutation=[3, 2, 0, 1],
    )
    expected = tuple(a * 6 + b * 2 + c for c in range(2) for b in range(3) for a in range(2))
    assert g.evaluate({"a": tuple(range(12))})["out"] == expected


@pytest.mark.parametrize("reduction", ["sum", "max"])
@pytest.mark.parametrize("keep", [True, False])
def test_multiaxis_reduction_broadcast_negative_and_empty(reduction, keep):
    shape = (1, 3, 1) if keep else (3,)
    low, high = (-36, 0) if reduction == "sum" else (-9, -1)
    empty = 0 if reduction == "sum" else -7
    g = graph(
        "masked-reduce",
        (tensor("a", (2, 3, 2), -9, -1), tensor("mask", (2, 1, 1), 0, 1)),
        tensor("out", shape, min(low, empty), max(high, empty)),
        axes=[0, 2],
        keep_dims=keep,
        reduction=reduction,
        empty_value=empty,
    )
    a = (-1, -2, -3, -4, -5, -6) * 2
    for mask in itertools.product(range(2), repeat=2):
        rows = [
            [a[batch * 6 + j * 2 + k] for batch in range(2) for k in range(2) if mask[batch]]
            for j in range(3)
        ]
        expected = tuple(
            (sum(row) if reduction == "sum" else max(row, default=empty)) for row in rows
        )
        assert g.evaluate({"a": a, "mask": mask})["out"] == expected


def test_elementwise_scale_alignment_and_negative_ties():
    g = graph(
        "add",
        (tensor("a", (2, 1), -9, 9, 1), tensor("b", (1, 3), -9, 9, 2)),
        tensor("out", (2, 3), -7, 7),
    )
    a, b = (-3, 3), (0, 1, -1)
    assert g.evaluate({"a": a, "b": b})["out"] == tuple(
        round(Fraction(x, 2) + Fraction(y, 4)) for x in a for y in b
    )
    g = graph(
        "multiply",
        (tensor("a", (2, 1), -9, 9, 1), tensor("b", (1, 3), -9, 9, 2)),
        tensor("out", (2, 3), -11, 11),
        mode="elementwise",
    )
    assert g.evaluate({"a": a, "b": b})["out"] == tuple(
        round(Fraction(x * y, 8)) for x in a for y in b
    )


def test_affine_and_relu_rounding():
    g = graph(
        "affine",
        (tensor("x", (2, 2), -3, 3), tensor("w", (1, 2), -2, 2, 1), tensor("bias", (1,), -1, 1, 1)),
        tensor("out", (2, 1), -6, 6),
    )
    assert g.evaluate({"x": (-1, 2, 3, -2), "w": (1, -1), "bias": (0,)})["out"] == (-2, 2)
    relu = graph("relu", (tensor("x", (4,), -9, 9, 1),), tensor("out", (4,), 0, 4))
    assert relu.evaluate({"x": (-1, 1, 3, 5)})["out"] == (0, 0, 2, 2)


def test_lookup_offset_and_preserved_scale():
    g = graph(
        "lookup",
        (tensor("table", (3,), -9, 7, 3), tensor("index", (2, 2), -1, 1)),
        tensor("out", (2, 2), -9, 7, 3),
        offset=1,
    )
    assert g.evaluate({"table": (7, -9, 4), "index": (-1, 0, 1, -1)})["out"] == (7, -9, 4, 7)


@pytest.mark.parametrize(
    "inputs",
    [
        {},
        {"x": (0, 0), "extra": (1,)},
        {"x": [0, 0]},
        {"x": (True, 0)},
        {"x": (1.0, 0)},
        {"x": (0,)},
        {"x": (0, 11)},
    ],
)
def test_reject_malformed_roots(inputs):
    g = graph("reshape", (tensor("x", (2,), -10, 10),), tensor("out", (1, 2), -10, 10))
    with pytest.raises(WireError):
        g.evaluate(inputs)


@pytest.mark.parametrize("op", ["add", "multiply", "affine", "masked-reduce"])
def test_unscaled_overflow_cannot_hide_behind_rescaling(op):
    maximum = 2**31 - 1
    if op == "add":
        g = graph(
            op,
            (tensor("x", (1,), maximum, maximum, 1), tensor("y", (1,), maximum, maximum, 1)),
            tensor("out", (1,), maximum, maximum),
        )
        values = {"x": (maximum,), "y": (maximum,)}
    elif op == "multiply":
        g = graph(
            op,
            (tensor("x", (1,), maximum, maximum, 1), tensor("y", (1,), 2, 2)),
            tensor("out", (1,), maximum, maximum),
            mode="elementwise",
        )
        values = {"x": (maximum,), "y": (2,)}
    elif op == "affine":
        g = graph(
            op,
            (
                tensor("x", (2,), maximum, maximum, 1),
                tensor("w", (1, 2), 1, 1),
                tensor("bias", (1,), 0, 0, 1),
            ),
            tensor("out", (1,), maximum, maximum),
        )
        values = {"x": (maximum, maximum), "w": (1, 1), "bias": (0,)}
    else:
        g = graph(
            op,
            (tensor("x", (2,), maximum, maximum, 1), tensor("mask", (2,), 0, 1)),
            tensor("out", (1,), 0, maximum),
            axes=[0],
            keep_dims=False,
            reduction="sum",
            empty_value=0,
        )
        values = {"x": (maximum, maximum), "mask": (1, 1)}
    with pytest.raises(WireError):
        g.evaluate(values)


def test_huge_dimensions_reject_before_allocation():
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        graph("reshape", (tensor("x", (2**63,)),), tensor("out", (2**63,)))


def test_large_matrix_work_rejects_before_execution():
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        graph(
            "multiply",
            (tensor("x", (128, 128), 0, 1), tensor("y", (128, 128), 0, 1)),
            tensor("out", (128, 128), 0, 128),
            mode="matmul",
        )
