import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from hallmark.contracts import LinearArtifact, Record, RunManifest
from hallmark.data import load_records, validate_splits
from hallmark.integrity import (
    commitment,
    parse_json,
    read_bytes,
    transcript_commitment,
    write_json_new,
)


@pytest.mark.parametrize("bad", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'])
def test_ambiguous_json_rejected(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_json(bad)


def test_canonical_commitments_separate_domains_and_types() -> None:
    assert commitment("a", {"x": 1, "y": 2}) == commitment("a", {"y": 2, "x": 1})
    assert commitment("a", 1) != commitment("a", True)
    assert commitment("a", b"abc") != commitment("a", "abc")
    assert commitment("a", [1]) != commitment("b", [1])


def test_transcript_binds_bytes_roles_salt_and_system() -> None:
    base = transcript_commitment("ab", "c", bytes(32))
    assert base != transcript_commitment("a", "bc", bytes(32))
    assert base != transcript_commitment("c", "ab", bytes(32))
    assert base != transcript_commitment("ab", "c", b"x" * 32)
    assert base != transcript_commitment("ab", "c", bytes(32), b"x" * 32)
    assert transcript_commitment("é", "", bytes(32)) != transcript_commitment("é", "", bytes(32))
    with pytest.raises(ValueError):
        transcript_commitment("ab", "c", b"short")


def test_output_and_symlink_boundaries(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    write_json_new(target, {"ok": True})
    with pytest.raises(FileExistsError):
        write_json_new(target, {})
    link = tmp_path / "linked"
    link.symlink_to(target)
    with pytest.raises(ValueError):
        read_bytes(link)


@pytest.mark.parametrize("field,value", [("bias", 2**31 - 1), ("scale", 3), ("threshold", True)])
def test_integer_model_refuses_unsafe_arithmetic(
    model: LinearArtifact, field: str, value: int
) -> None:
    payload = model.model_dump(mode="json")
    payload[field] = value
    with pytest.raises(ValidationError):
        LinearArtifact.model_validate_json(json.dumps(payload))


def test_fixture_and_split_leakage(root: Path) -> None:
    rows = load_records(root / "fixtures/smoke.jsonl")
    assert len(rows) == 52
    with pytest.raises(ValueError, match="duplicate"):
        validate_splits((rows[0], rows[0]))
    crossed = rows[1].model_copy(update={"group_id": rows[0].group_id, "split": "test"})
    with pytest.raises(ValueError, match="leakage"):
        validate_splits((rows[0], crossed))
    twin = rows[0].model_copy(update={"record_id": "other", "group_id": "other", "split": "test"})
    with pytest.raises(ValueError, match="leakage"):
        validate_splits((rows[0], twin))


def test_record_refuses_boolean_labels_and_extra_fields(root: Path) -> None:
    row = load_records(root / "fixtures/smoke.jsonl")[0].model_dump(mode="json")
    for update in ({"label": True}, {"unexpected": "ignored?"}):
        with pytest.raises(ValidationError):
            Record.model_validate_json(json.dumps(row | update))


@pytest.mark.parametrize(
    "raw",
    ["[]", "{}", '{"schema_id":"hallmark.run-manifest/1","status":"complete","artifacts":{}}'],
)
def test_incomplete_manifest_rejected(raw: str) -> None:
    with pytest.raises(ValidationError):
        RunManifest.model_validate_json(raw)
