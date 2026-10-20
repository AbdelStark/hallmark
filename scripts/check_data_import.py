"""Check the harmless import fixture with the installed package."""

import json
import sys
from pathlib import Path

from hallmark.admission import StudyPolicy
from hallmark.data_admission import DataImportPlan, build_dataset, verify_dataset


def check(path: Path) -> None:
    fixture = json.loads(path.read_text())
    plan = DataImportPlan.decode(bytes.fromhex(fixture["plan_cbor_hex"]))
    policy = StudyPolicy.decode(bytes.fromhex(fixture["policy_cbor_hex"]))
    arguments = dict(
        expected_plan=bytes.fromhex(fixture["expected_plan_hex"]),
        documents={name: bytes.fromhex(raw) for name, raw in fixture["documents"].items()},
        raw_files={name: bytes.fromhex(raw) for name, raw in fixture["raw_files"].items()},
    )
    manifest, files = build_dataset(plan, policy, **arguments)
    verify_dataset(manifest, files, plan, policy, expected_dataset=manifest.identity(), **arguments)
    records = [json.loads(line) for line in files["records.jsonl"].splitlines()]
    by_id = {row["record_id"]: row for row in records}
    for component in fixture["required_components"]:
        assert len({by_id[name]["group_id"] for name in component}) == 1
        assert len({by_id[name]["split"] for name in component}) == 1
    assert len(records) == 26 and manifest.record_count == 26
    assert {row["split"] for row in records} == {"train", "calibration", "test"}
    assert by_id["fixture-a-1"]["label"] == 0 and by_id["fixture-b-1"]["label"] == 1
    print(f"{len(records)} synthetic rows imported with complete lineage; no real data admitted.")


if __name__ == "__main__":
    check(Path(sys.argv[1]))
