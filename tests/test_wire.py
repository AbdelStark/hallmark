"""Fixed CBOR vectors and hostile-input tests for the separate v1 namespace."""

import hashlib
import random
from typing import Any

import cbor2
import pytest

from hallmark.integrity import commitment, transcript_commitment
from hallmark.wire import DOMAINS, H, WireError, WireLimits, decode, encode

# RFC 8949 Appendix A values, restricted to the Hallmark value algebra.
VECTORS: list[tuple[Any, str]] = [
    (0, "00"),
    (23, "17"),
    (24, "1818"),
    (255, "18ff"),
    (256, "190100"),
    (65535, "19ffff"),
    (65536, "1a00010000"),
    (2**32 - 1, "1affffffff"),
    (2**32, "1b0000000100000000"),
    (2**64 - 1, "1bffffffffffffffff"),
    (-1, "20"),
    (-24, "37"),
    (-25, "3818"),
    (-(2**63), "3b7fffffffffffffff"),
    (False, "f4"),
    (True, "f5"),
    (None, "f6"),
    (b"", "40"),
    (b"\x01\x02\x03\x04", "4401020304"),
    ("", "60"),
    ("a", "6161"),
    ("IETF", "6449455446"),
    ("é", "62c3a9"),
    ("e\u0301", "6365cc81"),
    ("\U0001f600", "64f09f9880"),
    ([], "80"),
    ([1, [2, 3], [4, 5]], "8301820203820405"),
    ({}, "a0"),
    ({"b": [2, 3], "a": 1}, "a26161016162820203"),
    ({"aa": 3, "b": 2, "a": 1}, "a361610161620262616103"),
]


@pytest.mark.parametrize("value,hex_bytes", VECTORS)
def test_fixed_vectors(value: Any, hex_bytes: str) -> None:
    raw = bytes.fromhex(hex_bytes)
    assert encode(value) == raw
    result = decode(raw)
    assert type(result) is type(value)
    assert result == value
    assert cbor2.dumps(value, canonical=True) == raw
    assert cbor2.loads(raw) == result


@pytest.mark.parametrize(
    "hex_bytes",
    [
        "",
        "00ff",  # empty/trailing
        "1800",
        "190018",
        "1a00000100",
        "1b0000000000010000",
        "3800",  # long integers
        "5800",
        "7800",
        "9800",
        "b800",  # long lengths
        "1c",
        "1d",
        "1e",
        "1f",
        "ff",  # reserved/indefinite/break
        "5f40ff",
        "7f60ff",
        "9f00ff",
        "bf616100ff",  # indefinite containers
        "c000",
        "c24101",
        "d81c80",
        "d81d00",  # tags and references
        "e0",
        "f7",
        "f814",
        "f818",
        "f90000",
        "fa3f800000",
        "fb7ff8000000000000",
        "3b8000000000000000",  # negative outside signed int64
        "61ff",
        "62c0af",
        "63eda080",
        "64f4908080",  # invalid UTF-8
        "a2616100616101",
        "a2616200616101",  # duplicate/out-of-order keys
        "a10100",
        "a1416100",
        "a1810000",
        "a1f400",  # non-text keys
        "1b00",
        "4161ff",
        "8200",
        "a16161",
        "5bffffffffffffffff",  # truncated/huge
    ],
)
def test_reject_noncanonical_or_unsupported_wire(hex_bytes: str) -> None:
    with pytest.raises(WireError):
        decode(bytes.fromhex(hex_bytes))


@pytest.mark.parametrize(
    "value",
    [
        1.0,
        float("nan"),
        2**64,
        -(2**63) - 1,
        (1,),
        {1: "x"},
        bytearray(b"x"),
        {"x"},
        cbor2.CBORTag(0, 1),
        "\ud800",
        {"\udfff": 1},
    ],
)
def test_reject_unsupported_host_values(value: Any) -> None:
    with pytest.raises(WireError, match="INPUT_INVALID"):
        encode(value)


def test_limits_are_symmetric_and_count_map_keys() -> None:
    value = {"a": [1, 2]}
    raw = bytes.fromhex("a16161820102")
    limits = WireLimits(max_bytes=len(raw), max_items=5, nesting=2)
    assert encode(value, limits=limits) == raw
    assert decode(raw, limits=limits) == value
    for smaller in (
        WireLimits(max_bytes=len(raw) - 1),
        WireLimits(max_items=4),
        WireLimits(nesting=1),
    ):
        for call, argument in ((encode, value), (decode, raw)):
            with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
                call(argument, limits=smaller)


def test_depth_empty_containers_cycles_and_declared_lengths() -> None:
    value: Any = 0
    for _ in range(16):
        value = [value]
    assert decode(encode(value)) == value
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        encode([value])
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        decode(b"\x81" * 17 + b"\x00")
    assert decode(b"\x81" * 15 + b"\x80") == _nested_empty(16)
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        decode(b"\x81" * 16 + b"\x80")
    cycle: list[Any] = []
    cycle.append(cycle)
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        encode(cycle)
    for raw in (b"\x9b" + b"\xff" * 8, b"\xbb" + b"\xff" * 8):
        with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
            decode(raw)


def _nested_empty(depth: int) -> list[Any]:
    result: list[Any] = []
    for _ in range(depth - 1):
        result = [result]
    return result


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_bytes": True},
        {"max_bytes": 0},
        {"max_bytes": 67108865},
        {"nesting": 0},
        {"nesting": 17},
        {"max_items": 0},
        {"max_items": 1048577},
        {"nesting": 1.0},
    ],
)
def test_limit_configuration_cannot_raise_hard_caps(kwargs: dict[str, Any]) -> None:
    with pytest.raises(WireError, match="INPUT_INVALID"):
        WireLimits(**kwargs)


def test_utf8_size_and_byte_text_identity() -> None:
    assert encode("é", limits=WireLimits(max_bytes=3)) == b"\x62\xc3\xa9"
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        encode("é", limits=WireLimits(max_bytes=2))
    assert H("input", True) != H("input", 1)
    assert H("input", b"abc") != H("input", "abc")
    assert H("input", "é") != H("input", "e\u0301")


def test_domain_preimages_and_legacy_ids() -> None:
    assert len(DOMAINS) == 22
    digests = set()
    for domain in DOMAINS:
        tag = ("hallmark/v1/" + domain).encode("ascii")
        expected = hashlib.sha256(len(tag).to_bytes(4, "big") + tag + b"\xf6").digest()
        digest = H(domain, None)
        assert digest == expected
        assert type(digest) is bytes and len(digest) == 32
        digests.add(digest)
    assert len(digests) == len(DOMAINS)
    assert commitment("fixture", {"x": 1, "y": b"abc"}) == (
        "d0648b9d9ffd9f3b458076868163315082cfe582ff846632b233cd21c09f2c32"
    )
    assert transcript_commitment("ab", "c", bytes(32)) == (
        "2a6c50c687495a59b064f7680a323cf4c221b888d1e796ea0b24e94cf727a451"
    )
    assert H("transcript", None).hex() != commitment("transcript", None)


@pytest.mark.parametrize("domain", ["", "research/1/input", "sign/receipt", "INPUT", None, []])
def test_unknown_domains_fail_without_echoing_input(domain: Any) -> None:
    with pytest.raises(WireError, match="^INPUT_INVALID$"):
        H(domain, None)


def test_errors_do_not_retain_private_unicode_content() -> None:
    for call, value in (
        (encode, "private-sentinel-\ud800"),
        (decode, b"\x72private-sentinel-\xff"),
        (decode, bytearray(b"private-sentinel")),
    ):
        with pytest.raises(WireError) as caught:
            call(value)
        error = caught.value
        assert error.args == ("INPUT_INVALID",)
        assert error.stage == "parse" and error.retryable is False
        assert error.__context__ is None


def test_decoder_truncation_and_seeded_differential_checks() -> None:
    rng = random.Random(20261020)
    for _ in range(200):
        value = {
            "n": rng.randrange(-(2**63), 2**64),
            "b": rng.randbytes(rng.randrange(32)),
            "list": [rng.choice([True, False, None, "é", ""]) for _ in range(10)],
        }
        raw = cbor2.dumps(value, canonical=True)
        assert encode(value) == raw
        assert decode(raw) == cbor2.loads(raw)
        for end in range(len(raw)):
            with pytest.raises(WireError):
                decode(raw[:end])
