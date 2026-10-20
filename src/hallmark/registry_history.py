"""Append-only local authoring history, not a globally witnessed transparency log."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path

from hallmark.enrollment import Enrollment, RegistryState, SignedRegistry, TrustPolicy, enroll
from hallmark.errors import HallmarkError
from hallmark.registry import SignedTransition, enroll_transition, validate_successor
from hallmark.registry_store import _connect
from hallmark.wire import WireLimits

_APP_ID = 0x484D4831
_LIMITS = WireLimits()


def _state(snapshot: SignedRegistry) -> RegistryState:
    return RegistryState(
        schema_id="hallmark/registry-state/1",
        sequence=snapshot.body.sequence,
        digest=snapshot.body.identity(),
    )


def _row(
    connection: sqlite3.Connection, state: RegistryState | None = None
) -> tuple[SignedRegistry, bytes]:
    if connection.execute("PRAGMA application_id").fetchone() != (_APP_ID,):
        raise HallmarkError("STORAGE_FAILED", "store")
    query = (
        "SELECT sequence, digest, trust, typeof(snapshot), length(snapshot), "
        "substr(snapshot, 1, ?) FROM snapshots "
    )
    parameters: tuple[int | bytes, ...] = (_LIMITS.max_bytes + 1,)
    if state is not None:
        query += "WHERE sequence=? "
        parameters += (state.sequence.to_bytes(8, "big"),)
    row = connection.execute(query + "ORDER BY sequence DESC LIMIT 1", parameters).fetchone()
    if (
        row is None
        or type(row[0]) is not bytes
        or len(row[0]) != 8
        or type(row[1]) is not bytes
        or len(row[1]) != 32
        or type(row[2]) is not bytes
        or len(row[2]) != 32
        or row[3] != "blob"
        or row[4] > _LIMITS.max_bytes
    ):
        raise HallmarkError("STORAGE_FAILED", "store")
    snapshot = SignedRegistry.decode(row[5])
    actual = _state(snapshot)
    if (
        actual.sequence != int.from_bytes(row[0], "big")
        or actual.digest != row[1]
        or (state is not None and actual != state)
    ):
        raise HallmarkError("REGISTRY_INVALID", "enroll")
    return snapshot, row[2]


def _insert(
    connection: sqlite3.Connection,
    snapshot: SignedRegistry,
    trust: TrustPolicy,
    transition: SignedTransition | None,
) -> None:
    state = _state(snapshot)
    raw = snapshot.encode()
    transition_raw = None if transition is None else transition.encode()
    connection.execute(
        "INSERT INTO snapshots(sequence,digest,snapshot,trust,transition) VALUES (?,?,?,?,?)",
        (state.sequence.to_bytes(8, "big"), state.digest, raw, trust.identity(), transition_raw),
    )
    stored, identity = _row(connection, state)
    retained = connection.execute(
        "SELECT transition FROM snapshots WHERE sequence=?", (state.sequence.to_bytes(8, "big"),)
    ).fetchone()
    if stored.encode() != raw or identity != trust.identity() or retained != (transition_raw,):
        raise HallmarkError("STORAGE_FAILED", "store")


def create_history(
    path: Path,
    snapshot: SignedRegistry,
    trust: TrustPolicy,
    external_state: RegistryState,
    now: int,
) -> Enrollment:
    """Start from an independently pinned signed checkpoint; refuse existing paths."""
    result = enroll(snapshot, trust, external_state, now)
    if result.state != external_state:
        raise HallmarkError("REGISTRY_INVALID", "enroll")
    if os.name != "posix":
        raise HallmarkError("STORAGE_FAILED", "store")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with closing(_connect(path)) as connection, connection:
            connection.execute(f"PRAGMA application_id={_APP_ID}")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE snapshots (sequence BLOB PRIMARY KEY, digest BLOB UNIQUE NOT NULL, "
                "snapshot BLOB NOT NULL, trust BLOB NOT NULL, transition BLOB)"
            )
            for action in ("UPDATE", "DELETE"):
                connection.execute(
                    f"CREATE TRIGGER refuse_{action} BEFORE {action} ON snapshots "
                    "BEGIN SELECT RAISE(ABORT, 'immutable history'); END"
                )
            _insert(connection, snapshot, trust, None)
        return result
    except (OSError, sqlite3.Error):
        pass
    raise HallmarkError("STORAGE_FAILED", "store")


def read_snapshot(path: Path, state: RegistryState) -> SignedRegistry:
    """Export an exact retained record against an independently retained identity."""
    if type(state) is not RegistryState:
        raise HallmarkError("TRUST_MISSING", "enroll")
    state = state._validated()
    try:
        with closing(_connect(path)) as connection:
            return _row(connection, state)[0]
    except (OSError, sqlite3.Error):
        pass
    raise HallmarkError("STORAGE_FAILED", "store")


def read_transition(path: Path, state: RegistryState) -> SignedTransition | None:
    """Export retained authorization bytes; external policies are still required."""
    if type(state) is not RegistryState:
        raise HallmarkError("TRUST_MISSING", "enroll")
    state = state._validated()
    try:
        with closing(_connect(path)) as connection:
            _row(connection, state)
            row = connection.execute(
                "SELECT typeof(transition), length(transition), substr(transition, 1, ?) "
                "FROM snapshots WHERE sequence=?",
                (_LIMITS.max_bytes + 1, state.sequence.to_bytes(8, "big")),
            ).fetchone()
            if row == ("null", None, None):
                return None
            if row is None or row[0] != "blob" or row[1] > _LIMITS.max_bytes:
                raise HallmarkError("STORAGE_FAILED", "store")
            return SignedTransition.decode(row[2])
    except (OSError, sqlite3.Error):
        pass
    raise HallmarkError("STORAGE_FAILED", "store")


def append_history(
    path: Path,
    snapshot: SignedRegistry,
    trust: TrustPolicy,
    expected_state: RegistryState,
    now: int,
    *,
    transition: SignedTransition | None = None,
    old_trust: TrustPolicy | None = None,
) -> Enrollment:
    """Compare and append one complete successor under a single write transaction."""
    if type(expected_state) is not RegistryState or type(trust) is not TrustPolicy:
        raise HallmarkError("TRUST_MISSING", "enroll")
    if type(snapshot) is not SignedRegistry:
        raise HallmarkError("INPUT_INVALID", "enroll")
    expected_state, trust = expected_state._validated(), trust._validated()
    snapshot = snapshot._validated()
    if (transition is None) != (old_trust is None):
        raise HallmarkError("TRUST_MISSING", "enroll")
    try:
        with closing(_connect(path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            previous, trust_id = _row(connection)
            if _state(previous) != expected_state:
                raise HallmarkError("REGISTRY_INVALID", "enroll")
            if transition is None:
                if trust_id != trust.identity():
                    raise HallmarkError("TRUST_MISSING", "enroll")
                previous.verify_signatures(trust)
                validate_successor(previous.body, snapshot.body)
                result = enroll(snapshot, trust, expected_state, now)
            else:
                if type(old_trust) is not TrustPolicy or trust_id != old_trust.identity():
                    raise HallmarkError("TRUST_MISSING", "enroll")
                result = enroll_transition(
                    snapshot, transition, old_trust, trust, expected_state, now, previous=previous
                )
            _insert(connection, snapshot, trust, transition)
        return result
    except (OSError, sqlite3.Error):
        pass
    raise HallmarkError("STORAGE_FAILED", "store")
