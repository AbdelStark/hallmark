"""Build harmless admission vectors; all approvals and model files are test markers."""

import hashlib
import json
from pathlib import Path

from hallmark.admission import (
    CANDIDATES,
    AdmissionProtocol,
    AdmissionReview,
    BudgetAdmission,
    Candidate,
    SourceApproval,
    StudyPolicy,
    validate_reviewed_admission,
)
from hallmark.manifests import ArtifactDigest, FileRef, FileSHA256

ROOT = Path(__file__).resolve().parents[1]


def build():
    files = {}

    def document(name, value):
        raw = (
            json.dumps(
                {"fixture_only": True, "measurement_permitted": False, **value}, sort_keys=True
            )
            + "\n"
        ).encode()
        path = f"review/{name}.json"
        files[path] = raw
        return FileRef(path=path, size=len(raw), sha256=FileSHA256(hashlib.sha256(raw).digest()))

    rubric = document("rubric", {"purpose": "hash/schema fixture, not an adopted policy"})
    revision = document("source", {"source": "local harmless markers"})
    license_text = document("notice", {"notice": "No new source/data licensing is granted."})
    source_approval = document("source-review", {"review": "synthetic test declaration"})
    restrictions = document("restrictions", {"use": "offline tests only"})
    split = document("split", {"unit": "root-group", "selection_access": "train-only"})
    evaluator = document("evaluator", {"purpose": "no classifier measurement"})
    subgroups = document("subgroups", {"report": "fixture counts only"})
    power = document("power", {"power": "not a real study"})
    hardware = document("host", {"host": "fixture-cpu", "threads": 1})
    budget_approval = document("budget-review", {"review": "no spending authority"})
    owner = document("owner-review", {"review": "not an actual owner approval"})
    party = document("party-review", {"review": "not an actual relying-party approval"})
    policy = StudyPolicy(
        schema_id="hallmark/study-policy/1",
        policy_id="inj.direct/1",
        language="en",
        scope="prompt",
        rubric=rubric.sha256,
        max_prompt_bytes=32768,
    )
    candidates = []
    for name in CANDIDATES:
        code = document(name + "-code", {"candidate": name})
        config = document(name + "-config", {"candidate": name, "selection": "fixed"})
        base = (
            FileRef(
                path=f"markers/{name}.txt",
                size=6,
                sha256=FileSHA256(hashlib.sha256(b"marker").digest()),
            ),
        )
        candidates.append(
            Candidate(
                id=name,
                code=code.sha256,
                config=config.sha256,
                base_files=base if name in ("task-guard", "compact-encoder") else (),
            )
        )
    protocol = AdmissionProtocol(
        schema_id="hallmark/admission/1",
        policy=policy.identity(),
        rubric=rubric.sha256,
        relying_party_role="fixture-auditor",
        sources=(
            SourceApproval(
                source_id="fixture",
                revision=revision.sha256,
                license_text=license_text.sha256,
                purpose="offline-tests",
                approval_ref=source_approval.sha256,
                restrictions=restrictions,
            ),
        ),
        split_manifest=split.sha256,
        candidate_roster=tuple(candidates),
        seeds=(17, 29, 43),
        evaluator=evaluator.sha256,
        target_fpr="0.01",
        alpha="0.05",
        min_tpr="0.9",
        max_quality_loss="0.02",
        subgroup_rules=subgroups,
        power_plan=power,
        budget=BudgetAdmission(
            host="fixture-cpu",
            hardware=hardware.sha256,
            max_wall_seconds=60,
            max_cost_minor=0,
            currency="EUR-cent",
            max_memory_bytes=268435456,
            max_disk_bytes=1048576,
            threads=1,
            jobs=1,
            max_proof_seconds=1,
            max_verify_seconds=1,
            max_native_overhead_basis_points=100,
            approved_by="fixture-owner",
            approval_ref=budget_approval.sha256,
        ),
        approval_ref=ArtifactDigest(bytes(32)),
    )
    evidence = tuple(
        FileRef(path=path, size=len(raw), sha256=FileSHA256(hashlib.sha256(raw).digest()))
        for path, raw in sorted(files.items())
    )
    review = AdmissionReview(
        schema_id="hallmark/admission-review/1",
        terms=protocol.review_terms(),
        owner="fixture-owner",
        relying_party_role="fixture-auditor",
        owner_approval=owner,
        relying_party_approval=party,
        evidence=evidence,
    )
    protocol = AdmissionProtocol.model_validate(
        {**protocol.model_dump(), "approval_ref": review.identity()}
    )
    validate_reviewed_admission(
        protocol, policy, review, expected_review=review.identity(), files=files
    )
    return policy, protocol, review, files


def main():
    policy, protocol, review, files = build()
    result = {
        "schema_id": "hallmark/admission-fixture/1",
        "fixture_only": True,
        "measurement_permitted": False,
        "files": {k: v.hex() for k, v in files.items()},
    }
    for name, obj in (
        ("study-policy", policy),
        ("admission", protocol),
        ("admission-review", review),
    ):
        result[name] = {
            "cbor_hex": obj.encode().hex(),
            "identity_hex": obj.identity().hex(),
            "json": json.loads(obj.model_dump_json()),
        }
        (ROOT / f"docs/schemas/{name}-v1.json").write_text(
            json.dumps(type(obj).model_json_schema(), indent=2) + "\n"
        )
    result["review_terms_hex"] = protocol.review_terms().hex()
    (ROOT / "fixtures/wire/admission-v1.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
