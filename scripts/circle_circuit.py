"""Fixed arithmetic/Boolean circuit construction over M31, not a virtual machine.

A wire is either caller-public, a deliberately constrained private input, or the
output of one enrolled equation. Python values generate witnesses only; the
serialized program contains wiring/constants and never specializes on a witness.
"""

from dataclasses import dataclass

P = 2**31 - 1
MAX_GATES = 2**22


@dataclass(frozen=True)
class Wire:
    index: int
    value: int
    low: int
    high: int
    constant: bool = False


class Circuit:
    def __init__(self, external, bounds=None):
        if not 2 <= len(external) <= 1024 or external[:2] != [0, 1]:
            raise ValueError("public wires start with zero and one")
        if any(type(v) is not int or not 0 <= v < P for v in external):
            raise ValueError("noncanonical public field")
        bounds = bounds or [(0, P - 1)] * len(external)
        if len(bounds) != len(external):
            raise ValueError("public bounds mismatch")
        self.external = len(external)
        self.wires = [Wire(i, v, *bounds[i], i < 2) for i, v in enumerate(external)]
        self.wires[:2] = [Wire(0, 0, 0, 0, True), Wire(1, 1, 1, 1, True)]
        self.gates = []
        self.constants = {0: self.wires[0], 1: self.wires[1]}
        self.bit_cache = {}

    @property
    def zero(self):
        return self.wires[0]

    @property
    def one(self):
        return self.wires[1]

    def _gate(self, mode, a, b, qa, qb, qm, qk, value, low, high, *, constant=False):
        if len(self.gates) >= MAX_GATES:
            raise ValueError("circuit gate cap exceeded")
        self.gates.append(
            dict(mode=mode, a=a.index, b=b.index, qa=qa % P, qb=qb % P, qm=qm % P, qk=qk % P)
        )
        wire = Wire(len(self.wires), value, low, high, constant)
        self.wires.append(wire)
        return wire

    def constant(self, value):
        if value not in self.constants:
            self.constants[value] = self._gate(
                1, self.zero, self.zero, 0, 0, 0, value, value, value, value, constant=True
            )
        return self.constants[value]

    def private(self, value, low, high):
        if type(value) is not int or not low <= value <= high:
            raise ValueError("honest private witness outside its declared range")
        # The application must add its range/semantic constraints; bounds are not AIR constraints.
        return self._gate(0, self.zero, self.zero, 0, 0, 0, 0, value, low, high)

    def linear(self, a, qa=1, b=None, qb=0, constant=0):
        b = self.zero if b is None else b
        if a.constant:
            constant += qa * a.value
            qa = 0
        if b.constant:
            constant += qb * b.value
            qb = 0
        if qa == qb == 0:
            return self.constant(constant)
        if qa == 1 and qb == constant == 0:
            return a
        aa, bb = (qa * a.low, qa * a.high), (qb * b.low, qb * b.high)
        low, high = min(aa) + min(bb) + constant, max(aa) + max(bb) + constant
        return self._gate(
            1, a, b, qa, qb, 0, constant, qa * a.value + qb * b.value + constant, low, high
        )

    def multiply(self, a, b):
        if a.constant:
            return self.linear(b, a.value)
        if b.constant:
            return self.linear(a, b.value)
        endpoints = [x * y for x in (a.low, a.high) for y in (b.low, b.high)]
        return self._gate(1, a, b, 0, 0, 1, 0, a.value * b.value, min(endpoints), max(endpoints))

    def assert_zero(self, value):
        self._gate(2, value, self.zero, 1, 0, 0, 0, 0, 0, 0)

    def equal(self, a, b):
        self._gate(2, a, b, 1, -1, 0, 0, 0, 0, 0)

    def boolean(self, value):
        self._gate(2, value, value, -1, 0, 1, 0, 0, 0, 0)

    def bit_not(self, a):
        return self.linear(a, -1, constant=1)

    def bit_xor(self, a, b):
        if a.constant:
            return self.bit_not(b) if a.value else b
        if b.constant:
            return self.bit_not(a) if b.value else a
        if not (0 <= a.low <= a.high <= 1 and 0 <= b.low <= b.high <= 1):
            raise ValueError("XOR requires constrained Boolean operands")
        return self._gate(1, a, b, 1, 1, -2, 0, a.value ^ b.value, 0, 1)

    def select(self, flag, yes, no):
        if not 0 <= flag.low <= flag.high <= 1:
            raise ValueError("selection requires constrained Boolean flag")
        if flag.constant:
            return yes if flag.value else no
        if yes.index == no.index:
            return yes
        if yes.constant and no.constant:
            return self.linear(flag, yes.value - no.value, constant=no.value)
        difference = self.linear(yes, 1, no, -1)
        result = self.linear(self.multiply(flag, difference), 1, no, 1)
        return Wire(result.index, result.value, min(yes.low, no.low), max(yes.high, no.high))

    def sum(self, values):
        result = self.zero
        for value in values:
            result = self.linear(result, 1, value, 1)
        return result

    def from_bits(self, bits):
        if len(bits) > 30:
            raise ValueError("M31 reconstruction requires at most 30 bits; use limbs")
        result = self.zero
        for i, bit in enumerate(bits):
            if not 0 <= bit.low <= bit.high <= 1:
                raise ValueError("non-Boolean reconstruction")
            result = self.linear(result, 1, bit, 1 << i)
        return result

    def bits(self, value, width):
        if not 0 <= width <= 30 or not 0 <= value.value < 1 << width:
            raise ValueError("unsigned bit decomposition outside supported range")
        key = (value.index, width)
        if key in self.bit_cache:
            return self.bit_cache[key]
        if value.constant:
            result = [self.constant((value.value >> i) & 1) for i in range(width)]
        else:
            result = [self.private((value.value >> i) & 1, 0, 1) for i in range(width)]
            for bit in result:
                self.boolean(bit)
            self.equal(value, self.from_bits(result))
        self.bit_cache[key] = result
        return result

    def program(self):
        return dict(schema="hallmark.gate-program/1", external=self.external, gates=self.gates)

    def witness(self):
        return [w.value % P for w in self.wires]

    def check_witness(self, values=None):
        values = self.witness() if values is None else values
        if len(values) != len(self.wires) or any(
            type(v) is not int or not 0 <= v < P for v in values
        ):
            return False
        for index, g in enumerate(self.gates, self.external):
            a, b = values[g["a"]], values[g["b"]]
            expression = (g["qm"] * a * b + g["qa"] * a + g["qb"] * b + g["qk"]) % P
            if (g["mode"] == 1 and values[index] != expression) or (
                g["mode"] == 2 and (expression != 0 or values[index] != 0)
            ):
                return False
        return True


SHA_INITIAL = (
    0x6A09E667,
    0xBB67AE85,
    0x3C6EF372,
    0xA54FF53A,
    0x510E527F,
    0x9B05688C,
    0x1F83D9AB,
    0x5BE0CD19,
)
SHA_K = (
    0x428A2F98,
    0x71374491,
    0xB5C0FBCF,
    0xE9B5DBA5,
    0x3956C25B,
    0x59F111F1,
    0x923F82A4,
    0xAB1C5ED5,
    0xD807AA98,
    0x12835B01,
    0x243185BE,
    0x550C7DC3,
    0x72BE5D74,
    0x80DEB1FE,
    0x9BDC06A7,
    0xC19BF174,
    0xE49B69C1,
    0xEFBE4786,
    0x0FC19DC6,
    0x240CA1CC,
    0x2DE92C6F,
    0x4A7484AA,
    0x5CB0A9DC,
    0x76F988DA,
    0x983E5152,
    0xA831C66D,
    0xB00327C8,
    0xBF597FC7,
    0xC6E00BF3,
    0xD5A79147,
    0x06CA6351,
    0x14292967,
    0x27B70A85,
    0x2E1B2138,
    0x4D2C6DFC,
    0x53380D13,
    0x650A7354,
    0x766A0ABB,
    0x81C2C92E,
    0x92722C85,
    0xA2BFE8A1,
    0xA81A664B,
    0xC24B8B70,
    0xC76C51A3,
    0xD192E819,
    0xD6990624,
    0xF40E3585,
    0x106AA070,
    0x19A4C116,
    0x1E376C08,
    0x2748774C,
    0x34B0BCB5,
    0x391C0CB3,
    0x4ED8AA4A,
    0x5B9CCA4F,
    0x682E6FF3,
    0x748F82EE,
    0x78A5636F,
    0x84C87814,
    0x8CC70208,
    0x90BEFFFA,
    0xA4506CEB,
    0xBEF9A3F7,
    0xC67178F2,
)


def word(circuit, value):
    return [circuit.constant((value >> i) & 1) for i in range(32)]


def rotate(bits, amount):
    return bits[amount:] + bits[:amount]


def shift(circuit, bits, amount):
    return bits[amount:] + [circuit.zero] * amount


def xor(circuit, *words):
    result = words[0]
    for other in words[1:]:
        result = [circuit.bit_xor(a, b) for a, b in zip(result, other, strict=True)]
    return result


def add_words(circuit, *words):
    """Exact mod-2^32 addition using two bounded 16-bit limbs and explicit carries."""
    if not 1 <= len(words) <= 8 or any(len(w) != 32 for w in words):
        raise ValueError("unsupported SHA word addition")
    low = circuit.sum([circuit.from_bits(w[:16]) for w in words])
    low_bits = circuit.bits(low, (len(words) * 65535).bit_length())
    carry = circuit.from_bits(low_bits[16:])
    high = circuit.sum([circuit.from_bits(w[16:]) for w in words] + [carry])
    high_bits = circuit.bits(high, (len(words) * 65535 + len(words) - 1).bit_length())
    return low_bits[:16] + high_bits[:16]


def compress(circuit, state, block):
    """FIPS 180-4 SHA-256 compression; all message words remain explicit bits."""
    if len(state) != 8 or len(block) != 64 or any(len(b) != 8 for b in block):
        raise ValueError("invalid SHA block shape")
    schedule = [sum((block[i + j] for j in (3, 2, 1, 0)), []) for i in range(0, 64, 4)]
    for i in range(16, 64):
        small0 = xor(
            circuit,
            rotate(schedule[i - 15], 7),
            rotate(schedule[i - 15], 18),
            shift(circuit, schedule[i - 15], 3),
        )
        small1 = xor(
            circuit,
            rotate(schedule[i - 2], 17),
            rotate(schedule[i - 2], 19),
            shift(circuit, schedule[i - 2], 10),
        )
        schedule.append(add_words(circuit, schedule[i - 16], small0, schedule[i - 7], small1))
    a, b, c, d, e, f, g, h = state
    for k, w in zip(SHA_K, schedule, strict=True):
        sigma1 = xor(circuit, rotate(e, 6), rotate(e, 11), rotate(e, 25))
        choose = xor(
            circuit, g, [circuit.multiply(x, y) for x, y in zip(e, xor(circuit, f, g), strict=True)]
        )
        t1 = add_words(circuit, h, sigma1, choose, word(circuit, k), w)
        sigma0 = xor(circuit, rotate(a, 2), rotate(a, 13), rotate(a, 22))
        majority = xor(
            circuit,
            [circuit.multiply(x, y) for x, y in zip(a, b, strict=True)],
            [circuit.multiply(x, y) for x, y in zip(c, xor(circuit, a, b), strict=True)],
        )
        t2 = add_words(circuit, sigma0, majority)
        h, g, f, e, d, c, b, a = (
            g,
            f,
            e,
            add_words(circuit, d, t1),
            c,
            b,
            a,
            add_words(circuit, t1, t2),
        )
    return [add_words(circuit, x, y) for x, y in zip(state, (a, b, c, d, e, f, g, h), strict=True)]


def digest_bytes(circuit, state):
    return [circuit.from_bits(w[start : start + 8]) for w in state for start in (24, 16, 8, 0)]


def sha256_fixed(circuit, message):
    """Known-length primitive. Variable classifier length must be constrained separately."""
    bits = [circuit.bits(b, 8) for b in message]
    pad = bytes([128]) + bytes((55 - len(message)) % 64) + (len(message) * 8).to_bytes(8, "big")
    bits += [[circuit.constant((b >> i) & 1) for i in range(8)] for b in pad]
    state = [word(circuit, v) for v in SHA_INITIAL]
    for i in range(0, len(bits), 64):
        state = compress(circuit, state, bits[i : i + 64])
    return digest_bytes(circuit, state)
