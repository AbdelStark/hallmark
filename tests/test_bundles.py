"""Container consistency only: synthetic text, signatures, quotes and proof payloads."""

import hashlib
import json
import socket
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from hallmark import bundles
from hallmark.bundles import (
    Bundle,
    BundleStatus,
    Claim,
    EmbeddedFile,
    ResponseEnvelope,
    VerificationResult,
    decode_bundle,
)
from hallmark.enrollment import (
    RegistryBody,
    RegistryEntry,
    RegistrySignature,
    SignedRegistry,
    TrustPolicy,
)
from hallmark.errors import HallmarkError
from hallmark.manifests import FileRef
from hallmark.openings import TranscriptOpening
from hallmark.receipts import EpochRecord, ProofArtifact, ReceiptBody, SignedReceipt
from hallmark.wire import H, WireError, decode, encode

ROOT = Path(__file__).resolve().parents[1]
COMMON = ("adaptive-evasion", "policy-errors", "unobserved-traffic")
PROOF = ("circuit-correctness", "proof-soundness", "registry-trust")


def embedded(path: str = "extra.bin", content: bytes = b"fixture") -> EmbeddedFile:
    return EmbeddedFile(
        ref=FileRef(path=path, size=len(content), sha256=hashlib.sha256(content).digest()),
        content=content,
    )


def claim(role: str, status: str = "accepted", mode: str = "B1") -> Claim:
    residuals = set(COMMON)
    if role == "A":
        residuals.add("hardware-trust")
    elif mode == "B2":
        residuals.add("hardware-input-binding")
    return Claim(
        status=status,
        strength=("hardware-attested" if role == "A" else "cryptographic")
        if status == "accepted"
        else "none",
        assumptions=PROOF if role == "B" and status == "accepted" else (),
        residuals=tuple(sorted(residuals)),
    )


def result(**changes: Any) -> VerificationResult:
    return VerificationResult.model_validate(
        {
            "schema_id": "hallmark/verification-result/1",
            "accepted": True,
            "mode": "B1",
            "claim_a": claim("A"),
            "claim_b": claim("B"),
            "policy_pass": True,
            "codes": (),
            "evidence": (b"e" * 32,),
        }
        | changes
    )


def make_artifacts() -> dict[str, Any]:
    v = json.loads((ROOT / "fixtures/wire/receipts-v1.json").read_text())
    r = json.loads((ROOT / "fixtures/wire/enrollment-v1.json").read_text())
    signed = SignedReceipt.decode(bytes.fromhex(v["signed_receipt"]["cbor_hex"]))
    epoch = EpochRecord.decode(bytes.fromhex(v["epoch"]["cbor_hex"]))
    opening = TranscriptOpening(
        schema_id="hallmark/transcript-opening/1",
        system_ref=b"s" * 32,
        prompt="Harmless bundle fixture prompt.",
        response="Harmless bundle fixture response.",
        salt=b"t" * 32,
    )
    inputs = tuple(
        value.model_copy(update={"context": opening.context(signed.body.expected)})
        for value in signed.body.inputs
    )
    body = ReceiptBody.model_validate(
        signed.body.model_dump() | {"transcript": opening.commitment(), "inputs": inputs}
    )
    signed = SignedReceipt.model_validate(signed.model_dump() | {"body": body})
    proofs = tuple(
        ProofArtifact.model_validate(
            ProofArtifact.decode(bytes.fromhex(item["cbor_hex"])).model_dump()
            | {"public_inputs": inputs[index]}
        )
        for index, item in enumerate(v["proofs"])
    )
    identities = {
        ("model", body.expected.model),
        ("policy", body.expected.policy),
        ("epoch-measurement", epoch.measurement),
        *(("classifier", item.classifier) for item in inputs),
        *(("backend", proof.backend) for proof in proofs),
    }
    registry = RegistryBody(
        schema_id="hallmark/registry/1",
        sequence=0,
        previous=None,
        issued_at=v["now"] - 100,
        expires_at=v["now"] + 100,
        entries=tuple(
            RegistryEntry(
                kind=kind,
                digest=digest,
                valid_from=0,
                valid_until=v["now"] + 200,
                retired_at=None,
                review=b"r" * 32,
            )
            for kind, digest in sorted(identities)
        ),
    )
    # Public fixture seed, matching W08. No operational key is generated.
    key = Ed25519PrivateKey.from_private_bytes(b"\x01" * 32)
    registry = SignedRegistry(
        schema_id="hallmark/signed-registry/1",
        body=registry,
        signatures=(
            RegistrySignature(
                key_id=H("key", key.public_key().public_bytes_raw()),
                signature=key.sign(registry.signing_bytes()),
            ),
        ),
    )
    trust = TrustPolicy.decode(bytes.fromhex(r["trust"]["cbor_hex"]))
    trust = TrustPolicy.model_validate(
        trust.model_dump()
        | {
            "accepted_models": (body.expected.model,),
            "accepted_policies": (body.expected.policy,),
            "accepted_backends": tuple(sorted({proof.backend for proof in proofs})),
        }
    )
    bundle = Bundle(
        schema_id="hallmark/bundle/1",
        receipt=signed,
        epoch=epoch,
        registry=registry,
        history=(),
        proofs=proofs,
        files=(EmbeddedFile(ref=epoch.collateral[0], content=v["collateral_utf8"].encode()),),
    )
    blocked_inputs = (inputs[0], inputs[1].model_copy(update={"verdict": False}), inputs[2])
    blocked = ReceiptBody.model_validate(
        body.model_dump() | {"release": "blocked", "inputs": blocked_inputs}
    )
    return {
        "bundle": bundle,
        "opening": opening,
        "trust": trust,
        "blocked_receipt": signed.model_copy(update={"body": blocked}),
        "now": v["now"],
    }


@pytest.fixture(scope="module")
def artifacts() -> dict[str, Any]:
    return make_artifacts()


def test_bundle_round_trip_and_declared_scope(artifacts: Any) -> None:
    bundle, trust = artifacts["bundle"], artifacts["trust"]
    assert decode_bundle(bundle.encode(), limits=trust.limits) == bundle
    assert Bundle.model_validate_json(bundle.model_dump_json()) == bundle
    bundle.registry.verify_signatures(trust)
    assert all(not hasattr(bundle, name) for name in ("verify", "accepted", "verified", "opening"))
    assert all(not hasattr(proof, "verify") for proof in bundle.proofs)


@pytest.mark.parametrize(
    "path",
    [
        "../private.txt",
        "/private.txt",
        "./file",
        "a//b",
        "a/../b",
        "a/./b",
        "a/",
        "a\\b",
        "https://example.test/file",
        "file:///private",
        "a\0b",
        "",
        "a\nb",
        "C:/file",
    ],
)
def test_logical_paths_reject_traversal_and_locators(path: str) -> None:
    with pytest.raises(ValidationError):
        embedded(path)


@pytest.mark.parametrize(
    "change",
    [
        {"size": 0},
        {"size": 8},
        {"size": True},
        {"sha256": b"x" * 32},
    ],
)
def test_embedded_file_exact_size_and_digest(change: Any) -> None:
    item = embedded()
    with pytest.raises(ValidationError):
        EmbeddedFile.model_validate(
            {"ref": item.ref.model_dump() | change, "content": item.content}
        )


def test_empty_file_and_logical_aliases_are_explicit(artifacts: Any) -> None:
    assert embedded(content=b"").ref.size == 0
    bundle = artifacts["bundle"]
    files = (embedded("a.bin"), embedded("b.bin"), *bundle.files)
    alias = Bundle.model_validate(bundle.model_dump() | {"files": files})
    assert alias.files[0].ref.sha256 == alias.files[1].ref.sha256
    assert alias.files[0].ref.path != alias.files[1].ref.path


@pytest.mark.parametrize("kind", ["duplicate", "unsorted", "missing", "different-reference"])
def test_unique_files_and_exact_collateral_resolution(artifacts: Any, kind: str) -> None:
    bundle = artifacts["bundle"]
    files = {
        "duplicate": (*bundle.files, *bundle.files),
        "unsorted": (*bundle.files, embedded("a.bin")),
        "missing": (embedded(),),
        "different-reference": (embedded(bundle.files[0].ref.path, b"different"),),
    }[kind]
    with pytest.raises(ValidationError):
        Bundle.model_validate(bundle.model_dump() | {"files": files})


@pytest.mark.parametrize("which", ["missing", "extra", "duplicate", "reordered", "other-context"])
def test_exact_ordered_three_proof_declarations(artifacts: Any, which: str) -> None:
    bundle = artifacts["bundle"]
    p = bundle.proofs
    proofs = {
        "missing": p[:2],
        "extra": (*p, p[0]),
        "duplicate": (p[0], p[0], p[2]),
        "reordered": p[::-1],
        "other-context": (
            p[0].model_copy(
                update={
                    "public_inputs": p[0].public_inputs.model_copy(update={"context": b"x" * 32})
                }
            ),
            *p[1:],
        ),
    }[which]
    with pytest.raises(ValidationError):
        Bundle.model_validate(bundle.model_dump() | {"proofs": proofs})


@pytest.mark.parametrize("field", ["epoch_id", "key", "model"])
def test_epoch_and_receipt_link_mismatch(artifacts: Any, field: str) -> None:
    bundle = artifacts["bundle"]
    epoch = bundle.epoch.model_copy(update={field: b"x" * 32})
    with pytest.raises(ValidationError):
        Bundle.model_validate(bundle.model_dump() | {"epoch": epoch})


@pytest.mark.parametrize("field", ["opening", "prompt", "response", "salt", "trust", "expected"])
def test_private_opening_and_trust_are_not_bundle_fields(artifacts: Any, field: str) -> None:
    raw = decode(artifacts["bundle"].encode())
    raw[field] = "PRIVATE_SENTINEL"
    limits = artifacts["trust"].limits
    # The same bundle format excludes openings in both externally selected modes.
    with pytest.raises(WireError, match="INPUT_INVALID") as exc:
        decode_bundle(encode(raw), limits=limits)
    assert "PRIVATE_SENTINEL" not in str(exc.value) and exc.value.__context__ is None


@pytest.mark.parametrize("kind", ["opening", "response"])
def test_private_wire_records_cannot_be_smuggled_as_embedded_files(
    artifacts: Any, kind: str
) -> None:
    bundle = artifacts["bundle"]
    private = artifacts["opening"]
    if kind == "response":
        private = ResponseEnvelope(
            schema_id="hallmark/response-envelope/1",
            receipt=bundle.receipt,
            response=private.response,
            opening=private,
            proof_status="pending",
        )
    files = (*bundle.files, embedded("private.cbor", private.encode()))
    with pytest.raises(ValidationError, match="separate exchange"):
        Bundle.model_validate(bundle.model_dump() | {"files": files})


def test_opaque_collateral_is_not_an_unbounded_artifact_decoder(artifacts: Any) -> None:
    bundle = artifacts["bundle"]
    for raw in (
        b"\xff",
        encode(b"\x00"),
        encode({"schema_id": "external/collateral/1"}),
        encode({"schema_id": []}),
        encode({"schema_id": {}}),
    ):
        files = (*bundle.files, embedded("opaque.bin", raw))
        assert Bundle.model_validate(bundle.model_dump() | {"files": files}).encode()


def test_caller_byte_depth_and_each_proof_budget(artifacts: Any) -> None:
    bundle, limits = artifacts["bundle"], artifacts["trust"].limits
    raw = bundle.encode()
    exact = limits.model_copy(update={"bundle_bytes": len(raw)})
    assert decode_bundle(raw, limits=exact) == bundle
    for lower in (
        limits.model_copy(update={"bundle_bytes": len(raw) - 1}),
        limits.model_copy(update={"nesting": 1}),
    ):
        with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
            decode_bundle(raw, limits=lower)
    small = limits.model_copy(update={"proof_bytes": 1})
    for index in range(3):
        proofs = tuple(
            item.model_copy(update={"proof": b"xx" if i == index else b"x"})
            for i, item in enumerate(bundle.proofs)
        )
        changed = Bundle.model_validate(bundle.model_dump() | {"proofs": proofs})
        with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
            decode_bundle(changed.encode(), limits=small)
    with pytest.raises(WireError, match="INPUT_INVALID"):
        decode_bundle(raw, limits=None)


def test_binary_size_is_checked_before_model_validation(artifacts: Any, monkeypatch: Any) -> None:
    bundle, limits = artifacts["bundle"], artifacts["trust"].limits
    raw = bundle.encode()

    def unexpected(*args: Any, **kwargs: Any) -> None:
        pytest.fail("schema validation ran on over-budget binary input")

    monkeypatch.setattr(Bundle, "model_validate", unexpected)
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        decode_bundle(raw, limits=limits.model_copy(update={"bundle_bytes": 1}))


def test_total_hard_cap_includes_container_overhead(artifacts: Any) -> None:
    bundle = artifacts["bundle"]
    too_large = embedded("large.bin", b"x" * bundles.MAX_BUNDLE_BYTES)
    with pytest.raises(ValidationError, match="LIMIT_EXCEEDED"):
        Bundle.model_validate(bundle.model_dump() | {"files": (*bundle.files, too_large)})
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        Bundle.decode(b"x" * (bundles.MAX_BUNDLE_BYTES + 1))


@pytest.mark.parametrize("field,count", [("history", 1025), ("files", 8193), ("files", 0)])
def test_container_count_caps(artifacts: Any, field: str, count: int) -> None:
    bundle = artifacts["bundle"]
    values = (bundle.registry if field == "history" else bundle.files[0],) * count
    with pytest.raises(ValidationError):
        Bundle.model_validate(bundle.model_dump() | {field: values})


def test_response_opening_binding_and_repr(artifacts: Any) -> None:
    for status in ("pending", "ready"):
        response = ResponseEnvelope(
            schema_id="hallmark/response-envelope/1",
            receipt=artifacts["bundle"].receipt,
            response=artifacts["opening"].response,
            opening=artifacts["opening"],
            proof_status=status,
        )
        assert ResponseEnvelope.decode(response.encode()) == response
        assert "Harmless" not in repr(response)
        assert "tttt" not in repr(response)
        assert response.model_copy(update={"opening": None}).encode()
        for change in (
            {"response": None},
            {"response": "different"},
            {"opening": artifacts["opening"].model_copy(update={"salt": b"x" * 32})},
        ):
            with pytest.raises(ValidationError):
                ResponseEnvelope.model_validate(response.model_dump() | change)


@pytest.mark.parametrize("status", ["blocked", "failed", "expired"])
@pytest.mark.parametrize("field", ["response", "opening"])
def test_terminal_responses_never_carry_private_payloads(
    artifacts: Any, status: str, field: str
) -> None:
    receipt = artifacts["blocked_receipt"] if status == "blocked" else artifacts["bundle"].receipt
    values = dict(
        schema_id="hallmark/response-envelope/1",
        receipt=receipt,
        response=None,
        opening=None,
        proof_status=status,
    )
    assert ResponseEnvelope(**values).encode()
    values[field] = artifacts["opening"] if field == "opening" else "PRIVATE_SENTINEL"
    with pytest.raises(ValidationError):
        ResponseEnvelope(**values)


def test_response_status_and_utf8_bounds(artifacts: Any) -> None:
    values = dict(
        schema_id="hallmark/response-envelope/1",
        receipt=artifacts["bundle"].receipt,
        response="é" * 16384,
        opening=None,
        proof_status="pending",
    )
    assert ResponseEnvelope(**values).response.encode() == b"\xc3\xa9" * 16384
    for change in (
        {"response": "é" * 16385},
        {"response": "\ud800"},
        {"proof_status": "blocked"},
        {"receipt": artifacts["blocked_receipt"]},
        {"proof_status": "sampled-out"},
    ):
        with pytest.raises(ValidationError):
            ResponseEnvelope.model_validate(values | change)


@pytest.mark.parametrize(
    "state,error",
    [
        ("pending", None),
        ("ready", None),
        ("blocked", "POLICY_BLOCKED"),
        ("failed", "PROOF_INVALID"),
        ("expired", "STALE_EVIDENCE"),
    ],
)
def test_collection_statuses_are_distinct(state: str, error: str | None) -> None:
    status = BundleStatus(
        schema_id="hallmark/bundle-status/1",
        receipt_id=b"r" * 32,
        state=state,
        bundle=embedded().ref if state == "ready" else None,
        error=error,
    )
    assert BundleStatus.decode(status.encode()) == status
    assert not hasattr(status, "accepted")
    changed = status.model_dump() | {"bundle": None if state == "ready" else embedded().ref}
    with pytest.raises(ValidationError):
        BundleStatus.model_validate(changed)


@pytest.mark.parametrize(
    "state,error",
    [
        ("pending", "PROOF_PENDING"),
        ("ready", "PROOF_INVALID"),
        ("blocked", None),
        ("expired", None),
        ("failed", None),
        ("failed", "PROOF_PENDING"),
        ("failed", "POLICY_BLOCKED"),
        ("failed", "PRIVATE_SENTINEL"),
    ],
)
def test_inconsistent_collection_errors(state: str, error: str | None) -> None:
    with pytest.raises(ValidationError):
        BundleStatus(
            schema_id="hallmark/bundle-status/1",
            receipt_id=b"r" * 32,
            state=state,
            bundle=embedded().ref if state == "ready" else None,
            error=error,
        )


def test_complete_reported_result_modes_and_external_requirements(artifacts: Any) -> None:
    trust = artifacts["trust"]
    ab = result()
    b = result(claim_a=claim("A", "not-accepted"))
    b.validate_requirements(trust)
    ab.validate_requirements(trust)
    required = TrustPolicy.model_validate(
        trust.model_dump()
        | {"required_claims": "A+B", "hardware_roots": (b"h" * 32,), "measurements": (b"m" * 32,)}
    )
    ab.validate_requirements(required)
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        b.validate_requirements(required)
    b2 = result(mode="B2", claim_b=claim("B", mode="B2"))
    b2.validate_requirements(required.model_copy(update={"binding": "B2"}))
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        b2.validate_requirements(trust)
    for value in (ab, b, b2):
        assert VerificationResult.decode(value.encode()) == value
        assert not hasattr(value, "verify") and not hasattr(value, "safe")


def test_rejected_not_accepted_pending_and_policy_blocked_reports() -> None:
    rejected = result(
        accepted=False,
        claim_b=claim("B", "rejected"),
        policy_pass=None,
        codes=("PROOF_INVALID",),
    )
    pending = result(
        accepted=False,
        claim_a=claim("A", "not-accepted"),
        claim_b=claim("B", "not-accepted"),
        policy_pass=None,
        codes=("PROOF_PENDING",),
        evidence=(),
    )
    blocked = result(accepted=False, policy_pass=False, codes=("POLICY_BLOCKED",))
    assert rejected.claim_b.status == "rejected"
    assert pending.claim_b.status == "not-accepted"
    assert blocked.claim_b.status == "accepted" and blocked.policy_pass is False
    assert all(not item.accepted for item in (rejected, pending, blocked))
    for item in (rejected, pending, blocked):
        assert VerificationResult.decode(item.encode()) == item
    for code in ("PROOF_INVALID", "ATTESTATION_INVALID"):
        with pytest.raises(ValidationError):
            result(accepted=False, codes=(code,))


@pytest.mark.parametrize(
    "change",
    [
        {"accepted": 1},
        {"accepted": False},
        {"mode": "B3"},
        {"policy_pass": 1},
        {"claim_a": claim("A", "rejected")},
        {"claim_b": claim("B", "not-accepted")},
        {"policy_pass": False},
        {"policy_pass": None},
        {"codes": ("PROOF_PENDING",)},
        {"codes": ("UNKNOWN",)},
        {"evidence": ()},
        {"safe": True},
        {"claim_a": claim("B")},
        {"claim_b": claim("A")},
        {"mode": "B2"},
        {"claim_b": claim("B", mode="B2")},
        {"evidence": (b"e" * 32, b"e" * 32)},
    ],
)
def test_contradictory_result_rejected(change: Any) -> None:
    with pytest.raises(ValidationError):
        result(**change)


def test_claim_strength_assumptions_and_residual_obligations() -> None:
    for change in (
        {"strength": "none"},
        {"status": "rejected"},
        {"status": "not-accepted"},
        {"residuals": ("policy-errors",)},
        {"residuals": COMMON[::-1]},
        {"assumptions": ("proof-soundness", "proof-soundness")},
    ):
        with pytest.raises(ValidationError):
            Claim.model_validate(claim("B").model_dump() | change)
    missing = claim("B").model_copy(update={"assumptions": ()})
    with pytest.raises(ValidationError):
        result(claim_b=missing)
    with pytest.raises(ValidationError):
        result(mode="B2", claim_b=claim("B", mode="B2"), claim_a=claim("A", "not-accepted"))
    with pytest.raises(ValidationError):
        result(claim_a=claim("A").model_copy(update={"residuals": COMMON}))
    with pytest.raises(ValidationError):
        result(
            claim_b=claim("B").model_copy(
                update={"assumptions": tuple(sorted((*PROOF, "hardware-trust")))}
            )
        )


def test_no_verifier_called_by_bundle_or_result_parsing(artifacts: Any, monkeypatch: Any) -> None:
    raw = artifacts["bundle"].encode()

    def unexpected(*args: Any, **kwargs: Any) -> None:
        pytest.fail("parsing must not authenticate evidence or fetch dependencies")

    monkeypatch.setattr(SignedRegistry, "verify_signatures", unexpected)
    monkeypatch.setattr("builtins.open", unexpected)
    monkeypatch.setattr(socket, "socket", unexpected)
    assert decode_bundle(raw, limits=artifacts["trust"].limits).encode() == raw
    assert VerificationResult.decode(result().encode()).accepted


def test_copy_bypass_missing_extra_fields_and_payload_privacy(artifacts: Any) -> None:
    bundle = artifacts["bundle"]
    invalid = bundle.model_copy(update={"proofs": bundle.proofs[:2]})
    with pytest.raises(WireError, match="INPUT_INVALID"):
        invalid.encode()
    for field in ("registry", "history", "files", "proofs", "receipt", "epoch"):
        value = decode(bundle.encode())
        del value[field]
        with pytest.raises(WireError):
            Bundle.decode(encode(value))
    item = embedded(content=b"PRIVATE_SENTINEL")
    assert "PRIVATE_SENTINEL" not in repr(item)
    with pytest.raises(ValidationError):
        item.content = b"changed"
    forged = result().model_copy(update={"claim_b": claim("B", "not-accepted")})
    with pytest.raises(WireError):
        forged.validate_requirements(artifacts["trust"])


def test_golden_containers_and_schema_snapshots() -> None:
    vector = json.loads((ROOT / "fixtures/wire/bundles-v1.json").read_text())
    models = {
        "bundle": Bundle,
        "response-envelope": ResponseEnvelope,
        "bundle-status": BundleStatus,
        "verification-result": VerificationResult,
    }
    for name, cls in models.items():
        assert cls.model_json_schema() == json.loads(
            (ROOT / f"docs/schemas/{name}-v1.json").read_text()
        )
    for row in vector["records"]:
        cls = models[row["kind"]]
        obj = cls.decode(bytes.fromhex(row["cbor_hex"]))
        assert obj.encode().hex() == row["cbor_hex"]
        assert json.loads(obj.model_dump_json()) == row["json"]
