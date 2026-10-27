import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from circle_classifiers import RULE_PROFILE, public_values, rule

from hallmark.wire import H


def statement(raw, salt):
    return [
        *b"c" * 32,
        *b"k" * 32,
        *H("input", [salt, RULE_PROFILE, len(raw), list(raw)]),
        len(raw),
        max(1, (len(raw) + 3) // 4),
        2**31 + 1,
        int(b"BAD" not in raw),
    ]


@pytest.mark.parametrize(
    "raw", [b"", b"abcBAD", b"x" * 23, b"x" * 24, b"x" * 93 + b"BAD", ("é" * 48).encode()]
)
def test_full_rule_sha_padding_and_chunk_binding(raw):
    salt = b"s" * 32
    circuit = rule(statement(raw, salt), raw, salt)
    assert circuit.check_witness()
    assert len(circuit.gates) < 2**22
    # Every private input must be consumed; a disconnected advice input is not supported.
    used = {g[k] for g in circuit.gates for k in ("a", "b")}
    assert all(i in used for i, g in enumerate(circuit.gates, circuit.external) if g["mode"] == 0)


def test_rule_public_fields_and_overcapacity_fail_closed():
    salt = b"s" * 32
    with pytest.raises(ValueError, match="public statement"):
        public_values(statement(b"x" * 97, salt))
    p = statement(b"abc", salt)
    p[0] = 256
    with pytest.raises(ValueError, match="public statement"):
        public_values(p)
