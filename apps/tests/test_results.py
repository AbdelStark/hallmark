import json
from copy import deepcopy
from pathlib import Path

import pytest

from hallmark_demo.catalog import CATALOG
from hallmark_demo.results import summarize


def classifier_result():
    return dict(
        schema_id="hallmark.e2e-result/1",
        status="passed",
        proofs_verified=9,
        cross_request_rejections=18,
        arithmetic_cases=405,
        qualified_backend=False,
        hardware_claim="not-accepted",
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
    summary = summarize(CATALOG["classifiers"], classifier_result())
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
        summarize(CATALOG["classifiers"], report)


def test_policy_release_must_match_verified_verdicts():
    report = classifier_result()
    report["cases"][1]["release"] = True
    with pytest.raises(ValueError):
        summarize(CATALOG["classifiers"], report)


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
