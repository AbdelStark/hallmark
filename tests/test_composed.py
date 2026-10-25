"""Binding and orchestration fixtures; real proofs require the retained campaigns."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import composed_input as composed
import run_composed as driver


class Policy:
    def identity(self):
        return b"p" * 32


def test_fixed_case_request_and_random_interaction():
    expected, opening = composed.request(Policy())
    assert (
        expected.model.hex() == "6e4bbf5af998722143be658312ab4abbc7ad05745436ebedaaa0174f30cffc2f"
    )
    composed.check_request(opening, expected)
    other, other_opening = composed.request(Policy())
    assert expected.model == other.model and expected.policy == other.policy
    assert expected.nonce != other.nonce
    assert expected.interaction_id != other.interaction_id
    assert opening.salt != other_opening.salt
    assert opening.prompt == "Name the capital of France in one short sentence."
    assert opening.response == "The capital of France is Paris."


@pytest.mark.parametrize("field", ["prompt", "response", "system_ref", "model"])
def test_changed_llm_statement_rejects(field):
    expected, opening = composed.request(Policy())
    if field == "model":
        expected = expected.model_copy(update={field: b"x" * 32})
    else:
        value = b"x" * 32 if field == "system_ref" else getattr(opening, field) + "!"
        opening = opening.model_copy(update={field: value})
    with pytest.raises(ValueError, match="request mismatch"):
        composed.check_request(opening, expected)


def test_model_identity_binds_quantization_checkpoint_and_calibration():
    value = composed.case()
    pin = composed.model_identity(value)
    for field in ("spec", "model", "calibration_sha256", "source"):
        changed = copy.deepcopy(value)
        changed[field] = "changed"
        assert composed.model_identity(changed) != pin
    value["prompt"] += "!"
    assert composed.model_identity(value) == pin


def test_changed_case_file_rejects(tmp_path, monkeypatch):
    path = tmp_path / "research/probes/sash/response-case.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    monkeypatch.setattr(composed, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="case changed"):
        composed.case()


def classifier_report(tmp_path):
    expected, opening = composed.request(Policy())
    (tmp_path / "llm-response-request.json").write_text(
        json.dumps(
            dict(
                expected_cbor_hex=expected.encode().hex(),
                opening_cbor_hex=opening.encode().hex(),
            )
        )
    )
    report = dict(
        schema_id="hallmark.trained-common-result/1",
        status="passed",
        qualified_backend=False,
        hardware_claim="not-accepted",
        composed_binding_rejections=driver.BINDINGS.copy(),
        arithmetic_cases=dict(rule=133, mlp=133, encoder=133),
        cases=[dict(name="llm-response", proofs_verified=3, verdicts=[1, 1, 0], release=False)],
    )
    return report


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r.update(status="failed"),
        lambda r: r["cases"][0].update(proofs_verified=2),
        lambda r: r["cases"][0].update(release=True),
        lambda r: r["composed_binding_rejections"].pop(),
        lambda r: r["arithmetic_cases"].update(encoder=132),
        lambda r: r.update(qualified_backend=True),
    ],
)
def test_incomplete_or_overclaimed_report_rejects(tmp_path, change):
    report = classifier_report(tmp_path)
    path = tmp_path / "result.json"
    path.write_text(json.dumps(report))
    assert driver.check_classifiers(tmp_path)[0] == report
    change(report)
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="incomplete composed"):
        driver.check_classifiers(tmp_path)


def test_saved_success_cannot_replace_fresh_llm_verification(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "ROOT", tmp_path)
    monkeypatch.setattr(driver.run_e2e, "source_pins", lambda: {"fixture": "pin"})
    monkeypatch.setattr(driver, "classifier_inputs", lambda _: ("unused",))
    monkeypatch.setattr(driver.shutil, "disk_usage", lambda _: type("Disk", (), {"free": 2**40})())
    old = tmp_path / "old"
    old.mkdir()
    (old / "result.json").write_text('{"passed":true}')
    calls = []

    def fail(path):
        calls.append(path)
        raise ValueError("fresh proof check failed")

    monkeypatch.setattr(driver.verify_llm, "run", fail)
    with pytest.raises(ValueError, match="fresh proof check"):
        driver.run(llm_run=old, classifier_run=old)
    assert calls == [old]
    outputs = list((tmp_path / "runs").iterdir())
    assert len(outputs) == 1
    assert (outputs[0] / "failure.json").is_file()
    assert not (outputs[0] / "result.json").exists()


def test_make_composed_supports_retained_inputs():
    import subprocess

    output = subprocess.check_output(
        [
            "make",
            "--no-print-directory",
            "-n",
            "e2e-composed",
            "LLM_RUN=llm",
            "CLASSIFIER_RUN=classifiers",
        ],
        cwd=driver.ROOT,
        text=True,
    )
    assert '--llm-run "llm"' in output and '--classifier-run "classifiers"' in output
    assert "--extra train --extra llm" in output
