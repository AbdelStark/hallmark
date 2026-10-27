"""Exact classifier circuits for the frozen Circle STARK comparison.

Shared byte/CBOR/SHA binding is constrained; host context reconstruction and
enrollment remain caller duties. These are fixed classifier circuits, not a VM.
"""

from circle_circuit import SHA_INITIAL, Circuit, compress, digest_bytes, word
from circle_integer import affine, affine32, maximum, relu, rounded, rounded_bits, strict_verdict

from hallmark.wire import decode, encode

CAPACITY = 96
ENCODED = 2 * CAPACITY + 6
RULE_PROFILE = bytes.fromhex("793a7a11ef3a2f0e9e556fb5ada8b4b8e40ed27a576e43c1af4f332a9a733f88")


def public_values(public):
    if (
        type(public) is not list
        or len(public) != 100
        or any(type(v) is not int for v in public)
        or any(not 0 <= v <= 255 for v in public[:96])
        or not 0 <= public[96] <= 96
        or not 1 <= public[97] <= 24
        or not 0 <= public[98] < 2**32
        or public[99] not in (0, 1)
    ):
        raise ValueError("noncanonical classifier public statement")
    return [0, 1, *public[:98], public[98] & 65535, public[98] >> 16, public[99]]


def equal_bits(circuit, bits, value):
    result = circuit.one
    for i, bit in enumerate(bits):
        result = circuit.multiply(result, bit if (value >> i) & 1 else circuit.bit_not(bit))
    return result


def lookup(circuit, table, index):
    width = (len(table) - 1).bit_length()
    bits = circuit.bits(index, width)
    values = list(table) + [circuit.zero] * ((1 << width) - len(table))
    for bit in bits:
        values = [circuit.select(bit, values[j + 1], values[j]) for j in range(0, len(values), 2)]
    return values[0]


def prefix(circuit, flags, count):
    previous = circuit.one
    for flag in flags:
        circuit.boolean(flag)
        circuit.bits(circuit.linear(previous, 1, flag, -1), 1)
        previous = flag
    circuit.equal(circuit.sum(flags), count)


def bind_input(circuit, raw, salt, profile):
    if (
        type(raw) is not bytes
        or len(raw) > 96
        or type(salt) is not bytes
        or len(salt) != 32
        or len(profile) != 32
    ):
        raise ValueError("unsupported complete byte input")
    for public_byte in circuit.wires[2:98]:
        circuit.bits(public_byte, 8)
    count = circuit.wires[98]
    circuit.bits(count, 7)
    circuit.bits(circuit.linear(count, -1, constant=96), 7)
    units = [circuit.private(v, 0, 255) for v in raw + bytes(96 - len(raw))]
    flags = [circuit.private(int(i < len(raw)), 0, 1) for i in range(96)]
    prefix(circuit, flags, count)
    unit_bits = []
    for unit, flag in zip(units, flags, strict=True):
        unit_bits.append(circuit.bits(unit, 8))
        circuit.assert_zero(circuit.multiply(circuit.bit_not(flag), unit))
    integer = encode(len(raw))
    packed = integer + encode(list(raw))
    data = [circuit.private(v, 0, 255) for v in packed + bytes(ENCODED - len(packed))]
    for byte in data:
        circuit.bits(byte, 8)
    wide = circuit.bits(circuit.linear(count, constant=104), 8)[7]
    width = circuit.linear(wide, constant=1)
    header = circuit.select(wide, circuit.constant(24), count)
    circuit.equal(data[0], header)
    circuit.equal(lookup(circuit, data, width), circuit.linear(header, constant=128))
    circuit.assert_zero(circuit.multiply(wide, circuit.linear(data[1], 1, count, -1)))
    circuit.assert_zero(
        circuit.multiply(
            wide,
            circuit.linear(lookup(circuit, data, circuit.linear(width, constant=1)), 1, count, -1),
        )
    )
    position = circuit.linear(width, 2)
    for unit, flag in zip(units, flags, strict=True):
        two = circuit.bits(circuit.linear(unit, constant=232), 9)[8]
        first = circuit.select(two, circuit.constant(24), unit)
        actual = lookup(circuit, data, circuit.multiply(flag, position))
        circuit.assert_zero(circuit.multiply(flag, circuit.linear(actual, 1, first, -1)))
        second_active = circuit.multiply(flag, two)
        actual = lookup(
            circuit, data, circuit.multiply(second_active, circuit.linear(position, constant=1))
        )
        circuit.assert_zero(circuit.multiply(second_active, circuit.linear(actual, 1, unit, -1)))
        position = circuit.linear(circuit.linear(position, 1, flag, 1), 1, second_active, 1)
    active = [circuit.private(int(i < len(packed)), 0, 1) for i in range(ENCODED)]
    prefix(circuit, active, position)
    for byte, flag in zip(data, active, strict=True):
        circuit.assert_zero(circuit.multiply(circuit.bit_not(flag), byte))
    tag = b"hallmark/v1/input"
    fixed = len(tag).to_bytes(4, "big") + tag + bytes([0x84, 0x58, 0x20])
    preimage = [circuit.constant(v) for v in fixed]
    preimage += [circuit.private(v, 0, 255) for v in salt]
    preimage += [circuit.constant(v) for v in bytes([0x58, 0x20]) + profile]
    base = len(preimage)
    preimage += data
    length = circuit.linear(position, constant=base)
    length_bits = circuit.bits(length, 9)
    block_bits = circuit.bits(circuit.linear(length, constant=72), 9)[6:]
    last = [equal_bits(circuit, block_bits, i + 1) for i in range(5)]
    circuit.equal(circuit.sum(last), circuit.one)
    low_length = circuit.from_bits([circuit.zero] * 3 + length_bits[:5])
    high_length = circuit.from_bits(length_bits[5:])
    message_active = [circuit.one] * base + active
    preimage += [circuit.zero] * (320 - len(preimage))
    message_active += [circuit.zero] * (320 - len(message_active))
    padded = []
    previous = circuit.one
    for i, (byte, flag) in enumerate(zip(preimage, message_active, strict=True)):
        at_end = circuit.linear(previous, 1, flag, -1)
        previous = flag
        value = circuit.linear(byte, 1, at_end, 128)
        for block in range(5):
            if i == (block + 1) * 64 - 2:
                value = circuit.linear(value, 1, circuit.multiply(last[block], high_length), 1)
            if i == (block + 1) * 64 - 1:
                value = circuit.linear(value, 1, circuit.multiply(last[block], low_length), 1)
        padded.append(circuit.bits(value, 8))
    state = [word(circuit, value) for value in SHA_INITIAL]
    selected = [circuit.zero] * 32
    for block in range(5):
        state = compress(circuit, state, padded[block * 64 : (block + 1) * 64])
        result = digest_bytes(circuit, state)
        selected = [
            circuit.linear(old, 1, circuit.multiply(last[block], new), 1)
            for old, new in zip(selected, result, strict=True)
        ]
    for i, byte in enumerate(selected):
        circuit.equal(byte, circuit.wires[66 + i])
    return units, flags, unit_bits


def new_circuit(public):
    external = public_values(public)
    bounds = [(0, 0), (1, 1)] + [(0, 255)] * 96 + [(0, 96), (1, 24), (0, 65535), (0, 65535), (0, 1)]
    return Circuit(external, bounds)


def rule(public, raw, salt):
    circuit = new_circuit(public)
    units, active, bits = bind_input(circuit, raw, salt, RULE_PROFILE)
    circuit.equal(circuit.wires[99], circuit.linear(circuit.sum(active[4::4]), constant=1))
    circuit.equal(circuit.wires[100], circuit.one)
    circuit.equal(circuit.wires[101], circuit.constant(32768))
    no_match = circuit.one
    for i in range(94):
        matched = active[i + 2]
        for j, byte in enumerate(b"BAD"):
            matched = circuit.multiply(matched, equal_bits(circuit, bits[i + j], byte))
        no_match = circuit.multiply(no_match, circuit.bit_not(matched))
    circuit.equal(no_match, circuit.wires[102])
    return circuit


def mlp(public, raw, salt, exported):
    c = new_circuit(public)
    _, active, bits = bind_input(c, raw, salt, exported["profile"].identity())
    c.equal(c.wires[99], c.one)
    counts = [c.zero] * 256
    for flag, byte_bits in zip(active, bits, strict=True):
        selected = [flag]
        for bit in byte_bits:
            selected = [c.multiply(v, c.bit_not(bit)) for v in selected] + [
                c.multiply(v, bit) for v in selected
            ]
        counts = [c.linear(a, 1, b, 1) for a, b in zip(counts, selected, strict=True)]
    c.equal(c.sum(counts), c.wires[98])
    model = exported["model"]
    if len(model["hidden_bias"]) != 4 or any(len(r) != 256 for r in model["hidden_weights"]):
        raise ValueError("only the four-hidden-unit byte-count MLP is supported")
    accumulators = [
        affine(c, counts, weights, bias)
        for weights, bias in zip(model["hidden_weights"], model["hidden_bias"], strict=True)
    ]
    hidden = [rounded(c, v, model["first_fraction"]) for v in accumulators]
    activated = [relu(c, v) for v in hidden]
    output = affine(c, activated, model["output_weights"], model["output_bias"])
    score = rounded(c, output, model["last_fraction"])
    strict_verdict(c, score, 0)
    return c, dict(
        counts=counts,
        accumulators=accumulators,
        hidden=hidden,
        relu=activated,
        output=output,
        score=score,
    )


def encoder(public, raw, salt, exported):
    c = new_circuit(public)
    units, mask, _ = bind_input(c, raw, salt, exported["profile"].identity())
    c.equal(c.wires[99], c.one)
    constants = decode(exported["weights"])["tensors"]
    specs = {s.name: s for s in exported["arithmetic"].tensors}
    if (
        specs["embedding"].shape != (256, 4)
        or specs["convolution-w"].shape != (32, 96)
        or specs["tokens"].shape != (96,)
        or len(constants["window-index"]) != 96 * 24
        or len(constants["causal-mask"]) != 96 * 24
    ):
        raise ValueError("only the fixed 96-position, width-24, 32-channel CNN is supported")
    table = constants["embedding"]
    embedded = [
        lookup(c, [c.constant(table[i * 4 + dim]) for i in range(256)], unit)
        for unit in units
        for dim in range(4)
    ]
    active = [c.multiply(value, mask[i // 4]) for i, value in enumerate(embedded)]
    window = [active[index * 4 + dim] for index in constants["window-index"] for dim in range(4)]
    flat = [c.linear(value, constants["causal-mask"][i // 4]) for i, value in enumerate(window)]
    shift = (
        specs["flat"].fractional_bits
        + specs["convolution-w"].fractional_bits
        - specs["convolution"].fractional_bits
    )
    accumulators, convolution, activated = [], [], []
    for pos in range(96):
        row = flat[pos * 96 : (pos + 1) * 96]
        for channel in range(32):
            acc = affine(
                c,
                row,
                constants["convolution-w"][channel * 96 : (channel + 1) * 96],
                constants["convolution-b"][channel],
            )
            z = rounded(c, acc, shift)
            accumulators.append(acc)
            convolution.append(z)
            activated.append(relu(c, z))
    pooled = []
    for channel in range(32):
        value = c.zero
        for pos in range(96):
            value = maximum(c, value, c.select(mask[pos], activated[pos * 32 + channel], c.zero))
        pooled.append(value)
    twos, sign = affine32(c, pooled, constants["score-w"], constants["score-b"][0])
    shift = (
        specs["pooled"].fractional_bits
        + specs["score-w"].fractional_bits
        - specs["score"].fractional_bits
    )
    score = rounded_bits(c, twos, sign, shift)
    strict_verdict(c, score, -3733)
    return c, dict(
        embedded=embedded,
        **{"row-mask": mask},
        active=active,
        **{"window-values": window, "causal-values": flat},
        flat=flat,
        convolution=convolution,
        relu=activated,
        pooled=pooled,
        score=[score],
        accumulators=accumulators,
        head_twos=twos,
        head_sign=sign,
    )
