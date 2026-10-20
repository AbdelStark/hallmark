"""Dataset admission keeps related records and identical transcripts in one split."""

from pathlib import Path

from hallmark.contracts import Record
from hallmark.integrity import commitment, parse_json, read_bytes


def load_records(path: Path) -> tuple[Record, ...]:
    rows = []
    for line in read_bytes(path).decode("utf-8").splitlines():
        if not line.strip():
            raise ValueError("blank JSONL records are forbidden")
        parse_json(line)
        rows.append(Record.model_validate_json(line))
    if not rows:
        raise ValueError("dataset must contain records")
    validate_splits(tuple(rows))
    return tuple(rows)


def validate_splits(rows: tuple[Record, ...]) -> None:
    ids: set[str] = set()
    groups: dict[str, str] = {}
    transcripts: dict[str, str] = {}
    for row in rows:
        if row.record_id in ids:
            raise ValueError("duplicate record id")
        ids.add(row.record_id)
        key = commitment("dataset-transcript", [row.prompt, row.response])
        for mapping, identifier in ((groups, row.group_id), (transcripts, key)):
            previous = mapping.setdefault(identifier, row.split)
            if previous != row.split:
                raise ValueError("split leakage: group or exact transcript crosses splits")


def dataset_summary(rows: tuple[Record, ...]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for row in rows:
        counts = result.setdefault(row.split, {"records": 0, "positive": 0, "negative": 0})
        counts["records"] += 1
        counts["positive" if row.label else "negative"] += 1
    return result
