"""Separate arithmetic implementation for the fixed synthetic encoder proof profile.

Supports 100 public scalars and one Pedersen commitment with no publicly committed
indices. The caller must enroll the key and public inputs outside the proof bundle.
This research checker does not qualify a backend or authenticate setup lineage.
"""

import hashlib
import re
import struct

from py_ecc.bls.hash import expand_message_xmd
from py_ecc.bls.point_compression import (
    compress_G1,
    compress_G2,
    decompress_G1,
    decompress_G2,
)
from py_ecc.optimized_bls12_381 import (
    FQ12,
    add,
    curve_order,
    final_exponentiate,
    is_inf,
    multiply,
    neg,
    normalize,
    pairing,
)

PUBLIC_SCALARS = 100
KEY_BYTES = 5536
PROOF_BYTES = 292


def _g1(raw):
    if type(raw) is not bytes or len(raw) != 48:
        raise ValueError("invalid G1 encoding length")
    encoded = int.from_bytes(raw, "big")
    point = decompress_G1(encoded)
    if compress_G1(point) != encoded or not is_inf(multiply(point, curve_order)):
        raise ValueError("noncanonical or non-subgroup G1 point")
    return point


def _g2(raw):
    if type(raw) is not bytes or len(raw) != 96:
        raise ValueError("invalid G2 encoding length")
    encoded = (int.from_bytes(raw[:48], "big"), int.from_bytes(raw[48:], "big"))
    point = decompress_G2(encoded)
    if compress_G2(point) != encoded or not is_inf(multiply(point, curve_order)):
        raise ValueError("noncanonical or non-subgroup G2 point")
    return point


def _commitment_scalar(point):
    # Gnark hashes its uncompressed encoding, including the infinity flag.
    if is_inf(point):
        raw = b"\x40" + bytes(95)
    else:
        x, y = normalize(point)
        raw = int(x).to_bytes(48, "big") + int(y).to_bytes(48, "big")
    uniform = expand_message_xmd(raw, b"bsb22-commitment", 48, hashlib.sha256)
    return int.from_bytes(uniform, "big") % curve_order


def verify(key, proof, public, *, expected_key_sha256):
    """Check exact encodings and both pairing equations against caller-owned inputs.

    Malformed or unsupported inputs raise ValueError. Well-formed algebraically
    invalid proofs return False. Canonical infinity points are subgroup members;
    the complete equations still have to hold. No serialized scalars are reduced.
    """
    if (
        type(key) is not bytes
        or len(key) != KEY_BYTES
        or type(expected_key_sha256) is not str
        or re.fullmatch(r"[0-9a-f]{64}", expected_key_sha256) is None
        or hashlib.sha256(key).hexdigest() != expected_key_sha256
    ):
        raise ValueError("verification key does not match enrollment")
    if type(proof) is not bytes or len(proof) != PROOF_BYTES:
        raise ValueError("invalid proof length")
    if type(public) not in (list, tuple) or len(public) != PUBLIC_SCALARS:
        raise ValueError("invalid public input count")
    if any(type(value) is not int or not 0 <= value < curve_order for value in public):
        raise ValueError("noncanonical public scalar")

    # The fixed layout has K[0], 100 public coefficients and one commitment hash.
    if (
        key[432:436] != struct.pack(">I", 102)
        or key[5332:5344] != struct.pack(">III", 1, 0, 1)
        or proof[192:196] != struct.pack(">I", 1)
    ):
        raise ValueError("unsupported commitment or public input layout")
    alpha = _g1(key[:48])
    _g1(key[48:96])  # Serialized beta/delta G1 points must also decode strictly.
    beta = _g2(key[96:192])
    gamma = _g2(key[192:288])
    _g1(key[288:336])
    delta = _g2(key[336:432])
    coefficients = [_g1(key[start : start + 48]) for start in range(436, 5332, 48)]
    pedersen_g = _g2(key[5344:5440])
    pedersen_sigma_negative = _g2(key[5440:5536])

    a = _g1(proof[:48])
    b = _g2(proof[48:144])
    c = _g1(proof[144:192])
    commitment = _g1(proof[196:244])
    knowledge = _g1(proof[244:292])

    # Check separately: multiplying both equations together permits cancellation.
    pedersen = pairing(pedersen_sigma_negative, commitment, final_exponentiate=False)
    pedersen *= pairing(pedersen_g, knowledge, final_exponentiate=False)
    if final_exponentiate(pedersen) != FQ12.one():
        return False

    total = coefficients[0]
    for coefficient, scalar in zip(
        coefficients[1:], (*public, _commitment_scalar(commitment)), strict=True
    ):
        total = add(total, multiply(coefficient, scalar))
    total = add(total, commitment)
    product = pairing(b, a, final_exponentiate=False)
    product *= pairing(delta, neg(c), final_exponentiate=False)
    product *= pairing(gamma, neg(total), final_exponentiate=False)
    product *= pairing(beta, neg(alpha), final_exponentiate=False)
    return final_exponentiate(product) == FQ12.one()
