"""Bounded local registry-check I/O; neither key discovery nor network retrieval."""

import os
import stat
from pathlib import Path

from hallmark.enrollment import MAX_HISTORY, SignedRegistry, TrustPolicy
from hallmark.errors import HallmarkError
from hallmark.registry import SignedTransition
from hallmark.registry_store import enroll_and_store, read_state, rotate_and_store
from hallmark.wire import WireLimits


def _read(path: Path, maximum: int) -> bytes:
    if maximum <= 0:
        raise HallmarkError("LIMIT_EXCEEDED", "parse")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise HallmarkError("INPUT_INVALID", "parse")
        if info.st_size > maximum:
            raise HallmarkError("LIMIT_EXCEEDED", "parse")
        raw = handle.read(maximum + 1)
    if len(raw) > maximum:
        raise HallmarkError("LIMIT_EXCEEDED", "parse")
    return raw


def check_registry(
    snapshot_path: Path,
    trust_path: Path,
    state_path: Path,
    now: int,
    *,
    history_paths: tuple[Path, ...] = (),
    old_trust_path: Path | None = None,
    transition_path: Path | None = None,
    previous_path: Path | None = None,
) -> dict[str, str | int]:
    """Read caller-provided CBOR and atomically advance an already provisioned state."""
    if len(history_paths) > MAX_HISTORY:
        raise HallmarkError("LIMIT_EXCEEDED", "parse")
    rotating = any(path is not None for path in (old_trust_path, transition_path, previous_path))
    if rotating and (
        old_trust_path is None or transition_path is None or previous_path is None or history_paths
    ):
        raise HallmarkError("INPUT_INVALID", "parse")
    trust = TrustPolicy.decode(_read(trust_path, 65536))
    remaining = trust.limits.bundle_bytes
    limits = WireLimits(max_bytes=remaining, nesting=trust.limits.nesting)

    def read(path: Path) -> bytes:
        nonlocal remaining
        raw = _read(path, remaining)
        remaining -= len(raw)
        return raw

    snapshot = SignedRegistry.decode(read(snapshot_path), limits=limits)
    expected = read_state(state_path)
    if old_trust_path is not None and transition_path is not None and previous_path is not None:
        old = TrustPolicy.decode(_read(old_trust_path, 65536))
        transition = SignedTransition.decode(read(transition_path), limits=limits)
        previous = SignedRegistry.decode(read(previous_path), limits=limits)
        result = rotate_and_store(
            state_path, snapshot, transition, old, trust, expected, now, previous=previous
        )
    else:
        history = tuple(SignedRegistry.decode(read(path), limits=limits) for path in history_paths)
        result = enroll_and_store(state_path, snapshot, trust, expected, now, history=history)
    return {
        "schema_id": "hallmark/registry-check/1",
        "registry": result.registry.hex(),
        "sequence": result.state.sequence,
        "trust": result.trust.hex(),
        "checked_at": result.checked_at,
    }
