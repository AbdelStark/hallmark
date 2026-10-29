"""Admission is a pinned declaration check, exercised only with harmless markers."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from hallmark.admission import (
    AdmissionProtocol,
    AdmissionReview,
    BudgetAdmission,
    Candidate,
    SourceApproval,
    StudyPolicy,
    validate_reviewed_admission,
)
from hallmark.errors import HallmarkError
from hallmark.manifests import FileRef
from hallmark.wire import WireError, decode, encode

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def vector() -> dict[str, Any]:
    return json.loads((ROOT / "fixtures/wire/admission-v1.json").read_text())


@pytest.fixture
def artifacts(vector: dict[str, Any]) -> tuple[Any, ...]:
    policy = StudyPolicy.decode(bytes.fromhex(vector["study-policy"]["cbor_hex"]))
    protocol = AdmissionProtocol.decode(bytes.fromhex(vector["admission"]["cbor_hex"]))
    review = AdmissionReview.decode(bytes.fromhex(vector["admission-review"]["cbor_hex"]))
    files = {k: bytes.fromhex(v) for k, v in vector["files"].items()}
    return policy, protocol, review, files


def check(artifacts: tuple[Any, ...], **kwargs: Any) -> None:
    policy, protocol, review, files = artifacts
    validate_reviewed_admission(
        protocol,
        policy,
        review,
        expected_review=kwargs.get("pin", review.identity()),
        files=kwargs.get("files", files),
    )


def rebind(protocol: AdmissionProtocol, review: AdmissionReview) -> tuple[Any, Any]:
    review = AdmissionReview.model_validate(
        {**review.model_dump(), "terms": protocol.review_terms()}
    )
    protocol = AdmissionProtocol.model_validate(
        {**protocol.model_dump(), "approval_ref": review.identity()}
    )
    return protocol, review


def test_fixture_roundtrips_and_fixed_hashes(vector: dict[str, Any], artifacts: Any) -> None:
    policy, protocol, review, _ = artifacts
    assert vector["fixture_only"] and vector["measurement_permitted"] is False
    check(artifacts)
    for name, obj, domain in (
        ("study-policy", policy, "policy"),
        ("admission", protocol, "protocol"),
        ("admission-review", review, "review"),
    ):
        assert obj.encode().hex() == vector[name]["cbor_hex"]
        assert obj.identity().hex() == vector[name]["identity_hex"]
        assert type(obj).model_validate_json(obj.model_dump_json()) == obj
        assert type(obj).model_json_schema() == json.loads(
            (ROOT / f"docs/schemas/{name}-v1.json").read_text()
        )
        tag = f"hallmark/v1/{domain}".encode()
        assert (
            hashlib.sha256(len(tag).to_bytes(4, "big") + tag + obj.encode()).digest()
            == obj.identity()
        )
    assert protocol.review_terms().hex() == vector["review_terms_hex"]
    changed = AdmissionProtocol.model_validate({**protocol.model_dump(), "approval_ref": b"x" * 32})
    assert changed.review_terms() == protocol.review_terms()
    assert changed.identity() != protocol.identity()


@pytest.mark.parametrize("pin", [None, b"", b"wrong" * 8, b"x" * 32, bytearray(32), True])
def test_external_pin_required(artifacts: Any, pin: Any) -> None:
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        check(artifacts, pin=pin)


@pytest.mark.parametrize(
    "field,value",
    [
        ("target_fpr", "0"),
        ("target_fpr", "1"),
        ("alpha", "0"),
        ("alpha", "1"),
        ("min_tpr", "0"),
        ("max_quality_loss", "1"),
        ("target_fpr", 0.01),
        ("alpha", True),
        ("target_fpr", "1e-2"),
        ("target_fpr", "0.010"),
        ("target_fpr", "00.1"),
        ("target_fpr", ".1"),
        ("target_fpr", "NaN"),
        ("alpha", " 0.05"),
        ("alpha", "0.05\n"),
        ("alpha", "0.0000000000000000001"),
        ("seeds", [17, 17, 43]),
        ("seeds", [True, 29, 43]),
        ("seeds", [17, 29]),
        ("relying_party_role", ""),
        ("approval_ref", None),
    ],
)
def test_incomplete_or_ambiguous_protocol_rejects(artifacts: Any, field: str, value: Any) -> None:
    _, protocol, _, _ = artifacts
    with pytest.raises(ValidationError):
        AdmissionProtocol.model_validate({**protocol.model_dump(), field: value})


@pytest.mark.parametrize(
    "field", ["policy", "rubric", "split_manifest", "evaluator", "approval_ref"]
)
def test_all_protocol_pins_are_required(artifacts: Any, field: str) -> None:
    value = artifacts[1].model_dump()
    del value[field]
    with pytest.raises(ValidationError):
        AdmissionProtocol.model_validate(value)


@pytest.mark.parametrize("mutation", ["omit", "reorder", "duplicate", "unpin-model", "alias-file"])
def test_roster_cannot_silently_shrink(artifacts: Any, mutation: str) -> None:
    value = artifacts[1].model_dump()
    roster = list(value["candidate_roster"])
    if mutation == "omit":
        roster.pop()
    elif mutation == "reorder":
        roster.reverse()
    elif mutation == "duplicate":
        roster[-1] = roster[0]
    elif mutation == "unpin-model":
        roster[-1]["base_files"] = ()
    else:
        roster[-1]["base_files"] *= 2
    value["candidate_roster"] = tuple(roster)
    with pytest.raises(ValidationError):
        AdmissionProtocol.model_validate(value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_cost_minor", -1),
        ("max_cost_minor", True),
        ("max_wall_seconds", 0),
        ("max_memory_bytes", 0),
        ("max_disk_bytes", 0),
        ("threads", 0),
        ("jobs", 0),
        ("max_proof_seconds", 61),
        ("max_verify_seconds", 61),
        ("max_native_overhead_basis_points", 0),
        ("approved_by", ""),
    ],
)
def test_budget_is_explicit_and_bounded(artifacts: Any, field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        BudgetAdmission.model_validate({**artifacts[1].budget.model_dump(), field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("target_fpr", "0.02"),
        ("alpha", "0.1"),
        ("min_tpr", "0.8"),
        ("max_quality_loss", "0.03"),
        ("seeds", (18, 29, 43)),
        ("split_manifest", b"s" * 32),
        ("evaluator", b"e" * 32),
        ("policy", b"p" * 32),
        ("rubric", b"r" * 32),
    ],
)
def test_changed_terms_need_a_new_review(artifacts: Any, field: str, value: Any) -> None:
    policy, protocol, review, files = artifacts
    changed = AdmissionProtocol.model_validate({**protocol.model_dump(), field: value})
    assert changed.review_terms() != protocol.review_terms()
    with pytest.raises(HallmarkError, match="REQUEST_MISMATCH"):
        check((policy, changed, review, files))


@pytest.mark.parametrize("mutation", ["missing", "extra", "changed", "wrong-type"])
def test_review_documents_are_exact(artifacts: Any, mutation: str) -> None:
    files = dict(artifacts[3])
    path = next(iter(files))
    if mutation == "missing":
        del files[path]
    elif mutation == "extra":
        files["extra.json"] = b"extra"
    elif mutation == "changed":
        files[path] += b"changed private data"
    else:
        files[path] = bytearray(files[path])
    with pytest.raises(HallmarkError, match="INPUT_INVALID") as error:
        check(artifacts, files=files)
    assert "private data" not in str(error.value)


@pytest.mark.parametrize("field", ["license_text", "revision", "approval_ref"])
def test_reissued_review_still_requires_source_evidence(artifacts: Any, field: str) -> None:
    policy, protocol, review, files = artifacts
    source = SourceApproval.model_validate({**protocol.sources[0].model_dump(), field: b"z" * 32})
    changed = AdmissionProtocol.model_validate({**protocol.model_dump(), "sources": (source,)})
    changed, review = rebind(changed, review)
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        check((policy, changed, review, files))


@pytest.mark.parametrize("field", ["owner_approval", "relying_party_approval"])
def test_reissued_review_still_requires_both_roles(artifacts: Any, field: str) -> None:
    policy, protocol, review, files = artifacts
    absent = FileRef(path="absent.json", size=1, sha256=b"a" * 32)
    review = AdmissionReview.model_validate({**review.model_dump(), field: absent})
    protocol, review = rebind(protocol, review)
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        check((policy, protocol, review, files))


@pytest.mark.parametrize("field", ["owner", "relying_party_role"])
def test_reissued_review_roles_must_match_terms(artifacts: Any, field: str) -> None:
    policy, protocol, review, files = artifacts
    review = AdmissionReview.model_validate({**review.model_dump(), field: "wrong-role"})
    protocol, review = rebind(protocol, review)
    with pytest.raises(HallmarkError, match="REQUEST_MISMATCH"):
        check((policy, protocol, review, files))


@pytest.mark.parametrize("kind", ["duplicate", "oversized", "aggregate", "traversal"])
def test_evidence_bounds(artifacts: Any, kind: str) -> None:
    value = artifacts[2].model_dump()
    refs = list(value["evidence"])
    if kind == "duplicate":
        refs.append(refs[0])
    elif kind == "oversized":
        refs[0]["size"] = 1024 * 1024 + 1
    elif kind == "aggregate":
        for ref in refs:
            ref["size"] = 1024 * 1024
    else:
        refs[0]["path"] = "../outside"
    value["evidence"] = tuple(refs)
    with pytest.raises(ValidationError):
        AdmissionReview.model_validate(value)


@pytest.mark.parametrize(
    "cls,index", [(StudyPolicy, 0), (AdmissionProtocol, 1), (AdmissionReview, 2)]
)
def test_wire_extra_fields_and_unsafe_constructs_reject(
    artifacts: Any, cls: Any, index: int
) -> None:
    obj = artifacts[index]
    value = decode(obj.encode())
    value["unreviewed"] = True
    with pytest.raises(WireError):
        cls.decode(encode(value))
    with pytest.raises(WireError):
        cls.decode(obj.encode() + b"\x00")
    invalid = obj.model_copy(update={"schema_id": "wrong"})
    with pytest.raises(WireError):
        invalid.identity()
    with pytest.raises(WireError):
        invalid.encode()


def test_duplicate_sources_and_changed_policy(artifacts: Any) -> None:
    policy, protocol, review, files = artifacts
    with pytest.raises(ValidationError):
        AdmissionProtocol.model_validate({**protocol.model_dump(), "sources": protocol.sources * 2})
    changed = StudyPolicy.model_validate({**policy.model_dump(), "max_prompt_bytes": 100})
    with pytest.raises(HallmarkError, match="REQUEST_MISMATCH"):
        check((changed, protocol, review, files))


def test_protocol_schema_cannot_accept_a_draft(artifacts: Any) -> None:
    value = artifacts[1].model_dump()
    value["schema_id"] = "hallmark/admission-proposal/1"
    value["min_tpr"] = None
    with pytest.raises(ValidationError):
        AdmissionProtocol.model_validate(value)


def test_approved_study_still_refuses_incomplete_measurement_admission() -> None:
    value = json.loads((ROOT / "research/proposals/inj-direct-v1/proposal.json").read_text())
    assert value["measurement_permitted"] is False
    assert value["asset_access_permitted"] is True
    assert all(source["admission_status"] == "hold" for source in value["sources"])
    assert all(v is not None for v in value["quality"].values())
    assert all(v is not None for v in value["budget"].values())
    assert value["evaluator"] is None
    assert value["sampling"]["split_manifest"] is None
    assert value["review"]["independently_enrolled_review"] is None
    with pytest.raises(ValidationError):
        AdmissionProtocol.model_validate(value)


def test_study_budget_and_roles_match_current_authority() -> None:
    authority = json.loads((ROOT / "research/AUTHORITY.json").read_text())
    proposal = json.loads((ROOT / "research/proposals/inj-direct-v1/proposal.json").read_text())
    budget, local = proposal["budget"], authority["local"]
    for key in ("max_memory_bytes", "max_disk_bytes", "max_cost_minor", "currency", "host"):
        assert budget[key] == local[key]
    assert budget["max_wall_seconds"] == local["max_total_seconds"]
    assert budget["max_job_seconds"] == local["max_job_seconds"]
    assert budget["threads"] == local["training_threads"]
    assert budget["jobs"] == local["concurrent_jobs"]
    assert proposal["relying_party"]["designated_owner"] == authority["relying_party"]["owner"]
    assert proposal["relying_party"]["approved_role"] == authority["relying_party"]["role"]
    assert proposal["review"]["owner_approval"] == authority["approval_ref"]
    assert (ROOT / authority["approval_ref"]).is_file()
    assert authority["source_selection"]["ambiguous_licences"] is False
    assert authority["hugging_face_jobs"]["authorized_if_needed"] is True
    assert authority["hugging_face_jobs"]["private_uploads"] is False
    assert authority["local"]["max_disk_bytes"] == 40 * 1024**3
    assert authority["data_review"]["synthetic_pipeline_permitted"] is True
    assert authority["data_review"]["human_review_required_for_pipeline"] is False
    assert authority["data_review"]["quality_claim_from_synthetic_pipeline"] is False
    assert authority["hugging_face_jobs"]["agent_execution_limits"]["allowed_flavors"] == [
        "t4-small",
        "l4x1",
    ]
    assert authority["hardware_procurement"] == authority["reviewer_contact"] == "options-only"
    assert authority["public_repository"] is True
    assert authority["make_private_only_on_explicit_request"] is True


@pytest.mark.train
def test_design_power_reproduces_with_exact_tail_cross_checks() -> None:
    pytest.importorskip("scipy")
    script = ROOT / "scripts/plan_admission_power.py"
    expected = json.loads(
        (ROOT / "research/evidence/dev-lock-design-power-refresh-2026-10-29.json").read_text()
    )
    original = json.loads((ROOT / "research/evidence/w13-design-power-2026-10-20.json").read_text())
    assert {k: v for k, v in expected.items() if k != "lock_sha256"} == {
        k: v for k, v in original.items() if k != "lock_sha256"
    }
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=55,
    )
    actual = json.loads(result.stdout)
    assert actual["source_sha256"] == expected["source_sha256"]
    assert actual["lock_sha256"] == expected["lock_sha256"]
    assert actual["observed_model_performance"] is False
    for observed, frozen in zip(actual["frozen_counts"], expected["frozen_counts"], strict=True):
        assert observed["endpoint"] == frozen["endpoint"]
        assert observed["groups"] == frozen["groups"]
        assert observed["maximum_events"] == frozen["maximum_events"]
        assert observed["conditional_power"] == pytest.approx(
            frozen["conditional_power"], abs=1e-12
        )


def test_nested_budget_change_requires_new_review(artifacts: Any) -> None:
    policy, protocol, review, files = artifacts
    budget = BudgetAdmission.model_validate({**protocol.budget.model_dump(), "threads": 2})
    changed = AdmissionProtocol.model_validate({**protocol.model_dump(), "budget": budget})
    with pytest.raises(HallmarkError, match="REQUEST_MISMATCH"):
        check((policy, changed, review, files))


def test_candidate_config_and_code_are_required_documents(artifacts: Any) -> None:
    policy, protocol, review, files = artifacts
    candidate = Candidate.model_validate(
        {**protocol.candidate_roster[0].model_dump(), "config": b"c" * 32}
    )
    protocol = AdmissionProtocol.model_validate(
        {**protocol.model_dump(), "candidate_roster": (candidate, *protocol.candidate_roster[1:])}
    )
    protocol, review = rebind(protocol, review)
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        check((policy, protocol, review, files))
