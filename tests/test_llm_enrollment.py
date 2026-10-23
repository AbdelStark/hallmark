"""Parameter authorization tests; fixture signers are not operational roots."""

import copy
import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hallmark.errors import HallmarkError
from hallmark.llm_enrollment import (
    LIMITS,
    LlmEnrollment,
    SignedLlmEnrollment,
    sign_llm_enrollment,
    verify_llm_enrollment,
)
from hallmark.wire import WireError, encode

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
native = importlib.import_module("verify_llm")
ROOT = Path(__file__).resolve().parents[1]


def test_enrollment_schemas_and_public_conformance_vector():
    for model, filename in [
        (LlmEnrollment, "llm-enrollment-v1.json"),
        (SignedLlmEnrollment, "signed-llm-enrollment-v1.json"),
    ]:
        assert model.model_json_schema() == json.loads(
            (ROOT / "docs/schemas" / filename).read_text()
        )
    vector = json.loads((ROOT / "fixtures/wire/llm-enrollment-v1.json").read_text())
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(vector["seed_hex"]))
    signed = SignedLlmEnrollment.decode(bytes.fromhex(vector["signed_cbor_hex"]), limits=LIMITS)
    assert signed.body.model_dump(mode="json") == vector["body"]
    assert signed.body.encode(limits=LIMITS).hex() == vector["body_cbor_hex"]
    assert signed.body.signing_bytes().hex() == vector["signing_bytes_hex"]
    assert sign_llm_enrollment(signed.body, key).encode(limits=LIMITS) == signed.encode(
        limits=LIMITS
    )
    assert key.public_key().public_bytes_raw().hex() == vector["public_key_hex"]
    assert signed.signature.hex() == vector["signature_hex"]
    assert verify(key, signed.body, signed) == signed.body


@pytest.fixture
def authorization():
    key = Ed25519PrivateKey.generate()
    body = LlmEnrollment(
        schema_id="hallmark/llm-enrollment/1",
        case_sha256=b"c" * 32,
        verifier=b"v" * 32,
        not_before=100,
        expires_at=200,
    )
    signed = sign_llm_enrollment(body, key)
    return key, body, signed


def verify(key, body, signed, **overrides):
    arguments = (
        dict(
            trusted_key=key.public_key().public_bytes_raw(),
            expected_case=body.case_sha256,
            expected_verifier=body.verifier,
            now=100,
        )
        | overrides
    )
    return verify_llm_enrollment(signed.encode(limits=LIMITS), **arguments)


def test_exact_authorization_verifies_without_embedded_trust(authorization):
    key, body, signed = authorization
    assert verify(key, body, signed) == body
    assert "key" not in signed.model_dump() and "trusted_key" not in signed.model_dump()
    wrong = Ed25519PrivateKey.generate()
    with pytest.raises(HallmarkError, match="SIGNATURE_INVALID"):
        verify(wrong, body, signed)


@pytest.mark.parametrize("field", ["case_sha256", "verifier", "not_before", "expires_at"])
def test_signed_body_tampering_rejects(authorization, field):
    key, body, signed = authorization
    replacement = b"x" * 32 if field in {"case_sha256", "verifier"} else getattr(body, field) + 1
    changed = signed.model_copy(update={"body": body.model_copy(update={field: replacement})})
    with pytest.raises(HallmarkError, match="SIGNATURE_INVALID"):
        verify(key, body, changed)


@pytest.mark.parametrize("field", ["expected_case", "expected_verifier"])
def test_valid_signature_cannot_authorize_other_parameters(authorization, field):
    key, body, signed = authorization
    with pytest.raises(HallmarkError, match="REQUEST_MISMATCH"):
        verify(key, body, signed, **{field: b"x" * 32})


@pytest.mark.parametrize("now,accepted", [(99, False), (100, True), (199, True), (200, False)])
def test_enrollment_validity_boundaries(authorization, now, accepted):
    key, body, signed = authorization
    if accepted:
        assert verify(key, body, signed, now=now) == body
    else:
        with pytest.raises(HallmarkError, match="STALE_EVIDENCE"):
            verify(key, body, signed, now=now)


@pytest.mark.parametrize("now", [True, -1, 2**64, 100.0])
def test_clock_is_a_strict_unsigned_integer(authorization, now):
    key, body, signed = authorization
    with pytest.raises(HallmarkError, match="INPUT_INVALID"):
        verify(key, body, signed, now=now)


def test_signature_domain_and_signature_bytes_are_checked(authorization):
    key, body, signed = authorization
    for signature in [key.sign(body.encode(limits=LIMITS)), bytes(64)]:
        changed = signed.model_copy(update={"signature": signature})
        with pytest.raises(HallmarkError, match="SIGNATURE_INVALID"):
            verify(key, body, changed)


def test_malformed_and_extra_fields_fail_closed(authorization):
    key, body, signed = authorization
    raw = signed.model_dump(mode="python")
    bad = copy.deepcopy(raw)
    bad["body"]["extra"] = True
    for encoded in [encode(bad), b"", b"x" * 16385]:
        with pytest.raises(WireError):
            verify_llm_enrollment(
                encoded,
                trusted_key=key.public_key().public_bytes_raw(),
                expected_case=body.case_sha256,
                expected_verifier=body.verifier,
                now=100,
            )
    with pytest.raises(WireError):
        sign_llm_enrollment(body.model_copy(update={"not_before": True}), key)


@pytest.mark.parametrize("case", ["missing-key", "missing-enrollment", "wrong-key", "expired"])
def test_invalid_authorization_never_starts_a_compiler(tmp_path, monkeypatch, case):
    monkeypatch.setattr(native.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(native.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(native.shutil, "which", lambda _: "cargo")
    monkeypatch.setattr(native.shutil, "disk_usage", lambda _: SimpleNamespace(free=9 * 1024**3))
    monkeypatch.setattr(native, "ROOT", tmp_path)
    inventory = {"case": "c" * 64}
    monkeypatch.setattr(native, "source_inventory", lambda: inventory)
    monkeypatch.setattr(native, "bounded", lambda *a, **k: pytest.fail("compiler was started"))
    previous = tmp_path / "submitted"
    previous.mkdir()
    (previous / "proofs.tar.gz").write_bytes(b"not processed before authorization")
    key = Ed25519PrivateKey.generate()
    body = LlmEnrollment(
        schema_id="hallmark/llm-enrollment/1",
        case_sha256=hashlib.sha256((native.PROBE / "response-case.json").read_bytes()).digest(),
        verifier=native.verifier_identity(inventory),
        not_before=0,
        expires_at=1 if case == "expired" else 2**64 - 1,
    )
    path = tmp_path / "enrollment.cbor"
    path.write_bytes(sign_llm_enrollment(body, key).encode(limits=LIMITS))
    public = key.public_key().public_bytes_raw().hex()
    if case == "wrong-key":
        public = Ed25519PrivateKey.generate().public_key().public_bytes_raw().hex()
    with pytest.raises((ValueError, HallmarkError)):
        native.run(
            previous,
            enrollment=None if case == "missing-enrollment" else path,
            trusted_key=None if case == "missing-key" else public,
        )
    failures = list((tmp_path / "runs").glob("llm-verify-*/failure.json"))
    assert len(failures) == 1
    assert json.loads(failures[0].read_text())["type"] in {"ValueError", "HallmarkError"}
