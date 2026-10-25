"""Binding and orchestration fixtures; real proofs require the retained campaigns."""

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hallmark.errors import HallmarkError
from hallmark.llm_enrollment import LIMITS, LlmEnrollment, sign_llm_enrollment

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import composed_input as composed
import run_composed as driver


class Policy:
    def identity(self):
        return b"p" * 32


@pytest.mark.parametrize("payload", [b"legacy build fixture", b"canonical build fixture"])
def test_classifier_binary_admission_preserves_the_actual_pin(tmp_path, monkeypatch, payload):
    binary = tmp_path / "probe"
    admitted = set()
    for content in (b"legacy build fixture", b"canonical build fixture"):
        binary.write_bytes(content)
        admitted.add(driver.run_e2e.sha(binary))
    monkeypatch.setattr(driver, "CLASSIFIER_BINARIES", admitted)
    monkeypatch.setattr(driver.run_e2e, "check_training", lambda _: None)
    binary.write_bytes(payload)
    inputs = driver.classifier_inputs(tmp_path)
    assert inputs[:2] == (binary, driver.run_e2e.sha(binary))
    binary.write_bytes(payload + b"changed")
    with pytest.raises(ValueError, match="binary pin mismatch"):
        driver.classifier_inputs(tmp_path)


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

    def fail(path, **kwargs):
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


@pytest.mark.parametrize("field", ["enrollment", "trusted_key"])
def test_partial_enrollment_rejects_before_preparation(tmp_path, monkeypatch, field):
    monkeypatch.setattr(driver, "ROOT", tmp_path)
    monkeypatch.setattr(driver.shutil, "disk_usage", lambda _: type("Disk", (), {"free": 2**40})())
    monkeypatch.setattr(driver.run_e2e, "source_pins", lambda: {"fixture": "pin"})
    calls = []
    monkeypatch.setattr(driver.run_llm_e2e, "run", lambda *_: calls.append("llm"))
    monkeypatch.setattr(driver.run_e2e, "run", lambda: calls.append("classifiers"))
    with pytest.raises(ValueError, match="Supply enrollment and trusted key together"):
        driver.run(**{field: tmp_path / "enrollment.cbor" if field == "enrollment" else "0" * 64})
    assert calls == []


@pytest.fixture
def signed_workflow(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "ROOT", tmp_path)
    monkeypatch.setattr(driver.shutil, "disk_usage", lambda _: type("Disk", (), {"free": 2**40})())
    monkeypatch.setattr(driver.run_e2e, "source_pins", lambda: {"fixture": "pin"})
    monkeypatch.setattr(driver, "classifier_inputs", lambda _: ("fixture",))
    clock = [100]
    monkeypatch.setattr(driver.verify_llm.time, "time", lambda: clock[0])
    key = Ed25519PrivateKey.generate()
    body = LlmEnrollment(
        schema_id="hallmark/llm-enrollment/1",
        case_sha256=bytes.fromhex(composed.CASE_SHA256),
        verifier=driver.verify_llm.verifier_identity(driver.verify_llm.source_inventory()),
        not_before=100,
        expires_at=200,
    )
    path = tmp_path / "authorization.cbor"
    raw = sign_llm_enrollment(body, key).encode(limits=LIMITS)
    path.write_bytes(raw)
    state = dict(calls=[], clock=clock, key=key, body=body, path=path, raw=raw)

    def unexpected_preparation(*args):
        state["calls"].append("preparation")
        raise AssertionError("unexpected fresh preparation")

    monkeypatch.setattr(driver.run_llm_e2e, "run", unexpected_preparation)
    monkeypatch.setattr(driver.run_e2e, "run", unexpected_preparation)

    def verifier(previous, *, enrollment, trusted_key):
        state["calls"].append("verify")
        expected = dict(kind="checkout-case")
        if enrollment is not None:
            assert enrollment != path and enrollment.read_bytes() == raw
            assert trusted_key == key.public_key().public_bytes_raw().hex()
            path.write_bytes(b"changed after the caller's snapshot")
            expected = dict(
                schema_id="hallmark.llm-parameter-authority/1",
                kind="ed25519",
                enrollment_sha256=hashlib.sha256(raw).hexdigest(),
                trusted_key_sha256=hashlib.sha256(key.public_key().public_bytes_raw()).hexdigest(),
                not_before=100,
                expires_at=200,
                checked_at=100,
                stage="after-verification",
            )
        expected.update(state.get("changed_authority", {}))
        output = tmp_path / "native-result"
        output.mkdir()
        driver.run_e2e.write_json(
            output / "result.json",
            dict(
                passed=True,
                proofs=23,
                residual_links=22,
                fresh_verifications=2,
                response="The capital of France is Paris.",
                parameter_authority=expected,
            ),
        )
        return output

    monkeypatch.setattr(driver.verify_llm, "run", verifier)

    def classifiers(*args, **kwargs):
        state["calls"].append("classifier-proofs")
        output = args[-1]
        output.mkdir()
        driver.run_e2e.write_json(output / "result.json", classifier_report(output))
        if state.get("expire"):
            clock[0] = 200

    monkeypatch.setattr(driver.run_trained_common, "run", classifiers)
    return state


def run_authorized(state):
    return driver.run(
        llm_run=state["path"].parent / "retained-llm",
        classifier_run=state["path"].parent / "retained-classifiers",
        enrollment=state["path"],
        trusted_key=state["key"].public_key().public_bytes_raw().hex(),
    )


@pytest.mark.parametrize("bad", ["wrong-key", "expired", "case", "source", "malformed", "tampered"])
def test_bad_authorization_never_prepares_or_verifies(signed_workflow, bad):
    state = signed_workflow
    if bad == "wrong-key":
        state["key"] = Ed25519PrivateKey.generate()
    elif bad == "expired":
        state["clock"][0] = 200
    elif bad in ("case", "source"):
        field = "case_sha256" if bad == "case" else "verifier"
        body = state["body"].model_copy(update={field: b"x" * 32})
        state["path"].write_bytes(sign_llm_enrollment(body, state["key"]).encode(limits=LIMITS))
    elif bad == "malformed":
        state["path"].write_bytes(b"invalid")
    else:
        state["path"].write_bytes(state["raw"][:-1] + bytes([state["raw"][-1] ^ 1]))
    with pytest.raises(HallmarkError):
        run_authorized(state)
    assert state["calls"] == []
    assert not list(state["path"].parent.glob("runs/*/result.json"))


def test_signed_workflow_freezes_and_reports_the_authority(signed_workflow):
    state = signed_workflow
    output = run_authorized(state)
    result = json.loads((output / "result.json").read_text())
    authority = result["parameter_authority"]
    assert authority["kind"] == "ed25519" and authority["stage"] == "after-composition"
    assert authority["enrollment_sha256"] == hashlib.sha256(state["raw"]).hexdigest()
    assert (output / "enrollment.cbor").read_bytes() == state["raw"]
    assert state["path"].read_bytes() != state["raw"]
    assert state["calls"] == ["verify", "classifier-proofs"]
    assert result["classifier_verdicts"] == [1, 1, 0] and result["policy_release"] is False


@pytest.mark.parametrize("public", ["z" * 64, "A" * 64, "a" * 63])
def test_invalid_key_encoding_rejects_before_preparation(signed_workflow, public):
    with pytest.raises(ValueError, match="64 lowercase hex"):
        driver.run(enrollment=signed_workflow["path"], trusted_key=public)
    assert signed_workflow["calls"] == []


@pytest.mark.parametrize("change", [{"kind": "checkout-case"}, {"enrollment_sha256": "0" * 64}])
def test_changed_native_authority_rejects_before_classifier_proving(signed_workflow, change):
    signed_workflow["changed_authority"] = change
    with pytest.raises(ValueError, match="authority mismatch"):
        run_authorized(signed_workflow)
    assert signed_workflow["calls"] == ["verify"]


def test_expiry_during_classifier_proving_never_publishes_success(signed_workflow):
    signed_workflow["expire"] = True
    with pytest.raises(HallmarkError, match="STALE_EVIDENCE"):
        run_authorized(signed_workflow)
    assert signed_workflow["calls"] == ["verify", "classifier-proofs"]
    output = next(signed_workflow["path"].parent.glob("runs/composed-*"))
    assert (output / "failure.json").is_file() and not (output / "result.json").exists()


def test_unsigned_workflow_reports_checkout_authority(signed_workflow):
    state = signed_workflow
    output = driver.run(llm_run=state["path"].parent, classifier_run=state["path"].parent)
    result = json.loads((output / "result.json").read_text())
    assert result["parameter_authority"] == {"kind": "checkout-case"}
    assert not (output / "enrollment.cbor").exists()
