"""Closed-log checks, privacy sentinels, bounded admission and durable-write failures."""

import hashlib
import json
import os
import stat
import subprocess
import sys
import threading
import traceback
import uuid
from pathlib import Path

import pytest

import hallmark.events as events
from hallmark.errors import HallmarkError
from hallmark.events import AttemptRecord, Event, EventLog, EventSummary, inspect_events

CAP = 16384
SECRET = "PRIVATE_EVENT_SENTINEL_/local/secret_\ud800"


def report(path):
    return inspect_events(path, max_bytes=CAP)


def completed(path):
    with EventLog(path, max_bytes=CAP) as log:
        with log.attempt(), log.stage("execute"):
            pass
    return report(path)


def assert_not_complete(path):
    try:
        result = report(path)
    except HallmarkError as exc:
        assert exc.code == "STORAGE_FAILED"
    else:
        assert result.status != "complete"


def records(path):
    return [json.loads(line) for line in (path / "events.jsonl").read_bytes().splitlines()]


def rewrite(path, values, *, reseal=False):
    raw = b"".join(json.dumps(value).encode() + b"\n" for value in values)
    (path / "events.jsonl").write_bytes(raw)
    if reseal:
        receipt = path / "attempt-0.json"
        value = json.loads(receipt.read_text())
        value["events_sha256"] = hashlib.sha256(raw).hexdigest()
        value["event_count"] = len(values)
        receipt.write_text(json.dumps(value))


def test_smallest_private_completion(tmp_path, monkeypatch):
    clock = iter((100, 107))
    monkeypatch.setattr(events.time, "monotonic_ns", lambda: next(clock))
    path = tmp_path / "log"
    with EventLog(path, max_bytes=CAP) as log:
        with log.attempt(), log.stage("execute"):
            with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
                report(path)
    summary = report(path)
    assert summary.status == "complete" and summary.event_count == 2
    assert uuid.UUID(summary.run_id).version == 4
    assert len(summary.attempts) == 1
    assert [r["ordinal"] for r in records(path)] == [0, 1]
    assert [r["elapsed_ns"] for r in records(path)] == [None, 7]
    assert stat.S_IMODE(path.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in path.iterdir())
    assert set(records(path)[0]) == {
        "schema_id",
        "run_id",
        "attempt",
        "ordinal",
        "stage",
        "outcome",
        "elapsed_ns",
        "code",
    }


@pytest.mark.parametrize(
    "exc,code",
    [
        (ValueError(SECRET), "INPUT_INVALID"),
        (UnicodeError(SECRET), "INPUT_INVALID"),
        (TimeoutError(SECRET), "RESOURCE_EXHAUSTED"),
        (MemoryError(SECRET), "RESOURCE_EXHAUSTED"),
        (OSError(SECRET), "STORAGE_FAILED"),
        (RuntimeError(SECRET), "INTERNAL_ERROR"),
        (subprocess.CalledProcessError(1, SECRET, output=SECRET, stderr=SECRET), "INTERNAL_ERROR"),
        (KeyboardInterrupt(SECRET), "RESOURCE_EXHAUSTED"),
        (SystemExit(SECRET), "RESOURCE_EXHAUSTED"),
    ],
)
def test_failure_is_retained_without_content(tmp_path, capsys, exc, code):
    path = tmp_path / "log"
    with pytest.raises(HallmarkError) as caught:
        with EventLog(path, max_bytes=CAP) as log:
            with log.attempt(), log.stage("prove"):
                raise exc
    assert caught.value.code == code
    assert caught.value.__suppress_context__
    assert "PRIVATE_EVENT_SENTINEL" not in "".join(traceback.format_exception(caught.value))
    result = report(path)
    assert result.status == "failed" and result.attempts[0].code == code
    assert records(path)[-1]["outcome"] == "failed"
    assert all(b"PRIVATE_EVENT_SENTINEL" not in p.read_bytes() for p in path.iterdir())
    assert capsys.readouterr() == ("", "")


def test_retry_is_explicit_and_keeps_failed_attempt(tmp_path):
    path = tmp_path / "log"
    with EventLog(path, max_bytes=CAP) as log:
        with pytest.raises(HallmarkError):
            with log.attempt(), log.stage("prove"):
                raise HallmarkError("RESOURCE_EXHAUSTED", "prove", retryable=True)
        assert (path / "attempt-0.json").exists()
        with log.attempt(), log.stage("prove"):
            pass
        with pytest.raises(HallmarkError, match="INPUT_INVALID"):
            with log.attempt():
                pytest.fail("third attempt entered")
    result = report(path)
    assert result.status == "complete"
    assert [r.status for r in result.attempts] == ["failed", "complete"]
    assert [r["attempt"] for r in records(path)] == [0, 0, 1, 1]
    assert [r["ordinal"] for r in records(path)] == [0, 1, 0, 1]


@pytest.mark.parametrize(
    "code,retryable",
    [("INPUT_INVALID", True), ("PROOF_INVALID", True), ("RESOURCE_EXHAUSTED", False)],
)
def test_permanent_or_unapproved_retry_refused(tmp_path, code, retryable):
    path = tmp_path / "log"
    with EventLog(path, max_bytes=CAP) as log:
        with pytest.raises(HallmarkError):
            with log.attempt(), log.stage("prove"):
                raise HallmarkError(code, "prove", retryable=retryable)
        with pytest.raises(HallmarkError, match="INPUT_INVALID"):
            with log.attempt():
                pytest.fail("unapproved retry")
    assert report(path).status == "failed"


def test_swallowed_stage_failure_cannot_complete(tmp_path):
    path = tmp_path / "log"
    with EventLog(path, max_bytes=CAP) as log:
        with pytest.raises(HallmarkError, match="INPUT_INVALID"):
            with log.attempt():
                with pytest.raises(HallmarkError):
                    with log.stage("parse"):
                        raise ValueError(SECRET)
    assert report(path).status == "failed"


def test_empty_attempt_fails(tmp_path):
    path = tmp_path / "log"
    with pytest.raises(HallmarkError, match="INPUT_INVALID"):
        with EventLog(path, max_bytes=CAP) as log, log.attempt():
            pass
    assert report(path).status == "failed"


def test_between_stage_failure_retained(tmp_path):
    path = tmp_path / "log"
    with pytest.raises(HallmarkError, match="INTERNAL_ERROR"):
        with EventLog(path, max_bytes=CAP) as log, log.attempt():
            with log.stage("parse"):
                pass
            raise RuntimeError(SECRET)
    assert report(path).status == "failed"


@pytest.mark.parametrize(
    "field,value",
    [
        ("extra", "private"),
        ("run_id", "a" * 64),
        ("run_id", "content-derived"),
        ("run_id", "0" * 32),
        ("run_id", "abcd" * 8),
        ("ordinal", True),
        ("ordinal", -1),
        ("ordinal", 2**64),
        ("ordinal", "0"),
        ("attempt", True),
        ("attempt", 2),
        ("stage", "provider-path"),
        ("outcome", "accepted"),
        ("elapsed_ns", 0),
        ("code", "INTERNAL_ERROR"),
        ("schema_id", "hallmark/event/2"),
    ],
)
def test_event_schema_rejects_unknown_content_fields(tmp_path, field, value):
    path = tmp_path / "log"
    completed(path)
    values = records(path)
    values[0][field] = value
    rewrite(path, values, reseal=True)
    with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
        report(path)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "gap",
        "stage",
        "run",
        "attempt",
        "reverse",
        "missing_start",
        "unfinished",
        "failure",
        "after_failure",
    ],
)
def test_sequence_rejects_even_with_recomputed_receipt(tmp_path, mutation):
    path = tmp_path / "log"
    completed(path)
    values = records(path)
    if mutation == "duplicate":
        values[1]["ordinal"] = 0
    elif mutation == "gap":
        values[1]["ordinal"] = 3
    elif mutation == "stage":
        values[1]["stage"] = "prove"
    elif mutation == "run":
        values[1]["run_id"] = uuid.uuid4().hex
    elif mutation == "attempt":
        values[0]["attempt"] = 1
    elif mutation == "reverse":
        values.reverse()
    elif mutation == "missing_start":
        values = [values[1]]
        values[0]["ordinal"] = 0
    elif mutation == "unfinished":
        values = values[:1]
    else:
        values[1].update(outcome="failed", code="PROOF_INVALID")
        if mutation == "after_failure":
            values.append(values[0] | {"ordinal": 2})
    rewrite(path, values, reseal=True)
    assert_not_complete(path)


@pytest.mark.parametrize(
    "content",
    [b'{"extra":1,"extra":2}\n', b'{"x":NaN}\n', b"\xff\n", b"{}", b"\n", b"x" * 513 + b"\n"],
)
def test_malformed_lines_reject(tmp_path, content):
    path = tmp_path / "log"
    completed(path)
    (path / "events.jsonl").write_bytes(content)
    assert_not_complete(path)


def test_missing_schema_rejects(tmp_path):
    path = tmp_path / "log"
    completed(path)
    values = records(path)
    del values[0]["schema_id"]
    rewrite(path, values, reseal=True)
    assert_not_complete(path)


@pytest.mark.parametrize("point", ["empty", "stage", "after_stage", "retry"])
def test_process_exit_never_completes(tmp_path, point):
    path = tmp_path / "log"
    code = """
import os, sys
from pathlib import Path
from hallmark.events import EventLog
from hallmark.errors import HallmarkError
with EventLog(Path(sys.argv[1]), max_bytes=16384) as log:
    if sys.argv[2] == 'retry':
        try:
            with log.attempt(), log.stage('prove'):
                raise HallmarkError('RESOURCE_EXHAUSTED', 'prove', retryable=True)
        except HallmarkError:
            pass
    with log.attempt():
        if sys.argv[2] in ('empty', 'retry'):
            os._exit(7)
        with log.stage('execute'):
            if sys.argv[2] == 'stage':
                os._exit(7)
        os._exit(7)
"""
    child = subprocess.run(
        [sys.executable, "-c", code, str(path), point], timeout=10, capture_output=True
    )
    assert child.returncode == 7 and not child.stdout and not child.stderr
    assert report(path).status == "incomplete"


def test_second_writer_and_thread_refused(tmp_path):
    path = tmp_path / "log"
    with EventLog(path, max_bytes=CAP) as log:
        with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
            EventLog(path, max_bytes=CAP)
        errors = []

        def other_thread():
            try:
                with log.attempt():
                    pass
            except HallmarkError as exc:
                errors.append(exc.code)

        thread = threading.Thread(target=other_thread)
        thread.start()
        thread.join(timeout=5)
        assert errors == ["STORAGE_FAILED"]
        with log.attempt(), log.stage("execute"):
            pass
    assert report(path).status == "complete"


def test_content_identifier_not_an_input(tmp_path):
    with pytest.raises(TypeError):
        EventLog(tmp_path / "log", max_bytes=CAP, run_id=SECRET)
    assert not (tmp_path / "log").exists()


@pytest.mark.parametrize("budget", [True, 4095, CAP * 100, "4096", None])
def test_invalid_budgets_reject_before_creation(tmp_path, budget):
    with pytest.raises(HallmarkError, match="INPUT_INVALID"):
        EventLog(tmp_path / "log", max_bytes=budget)
    assert not (tmp_path / "log").exists()


def test_disk_cap_retains_failed_attempt(tmp_path):
    path = tmp_path / "log"
    with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
        with EventLog(path, max_bytes=4096) as log, log.attempt():
            for _ in range(20):
                with log.stage("execute"):
                    pass
    assert sum(p.stat().st_size for p in path.iterdir()) <= 4096
    assert report(path).status == "failed"
    assert report(path).attempts[0].code == "STORAGE_FAILED"


@pytest.mark.parametrize("operation", ["write", "zero_write", "partial_write", "fsync", "link"])
def test_disk_failures_do_not_publish_completion(tmp_path, monkeypatch, operation):
    path = tmp_path / "log"
    with EventLog(path, max_bytes=CAP) as log:
        original_write = os.write
        calls = 0

        def broken(*args, **kwargs):
            nonlocal calls
            calls += 1
            if operation == "zero_write":
                return 0
            if operation == "partial_write" and calls == 1:
                return original_write(args[0], args[1][:7])
            raise OSError(SECRET)

        with monkeypatch.context() as patch:
            patch.setattr(events.os, "write" if "write" in operation else operation, broken)
            with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
                with log.attempt(), log.stage("execute"):
                    pass
    assert_not_complete(path)
    assert all(b"PRIVATE_EVENT_SENTINEL" not in p.read_bytes() for p in path.iterdir())


@pytest.mark.parametrize("failure_at", range(1, 10))
def test_each_sync_failure_never_yields_complete(tmp_path, monkeypatch, failure_at):
    path = tmp_path / "log"
    original = os.fsync
    calls = 0

    def fail_once(fd):
        nonlocal calls
        calls += 1
        if calls == failure_at:
            raise OSError(SECRET)
        return original(fd)

    with monkeypatch.context() as patch:
        patch.setattr(events.os, "fsync", fail_once)
        with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
            with EventLog(path, max_bytes=CAP) as log, log.attempt(), log.stage("execute"):
                pass
    assert calls >= failure_at
    assert_not_complete(path)


def test_short_writes_are_completed(tmp_path, monkeypatch):
    original = os.write
    monkeypatch.setattr(events.os, "write", lambda fd, raw: original(fd, raw[:7]))
    assert completed(tmp_path / "log").status == "complete"


@pytest.mark.parametrize(
    "target,change",
    [
        (target, change)
        for target in ("root", "events", "receipt")
        for change in ("permissions", "symlink", "hardlink")
        if (target, change) != ("root", "hardlink")
    ],
)
def test_unsafe_paths_rejected(tmp_path, target, change):
    path = tmp_path / "log"
    completed(path)
    chosen = (
        path
        if target == "root"
        else path / ("events.jsonl" if target == "events" else "attempt-0.json")
    )
    if change == "permissions":
        chosen.chmod(0o755 if target == "root" else 0o644)
    elif change == "symlink":
        saved = tmp_path / "saved"
        chosen.rename(saved)
        chosen.symlink_to(saved, target_is_directory=target == "root")
    else:
        os.link(chosen, tmp_path / "alias")
    assert_not_complete(path)


def test_extra_file_and_fifo_reject_without_blocking(tmp_path):
    path = tmp_path / "log"
    completed(path)
    os.mkfifo(path / "unknown", 0o600)
    assert_not_complete(path)
    (path / "unknown").unlink()
    (path / "events.jsonl").unlink()
    os.mkfifo(path / "events.jsonl", 0o600)
    assert_not_complete(path)


def test_receipt_hash_and_inventory_are_checked(tmp_path):
    path = tmp_path / "log"
    completed(path)
    values = records(path)
    values[1]["elapsed_ns"] += 1
    rewrite(path, values)
    assert_not_complete(path)


@pytest.mark.parametrize("delta", [-1, 2**64])
def test_bad_monotonic_duration_cannot_complete(tmp_path, monkeypatch, delta):
    clock = iter((100, 100 + delta))
    monkeypatch.setattr(events.time, "monotonic_ns", lambda: next(clock))
    path = tmp_path / "log"
    with pytest.raises(HallmarkError, match="INTERNAL_ERROR"):
        completed(path)
    assert report(path).status == "failed"


def test_mutated_typed_error_never_leaks(tmp_path):
    exc = HallmarkError("INTERNAL_ERROR", "execute")
    exc.code = SECRET
    path = tmp_path / "log"
    with pytest.raises(HallmarkError, match="INTERNAL_ERROR"):
        with EventLog(path, max_bytes=CAP) as log, log.attempt(), log.stage("execute"):
            raise exc
    assert report(path).status == "failed"
    assert all(b"PRIVATE_EVENT_SENTINEL" not in p.read_bytes() for p in path.iterdir())


@pytest.mark.parametrize(
    "name,cls",
    [("event", Event), ("event-attempt", AttemptRecord), ("event-summary", EventSummary)],
)
def test_schema_snapshots(name, cls):
    root = Path(__file__).resolve().parents[1]
    assert (
        json.loads((root / f"docs/schemas/{name}-v1.json").read_text()) == cls.model_json_schema()
    )


def test_event_count_cap_retains_failure(tmp_path, monkeypatch):
    path = tmp_path / "log"
    monkeypatch.setattr(events, "MAX_EVENTS", 3)
    with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
        with EventLog(path, max_bytes=CAP) as log, log.attempt():
            for _ in range(2):
                with log.stage("execute"):
                    pass
    result = report(path)
    assert result.status == "failed" and result.event_count == 3


def test_second_process_cannot_write_or_inspect_live_log(tmp_path):
    path = tmp_path / "log"
    code = """
import sys
from pathlib import Path
from hallmark.events import EventLog, inspect_events
from hallmark.errors import HallmarkError
for action in (EventLog, inspect_events):
    try:
        action(Path(sys.argv[1]), max_bytes=16384)
    except HallmarkError as error:
        assert error.code == 'STORAGE_FAILED'
    else:
        raise AssertionError('live log admitted')
"""
    with EventLog(path, max_bytes=CAP) as log:
        child = subprocess.run(
            [sys.executable, "-c", code, str(path)], capture_output=True, timeout=10
        )
        assert child.returncode == 0 and not child.stdout and not child.stderr
        with log.attempt(), log.stage("execute"):
            pass
    assert report(path).status == "complete"


def test_fork_cannot_reuse_writer(tmp_path):
    path = tmp_path / "log"
    with EventLog(path, max_bytes=CAP) as log:
        pid = os.fork()
        if pid == 0:
            try:
                with log.attempt():
                    pass
            except HallmarkError:
                os._exit(0)
            os._exit(1)
        _, status = os.waitpid(pid, 0)
        assert status == 0
        with log.attempt(), log.stage("execute"):
            pass
    assert report(path).status == "complete"


@pytest.mark.parametrize("when", ["before_append", "before_seal"])
def test_external_edits_are_not_silently_sealed(tmp_path, when):
    path = tmp_path / "log"
    with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
        with EventLog(path, max_bytes=CAP) as log, log.attempt():
            with log.stage("execute"):
                if when == "before_append":
                    with (path / "events.jsonl").open("ab") as handle:
                        handle.write(b"{}\n")
            if when == "before_seal":
                values = records(path)
                values[1]["elapsed_ns"] += 1
                rewrite(path, values)
    assert_not_complete(path)


def test_writer_will_not_resume_or_overwrite(tmp_path):
    path = tmp_path / "log"
    completed(path)
    before = {p.name: p.read_bytes() for p in path.iterdir()}
    with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
        EventLog(path, max_bytes=CAP)
    assert {p.name: p.read_bytes() for p in path.iterdir()} == before


def test_reader_caps_bytes_and_directory_entries(tmp_path):
    path = tmp_path / "log"
    completed(path)
    original = (path / "events.jsonl").read_bytes()
    (path / "events.jsonl").write_bytes(b" " * (CAP + 1))
    assert_not_complete(path)
    (path / "events.jsonl").write_bytes(original)
    for index in range(6):
        (path / f"extra-{index}").touch(mode=0o600)
    assert_not_complete(path)


def test_installed_fixture():
    script = Path(__file__).resolve().parents[1] / "scripts/check_event_storage.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=True, timeout=10)
    assert result.returncode == 0 and not result.stderr
    assert b"6 events" in result.stdout
