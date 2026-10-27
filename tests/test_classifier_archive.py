"""Synthetic report rejection happens before model or cryptographic worker admission."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_classifier_measurements import matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_classifier_archive as checker
from benchmark_classifiers import summarize


@pytest.mark.parametrize("mutation", ["source", "sample", "preparation", "missing"])
def test_invalid_report_cannot_reach_model_or_verifier_admission(tmp_path, monkeypatch, mutation):
    plan, samples = matrix()
    for sample in samples:
        sample["sample_id"] = f"{sample['phase']}-{sample['repetition']:02d}-{sample['backend']}"
        sample["preparation_reference"] = (
            sample["sample_id"] if sample["phase"] == "fresh" else "fresh-00-" + sample["backend"]
        )
    summary = summarize(samples, plan)
    report = dict(
        status="passed",
        measured_proofs=144,
        raw_samples=samples,
        source_commit="a" * 40,
        campaign=dict(summary=summary),
    )
    if mutation == "source":
        report["source_commit"] = "b" * 40
    elif mutation == "sample":
        samples[0]["sample_id"] = "../escape"
    elif mutation == "preparation":
        samples[0]["preparation_reference"] = "../escape"
    else:
        samples.pop()
    root = tmp_path / "audit"
    root.mkdir()
    (root / "report.json").write_text(json.dumps(report))
    (tmp_path / "runs").mkdir()
    monkeypatch.setattr(checker, "ROOT", tmp_path)

    def forbidden(*args):
        raise AssertionError("model admission must not be reached")

    monkeypatch.setattr(checker.comparison, "admitted", forbidden)
    args = SimpleNamespace(
        audit_run=root,
        classifier_run=tmp_path / "absent-models",
        output=tmp_path / "runs/verify",
        expected_commit="a" * 40,
    )
    with pytest.raises(ValueError):
        checker.run(args)
