"""Private bounded local event attempts; completion records are not evidence verdicts."""

import hashlib
import os
import stat
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from hallmark.classifier_manifest import U64
from hallmark.errors import STAGES, ErrorCode, HallmarkError, Stage, sanitize_exception
from hallmark.integrity import parse_json
from hallmark.manifests import _Record

MAX_BYTES = 1024 * 1024
MAX_EVENTS = 4096
LINE_BYTES = 512
RECORD_BYTES = 1024
_RETRY_CODES = {"RESOURCE_EXHAUSTED", "STORAGE_FAILED", "INTERNAL_ERROR"}
RunId = Annotated[str, Field(pattern=r"^[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$")]


class Event(_Record):
    schema_id: Literal["hallmark/event/1"]
    run_id: RunId
    attempt: Annotated[int, Field(ge=0, le=1)]
    ordinal: U64
    stage: Stage
    outcome: Literal["started", "completed", "failed"]
    elapsed_ns: U64 | None
    code: ErrorCode | None

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (self.outcome == "started") != (self.elapsed_ns is None):
            raise ValueError("invalid event duration")
        if (self.outcome == "failed") != (self.code is not None):
            raise ValueError("invalid event code")
        return self


class AttemptRecord(_Record):
    schema_id: Literal["hallmark/event-attempt/1"]
    run_id: RunId
    attempt: Annotated[int, Field(ge=0, le=1)]
    status: Literal["complete", "failed"]
    event_count: Annotated[int, Field(ge=0, le=MAX_EVENTS)]
    events_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    code: ErrorCode | None
    stage: Stage | None
    retryable: bool

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.status == "complete":
            if (
                self.event_count < 2
                or self.code is not None
                or self.stage is not None
                or self.retryable
            ):
                raise ValueError("invalid completion record")
        elif self.code is None or self.stage is None:
            raise ValueError("invalid failure record")
        if self.retryable and self.code not in _RETRY_CODES:
            raise ValueError("invalid retry")
        return self


class EventSummary(_Record):
    schema_id: Literal["hallmark/event-summary/1"] = "hallmark/event-summary/1"
    run_id: RunId | None
    status: Literal["complete", "failed", "incomplete"]
    event_count: Annotated[int, Field(ge=0, le=MAX_EVENTS)]
    attempts: Annotated[tuple[AttemptRecord, ...], Field(max_length=2)]


def _storage() -> HallmarkError:
    return HallmarkError("STORAGE_FAILED", "store")


def _safe(exc: BaseException, stage: Stage) -> HallmarkError:
    # Reconstruct typed exceptions too: their mutable attributes are not trusted.
    try:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            return HallmarkError("RESOURCE_EXHAUSTED", stage)
        if not isinstance(exc, Exception):
            return HallmarkError("INTERNAL_ERROR", stage)
        error = sanitize_exception(exc, stage=stage)
        if type(error.retryable) is not bool:
            return HallmarkError("INTERNAL_ERROR", stage)
        return HallmarkError(
            error.code, error.stage, error.retryable and error.code in _RETRY_CODES
        )
    except Exception:
        pass
    return HallmarkError("INTERNAL_ERROR", stage)


def _budget(max_bytes: int) -> None:
    if type(max_bytes) is not int or not 4096 <= max_bytes <= MAX_BYTES:
        raise HallmarkError("INPUT_INVALID", "parse")
    if os.name != "posix":
        raise _storage()


def _private(fd: int, *, directory: bool = False) -> None:
    info = os.fstat(fd)
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if (
        not kind(info.st_mode)
        or info.st_uid != os.geteuid()
        or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)
        or (not directory and info.st_nlink != 1)
    ):
        raise _storage()


def _root(path: Path) -> int:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        _private(fd, directory=True)
    except BaseException:
        os.close(fd)
        raise
    return fd


def _file(root: int, name: str, flags: int = os.O_RDONLY) -> int:
    fd = os.open(name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=root)
    try:
        _private(fd)
    except BaseException:
        os.close(fd)
        raise
    return fd


def _lock(fd: int, *, writer: bool) -> None:
    import fcntl

    fcntl.flock(fd, (fcntl.LOCK_EX if writer else fcntl.LOCK_SH) | fcntl.LOCK_NB)


def _write(fd: int, raw: bytes) -> None:
    while raw:
        count = os.write(fd, raw)
        if count <= 0:
            raise _storage()
        raw = raw[count:]
    os.fsync(fd)


def _json(record: _Record) -> bytes:
    return record._validated().model_dump_json().encode("ascii") + b"\n"


def _parse[T: _Record](raw: bytes, cls: type[T], limit: int) -> T:
    if len(raw) > limit:
        raise _storage()
    try:
        return cls.model_validate(parse_json(raw.decode("ascii")))
    except Exception:
        pass
    raise _storage()


def _read(root: int, name: str, cap: int) -> bytes:
    fd = _file(root, name)
    try:
        if os.fstat(fd).st_size > cap:
            raise _storage()
        raw = os.read(fd, cap + 1)
        if len(raw) > cap:
            raise _storage()
        return raw
    finally:
        os.close(fd)


class EventLog:
    """Fresh, single-thread/PID writer. No reopening, implicit retry or remote sink."""

    def __init__(self, path: Path, *, max_bytes: int) -> None:
        _budget(max_bytes)
        self._root = self._fd = -1
        self._owner = (os.getpid(), threading.get_ident())
        self._run_id = uuid.uuid4().hex
        self._max_bytes = max_bytes
        self._raw = b""
        self._attempt_raw = b""
        self._records: list[AttemptRecord] = []
        self._ordinal = self._count = 0
        self._active = self._stage_active = self._poisoned = False
        self._failure: HallmarkError | None = None
        try:
            path.mkdir(mode=0o700)
            self._root = _root(path)
            self._fd = _file(self._root, "events.jsonl", os.O_RDWR | os.O_CREAT | os.O_EXCL)
            _lock(self._fd, writer=True)
            os.fsync(self._fd)
            os.fsync(self._root)
        except BaseException:
            self.close()
            raise _storage() from None

    def __enter__(self) -> Self:
        self._guard()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owner != (os.getpid(), threading.get_ident()):
            raise _storage()
        for name in ("_fd", "_root"):
            fd = getattr(self, name)
            if fd >= 0:
                os.close(fd)
                setattr(self, name, -1)

    def _guard(self) -> None:
        if self._owner != (os.getpid(), threading.get_ident()) or self._fd < 0 or self._poisoned:
            raise _storage()

    def _emit(
        self,
        stage: Stage,
        outcome: Literal["started", "completed", "failed"],
        elapsed: int | None,
        code: ErrorCode | None = None,
    ) -> None:
        self._guard()
        raw = _json(
            Event(
                schema_id="hallmark/event/1",
                run_id=self._run_id,
                attempt=len(self._records),
                ordinal=self._ordinal,
                stage=stage,
                outcome=outcome,
                elapsed_ns=elapsed,
                code=code,
            )
        )
        if (
            len(raw) > LINE_BYTES
            or self._count >= MAX_EVENTS
            or len(self._raw) + len(raw) > self._max_bytes - 2 * RECORD_BYTES
        ):
            raise _storage()
        try:
            _private(self._fd)
            if os.fstat(self._fd).st_size != len(self._raw):
                raise _storage()
            _write(self._fd, raw)
            if os.pread(self._fd, len(raw), len(self._raw)) != raw:
                raise _storage()
        except BaseException:
            self._poisoned = True
            raise _storage() from None
        self._raw += raw
        self._attempt_raw += raw
        self._ordinal += 1
        self._count += 1

    def _seal(self, record: AttemptRecord) -> None:
        """A pending link invalidates completion until all publication syncs succeed."""
        pending = f"attempt-{record.attempt}.pending"
        final = f"attempt-{record.attempt}.json"
        linked = False
        try:
            _private(self._fd)
            if os.pread(self._fd, MAX_BYTES + 1, 0) != self._raw:
                raise _storage()
            raw = _json(record)
            if len(raw) > RECORD_BYTES:
                raise _storage()
            fd = _file(self._root, pending, os.O_RDWR)
            try:
                if os.fstat(fd).st_size:
                    raise _storage()
                _write(fd, raw)
                if os.pread(fd, RECORD_BYTES + 1, 0) != raw:
                    raise _storage()
            finally:
                os.close(fd)
            os.link(
                pending, final, src_dir_fd=self._root, dst_dir_fd=self._root, follow_symlinks=False
            )
            linked = True
            os.fsync(self._root)
            os.unlink(pending, dir_fd=self._root)
            os.fsync(self._root)
        except BaseException:
            self._poisoned = True
            if linked:
                # Never leave an accepted completion after a reported sync failure.
                try:
                    os.link(
                        final,
                        pending,
                        src_dir_fd=self._root,
                        dst_dir_fd=self._root,
                        follow_symlinks=False,
                    )
                except OSError:
                    pass
                try:
                    os.unlink(final, dir_fd=self._root)
                    os.fsync(self._root)
                except OSError:
                    pass
            raise _storage() from None
        self._records.append(record)

    @contextmanager
    def attempt(self) -> Iterator[None]:
        self._guard()
        if (
            self._active
            or len(self._records) >= 2
            or (
                self._records
                and (self._records[-1].status != "failed" or not self._records[-1].retryable)
            )
        ):
            raise HallmarkError("INPUT_INVALID", "parse")
        self._active = True
        self._attempt_raw = b""
        self._ordinal = 0
        self._failure = None
        try:
            try:
                fd = _file(
                    self._root,
                    f"attempt-{len(self._records)}.pending",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                )
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
                os.fsync(self._root)
            except BaseException:
                self._poisoned = True
                raise _storage() from None
            try:
                yield
            except BaseException as exc:
                self._failure = self._failure or _safe(exc, "execute")
            if not self._ordinal and self._failure is None:
                self._failure = HallmarkError("INPUT_INVALID", "parse")
            error = self._failure
            if not self._poisoned:
                self._seal(
                    AttemptRecord(
                        schema_id="hallmark/event-attempt/1",
                        run_id=self._run_id,
                        attempt=len(self._records),
                        status="failed" if error else "complete",
                        event_count=self._ordinal,
                        events_sha256=hashlib.sha256(self._attempt_raw).hexdigest(),
                        code=error.code if error else None,
                        stage=error.stage if error else None,
                        retryable=error.retryable if error else False,
                    )
                )
            else:
                error = _storage()
            if error:
                raise error from None
        finally:
            self._active = False

    @contextmanager
    def stage(self, stage: Stage) -> Iterator[None]:
        self._guard()
        if (
            not self._active
            or self._stage_active
            or self._failure
            or type(stage) is not str
            or stage not in STAGES
        ):
            self._failure = self._failure or HallmarkError("INPUT_INVALID", "parse")
            raise self._failure
        self._stage_active = True
        error: HallmarkError | None = None
        try:
            try:
                self._emit(stage, "started", None)
                start = time.monotonic_ns()
                try:
                    yield
                except BaseException as exc:
                    error = _safe(exc, stage)
                elapsed = time.monotonic_ns() - start
                if type(elapsed) is not int or not 0 <= elapsed < 2**64:
                    raise HallmarkError("INTERNAL_ERROR", stage)
                self._emit(
                    stage,
                    "failed" if error else "completed",
                    elapsed,
                    error.code if error else None,
                )
            except BaseException as exc:
                error = _safe(exc, stage)
            if error:
                self._failure = error
                raise error from None
        finally:
            self._stage_active = False


def _inspect(root: int, fd: int, max_bytes: int) -> EventSummary:
    names: set[str] = set()
    with os.scandir(root) as entries:
        for entry in entries:
            names.add(entry.name)
            if len(names) > 5:
                raise _storage()
    allowed = {"events.jsonl"} | {
        f"attempt-{i}.{ext}" for i in range(2) for ext in ("json", "pending")
    }
    if not names <= allowed or "events.jsonl" not in names:
        raise _storage()
    raw = os.read(fd, max_bytes + 1)
    if len(raw) > max_bytes or (raw and not raw.endswith(b"\n")):
        raise _storage()
    lines = raw.splitlines(keepends=True)
    if len(lines) > MAX_EVENTS:
        raise _storage()
    events = [_parse(line, Event, LINE_BYTES) for line in lines]
    records = [
        _parse(_read(root, f"attempt-{i}.json", RECORD_BYTES), AttemptRecord, RECORD_BYTES)
        for i in range(2)
        if f"attempt-{i}.json" in names
    ]
    total = len(raw)
    for name in names - {"events.jsonl"}:
        total += len(_read(root, name, RECORD_BYTES))
    if total > max_bytes or any(r.attempt != i for i, r in enumerate(records)):
        raise _storage()
    run_ids = {event.run_id for event in events} | {record.run_id for record in records}
    if len(run_ids) > 1:
        raise _storage()
    previous = 0
    for event in events:
        if event.attempt < previous or event.attempt > previous + 1:
            raise _storage()
        previous = event.attempt
    for attempt in range(2):
        group = [
            (event, line)
            for event, line in zip(events, lines, strict=True)
            if event.attempt == attempt
        ]
        opened: Stage | None = None
        failed: ErrorCode | None = None
        for ordinal, (event, _) in enumerate(group):
            if event.ordinal != ordinal or failed is not None:
                raise _storage()
            if event.outcome == "started":
                if opened is not None:
                    raise _storage()
                opened = event.stage
            else:
                if opened != event.stage:
                    raise _storage()
                opened = None
                failed = event.code
        if attempt < len(records):
            record = records[attempt]
            if (
                record.event_count != len(group)
                or record.events_sha256 != hashlib.sha256(b"".join(x[1] for x in group)).hexdigest()
                or (record.status == "complete" and (opened is not None or failed is not None))
                or (failed is not None and record.code not in (failed, "STORAGE_FAILED"))
            ):
                raise _storage()
        if attempt == 1 and (group or len(records) == 2):
            if not records or records[0].status != "failed" or not records[0].retryable:
                raise _storage()
    status: Literal["complete", "failed", "incomplete"] = "incomplete"
    if (
        records
        and not any(name.endswith(".pending") for name in names)
        and all(event.attempt < len(records) for event in events)
    ):
        status = records[-1].status
    return EventSummary(
        run_id=next(iter(run_ids), None),
        status=status,
        event_count=len(events),
        attempts=tuple(records),
    )


def inspect_events(path: Path, *, max_bytes: int) -> EventSummary:
    """Check closed local files and durable attempt records; never authenticate execution."""
    _budget(max_bytes)
    root = fd = -1
    try:
        root = _root(path)
        fd = _file(root, "events.jsonl")
        _lock(fd, writer=False)
        return _inspect(root, fd, max_bytes)
    except Exception:
        pass
    finally:
        if fd >= 0:
            os.close(fd)
        if root >= 0:
            os.close(root)
    raise _storage()
