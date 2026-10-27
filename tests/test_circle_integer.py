import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from circle_circuit import Circuit
from circle_integer import affine32, maximum, relu, rounded, rounded_bits, strict_verdict


@pytest.mark.parametrize(
    "value", [-65536, -129, -65, -64, -63, -3, -1, 0, 1, 3, 63, 64, 65, 129, 65535]
)
@pytest.mark.parametrize("shift", [1, 6, 7])
def test_signed_rounding_relu_and_maximum(value, shift):
    c = Circuit([0, 1])
    v = c.private(value, -65536, 65535)
    result = rounded(c, v, shift)
    assert result.value == round(Fraction(value, 2**shift))
    assert relu(c, v).value == max(0, value)
    assert maximum(c, v, c.constant(42)).value == max(value, 42)
    assert c.check_witness()
    private_bit = next(
        i for i, g in enumerate(c.gates, c.external) if g["mode"] == 0 and i != v.index
    )
    mutated = c.witness()
    mutated[private_bit] ^= 1
    assert not c.check_witness(mutated)


@pytest.mark.parametrize(
    "bias,weight", [(-(2**31), 0), (2**31 - 1, 0), (-7, -28416), (65535, 24832)]
)
def test_limb_head_exact_rounding_and_advice_binding(bias, weight):
    c = Circuit([0, 1])
    x = c.private(1234, 0, 19816)
    c.bits(x, 15)
    twos, sign = affine32(c, [x], [weight], bias)
    result = rounded_bits(c, twos, sign, 15)
    assert result.value == round(Fraction(bias + 1234 * weight, 2**15))
    assert c.check_witness()
    for i, gate in enumerate(c.gates, c.external):
        if gate["mode"] == 0:
            mutated = c.witness()
            mutated[i] = (mutated[i] + 1) % (2**31 - 1)
            assert not c.check_witness(mutated)


def test_limb_head_rejects_native_overflow_and_unbounded_products():
    c = Circuit([0, 1])
    x = c.private(1, 0, 1)
    c.bits(x, 1)
    with pytest.raises(ValueError, match="overflow"):
        affine32(c, [x], [1], 2**31 - 1)
    with pytest.raises(ValueError, match="narrow input"):
        affine32(c, [x], [2**30], 0)


@pytest.mark.parametrize("threshold", [0, -3733])
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_strict_threshold_equality_blocks_and_public_claims_are_bound(threshold, offset):
    public = [0, 1] + [0] * 101
    biased = threshold + 2**31
    public[100:103] = [biased & 65535, biased >> 16, int(offset < 0)]
    c = Circuit(public)
    score = c.private(threshold + offset, threshold - 2, threshold + 2)
    strict_verdict(c, score, threshold)
    assert c.check_witness()
    for index in (100, 101, 102):
        changed = c.witness()
        changed[index] ^= 1
        assert not c.check_witness(changed)
