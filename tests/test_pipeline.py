import json
from pathlib import Path

import pytest

from hallmark.cli import main
from hallmark.contracts import Experiment
from hallmark.experiment import admit, audit_run, run_experiment
from hallmark.integrity import digest_bytes, load_contract, parse_json, read_bytes


def test_admission_rejects_changed_data_and_missing_approval(root: Path) -> None:
    config = load_contract(root / "configs/fixture.json", Experiment)
    dataset = root / "fixtures/smoke.jsonl"
    with pytest.raises(ValueError, match="SHA-256"):
        admit(config.model_copy(update={"dataset_sha256": "0" * 64}), dataset)
    with pytest.raises(ValueError, match="approval"):
        admit(config.model_copy(update={"approved_licenses": ()}), dataset)


def test_cli_validation_and_privacy_errors(
    root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["schema", "experiment"]) == 0
    assert json.loads(capsys.readouterr().out)["additionalProperties"] is False
    assert main(["validate-data", str(root / "fixtures/smoke.jsonl")]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "valid"
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"private_prompt":"do not log me"}\n')
    assert main(["validate-data", str(bad)]) == 2
    assert "do not log me" not in capsys.readouterr().err


@pytest.mark.train
def test_training_replay_and_tamper_rejection(root: Path, tmp_path: Path) -> None:
    pytest.importorskip("sklearn")
    output = tmp_path / "run"
    pin = run_experiment(root / "configs/fixture.json", output)
    assert (
        audit_run(output, root / "fixtures/smoke.jsonl", pin)["status"] == "research-replay-matched"
    )
    report = parse_json(read_bytes(output / "results.json").decode())
    assert report["evidence_class"] == "synthetic-fixture"
    assert report["fpr_evidence_status"] == "insufficient-evidence"
    assert report["zk_proof"] == "not-implemented"
    with pytest.raises(FileExistsError):
        run_experiment(root / "configs/fixture.json", output)
    with pytest.raises(ValueError, match="caller-enrolled"):
        audit_run(output, root / "fixtures/smoke.jsonl", "0" * 64)
    report["metrics"]["test"]["tp"] = 999
    (output / "results.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="hash mismatch"):
        audit_run(output, root / "fixtures/smoke.jsonl", pin)
    manifest = parse_json(read_bytes(output / "manifest.json").decode())
    manifest["artifacts"]["results.json"] = digest_bytes(read_bytes(output / "results.json"))
    (output / "manifest.json").write_text(json.dumps(manifest))
    new_pin = digest_bytes(read_bytes(output / "manifest.json"))
    with pytest.raises(ValueError, match="software replay"):
        audit_run(output, root / "fixtures/smoke.jsonl", new_pin)
