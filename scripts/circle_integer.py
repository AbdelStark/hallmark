"""Constrained signed arithmetic for the fixed classifier circuits.

Narrow values have a derived interval smaller than M31. Wide accumulators keep
two 16-bit limbs: field equality alone cannot identify a signed 32-bit integer.
"""

from circle_circuit import Wire


def signed_parts(circuit, value):
    width = max(1, (-value.low - 1).bit_length() + 1, value.high.bit_length() + 1)
    if width > 30:
        raise ValueError("signed interval requires limb arithmetic")
    bits = circuit.bits(circuit.linear(value, constant=1 << (width - 1)), width)
    negative = circuit.bit_not(bits[-1])
    return bits[:-1] + [negative], negative


def absolute_bits(circuit, twos, negative):
    carry = negative
    result = []
    for bit in twos:
        inverted = circuit.bit_xor(bit, negative)
        result.append(circuit.bit_xor(inverted, carry))
        carry = circuit.multiply(inverted, carry)
    return result


def rounded_bits(circuit, twos, negative, shift):
    if not 1 <= shift < len(twos) or len(twos) - shift > 30:
        raise ValueError("unsupported rounding shift")
    bits = absolute_bits(circuit, twos, negative)
    quotient = circuit.from_bits(bits[shift:])
    low_zero = circuit.one
    for bit in bits[: shift - 1]:
        low_zero = circuit.multiply(low_zero, circuit.bit_not(bit))
    # Round half to even: round up iff half-bit and (lower remainder or odd quotient).
    upward = circuit.multiply(
        bits[shift - 1],
        circuit.bit_not(circuit.multiply(low_zero, circuit.bit_not(bits[shift]))),
    )
    magnitude = circuit.linear(quotient, 1, upward, 1)
    result = circuit.linear(magnitude, 1, circuit.multiply(negative, magnitude), -2)
    bound = 1 << (len(twos) - 1 - shift)
    return Wire(result.index, result.value, -bound, bound)


def rounded(circuit, value, shift):
    if shift == 0:
        return value
    twos, negative = signed_parts(circuit, value)
    return rounded_bits(circuit, twos, negative, shift)


def relu(circuit, value):
    _, negative = signed_parts(circuit, value)
    result = circuit.select(negative, circuit.zero, value)
    return Wire(result.index, result.value, 0, max(0, value.high))


def maximum(circuit, left, right):
    _, negative = signed_parts(circuit, circuit.linear(left, 1, right, -1))
    return circuit.select(negative, right, left)


def affine(circuit, values, weights, bias):
    result = circuit.constant(bias)
    for value, weight in zip(values, weights, strict=True):
        result = circuit.linear(result, 1, value, weight)
        if result.low < -(2**31) or result.high >= 2**31:
            raise ValueError("static affine interval needs signed 32-bit limbs")
    return result


def signed32(circuit, value):
    if not -(2**31) <= value < 2**31:
        raise ValueError("native signed 32-bit overflow")
    biased = value + 2**31
    limbs = [circuit.private((biased >> i) & 65535, 0, 65535) for i in (0, 16)]
    bits = [bit for limb in limbs for bit in circuit.bits(limb, 16)]
    return limbs, bits


def affine32(circuit, values, weights, bias):
    """Bias-first exact i32 sums; low/high limb equations rule out M31 aliases."""
    if not -(2**31) <= bias < 2**31:
        raise ValueError("native signed 32-bit overflow")
    total = bias
    limbs = [circuit.constant((bias + 2**31) & 65535), circuit.constant((bias + 2**31) >> 16)]
    bits = None
    for value, weight in zip(values, weights, strict=True):
        if not 0 <= value.low <= value.high or value.high * abs(weight) >= 2**30:
            raise ValueError("wide affine product requires a nonnegative narrow input")
        product = circuit.linear(value, abs(weight))
        product_bits = circuit.bits(product, max(1, (value.high * abs(weight)).bit_length()))
        low = circuit.from_bits(product_bits[:16])
        high = circuit.from_bits(product_bits[16:])
        sign = -1 if weight < 0 else 1
        low_sum = limbs[0].value + sign * low.value
        carry_value = low_sum // 65536
        carry_advice = circuit.private(carry_value + 1, 0, 3)
        circuit.bits(carry_advice, 2)
        carry = circuit.linear(carry_advice, constant=-1)
        total += value.value * weight
        next_limbs, bits = signed32(circuit, total)
        circuit.equal(
            circuit.linear(limbs[0], 1, low, sign),
            circuit.linear(next_limbs[0], 1, carry, 65536),
        )
        circuit.equal(
            next_limbs[1], circuit.linear(circuit.linear(limbs[1], 1, high, sign), 1, carry, 1)
        )
        limbs = next_limbs
    if bits is None:
        limbs, bits = signed32(circuit, total)
        for limb, expected in zip(limbs, (bias + 2**31 & 65535, (bias + 2**31) >> 16), strict=True):
            circuit.equal(limb, circuit.constant(expected))
    negative = circuit.bit_not(bits[-1])
    return bits[:-1] + [negative], negative


def strict_verdict(circuit, score, threshold):
    _, negative = signed_parts(circuit, circuit.linear(score, constant=-threshold))
    circuit.equal(negative, circuit.wires[102])
    biased = threshold + 2**31
    circuit.equal(circuit.wires[100], circuit.constant(biased & 65535))
    circuit.equal(circuit.wires[101], circuit.constant(biased >> 16))
