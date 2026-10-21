"""Report caller-pinned held-out scores; this command never loads or selects a model."""

import json
import os
import sys
from pathlib import Path

from hallmark.cli import _Parser
from hallmark.contracts import Record
from hallmark.errors import sanitize_exception
from hallmark.group_evaluation import (
    GroupReportPlan,
    ReportObservation,
    ReportUnavailable,
    group_report,
)
from hallmark.integrity import parse_json, read_bytes


def put(path, value):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as handle:
        json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main():
    parser = _Parser(description=__doc__)
    for name in ("plan", "records", "observations", "source", "provenance", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-plan", required=True)
    args = parser.parse_args()
    created = False
    try:
        plan = GroupReportPlan.model_validate(parse_json(read_bytes(args.plan).decode()))
        rows = tuple(
            Record.model_validate(parse_json(line))
            for line in read_bytes(args.records).decode().splitlines()
        )
        raw = parse_json(read_bytes(args.observations).decode())
        if type(raw) is not dict:
            raise ValueError("invalid observation map")
        observations = {
            name: (
                ReportUnavailable
                if value.get("schema_id") == "hallmark/report-unavailable/1"
                else ReportObservation
            ).model_validate(value)
            for name, value in raw.items()
        }
        source, provenance = read_bytes(args.source), read_bytes(args.provenance)
        args.output.mkdir(mode=0o700)
        created = True
        put(args.output / "plan.json", plan.model_dump(mode="json"))
        result = group_report(
            plan,
            rows,
            observations,
            expected_plan=args.expected_plan,
            source=source,
            provenance=provenance,
        )
        put(args.output / "report.json", result)
        print(
            json.dumps(
                {"schema_id": result["schema_id"], "status": "reported", "quality_claim": False},
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:
        error = sanitize_exception(exc, stage="execute").as_dict()
        if created:
            try:
                put(args.output / "failure.json", error)
            except OSError:
                pass
        print(json.dumps(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
