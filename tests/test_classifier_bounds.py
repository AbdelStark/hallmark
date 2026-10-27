"""Interval relaxation must cover every small-domain native ReLU/rounding case."""

import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_classifier_bounds import mlp_bounds


def test_signed_relu_and_rounding_intervals_cover_exhaustive_two_byte_counts():
    model = dict(
        hidden_weights=[[3, -5], [-2, 7]],
        hidden_bias=[-1, 3],
        output_weights=[-3, 5],
        output_bias=-2,
        first_fraction=1,
        last_fraction=2,
    )
    bounds = mlp_bounds(model, 8)
    values = []
    for first in range(9):
        for second in range(9 - first):
            hidden = [
                max(0, round(Fraction(bias + first * w[0] + second * w[1], 2)))
                for w, bias in zip(model["hidden_weights"], model["hidden_bias"], strict=True)
            ]
            score = round(
                Fraction(
                    model["output_bias"]
                    + sum(w * h for w, h in zip(model["output_weights"], hidden, strict=True)),
                    4,
                )
            )
            values.append(score)
    assert bounds["score"][0] <= min(values) <= max(values) <= bounds["score"][1]
    assert bounds["tight_bound"] is False and bounds["held_out_evaluation"] is False


@pytest.mark.parametrize("capacity", [-1, 97, True])
def test_interval_cannot_silently_extend_the_frozen_domain(capacity):
    with pytest.raises(ValueError, match="domain"):
        mlp_bounds({}, capacity)
