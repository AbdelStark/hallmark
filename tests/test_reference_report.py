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
