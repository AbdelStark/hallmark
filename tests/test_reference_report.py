"""Timing reports must retain failures, counts and distinct timer boundaries."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from reference_report import classifier


def test_incomplete_classifier_campaign_cannot_publish_timing_numbers(tmp_path):
    (tmp_path / "proofs").mkdir()
    path = tmp_path / "proofs/result.json"
    for costs in ([], [{"name": "allow-prove-rule", "exit_code": 0}]):
        path.write_text(json.dumps(dict(status="passed", costs=costs)))
        with pytest.raises(ValueError, match="incomplete classifier timing"):
            classifier(tmp_path)


def test_readme_headlines_match_frozen_reference_rows():
    root = Path(__file__).resolve().parents[1]
    evidence = json.loads((root / "research/evidence/circle-reference-2026-10-28.json").read_text())
    metrics = evidence["metrics"]
    c = metrics["classifiers"]
    assert c["proof_bytes"] == sum(r["proof_bytes"] for r in c["rows"]) == 18_063_779
    assert len(c["rows"]) == 9
    assert metrics["llm"]["backends"]["cuda"]["proof_bytes"] == 737_858_641
    readme = (root / "README.md").read_text()
    for exact_row in (
        "| **Final STWO proving calls** | **24.061 s** |",
        "| **Fresh proof-only verifier commands** | **0.807 s** |",
        "| **Actual serialized proofs** | **18,063,779 bytes** |",
        "| **Proving-session timers** | 547.75 s | **53.94 s** |",
        "| Separate full-grid **CPU** verifier on H200 host | 85.35 s | **84.32 s** |",
    ):
        assert exact_row in readme
    assert evidence["discussion_url"] in readme
