"""An independent Decimal oracle checks the complete bounded integer domain."""

import json
import runpy
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
BUILDER = runpy.run_path(str(ROOT / "scripts/build_gnark_normalization_fixture.py"))
CONTROLLER = runpy.run_path(str(ROOT / "scripts/check_gnark_normalization.py"))


def test_normalization_frozen_fixture_and_independent_oracle():
    fixture = BUILDER["build"]()
    assert fixture == json.loads(
        (ROOT / "research/probes/gnark/normalization-fixture.json").read_text()
    )
    assert len(fixture["cases"]) == 289
    with localcontext() as context:
        context.prec = 80
        for case in fixture["cases"]:
            a, b = [Decimal(x - 2**31) for x in case["public"][:2]]
            mean = ((a + b) / 2).to_integral_value()
            centered = [a - mean, b - mean]
            squares = [x**2 for x in centered]
            variance = (sum(squares) / 2).to_integral_value()
            inverse = (Decimal(256) / (variance + 1).sqrt()).to_integral_value()
            normalized = [x * inverse for x in centered]
            output = [normalized[0] + 256, -2 * normalized[1] - 256]
            assert case["trace"] == [
                int(x) for x in [mean, *centered, *squares, variance, inverse, *normalized, *output]
            ]
            assert case["public"][2:] == [int(x) + 2**31 for x in output]


@pytest.mark.parametrize("value", [-9, 9, True, 0.5, "0"])
def test_normalization_rejects_values_outside_frozen_domain(value):
    with pytest.raises(ValueError):
        BUILDER["evaluate"](value, 0)


def test_constant_rows_have_zero_normalized_values():
    for value in range(-8, 9):
        trace, output = BUILDER["evaluate"](value, value)
        assert trace[5:9] == [0, 256, 0, 0]
        assert output == [256, -256]


@pytest.mark.parametrize("change", ["duplicate", "name", "boolean", "trace", "graph", "output"])
def test_normalization_controller_rejects_malformed_fixture(change):
    fixture = BUILDER["build"]()
    assert CONTROLLER["validate_fixture"](json.dumps(fixture).encode()) == fixture
    row = fixture["cases"][0]
    if change == "duplicate":
        fixture["cases"][-1] = row
    elif change == "name":
        row["name"] = "../outside"
    elif change == "boolean":
        row["public"][0] = True
    elif change == "trace":
        row["trace"].pop()
    elif change == "graph":
        fixture["graph"]["epsilon"] = 0
    else:
        row["public"][2] ^= 1
    with pytest.raises(ValueError):
        CONTROLLER["validate_fixture"](json.dumps(fixture).encode())
