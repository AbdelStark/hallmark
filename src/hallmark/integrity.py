"""Canonical research hashes, byte-exact transcript openings, and bounded JSON I/O."""

import hashlib
import json
import stat
from pathlib import Path
from typing import Any

import cbor2

from hallmark.contracts import C

MAX_FILE_BYTES = 8 * 1024 * 1024


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def read_bytes(path: Path) -> bytes:
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("input must be a regular, non-symlink file")
    with path.open("rb") as handle:
        content = handle.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("input exceeds the 8 MiB research boundary")
    return content


def parse_json(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)


def load_contract(path: Path, contract: type[C]) -> C:
    text = read_bytes(path).decode("utf-8")
    parse_json(text)
    return contract.model_validate_json(text)


def digest_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def commitment(domain: str, value: Any) -> str:
    tag = ("hallmark/research/1/" + domain).encode("ascii")
    encoded = cbor2.dumps(value, canonical=True)
    return digest_bytes(len(tag).to_bytes(4, "big") + tag + encoded)


def transcript_commitment(
    prompt: str, response: str, salt: bytes, system_ref: bytes = bytes(32)
) -> str:
    if type(salt) is not bytes or len(salt) != 32:
        raise ValueError("transcript salt must be exactly 32 bytes")
    if type(system_ref) is not bytes or len(system_ref) != 32:
        raise ValueError("system_ref must be exactly 32 bytes")
    fields = (system_ref, prompt.encode("utf-8"), response.encode("utf-8"))
    tag = b"hallmark/v0/transcript\x00"
    return digest_bytes(tag + salt + b"".join(len(x).to_bytes(8, "big") + x for x in fields))


def write_json_new(path: Path, value: Any) -> None:
    text = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)
