import json
from copy import deepcopy
from pathlib import Path

import pytest

from hallmark_demo.catalog import CATALOG
from hallmark_demo.results import summarize


def classifier_result():
    return dict(
        schema_id="hallmark.circle-e2e-result/1",
        status="passed",
        backend="circle",
        proofs_verified=9,
        cross_request_rejections=18,
        direct_public_mutations_rejected=63,
        roster_rejections=3,
        intermediate_parity=True,
        qualified_backend=False,
        hardware_claim="not-accepted",
        hiding_claim=False,
        cases=[
            dict(name=name, verdicts=values, proofs_verified=3, release=all(values))
            for name, values in [
                ("allow", [1, 1, 1]),
                ("cnn-block", [1, 1, 0]),
                ("rule-block", [0, 1, 1]),
            ]
        ],
    )


def test_shared_view_separates_validity_from_policy():
    summary = summarize(CATALOG["classifiers-circle"], classifier_result())
    assert summary["title"] == "Verification passed"
    assert [c["release"] for c in summary["cases"]] == [True, False, False]
    assert summary["metrics"][0]["value"] == 9


@pytest.mark.parametrize(
    "change",
    [
        {"proofs_verified": 8},
        {"proofs_verified": True},
        {"schema_id": "other"},
        {"qualified_backend": True},
        {"hardware_claim": "accepted"},
        {"status": "failed"},
    ],
)
def test_partial_or_changed_reports_cannot_claim_verification(change):
    report = classifier_result() | change
    with pytest.raises(ValueError):
        summarize(CATALOG["classifiers-circle"], report)


def test_policy_release_must_match_verified_verdicts():
    report = classifier_result()
    report["cases"][1]["release"] = True
    with pytest.raises(ValueError):
        summarize(CATALOG["classifiers-circle"], report)


def test_recorded_gpu_result_uses_real_numeric_evidence():
    path = (
        Path(__file__).resolve().parents[2]
        / "research/evidence/llm-gpu-generated-constraints-2026-10-26.json"
    )
    result = json.loads(path.read_text())["result"]
    view = summarize(CATALOG["gpu"], result)
    assert len(view["measurements"]) == 2
    assert view["measurements"][1]["prove_seconds"] == 53.941293719
    changed = deepcopy(result)
    changed["measurements"][1]["backend"] = "simd"
    with pytest.raises(ValueError):
        summarize(CATALOG["gpu"], changed)


def test_circle_default_requires_complete_cryptographic_checks():
    report = classifier_result()
    assert len(summarize(CATALOG["classifiers-circle"], report)["cases"]) == 3
    for change in (
        {"backend": "other"},
        {"direct_public_mutations_rejected": 62},
        {"roster_rejections": 2},
        {"intermediate_parity": False},
    ):
        with pytest.raises(ValueError):
            summarize(CATALOG["classifiers-circle"], report | change)


def test_circle_composed_requires_all_links_and_distinct_binding_checks():
    report = dict(
        schema_id="hallmark.circle-composed-request-result/1",
        status="passed",
        backend="circle",
        llm_proofs_verified=23,
        residual_links=22,
        fresh_llm_verifications=2,
        classifier_proofs_verified=3,
        qualified_backend=False,
        hiding_claim=False,
        hardware_claim="not-accepted",
        classifier_scope="prompt",
        safety_quality_claim=False,
        host_join=True,
        recursion=False,
        classifier_verdicts=[1, 1, 0],
        policy_release=False,
        binding_rejections=[str(i) for i in range(16)],
    )
    assert summarize(CATALOG["composed-circle"], report)["cases"][0]["release"] is False
    for change in (
        {"residual_links": 21},
        {"classifier_proofs_verified": 2},
        {"binding_rejections": ["same"] * 16},
        {"policy_release": True},
    ):
        with pytest.raises(ValueError):
            summarize(CATALOG["composed-circle"], report | change)
