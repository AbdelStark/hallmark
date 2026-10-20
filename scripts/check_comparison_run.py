"""Build and execute an explicitly invented review dossier using local marker data."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from build_admission_fixture import build as admission_fixture
from build_data_fixture import export, file_ref, row
from build_selection_fixture import build as selection_fixture
from check_guard import fixture as guard_fixture

from hallmark.admission import AdmissionProtocol, AdmissionReview, Candidate
from hallmark.comparison_run import (
    ComparisonRunPlan,
    execution_inventory,
    json_bytes,
)
from hallmark.data_admission import build_dataset
from hallmark.guard import LocalGuard
from hallmark.selection import SelectionPlan


def fixture(root):
    root.mkdir()
    guard_root = root / "guard"
    guard_spec = guard_fixture(guard_root)
    imported, policy, documents, raw_files = export(
        {
            "authored": [
                row(
                    f"r-{i:03d}",
                    ("hello" if i % 2 == 0 else "ALERT") + f" {i:03d}",
                    "absent" if i % 2 == 0 else "present",
                )
                for i in range(200)
            ]
        }
    )
    guard = LocalGuard(guard_root, guard_spec, expected_spec=guard_spec.identity())
    manifest, dataset_files = build_dataset(
        imported,
        policy,
        expected_plan=imported.identity(),
        documents=documents,
        raw_files=raw_files,
    )
    selection_data = selection_fixture()["plan"]
    selection_data["bounds"].update(
        policy_id=policy.policy_id, max_rows=256, max_prompt_bytes=32768, max_total_bytes=32768
    )
    selection_data["chunk_bytes"] = 512
    for candidate in selection_data["candidates"]:
        if candidate["mlp"] is not None:
            candidate["mlp"].update(
                policy_id=policy.policy_id,
                chunk_bytes=512,
                max_prompt_bytes=32768,
                max_rows=256,
                max_feature_values=2097152,
            )
    plan = ComparisonRunPlan(
        schema_id="hallmark/comparison-run-plan/1",
        fixture_only=True,
        dataset=manifest.identity().hex(),
        import_plan=imported.identity().hex(),
        selection=SelectionPlan.model_validate_json(json.dumps(selection_data)),
        guard=guard_spec,
        guard_runtime=guard.identity,
    )
    plan_raw = json_bytes(plan.model_dump(mode="json"))
    _, old_protocol, old_review, old_documents = admission_fixture()
    review_documents = dict(old_documents) | documents
    review_documents["review/comparison-plan.json"] = plan_raw
    source = execution_inventory()
    review_documents["review/executable-source.json"] = source
    review_documents["review/dataset-split.json"] = dataset_files[manifest.splits.path]
    candidates = []
    for candidate in old_protocol.candidate_roster:
        if candidate.id == "compact-encoder":
            candidates.append(candidate)
        else:
            base_files = (
                tuple(
                    file_ref(name, (guard_root / name).read_bytes())
                    for name in ("model.onnx", "tokenizer.json")
                )
                if candidate.id == "task-guard"
                else ()
            )
            candidates.append(
                Candidate(
                    id=candidate.id,
                    code=hashlib.sha256(source).digest(),
                    config=hashlib.sha256(plan_raw).digest(),
                    base_files=base_files,
                )
            )
    protocol = AdmissionProtocol.model_validate(
        old_protocol.model_dump()
        | {
            "policy": policy.identity(),
            "rubric": policy.rubric,
            "sources": imported.sources,
            "split_manifest": manifest.splits.sha256,
            "evaluator": hashlib.sha256(source).digest(),
            "candidate_roster": tuple(candidates),
            "budget": old_protocol.budget.model_copy(
                update={"max_disk_bytes": 32 * 1024 * 1024, "max_memory_bytes": 2 * 1024**3}
            ),
        }
    )
    review = AdmissionReview.model_validate(
        old_review.model_dump()
        | {
            "terms": protocol.review_terms(),
            "evidence": tuple(
                file_ref(path, raw) for path, raw in sorted(review_documents.items())
            ),
        }
    )
    protocol = protocol.model_copy(update={"approval_ref": review.identity()})
    dossier = root / "dossier"
    dossier.mkdir()
    for name, value in (
        ("policy", policy),
        ("protocol", protocol),
        ("review", review),
        ("import", imported),
        ("dataset", manifest),
    ):
        (dossier / f"{name}.cbor").write_bytes(value.encode())
    (dossier / "comparison.json").write_bytes(plan_raw)
    for directory, files in (
        ("documents", review_documents),
        ("sources", raw_files),
        ("dataset", dataset_files),
    ):
        for name, raw in files.items():
            path = dossier / directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    return dossier, guard_root, review.identity()


def check(root):
    dossier, guard, pin = fixture(root / "input")
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("run_comparisons.py")),
            "--dossier",
            str(dossier),
            "--guard-assets",
            str(guard),
            "--expected-review",
            pin.hex(),
            "--output",
            str(root / "output"),
            "--fixture-only",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=45,
    )
    result = json.loads((root / "output/result.json").read_text())
    assert result["baseline_complete"]
    assert not result["full_study_complete"] and not result["quality_claim"]
    assert len(result["evaluated"]) == 10
    assert result["unavailable"] == [{"kind": "compact-encoder", "reason": "W16-not-executed"}]
    return {
        "schema_id": "hallmark/comparison-command-fixture/1",
        "passed": True,
        "fixture_only": True,
        "quality_claim": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output is None:
        with tempfile.TemporaryDirectory(prefix="hallmark-comparison-") as directory:
            print(json.dumps(check(Path(directory))))
    else:
        args.output.mkdir(mode=0o700)
        print(json.dumps(check(args.output)))
