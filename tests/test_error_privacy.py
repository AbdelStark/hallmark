"""Exercise every diagnostic class with private content and no external providers."""

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

from hallmark import cli
from hallmark.errors import (
    ERROR_CODES,
    STAGES,
    HallmarkError,
    first_stage_errors,
    sanitize_exception,
)
from hallmark.wire import WireError

SENTINEL = "PRIVATE_SENTINEL_31"


def _error(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    captured = capsys.readouterr()
    assert captured.out == ""
    assert SENTINEL not in captured.err
    assert "Traceback" not in captured.err
    record = json.loads(captured.err)
    assert set(record) == {"schema_id", "code", "stage", "retryable", "diagnostic_id"}
    assert record["schema_id"] == "hallmark/error/1"
    assert record["code"] in ERROR_CODES
    assert record["stage"] in STAGES
    return record


@pytest.mark.parametrize(
    "argv",
    [
        [],
        [SENTINEL],
        ["schema", SENTINEL],
        ["validate-data", "--" + SENTINEL],
        ["validate-data", "unused", "--" + SENTINEL],
        ["run", SENTINEL],
        ["audit-run", SENTINEL, "--dataset", SENTINEL],
    ],
)
def test_argument_errors_never_echo_values(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(argv) == 2
    record = _error(capsys)
    assert (record["code"], record["stage"]) == ("INPUT_INVALID", "parse")


@pytest.mark.parametrize(
    "content",
    [
        b'{"schema_id":"' + SENTINEL.encode() + b'"}\n',
        b'{"x":' + SENTINEL.encode() + b"}\n",
        SENTINEL.encode() + b"\xff",
        b'{"x":"' + SENTINEL.encode() + b'","x":1}\n',
    ],
)
def test_file_validation_and_unicode_are_redacted(
    content: bytes, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / SENTINEL
    path.write_bytes(content)
    assert cli.main(["validate-data", str(path)]) == 2
    assert _error(capsys)["code"] == "INPUT_INVALID"


def test_missing_paths_and_program_name_are_private(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    assert cli.main(["validate-data", str(tmp_path / SENTINEL)]) == 2
    assert _error(capsys)["code"] == "INPUT_INVALID"
    monkeypatch.setattr("sys.argv", [str(tmp_path / SENTINEL)])
    with pytest.raises(SystemExit) as caught:
        cli.main(["--help"])
    assert caught.value.code == 0
    output = capsys.readouterr()
    assert SENTINEL not in output.out + output.err
    assert "usage: hallmark" in output.out


@pytest.mark.parametrize(
    "exception,code,stage,status",
    [
        (ValueError(SENTINEL), "INPUT_INVALID", "parse", 2),
        (
            UnicodeEncodeError("utf-8", SENTINEL + "\ud800", 0, 1, SENTINEL),
            "INPUT_INVALID",
            "parse",
            2,
        ),
        (PermissionError(SENTINEL), "STORAGE_FAILED", "store", 3),
        (FileExistsError(SENTINEL), "STORAGE_FAILED", "store", 3),
        (OSError(28, SENTINEL, "/" + SENTINEL), "STORAGE_FAILED", "store", 3),
        (TimeoutError(SENTINEL), "RESOURCE_EXHAUSTED", "execute", 3),
        (MemoryError(SENTINEL), "RESOURCE_EXHAUSTED", "execute", 3),
        (
            subprocess.TimeoutExpired(SENTINEL, 1, output=SENTINEL, stderr=SENTINEL),
            "RESOURCE_EXHAUSTED",
            "execute",
            3,
        ),
        (
            subprocess.CalledProcessError(1, SENTINEL, output=SENTINEL, stderr=SENTINEL),
            "INTERNAL_ERROR",
            "execute",
            3,
        ),
        (RuntimeError(SENTINEL), "INTERNAL_ERROR", "execute", 3),
        (KeyError(SENTINEL), "INTERNAL_ERROR", "execute", 3),
        (TypeError(SENTINEL), "INTERNAL_ERROR", "execute", 3),
        (WireError("LIMIT_EXCEEDED"), "LIMIT_EXCEEDED", "parse", 2),
    ],
)
def test_fail_closed_for_execution_and_storage_errors(
    exception: Exception,
    code: str,
    stage: str,
    status: int,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(*args: Any) -> None:
        raise exception

    monkeypatch.setattr(cli, "load_records", fail)
    assert cli.main(["validate-data", SENTINEL]) == status
    record = _error(capsys)
    assert (record["code"], record["stage"]) == (code, stage)
    assert record["retryable"] is False
    if code == "INTERNAL_ERROR":
        assert re.fullmatch("[0-9a-f]{32}", record["diagnostic_id"])
    else:
        assert record["diagnostic_id"] is None


def test_all_codes_are_finite_serializable_and_non_success() -> None:
    assert len(ERROR_CODES) == 19
    for code in ERROR_CODES:
        error = HallmarkError(code, "verify")
        assert error.exit_code in (1, 2, 3)
        assert json.loads(json.dumps(error.as_dict(), allow_nan=False))["code"] == code
        assert str(error) == code
    assert HallmarkError("PROOF_PENDING", "prove").exit_code == 3
    assert HallmarkError("POLICY_BLOCKED", "verify").exit_code == 1
    assert HallmarkError("TRUST_MISSING", "enroll").exit_code == 2


@pytest.mark.parametrize("code", sorted(ERROR_CODES))
def test_typed_errors_emit_only_allowlisted_fields(
    code: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    error = HallmarkError(code, "verify")
    error.add_note(SENTINEL)

    def fail(*args: Any) -> None:
        raise error from RuntimeError(SENTINEL)

    monkeypatch.setattr(cli, "load_records", fail)
    assert cli.main(["validate-data", SENTINEL]) == error.exit_code
    assert _error(capsys)["code"] == code


@pytest.mark.parametrize(
    "args",
    [(SENTINEL, "parse"), ("INPUT_INVALID", SENTINEL), ("INPUT_INVALID", "parse", SENTINEL)],
)
def test_error_metadata_cannot_contain_arbitrary_strings(args: tuple[Any, ...]) -> None:
    with pytest.raises(ValueError) as caught:
        HallmarkError(*args)
    assert SENTINEL not in str(caught.value)


def test_stage_precedence_codes_and_input_bounds() -> None:
    errors = [
        HallmarkError("PROOF_INVALID", "verify"),
        HallmarkError("LIMIT_EXCEEDED", "parse"),
        HallmarkError("INPUT_INVALID", "parse"),
        HallmarkError("TRUST_MISSING", "enroll"),
    ]
    expected = ("INPUT_INVALID", "LIMIT_EXCEEDED")
    for order in (errors, list(reversed(errors)), errors[2:] + errors[:2]):
        assert tuple(e.code for e in first_stage_errors(order)) == expected
    for invalid in ([], [errors[0]] * 65, [SENTINEL]):
        with pytest.raises(HallmarkError, match="INPUT_INVALID"):
            first_stage_errors(invalid)  # type: ignore[arg-type]
    for earlier, later in zip(STAGES, STAGES[1:], strict=False):
        first = HallmarkError("INPUT_INVALID", earlier)
        second = HallmarkError("INTERNAL_ERROR", later)
        assert first_stage_errors([second, first]) == (first,)


def test_unexpected_error_ids_are_fresh_and_messages_are_never_inspected() -> None:
    class HostileError(Exception):
        def __str__(self) -> str:
            raise AssertionError("exception messages must not be inspected")

    first = sanitize_exception(HostileError(SENTINEL), stage="prove")
    second = sanitize_exception(HostileError(SENTINEL), stage="prove")
    assert first.code == second.code == "INTERNAL_ERROR"
    assert first.diagnostic_id != second.diagnostic_id
    assert first.__context__ is None and first.__cause__ is None
    assert SENTINEL not in json.dumps(first.as_dict())


def test_result_serialization_failure_cannot_print_partial_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "load_records", lambda _: ())
    monkeypatch.setattr(cli, "dataset_summary", lambda _: {"bad": float("nan")})
    assert cli.main(["validate-data", SENTINEL]) == 2
    assert _error(capsys)["code"] == "INPUT_INVALID"


def test_failed_run_keeps_redacted_legacy_record_and_never_emits_a_manifest(
    root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(*args: Any) -> None:
        raise subprocess.CalledProcessError(1, SENTINEL, output=SENTINEL, stderr=SENTINEL)

    monkeypatch.setattr("hallmark.experiment.train_linear", fail)
    output = tmp_path / SENTINEL
    assert cli.main(["run", str(root / "configs/fixture.json"), "--output", str(output)]) == 3
    assert _error(capsys)["code"] == "INTERNAL_ERROR"
    assert not (output / "manifest.json").exists()
    failure = (output / "failure.json").read_text()
    assert SENTINEL not in failure
    assert json.loads(failure) == {"status": "failed", "artifacts_complete": False}
    assert cli.main(["run", str(root / "configs/fixture.json"), "--output", str(output)]) == 3
    assert _error(capsys)["code"] == "STORAGE_FAILED"
    assert (output / "failure.json").read_text() == failure
