import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from circle_circuit import Circuit, P, add_words, sha256_fixed, word


@pytest.mark.parametrize("raw", [b"", b"abc", b"a" * 55, b"b" * 56, bytes(range(64))])
def test_sha256_bit_limb_constraints_match_hashlib(raw):
    circuit = Circuit([0, 1])
    message = [circuit.private(v, 0, 255) for v in raw]
    digest = sha256_fixed(circuit, message)
    assert bytes(x.value for x in digest) == hashlib.sha256(raw).digest()
    assert circuit.check_witness()
    if raw:
        changed = circuit.witness()
        changed[message[0].index] = (changed[message[0].index] + 1) % 256
        assert not circuit.check_witness(changed)


def test_circuit_does_not_specialize_program_on_private_byte_values():
    programs = []
    for v in (0, 255):
        circuit = Circuit([0, 1])
        data = circuit.private(v, 0, 255)
        sha256_fixed(circuit, [data])
        programs.append(circuit.program())
    assert programs[0] == programs[1]


def test_full_uint32_sha_addition_uses_limbs_not_one_reduced_field():
    circuit = Circuit([0, 1])
    a = [circuit.private((0xFFFFFFFF >> i) & 1, 0, 1) for i in range(32)]
    for bit in a:
        circuit.boolean(bit)
    result = add_words(circuit, a, word(circuit, 1))
    assert sum(b.value << i for i, b in enumerate(result)) == 0
    assert circuit.check_witness()
    with pytest.raises(ValueError, match="at most 30 bits"):
        circuit.from_bits(a)
    with pytest.raises(ValueError, match="noncanonical"):
        Circuit([0, 1, P])


def test_boolean_and_wiring_mutations_fail_equations():
    circuit = Circuit([0, 1])
    a = circuit.private(1, 0, 1)
    circuit.boolean(a)
    b = circuit.private(0, 0, 1)
    circuit.boolean(b)
    out = circuit.bit_xor(a, b)
    circuit.equal(out, circuit.one)
    assert circuit.check_witness()
    for wire in (a, out):
        changed = circuit.witness()
        changed[wire.index] = (changed[wire.index] + 1) % P
        assert not circuit.check_witness(changed)
