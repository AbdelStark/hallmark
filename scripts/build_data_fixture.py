"""Build harmless source-admission inputs with explicit invented review markers."""

import argparse
import hashlib
import json
from pathlib import Path

from hallmark.admission import SourceApproval, StudyPolicy
from hallmark.data_admission import (
    DataImportPlan,
    LabelMapping,
    NearDuplicateReview,
    SourceManifest,
    SourceRow,
    near_duplicate_candidates,
)
from hallmark.manifests import FileRef


def json_bytes(value):
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode()


def file_ref(path, raw):
    return FileRef(path=path, size=len(raw), sha256=hashlib.sha256(raw).digest())


def row(name, text, label="absent", **changes):
    return SourceRow.model_validate(
        dict(
            schema_id="hallmark/source-row/1",
            record_id=name,
            family_id="marker-family",
            language="en",
            prompt=text,
            response="",
            source_label=label,
            parents=(),
            history_id=None,
            difficult_negative=False,
        )
        | changes
    )


def source_rows():
    sources = {
        name: [
            row(f"{name}-{i}", f"Harmless {name} example {i}.", "present" if i % 2 else "absent")
            for i in range(12)
        ]
        for name in ("fixture-a", "fixture-b")
    }
    sources["fixture-a"][0] = row("fixture-a-0", "parent marker")
    sources["fixture-a"].append(row("fixture-child", "child marker", parents=("fixture-a-0",)))
    sources["fixture-b"].append(
        row("fixture-grandchild", "grandchild marker", parents=("fixture-child",))
    )
    sources["fixture-a"][1] = row("fixture-a-1", "Review Marker", "absent", difficult_negative=True)
    sources["fixture-b"][1] = row("fixture-b-1", "review   MARKER", "present")
    sources["fixture-a"][2] = row("fixture-a-2", "history first", history_id="shared-history")
    sources["fixture-b"][2] = row("fixture-b-2", "history second", history_id="shared-history")
    sources["fixture-a"][3] = row("fixture-a-3", "same prompt", response="first response")
    sources["fixture-b"][3] = row("fixture-b-3", "same prompt", response="different response")
    return sources


def export(rows_by_source=None, *, held_sources=(), held_families=()):
    rows_by_source = source_rows() if rows_by_source is None else rows_by_source
    documents, raw_files = {}, {}

    def doc(path, raw):
        documents[path] = raw
        return file_ref(path, raw)

    rubric = doc("review/rubric.txt", b"Synthetic marker rubric, not a validated safety policy.\n")
    policy = StudyPolicy(
        schema_id="hallmark/study-policy/1",
        policy_id="inj.direct/1",
        language="en",
        scope="prompt",
        rubric=rubric.sha256,
        max_prompt_bytes=32768,
    )
    approvals = []
    for name, rows in sorted(rows_by_source.items()):
        path = f"raw/{name}.jsonl"
        raw_files[path] = b"".join(json_bytes(item.model_dump(mode="json")) for item in rows)
        license_ref = doc(
            f"review/{name}/licence.txt",
            b"Existing repository licence; authored synthetic fixtures, no additional grant.\n",
        )
        approval = doc(
            f"review/{name}/approval.txt",
            f"Invented source approval marker for {name}; no real data access granted.\n".encode(),
        )
        restrictions = doc(
            f"review/{name}/restrictions.txt",
            b"Harmless fixture use only; not evidence of legal rights to external data.\n",
        )
        labels = doc(
            f"review/{name}/labels.txt",
            b"Invented review: absent=0, present=1; "
            b"fixture labels are not human-audited task labels.\n",
        )
        annotations = doc(
            f"review/{name}/annotations.txt",
            b"Invented audit marker includes difficult-negative rows; no human review occurred.\n",
        )
        recipe = doc(
            f"review/{name}/recipe.txt",
            b"Authored SourceRow JSONL; preserve prompt/response UTF-8 "
            b"and map only declared labels.\n",
        )
        card = doc(
            f"review/{name}/card.txt",
            b"Purpose: software tests. Privacy: synthetic. "
            b"No downloads. No real label/lineage quality.\n",
        )
        manifest = SourceManifest(
            schema_id="hallmark/source-manifest/1",
            source_id=name,
            upstream_revision="authored-fixture/1",
            license_id="LicenseRef-Proprietary",
            policy=policy.identity(),
            purpose="inj.direct-study",
            privacy="synthetic",
            review_kind="fixture",
            raw_files=(file_ref(path, raw_files[path]),),
            label_mapping=(
                LabelMapping(source_label="absent", label=0, review=labels.sha256),
                LabelMapping(source_label="present", label=1, review=labels.sha256),
            ),
            annotation_review=annotations.sha256,
            transformation_recipe=recipe.sha256,
            data_card=card.sha256,
        )
        manifest_ref = doc(f"review/{name}/source.cbor", manifest.encode())
        approvals.append(
            SourceApproval(
                source_id=name,
                revision=manifest_ref.sha256,
                license_text=license_ref.sha256,
                purpose=manifest.purpose,
                approval_ref=approval.sha256,
                restrictions=restrictions,
            )
        )
    candidates = near_duplicate_candidates(
        tuple(item for rows in rows_by_source.values() for item in rows)
    )
    notes = doc(
        "review/near-duplicate-notes.txt",
        b"Invented review marker: group every ASCII case/space candidate; "
        b"retain contrastive rows.\n",
    )
    review = NearDuplicateReview(
        schema_id="hallmark/near-duplicate-review/1",
        candidate_inventory=hashlib.sha256(json_bytes(candidates)).digest(),
        review_kind="fixture",
        reviewer="fixture-reviewer",
        evidence=notes.sha256,
        disposition="retain-and-group-all-candidates",
    )
    near = doc("review/near-duplicates.cbor", review.encode())
    plan = DataImportPlan(
        schema_id="hallmark/data-import/1",
        policy=policy.identity(),
        design="inj-direct-design/1",
        fixture_only=True,
        sources=tuple(approvals),
        near_duplicate_review=near,
        held_out_sources=held_sources,
        held_out_families=held_families,
        evidence=tuple(file_ref(path, raw) for path, raw in sorted(documents.items())),
    )
    return plan, policy, documents, raw_files


def build():
    plan, policy, documents, raw_files = export()
    return {
        "schema_id": "hallmark/data-import-fixture/1",
        "fixture_only": True,
        "measurement_permitted": False,
        "provenance": (
            "Hand-authored markers and invented reviews; no external data or human review."
        ),
        "plan_cbor_hex": plan.encode().hex(),
        "expected_plan_hex": plan.identity().hex(),
        "policy_cbor_hex": policy.encode().hex(),
        "documents": {name: raw.hex() for name, raw in documents.items()},
        "raw_files": {name: raw.hex() for name, raw in raw_files.items()},
        "required_components": [
            ["fixture-a-0", "fixture-child", "fixture-grandchild"],
            ["fixture-a-1", "fixture-b-1"],
            ["fixture-a-2", "fixture-b-2"],
            ["fixture-a-3", "fixture-b-3"],
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with args.output.open("x") as handle:
        handle.write(json.dumps(build(), indent=2, sort_keys=True) + "\n")
