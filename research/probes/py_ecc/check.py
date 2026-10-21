"""Check a caller-pinned synthetic proof fixture and fixed negative roster."""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from py_ecc.bls.point_compression import compress_G1, compress_G2
from py_ecc.optimized_bls12_381 import (
    FQ,
    FQ2,
    Z1,
    Z2,
    curve_order,
    field_modulus,
    is_inf,
    iso_map_G2,
    multiply,
    neg,
    optimized_swu_G2,
)
from verify import _g1, _g2, verify

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from hallmark._gnark_probe import read_regular  # noqa: E402


def encode_g1(point):
    return int(compress_G1(point)).to_bytes(48, "big")


def encode_g2(point):
    return b"".join(int(value).to_bytes(48, "big") for value in compress_G2(point))


def check(raw, expected_fixture, expected_key):
    if type(raw) is not bytes or len(raw) > 128 * 1024:
        raise ValueError("fixture size limit")
    if hashlib.sha256(raw).hexdigest() != expected_fixture:
        raise ValueError("fixture enrollment mismatch")
    fixture = json.loads(raw)
    if set(fixture) != {"key_hex", "records"}:
        raise ValueError("unexpected fixture fields")
    key = bytes.fromhex(fixture["key_hex"])
    rows = fixture["records"]
    if not 1 <= len(rows) <= 15 or len({row["name"] for row in rows}) != len(rows):
        raise ValueError("invalid fixture roster")
    cases = []

    def case(name, operation, expected):
        start = time.monotonic()
        try:
            result = operation()
        except ValueError:
            if expected != "malformed":
                raise
            outcome = "malformed"
        else:
            if result is not expected:
                raise AssertionError(name)
            outcome = "accepted" if result else "rejected"
        record = dict(name=name, outcome=outcome, seconds=time.monotonic() - start)
        cases.append(record)
        print(json.dumps(record), flush=True)

    for row in rows:
        if set(row) != {"name", "proof_hex", "public"}:
            raise ValueError("unexpected case fields")
        proof, public = bytes.fromhex(row["proof_hex"]), row["public"]
        case(
            "valid-" + row["name"],
            lambda proof=proof, public=public: verify(
                key, proof, public, expected_key_sha256=expected_key
            ),
            True,
        )
    row = next((row for row in rows if row["name"] == "capacity"), rows[-1])
    proof, public = bytes.fromhex(row["proof_hex"]), row["public"]

    def run(p=proof, values=public, k=key, pin=expected_key):
        return verify(k, p, values, expected_key_sha256=pin)

    for index in range(100):
        changed = public.copy()
        changed[index] ^= 1
        case(f"public-{index:03d}", lambda changed=changed: run(values=changed), False)
    for name, value in (
        ("field-alias", public[0] + curve_order),
        ("negative", -1),
        ("boolean", True),
        ("float", 0.0),
        ("text", "0"),
    ):
        changed = public.copy()
        changed[0] = value
        case(name, lambda changed=changed: run(values=changed), "malformed")
    case("short-public", lambda: run(values=public[:-1]), "malformed")
    case("long-public", lambda: run(values=public + [0]), "malformed")
    case("short-proof", lambda: run(p=proof[:-1]), "malformed")
    case("trailing-proof", lambda: run(p=proof + b"\0"), "malformed")
    case("proof-count", lambda: run(p=proof[:192] + bytes(4) + proof[196:]), "malformed")

    for name, start, end, decode, encode in (
        ("a", 0, 48, _g1, encode_g1),
        ("b", 48, 144, _g2, encode_g2),
        ("c", 144, 192, _g1, encode_g1),
        ("commitment", 196, 244, _g1, encode_g1),
        ("knowledge", 244, 292, _g1, encode_g1),
    ):
        changed = proof[:start] + encode(neg(decode(proof[start:end]))) + proof[end:]
        case("negated-" + name, lambda changed=changed: run(p=changed), False)
    # Negating both A and B preserves their pairing; proofs are not byte-unique.
    changed = encode_g1(neg(_g1(proof[:48]))) + encode_g2(neg(_g2(proof[48:144])))
    case("valid-negated-a-and-b", lambda: run(p=changed + proof[144:]), True)
    changed = proof[:196] + encode_g1(neg(_g1(proof[196:244])))
    changed += encode_g1(neg(_g1(proof[244:292])))
    case("negated-commitment-and-knowledge", lambda changed=changed: run(p=changed), False)

    invalid_g1 = (field_modulus | (1 << 383)).to_bytes(48, "big")
    case("noncanonical-g1-coordinate", lambda: run(p=invalid_g1 + proof[48:]), "malformed")
    case("uncompressed-flag", lambda: run(p=bytes([proof[0] & 0x7F]) + proof[1:]), "malformed")
    invalid_infinity = bytes([0xE0]) + bytes(47)
    case("invalid-infinity", lambda: run(p=invalid_infinity + proof[48:]), "malformed")
    case("infinity-a", lambda: run(p=encode_g1(Z1) + proof[48:]), False)
    case("infinity-b", lambda: run(p=proof[:48] + encode_g2(Z2) + proof[144:]), False)
    torsion = (FQ(0), FQ(2), FQ(1))
    assert not is_inf(multiply(torsion, curve_order))
    case("g1-outside-subgroup", lambda: run(p=encode_g1(torsion) + proof[48:]), "malformed")
    torsion2 = iso_map_G2(*optimized_swu_G2(FQ2([1, 0])))
    assert not is_inf(multiply(torsion2, curve_order))
    case(
        "g2-outside-subgroup",
        lambda: run(p=proof[:48] + encode_g2(torsion2) + proof[144:]),
        "malformed",
    )
    case("wrong-enrollment", lambda: run(pin="0" * 64), "malformed")
    changed_key = encode_g1(neg(_g1(key[:48]))) + key[48:]
    case("changed-key-old-pin", lambda: run(k=changed_key), "malformed")
    case(
        "wrong-algebraic-key",
        lambda changed_key=changed_key: run(
            k=changed_key, pin=hashlib.sha256(changed_key).hexdigest()
        ),
        False,
    )
    for name, start, replacement in (
        ("key-k-count", 432, bytes(4)),
        ("key-commitment-count", 5332, bytes(4)),
        ("key-public-committed", 5336, b"\0\0\0\1"),
        ("key-pedersen-count", 5340, bytes(4)),
        ("key-unused-subgroup", 48, encode_g1(torsion)),
    ):
        changed_key = key[:start] + replacement + key[start + len(replacement) :]
        case(
            name,
            lambda changed_key=changed_key: run(
                k=changed_key, pin=hashlib.sha256(changed_key).hexdigest()
            ),
            "malformed",
        )
    return {"status": "passed", "qualified_backend": False, "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--expected-fixture", required=True)
    parser.add_argument("--expected-key", required=True)
    args = parser.parse_args()
    report = check(read_regular(args.fixture, 128 * 1024), args.expected_fixture, args.expected_key)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
