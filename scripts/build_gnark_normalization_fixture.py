"""Freeze a bounded integer normalization relation, not floating model equivalence."""

import hashlib
import itertools
import json
import math
from fractions import Fraction


def inverse(variance):
    denominator = variance + 1
    lower = math.isqrt(256**2 // denominator)
    midpoint = denominator * (2 * lower + 1) ** 2
    return lower + int(midpoint < 4 * 256**2 or (midpoint == 4 * 256**2 and lower % 2))


INVERSE = [inverse(n) for n in range(65)]


def evaluate(a, b):
    if any(type(x) is not int or not -8 <= x <= 8 for x in (a, b)):
        raise ValueError("normalization input outside frozen domain")
    mean = round(Fraction(a + b, 2))
    centered = [a - mean, b - mean]
    squared = [x * x for x in centered]
    variance = round(Fraction(sum(squared), 2))
    scale = INVERSE[variance]
    normalized = [x * scale for x in centered]
    output = [normalized[0] + 256, -2 * normalized[1] - 256]
    trace = [mean, *centered, *squared, variance, scale, *normalized, *output]
    assert len(trace) == 11 and all(-(2**31) <= x < 2**31 for x in trace)
    return trace, output


def build():
    graph = {
        "features": 2,
        "input_range": [-8, 8],
        "rounding": "nearest-ties-even",
        "variance": "mean squared difference from rounded mean",
        "epsilon": 1,
        "inverse_fractional_bits": 8,
        "inverse_table": INVERSE,
        "gamma": [1, -2],
        "beta": [1, -1],
        "output_fractional_bits": 8,
        "trace_order": [
            "mean",
            "centered-0",
            "centered-1",
            "square-0",
            "square-1",
            "variance",
            "inverse",
            "normalized-0",
            "normalized-1",
            "output-0",
            "output-1",
        ],
    }
    cases = []
    for a, b in itertools.product(range(-8, 9), repeat=2):
        trace, output = evaluate(a, b)
        cases.append(
            {
                "name": f"input-{a + 8}-{b + 8}",
                "public": [x + 2**31 for x in [a, b, *output]],
                "trace": trace,
            }
        )
    return {
        "schema_id": "hallmark.gnark-normalization-fixture/1",
        "qualified_backend": False,
        "graph": graph,
        "graph_sha256": hashlib.sha256(
            json.dumps(graph, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "cases": cases,
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
