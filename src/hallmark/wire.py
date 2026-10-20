"""Bounded RFC-0001 value codec; parsing does not authenticate an artifact."""

import hashlib
from dataclasses import dataclass
from typing import Literal, cast, get_args

import cbor2

from hallmark.errors import HallmarkError

type WireValue = None | bool | int | bytes | str | list[WireValue] | dict[str, WireValue]
type Domain = Literal[
    "model",
    "classifier",
    "policy",
    "input-profile",
    "program",
    "arithmetic",
    "backend",
    "setup",
    "registry",
    "epoch",
    "context",
    "transcript",
    "input-salt",
    "input",
    "receipt",
    "key",
    "trust",
    "protocol",
    "review",
    "corpus",
    "cost",
    "release",
]
DOMAINS: frozenset[Domain] = frozenset(get_args(Domain.__value__))


class WireError(HallmarkError):
    """Safe codec failure without an offending value or underlying exception."""

    def __init__(self, code: Literal["INPUT_INVALID", "LIMIT_EXCEEDED"]) -> None:
        super().__init__(code, "parse")


@dataclass(frozen=True, slots=True)
class WireLimits:
    """Caller may lower byte, container-depth and total-value hard limits."""

    max_bytes: int = 64 * 1024 * 1024
    nesting: int = 16
    max_items: int = 1_048_576

    def __post_init__(self) -> None:
        for value, cap in (
            (self.max_bytes, 64 * 1024 * 1024),
            (self.nesting, 16),
            (self.max_items, 1_048_576),
        ):
            if type(value) is not int or not 1 <= value <= cap:
                raise WireError("INPUT_INVALID")


DEFAULT_LIMITS = WireLimits()


def _header_size(value: int) -> int:
    if value < 24:
        return 1
    if value < 256:
        return 2
    if value < 65536:
        return 3
    if value < 2**32:
        return 5
    return 9


class _Measure:
    """Validate exact host types and bound output before invoking the encoder."""

    def __init__(self, limits: WireLimits) -> None:
        self.limits = limits
        self.size = 0
        self.items = 0

    def add(self, size: int) -> None:
        self.size += size
        if self.size > self.limits.max_bytes:
            raise WireError("LIMIT_EXCEEDED")

    def visit(self, value: WireValue, depth: int = 0) -> None:
        self.items += 1
        if self.items > self.limits.max_items:
            raise WireError("LIMIT_EXCEEDED")
        kind = type(value)
        if value is None or kind is bool:
            self.add(1)
        elif kind is int:
            number = cast(int, value)
            if not -(2**63) <= number < 2**64:
                raise WireError("INPUT_INVALID")
            self.add(_header_size(number if number >= 0 else -1 - number))
        elif kind is bytes:
            length = len(cast(bytes, value))
            self.add(_header_size(length) + length)
        elif kind is str:
            text = cast(str, value)
            if len(text) > self.limits.max_bytes - self.size:
                raise WireError("LIMIT_EXCEEDED")
            length = 0
            # Chunk validation bounds temporary UTF-8 allocation even for hostile text.
            for offset in range(0, len(text), 4096):
                try:
                    part = text[offset : offset + 4096].encode("utf-8")
                except UnicodeError:
                    part = None
                if part is None:
                    raise WireError("INPUT_INVALID")
                length += len(part)
                self.add(len(part))
            self.add(_header_size(length))
        elif kind is list or kind is dict:
            if depth >= self.limits.nesting:
                raise WireError("LIMIT_EXCEEDED")
            container = cast(list[WireValue] | dict[str, WireValue], value)
            count = len(container) * (2 if kind is dict else 1)
            if count > self.limits.max_items - self.items:
                raise WireError("LIMIT_EXCEEDED")
            self.add(_header_size(len(container)))
            if kind is list:
                for child in cast(list[WireValue], container):
                    self.visit(child, depth + 1)
            else:
                for key, child in cast(dict[str, WireValue], container).items():
                    if type(key) is not str:
                        raise WireError("INPUT_INVALID")
                    self.visit(key, depth + 1)
                    self.visit(child, depth + 1)
        else:
            raise WireError("INPUT_INVALID")


def _check_limits(limits: WireLimits) -> None:
    if type(limits) is not WireLimits:
        raise WireError("INPUT_INVALID")
    limits.__post_init__()


def encode(value: WireValue, *, limits: WireLimits = DEFAULT_LIMITS) -> bytes:
    """Encode exactly the restricted value algebra using length-first map order."""
    _check_limits(limits)
    measure = _Measure(limits)
    measure.visit(value)
    return cbor2.dumps(value, canonical=True)


class _Decoder:
    """Parse only the allowed CBOR types, without tag hooks or shared references."""

    def __init__(self, raw: bytes, limits: WireLimits) -> None:
        self.raw = raw
        self.limits = limits
        self.offset = 0
        self.items = 0

    def take(self, size: int) -> bytes:
        end = self.offset + size
        if end > len(self.raw):
            raise WireError("INPUT_INVALID")
        part = self.raw[self.offset : end]
        self.offset = end
        return part

    def argument(self, info: int) -> int:
        if info < 24:
            return info
        if info > 27:
            raise WireError("INPUT_INVALID")
        size = 1 << (info - 24)
        value = int.from_bytes(self.take(size), "big")
        minimum = (24, 256, 65536, 2**32)[info - 24]
        if value < minimum:
            raise WireError("INPUT_INVALID")
        return value

    def value(self, depth: int = 0) -> WireValue:
        self.items += 1
        if self.items > self.limits.max_items:
            raise WireError("LIMIT_EXCEEDED")
        initial = self.take(1)[0]
        major, info = initial >> 5, initial & 31
        if major == 7:
            if initial == 0xF4:
                return False
            if initial == 0xF5:
                return True
            if initial == 0xF6:
                return None
            raise WireError("INPUT_INVALID")
        if major == 6:
            raise WireError("INPUT_INVALID")
        argument = self.argument(info)
        if major == 0:
            return argument
        if major == 1:
            if argument >= 2**63:
                raise WireError("INPUT_INVALID")
            return -1 - argument
        if major in (2, 3):
            data = self.take(argument)
            if major == 2:
                return data
            try:
                text = data.decode("utf-8")
            except UnicodeError:
                text = None
            if text is None:
                raise WireError("INPUT_INVALID")
            return text
        if depth >= self.limits.nesting:
            raise WireError("LIMIT_EXCEEDED")
        count = argument * (2 if major == 5 else 1)
        if count > self.limits.max_items - self.items:
            raise WireError("LIMIT_EXCEEDED")
        if count > len(self.raw) - self.offset:
            raise WireError("INPUT_INVALID")
        if major == 4:
            return [self.value(depth + 1) for _ in range(argument)]
        result: dict[str, WireValue] = {}
        previous: tuple[int, bytes] | None = None
        for _ in range(argument):
            start = self.offset
            if self.offset == len(self.raw) or self.raw[self.offset] >> 5 != 3:
                raise WireError("INPUT_INVALID")
            key = cast(str, self.value(depth + 1))
            encoded_key = self.raw[start : self.offset]
            order = (len(encoded_key), encoded_key)
            if key in result or (previous is not None and order <= previous):
                raise WireError("INPUT_INVALID")
            previous = order
            result[key] = self.value(depth + 1)
        return result


def decode(raw: bytes, *, limits: WireLimits = DEFAULT_LIMITS) -> WireValue:
    """Parse one canonical value; artifact schema validation is a separate step."""
    _check_limits(limits)
    if type(raw) is not bytes:
        raise WireError("INPUT_INVALID")
    if len(raw) > limits.max_bytes:
        raise WireError("LIMIT_EXCEEDED")
    decoder = _Decoder(raw, limits)
    value = decoder.value()
    if decoder.offset != len(raw) or cbor2.dumps(value, canonical=True) != raw:
        raise WireError("INPUT_INVALID")
    return value


def H(kind: Domain, value: WireValue, *, limits: WireLimits = DEFAULT_LIMITS) -> bytes:
    """Return the 32-byte v1 typed identity, never a research or raw-file hash."""
    if type(kind) is not str or kind not in DOMAINS:
        raise WireError("INPUT_INVALID")
    tag = ("hallmark/v1/" + kind).encode("ascii")
    digest = hashlib.sha256(len(tag).to_bytes(4, "big") + tag)
    digest.update(encode(value, limits=limits))
    return digest.digest()
