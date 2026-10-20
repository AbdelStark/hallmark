"""Atomic checkpoints in an owner-controlled local SQLite database, never bundle paths."""

import os
import sqlite3
import stat
from contextlib import closing
from pathlib import Path

from hallmark.enrollment import Enrollment, RegistryState, SignedRegistry, TrustPolicy, enroll
from hallmark.errors import HallmarkError
from hallmark.wire import WireLimits

_STATE_LIMITS = WireLimits(max_bytes=256, nesting=2, max_items=16)
_APP_ID = 0x484D5231


def _connect(path: Path) -> sqlite3.Connection:
    info = path.lstat()
    if (
        os.name != "posix"
        or not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or info.st_uid != os.geteuid()
        or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise HallmarkError("STORAGE_FAILED", "store")
    connection = sqlite3.connect(path.absolute().as_uri() + "?mode=rw", uri=True, timeout=0)
    try:
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA synchronous=EXTRA")
        if connection.execute("PRAGMA journal_mode").fetchone() != ("delete",):
            raise HallmarkError("STORAGE_FAILED", "store")
        return connection
    except Exception:
        connection.close()
        raise


def _read(connection: sqlite3.Connection) -> RegistryState:
    if connection.execute("PRAGMA application_id").fetchone() != (_APP_ID,):
        raise HallmarkError("STORAGE_FAILED", "store")
    rows = connection.execute(
        "SELECT id, typeof(state), length(state), substr(state, 1, 257) FROM checkpoint LIMIT 2"
    ).fetchall()
    if (
        len(rows) != 1
        or rows[0][0] != 1
        or rows[0][1] != "blob"
        or rows[0][2] > _STATE_LIMITS.max_bytes
    ):
        raise HallmarkError("STORAGE_FAILED", "store")
    try:
        return RegistryState.decode(rows[0][3], limits=_STATE_LIMITS)
    except HallmarkError:
        pass
    raise HallmarkError("STORAGE_FAILED", "store")


def provision_state(path: Path, external_state: RegistryState) -> None:
    """Create a new private database from an independently retained checkpoint.

    The caller controls the parent directory. Existing files are never replaced.
    A failed initialization can leave an unusable file; inspect it, do not reuse it.
    """
    if type(external_state) is not RegistryState:
        raise HallmarkError("TRUST_MISSING", "enroll")
    if os.name != "posix":
        raise HallmarkError("STORAGE_FAILED", "store")
    external_state = external_state._validated()
    raw = external_state.encode(limits=_STATE_LIMITS)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with closing(_connect(path)) as connection, connection:
            connection.execute(f"PRAGMA application_id={_APP_ID}")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE checkpoint (id INTEGER PRIMARY KEY CHECK(id=1), state BLOB NOT NULL)"
            )
            connection.execute("INSERT INTO checkpoint VALUES (1, ?)", (raw,))
        return
    except (OSError, sqlite3.Error):
        pass
    raise HallmarkError("STORAGE_FAILED", "store")


def read_state(path: Path) -> RegistryState:
    """Read an already provisioned local checkpoint; absence never bootstraps trust."""
    try:
        with closing(_connect(path)) as connection:
            return _read(connection)
    except (OSError, sqlite3.Error, HallmarkError):
        pass
    raise HallmarkError("STORAGE_FAILED", "store")


def enroll_and_store(
    path: Path,
    snapshot: SignedRegistry,
    trust: TrustPolicy,
    expected_state: RegistryState,
    now: int,
    *,
    history: tuple[SignedRegistry, ...] = (),
) -> Enrollment:
    """Compare the caller's checkpoint under a write lock; commit only verified state."""
    if type(expected_state) is not RegistryState:
        raise HallmarkError("TRUST_MISSING", "enroll")
    expected_state = expected_state._validated()
    try:
        with closing(_connect(path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            saved = _read(connection)
            if saved != expected_state:
                raise HallmarkError("REGISTRY_INVALID", "enroll")
            result = enroll(snapshot, trust, saved, now, history=history)
            connection.execute("UPDATE checkpoint SET state=? WHERE id=1", (result.state.encode(),))
            if _read(connection) != result.state:
                raise HallmarkError("STORAGE_FAILED", "store")
        return result
    except (OSError, sqlite3.Error):
        pass
    raise HallmarkError("STORAGE_FAILED", "store")
