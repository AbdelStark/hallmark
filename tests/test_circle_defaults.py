"""Native enrollment parity and default dispatch; synthetic fixtures make no proof claim."""

import copy
import subprocess
import sys
from pathlib import Path

import pytest
from test_trained_common import fixture as fixture

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import circle_backend as backend
import circle_inputs
import classifier_comparison as comparison
import run_circle_e2e

pytestmark = pytest.mark.train


def test_native_preparation_has_identical_circle_enrollment_without_keys(fixture):
    _, _, exports, _, legacy, _, *_ = fixture
    native, policy = circle_inputs.native_templates(exports)
    assert all("key" not in n for n in native)
    for before, after in zip(legacy, native, strict=True):
        before = before["classifier"].model_dump()
        after = after["classifier"].model_dump()
        for field in ("backend", "verifier_key", "setup"):
            before.pop(field)
            after.pop(field)
        assert before == after
    engines = {
        kind: comparison.encoded(
            dict(
                schema="hallmark.circle-enrollment/1",
                external_multiplicities=[1] * 103,
                program_sha256=str(i) * 64,
            )
        )
        for i, kind in enumerate(backend.KINDS)
    }
    assert backend.enroll(engines, native) == backend.enroll(engines, legacy)
    assert policy.max_prompt_bytes == 96


def test_native_preparation_rejects_changed_request_and_pin(fixture, tmp_path, monkeypatch):
    exports = fixture[2]
    monkeypatch.setattr(comparison, "exports", lambda _: copy.deepcopy(exports))
    monkeypatch.setattr(comparison, "EXPORTS", {})
    pin = circle_inputs.create(tmp_path)
    circle_inputs.admit(tmp_path, pin)
    with pytest.raises(ValueError, match="pin mismatch"):
        circle_inputs.admit(tmp_path, "0" * 64)
    path = tmp_path / "requests/allow-request.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="request mismatch"):
        circle_inputs.admit(tmp_path, pin)


def test_circle_unsupported_host_stops_before_output(monkeypatch):
    monkeypatch.setattr(run_circle_e2e.platform, "system", lambda: "Linux")
    with pytest.raises(ValueError, match="Apple Silicon"):
        run_circle_e2e.run()


@pytest.mark.parametrize(
    "target,driver,legacy",
    [
        ("e2e", "run_circle_e2e.py", "run_e2e.py"),
        ("e2e-composed", "run_circle_composed.py", "run_composed.py"),
    ],
)
def test_make_defaults_circle_and_preserves_explicit_gnark(target, driver, legacy):
    root = Path(__file__).resolve().parents[1]
    command = ["make", "--no-print-directory", "-n", target]
    default = subprocess.check_output(command, cwd=root, text=True)
    baseline = subprocess.check_output([*command, "BACKEND=gnark"], cwd=root, text=True)
    assert driver in default and legacy not in default
    assert legacy in baseline and driver not in baseline


@pytest.mark.parametrize("bad_authority", [True, False])
def test_composition_rejects_authority_or_incomplete_llm_before_classifier_proving(
    tmp_path, monkeypatch, bad_authority
):
    from types import SimpleNamespace

    import run_circle_composed as composed

    monkeypatch.setattr(composed, "ROOT", tmp_path)
    monkeypatch.setattr(
        composed.shutil, "disk_usage", lambda _: SimpleNamespace(free=128 * 1024**3)
    )
    monkeypatch.setattr(composed.verify_llm, "read_enrollment", lambda *a: (None, None))
    monkeypatch.setattr(composed.verify_llm, "source_inventory", lambda: {})
    monkeypatch.setattr(composed.verify_llm, "verifier_identity", lambda _: bytes(32))
    monkeypatch.setattr(composed.run_e2e, "source_pins", lambda: {})
    invoked = []

    def authority(*args, **kwargs):
        if bad_authority:
            raise ValueError("invalid authority")
        return {"kind": "checkout-case"}

    monkeypatch.setattr(composed.verify_llm, "parameter_authority", authority)
    verification = tmp_path / "native"
    verification.mkdir()
    (verification / "result.json").write_text('{"passed": true, "proofs": 22}')
    monkeypatch.setattr(composed.verify_llm, "run", lambda *a, **k: verification)
    monkeypatch.setattr(composed.run_circle_e2e, "run", lambda *a, **k: invoked.append("prove"))
    with pytest.raises(ValueError, match="invalid authority|incomplete fresh LLM"):
        composed.run(llm_run=tmp_path)
    assert invoked == []
    assert len(list((tmp_path / "runs").glob("composed-circle-*/failure.json"))) == 1
