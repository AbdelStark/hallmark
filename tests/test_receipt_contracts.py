"""Structural and declared-binding checks only; all evidence bytes here are synthetic."""

import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

import cbor2
import pytest
from pydantic import ValidationError

from hallmark.classifier_manifest import ClassifierManifest, InputProfile
from hallmark.errors import HallmarkError
from hallmark.policy import Policy, RequestExpectation
from hallmark.receipts import (
    MAX_EVIDENCE_BYTES,
    MAX_PROOF_BYTES,
    EpochRecord,
    ProofArtifact,
    ProofInputs,
    ReceiptBody,
    SignedReceipt,
)
from hallmark.wire import H, WireError, decode, encode

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def vector() -> dict[str, Any]:
    return json.loads((ROOT / "fixtures/wire/receipts-v1.json").read_text())


@pytest.fixture
def artifacts(vector: Any) -> dict[str, Any]:
    def read(model: Any, record: Any) -> Any:
        return model.decode(bytes.fromhex(record["cbor_hex"]))

    profiles = {name: read(InputProfile, item) for name, item in vector["profiles"].items()}
    return {
        "body": read(ReceiptBody, vector["receipt"]),
        "signed": read(SignedReceipt, vector["signed_receipt"]),
        "epoch": read(EpochRecord, vector["epoch"]),
        "policy": read(Policy, vector["policy"]),
        "expected": read(RequestExpectation, vector["expected"]),
        "classifiers": tuple(
            read(ClassifierManifest, item) for item in vector["classifiers"].values()
        ),
        "profiles": (profiles["bytes"], profiles["bytes"], profiles["tokens"]),
        "proofs": tuple(read(ProofArtifact, item) for item in vector["proofs"]),
    }


def oracle(domain: str, value: Any) -> bytes:
    tag = ("hallmark/v1/" + domain).encode("ascii")
    return hashlib.sha256(
        len(tag).to_bytes(4, "big") + tag + cbor2.dumps(value, canonical=True)
    ).digest()


def changed_expectation(body: ReceiptBody, expected: RequestExpectation) -> ReceiptBody:
    context = H("context", [decode(expected.encode()), body.transcript])
    inputs = tuple(item.model_copy(update={"context": context}) for item in body.inputs)
    return ReceiptBody.model_validate(body.model_dump() | {"expected": expected, "inputs": inputs})


def test_golden_records_snapshots_and_declared_bindings(vector: Any, artifacts: Any) -> None:
    a = artifacts
    for obj, name in (
        (a["body"], "receipt"),
        (a["signed"], "signed-receipt"),
        (a["epoch"], "epoch"),
        (a["proofs"][0], "proof-artifact"),
        (a["body"].inputs[0], "proof-inputs"),
    ):
        assert type(obj).model_json_schema() == json.loads(
            (ROOT / f"docs/schemas/{name}-v1.json").read_text()
        )
        assert type(obj).decode(obj.encode()) == obj
        assert type(obj).model_validate_json(obj.model_dump_json()) == obj
        assert not hasattr(obj, "verify") and not hasattr(obj, "accepted")
    for name, obj in (
        ("receipt", a["body"]),
        ("signed_receipt", a["signed"]),
        ("epoch", a["epoch"]),
    ):
        assert obj.encode().hex() == vector[name]["cbor_hex"]
        assert json.loads(obj.model_dump_json()) == vector[name]["json"]
    assert a["body"].identity() == oracle("receipt", decode(a["body"].encode()))
    assert a["body"].identity().hex() == vector["receipt"]["identity_hex"]
    assert a["epoch"].identity() == oracle("epoch", decode(a["epoch"].encode()))
    assert a["epoch"].identity().hex() == vector["epoch"]["identity_hex"]
    assert a["epoch"].key_id() == oracle("key", a["epoch"].key)
    assert a["epoch"].key_id().hex() == vector["epoch"]["key_id_hex"]
    assert a["epoch"].challenge() != a["epoch"].identity()
    preimage = decode(bytes.fromhex(vector["epoch"]["challenge_preimage_cbor_hex"]))
    assert preimage == [
        a["epoch"].epoch_id,
        a["epoch"].key,
        a["epoch"].model,
        a["epoch"].measurement,
        a["epoch"].issued_at,
        a["epoch"].expires_at,
    ]
    assert a["epoch"].challenge() == oracle("epoch", preimage)
    assert a["epoch"].challenge().hex() == vector["epoch"]["challenge_hex"]
    tag = b"hallmark/v1/sign/receipt"
    assert a["body"].signing_bytes() == len(tag).to_bytes(4, "big") + tag + a["body"].encode()
    assert a["body"].signing_bytes().hex() == vector["receipt"]["signing_bytes_hex"]
    a["body"].validate_expectation(a["expected"], now=vector["now"])
    a["body"].validate_policy(a["policy"], a["classifiers"], a["profiles"])
    a["signed"].validate_epoch(a["epoch"], now=vector["now"])
    for index, artifact in enumerate(a["proofs"]):
        artifact.validate_inputs(
            a["body"].inputs[index],
            a["classifiers"][index],
            a["profiles"][index],
            max_proof_bytes=1024,
        )
    blocked = ReceiptBody.decode(bytes.fromhex(vector["blocked_receipt"]["cbor_hex"]))
    blocked.validate_policy(a["policy"], a["classifiers"], a["profiles"])
    assert blocked.release == "blocked"
    assert not blocked.inputs[1].verdict


def test_packing_golden_layout_and_signed_extrema(vector: Any) -> None:
    layout = json.loads((ROOT / "docs/schemas/proof-input-layout-v1.json").read_text())
    assert layout["field_count"] == 100
    assert [(s["name"], s["offset"], s["count"]) for s in layout["segments"]] == [
        ("context", 0, 32),
        ("classifier", 32, 32),
        ("input_digest", 64, 32),
        ("unit_count", 96, 1),
        ("chunk_count", 97, 1),
        ("threshold", 98, 1),
        ("verdict", 99, 1),
    ]
    assert layout["field_modulus_must_exceed"] == 2**32 - 1
    for item, threshold, offset in zip(
        vector["packing_only"],
        (-(2**31), -1, 0, 2**31 - 1),
        (0, 2**31 - 1, 2**31, 2**32 - 1),
        strict=True,
    ):
        inputs = ProofInputs.decode(bytes.fromhex(item["cbor_hex"]))
        fields = tuple(item["fields"])
        assert inputs.threshold == threshold
        assert fields == (*range(96), 32768, 32768, offset, int(threshold >= 0))
        assert inputs.to_fields() == fields
        assert ProofInputs.from_fields(fields) == inputs


def test_every_public_field_position_survives_packing(artifacts: Any) -> None:
    original = artifacts["body"].inputs[0]
    fields = original.to_fields()
    for index in range(100):
        changed = list(fields)
        changed[index] = (changed[index] ^ 1) if index < 96 or index == 99 else changed[index] + 1
        decoded = ProofInputs.from_fields(tuple(changed))
        assert decoded != original, index
        assert decoded.to_fields() == tuple(changed), index
        assert decoded.encode() != original.encode(), index


@pytest.mark.parametrize(
    "index,bad",
    [
        (0, -1),
        (31, 256),
        (32, 2**64),
        (64, True),
        (95, 1.0),
        (96, -1),
        (96, 32769),
        (97, 0),
        (97, 32769),
        (98, -1),
        (98, 2**32),
        (99, 2),
        (99, -1),
    ],
)
def test_packed_aliases_fail(artifacts: Any, index: int, bad: Any) -> None:
    fields = list(artifacts["body"].inputs[0].to_fields())
    fields[index] = bad
    with pytest.raises(WireError):
        ProofInputs.from_fields(tuple(fields))


def test_field_shape_is_fixed_and_does_not_consume_iterators(artifacts: Any) -> None:
    fields = artifacts["body"].inputs[0].to_fields()
    for bad in (None, list(fields), fields[:-1], fields + (0,), iter(fields)):
        with pytest.raises(WireError):
            ProofInputs.from_fields(bad)


@pytest.mark.parametrize(
    "changes",
    [
        {"unit_count": -1},
        {"unit_count": 32769},
        {"unit_count": True},
        {"chunk_count": 0},
        {"chunk_count": 3},
        {"chunk_count": 1.0},
        {"unit_count": 0, "chunk_count": 2},
        {"threshold": -(2**31) - 1},
        {"threshold": 2**31},
        {"threshold": False},
        {"verdict": 1},
        {"context": b"x"},
        {"classifier": "00" * 32},
        {"input_digest": False},
    ],
)
def test_public_input_constraints(artifacts: Any, changes: Any) -> None:
    inputs = artifacts["body"].inputs[0]
    with pytest.raises(WireError):
        ProofInputs.decode(encode(decode(inputs.encode()) | changes))
    with pytest.raises(WireError):
        inputs.model_copy(update=changes).to_fields()


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("count", [0, 1, 2, 3, 16, 17, 32768])
def test_exact_profile_count_relation(artifacts: Any, index: int, count: int) -> None:
    a = artifacts
    classifier, profile = a["classifiers"][index], a["profiles"][index]
    capacity = profile.chunk_size - len(profile.prefix_tokens) - len(profile.suffix_tokens)
    chunks = max(1, (count + capacity - 1) // capacity)
    inputs = a["body"].inputs[index].model_copy(update={"unit_count": count, "chunk_count": chunks})
    inputs.validate_profile(classifier, profile)
    if count > 1:
        wrong = inputs.model_copy(update={"chunk_count": chunks - 1 if chunks > 1 else 2})
        with pytest.raises(HallmarkError, match="INPUT_BINDING_FAILED"):
            wrong.validate_profile(classifier, profile)


def test_resolved_profile_and_threshold_must_match(artifacts: Any) -> None:
    a = artifacts
    inputs, classifier, profile = a["body"].inputs[1], a["classifiers"][1], a["profiles"][1]
    for wrong in (
        inputs.model_copy(update={"classifier": b"x" * 32}),
        inputs.model_copy(update={"threshold": inputs.threshold + 1}),
    ):
        with pytest.raises(HallmarkError, match="INPUT_BINDING_FAILED"):
            wrong.validate_profile(classifier, profile)
    lower = profile.model_copy(update={"max_units": 1})
    changed = classifier.model_copy(update={"input_profile": lower.identity()})
    matched = inputs.model_copy(update={"classifier": changed.identity()})
    with pytest.raises(HallmarkError, match="INPUT_BINDING_FAILED"):
        matched.validate_profile(changed, lower)
    for wrong_classifier, wrong_profile in (
        (None, profile),
        (classifier, None),
        (classifier, a["profiles"][2]),
    ):
        with pytest.raises(HallmarkError):
            inputs.validate_profile(wrong_classifier, wrong_profile)


@pytest.mark.parametrize(
    "order", [order for order in itertools.permutations(range(3)) if order != (0, 1, 2)]
)
def test_reordered_policy_inputs_fail(artifacts: Any, order: Any) -> None:
    a = artifacts
    body = a["body"].model_copy(update={"inputs": tuple(a["body"].inputs[i] for i in order)})
    with pytest.raises(HallmarkError, match="INPUT_BINDING_FAILED"):
        body.validate_policy(a["policy"], a["classifiers"], a["profiles"])
    with pytest.raises(WireError):
        body.validate_policy(a["policy"], tuple(a["classifiers"][i] for i in order), a["profiles"])


def test_missing_duplicate_and_extra_receipt_inputs(artifacts: Any) -> None:
    body = artifacts["body"]
    for inputs in (body.inputs[:2], body.inputs + (body.inputs[0],), (body.inputs[0],) * 3):
        with pytest.raises(WireError):
            body.model_copy(update={"inputs": inputs}).encode()


@pytest.mark.parametrize(
    "changes",
    [
        {"issued_at": 500},
        {"expires_at": 110},
        {"expires_at": 109},
        {"issued_at": True},
        {"expires_at": 2**64},
        {"sequence": 1},
        {"sequence": -1},
        {"sequence": 2**64},
        {"sequence": False},
        {"previous": b"x" * 32},
        {"release": "pending"},
        {"release": "blocked"},
        {"transcript": b"x" * 32},
    ],
)
def test_receipt_shape_rejections(artifacts: Any, changes: Any) -> None:
    with pytest.raises(WireError):
        artifacts["body"].model_copy(update=changes).encode()


def test_false_native_release_and_wrong_context_fail(artifacts: Any) -> None:
    body = artifacts["body"]
    for changes in ({"verdict": False}, {"context": b"x" * 32}):
        inputs = (body.inputs[0].model_copy(update=changes), *body.inputs[1:])
        with pytest.raises(WireError):
            body.model_copy(update={"inputs": inputs}).identity()


@pytest.mark.parametrize(
    "field", ["audience", "nonce", "interaction_id", "model", "policy", "continuity"]
)
def test_external_expectation_is_required_and_all_fields_compared(
    artifacts: Any, field: str
) -> None:
    a = artifacts
    value = (
        "other/audience"
        if field == "audience"
        else {"sequence": 0, "previous": None}
        if field == "continuity"
        else b"x" * 32
    )
    expected = RequestExpectation.model_validate(a["expected"].model_dump() | {field: value})
    with pytest.raises(HallmarkError, match="REQUEST_MISMATCH"):
        a["body"].validate_expectation(expected, now=120)
    body = changed_expectation(a["body"], expected)
    assert body.identity() != a["body"].identity()
    with pytest.raises(HallmarkError, match="REQUEST_MISMATCH"):
        body.validate_expectation(a["expected"], now=120)


def test_continuity_comparison_is_exact(artifacts: Any) -> None:
    a = artifacts
    expected = RequestExpectation.model_validate(
        a["expected"].model_dump()
        | {
            "continuity": {"sequence": 7, "previous": b"x" * 32},
        }
    )
    raw = a["body"].model_dump() | {"expected": expected, "sequence": 7, "previous": b"x" * 32}
    context = H("context", [decode(expected.encode()), a["body"].transcript])
    raw["inputs"] = tuple(item.model_copy(update={"context": context}) for item in a["body"].inputs)
    body = ReceiptBody.model_validate(raw)
    body.validate_expectation(expected, now=120)
    for changed in ({"sequence": 8}, {"previous": b"y" * 32}):
        with pytest.raises(WireError):
            body.model_copy(update=changed).identity()
    # Null continuity permits a structurally valid later receipt without a history claim.
    loose = a["body"].model_copy(update={"sequence": 2**64 - 1, "previous": b"z" * 32})
    assert ReceiptBody.decode(loose.encode()) == loose


@pytest.mark.parametrize(
    "now,valid", [(99, False), (100, True), (109, True), (3699, True), (3700, False)]
)
def test_epoch_clock_boundaries(artifacts: Any, now: int, valid: bool) -> None:
    if valid:
        artifacts["epoch"].validate_time(now)
    else:
        with pytest.raises(HallmarkError, match="STALE_EVIDENCE"):
            artifacts["epoch"].validate_time(now)


@pytest.mark.parametrize("now,valid", [(109, False), (110, True), (499, True), (500, False)])
def test_receipt_clock_boundaries(artifacts: Any, now: int, valid: bool) -> None:
    a = artifacts
    if valid:
        a["body"].validate_expectation(a["expected"], now=now)
    else:
        with pytest.raises(HallmarkError, match="STALE_EVIDENCE"):
            a["body"].validate_expectation(a["expected"], now=now)


@pytest.mark.parametrize("now", [-1, 2**64, True, 120.0, "120", None])
def test_clock_must_be_explicit_u64(artifacts: Any, now: Any) -> None:
    with pytest.raises(WireError):
        artifacts["epoch"].validate_time(now)
    with pytest.raises(WireError):
        artifacts["body"].validate_expectation(artifacts["expected"], now=now)


@pytest.mark.parametrize(
    "changes",
    [
        {"expires_at": 100},
        {"expires_at": 99},
        {"expires_at": 3701},
        {"issued_at": False},
        {"issued_at": -1},
        {"expires_at": 2**64},
        {"key": b"x" * 31},
        {"key": b"x" * 33},
        {"key": "00" * 32},
        {"epoch_id": b"x"},
        {"measurement": False},
        {"model": b"x"},
        {"cpu_evidence": b""},
        {"accelerator_evidence": b""},
        {"cpu_evidence": "private"},
        {"collateral": []},
    ],
)
def test_epoch_constraints(artifacts: Any, changes: Any) -> None:
    with pytest.raises(WireError):
        artifacts["epoch"].model_copy(update=changes).identity()


def test_collateral_paths_counts_and_epoch_extrema(artifacts: Any) -> None:
    epoch = artifacts["epoch"]
    ref = epoch.collateral[0]
    for refs in ((ref, ref), (ref,) * 257, (ref.model_copy(update={"path": "z"}), ref)):
        with pytest.raises(WireError):
            epoch.model_copy(update={"collateral": refs}).encode()
    edge = epoch.model_copy(update={"issued_at": 2**64 - 3601, "expires_at": 2**64 - 1})
    edge.validate_time(2**64 - 2)
    assert EpochRecord.decode(edge.encode()) == edge


@pytest.mark.parametrize(
    "field", ["epoch_id", "key", "model", "measurement", "issued_at", "expires_at"]
)
def test_epoch_challenge_binds_every_field(artifacts: Any, field: str) -> None:
    epoch = artifacts["epoch"]
    value = 101 if field == "issued_at" else 3699 if field == "expires_at" else b"x" * 32
    changed = epoch.model_copy(update={field: value})
    assert changed.challenge() != epoch.challenge()
    assert changed.identity() != epoch.identity()


def test_quotes_and_collateral_change_identity_not_challenge(artifacts: Any) -> None:
    epoch = artifacts["epoch"]
    for changes in (
        {"cpu_evidence": b"changed"},
        {"accelerator_evidence": b"changed"},
        {"collateral": (epoch.collateral[0].model_copy(update={"sha256": b"x" * 32}),)},
    ):
        changed = epoch.model_copy(update=changes)
        assert changed.identity() != epoch.identity()
        assert changed.challenge() == epoch.challenge()


@pytest.mark.parametrize("signature", [b"x" * 63, b"x" * 65, b"", None, "00" * 64, False])
def test_signature_shape(artifacts: Any, signature: Any) -> None:
    with pytest.raises(WireError):
        artifacts["signed"].model_copy(update={"signature": signature}).encode()


def test_declared_epoch_links_and_issuance_window(artifacts: Any) -> None:
    a = artifacts
    signed = a["signed"]
    for changed in (
        signed.model_copy(update={"key_id": b"x" * 32}),
        signed.model_copy(update={"body": signed.body.model_copy(update={"epoch": b"x" * 32})}),
        signed.model_copy(
            update={
                "body": changed_expectation(
                    signed.body, a["expected"].model_copy(update={"model": b"x" * 32})
                )
            }
        ),
    ):
        with pytest.raises(HallmarkError, match="INPUT_BINDING_FAILED"):
            changed.validate_epoch(a["epoch"], now=120)
    for issued in (99, 121):
        changed = signed.model_copy(
            update={"body": signed.body.model_copy(update={"issued_at": issued})}
        )
        with pytest.raises(HallmarkError, match="STALE_EVIDENCE"):
            changed.validate_epoch(a["epoch"], now=120)
    with pytest.raises(WireError):
        signed.validate_epoch(None, now=120)


@pytest.mark.parametrize(
    "field",
    [
        "backend",
        "verifier_key",
        "context",
        "classifier",
        "input_digest",
        "unit_count",
        "chunk_count",
        "threshold",
        "verdict",
    ],
)
def test_proof_declared_input_substitutions_fail(artifacts: Any, field: str) -> None:
    a = artifacts
    proof = a["proofs"][0]
    inputs = proof.public_inputs
    if field in ("backend", "verifier_key"):
        changed = proof.model_copy(update={field: b"x" * 32})
    else:
        value = (
            False
            if field == "verdict"
            else getattr(inputs, field) + 1
            if field in ("unit_count", "chunk_count", "threshold")
            else b"x" * 32
        )
        changed = proof.model_copy(
            update={"public_inputs": inputs.model_copy(update={field: value})}
        )
    with pytest.raises(HallmarkError, match="INPUT_BINDING_FAILED"):
        changed.validate_inputs(inputs, a["classifiers"][0], a["profiles"][0], max_proof_bytes=1024)


@pytest.mark.parametrize("limit", [0, -1, True, 1024.0, None, MAX_PROOF_BYTES + 1])
def test_proof_budget_is_required_and_bounded(artifacts: Any, limit: Any) -> None:
    a = artifacts
    with pytest.raises(WireError):
        a["proofs"][0].validate_inputs(
            a["body"].inputs[0], a["classifiers"][0], a["profiles"][0], max_proof_bytes=limit
        )


def test_opaque_payload_limits_and_repr(artifacts: Any) -> None:
    a = artifacts
    for model, obj, field, cap in (
        (ProofArtifact, a["proofs"][0], "proof", MAX_PROOF_BYTES),
        (EpochRecord, a["epoch"], "cpu_evidence", MAX_EVIDENCE_BYTES),
        (EpochRecord, a["epoch"], "accelerator_evidence", MAX_EVIDENCE_BYTES),
    ):
        maximum = model.model_validate(obj.model_dump() | {field: b"x" * cap})
        assert len(getattr(maximum, field)) == cap
        with pytest.raises(ValidationError):
            model.model_validate(obj.model_dump() | {field: b"x" * (cap + 1)})
        with pytest.raises(ValidationError):
            model.model_validate(obj.model_dump() | {field: b""})
    proof = a["proofs"][0].model_copy(update={"proof": b"PRIVATE_PROOF"})
    assert "PRIVATE_PROOF" not in repr(proof)
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        proof.validate_inputs(
            a["body"].inputs[0], a["classifiers"][0], a["profiles"][0], max_proof_bytes=1
        )
    assert "SYNTHETIC_CPU" not in repr(a["epoch"])
    assert "NOT_A_REAL_SIGNATURE" not in repr(a["signed"])
    raw = decode(proof.encode()) | {"extra": "PRIVATE_SENTINEL"}
    with pytest.raises(WireError) as error:
        ProofArtifact.decode(encode(raw))
    assert error.value.__context__ is None and "PRIVATE_" not in str(error.value)


def test_required_fields_schema_versions_and_frozen_nested_values(artifacts: Any) -> None:
    a = artifacts
    for obj in (a["body"], a["signed"], a["epoch"], a["proofs"][0], a["body"].inputs[0]):
        value = decode(obj.encode())
        for missing in value:
            with pytest.raises(WireError):
                type(obj).decode(
                    encode({key: item for key, item in value.items() if key != missing})
                )
        for changes in ({"schema_id": "hallmark/unknown/2"}, {"extra": True}):
            with pytest.raises(WireError):
                type(obj).decode(encode(value | changes))
        with pytest.raises(ValidationError):
            obj.schema_id = obj.schema_id
    invalid = a["signed"].model_copy(update={"body": a["body"].model_copy(update={"inputs": ()})})
    with pytest.raises(WireError):
        invalid.validate_epoch(a["epoch"], now=120)


def test_external_arguments_cannot_default_to_the_artifact(artifacts: Any) -> None:
    a = artifacts
    for expected in (
        None,
        a["expected"].model_dump(),
        a["expected"].model_copy(update={"nonce": b"x"}),
    ):
        with pytest.raises(WireError):
            a["body"].validate_expectation(expected, now=120)
    with pytest.raises(TypeError):
        a["body"].validate_expectation(now=120)
    with pytest.raises(TypeError):
        a["body"].validate_expectation(a["expected"])
    for policy, profiles in (
        (None, a["profiles"]),
        (a["policy"], a["profiles"][:2]),
        (a["policy"], list(a["profiles"])),
        (a["policy"], (a["profiles"][0], None, a["profiles"][2])),
    ):
        with pytest.raises(WireError):
            a["body"].validate_policy(policy, a["classifiers"], profiles)
    with pytest.raises(HallmarkError, match="INPUT_BINDING_FAILED"):
        a["body"].validate_policy(
            a["policy"].model_copy(update={"max_response_bytes": 0}),
            a["classifiers"],
            a["profiles"],
        )
    with pytest.raises(WireError):
        a["proofs"][0].validate_inputs(
            None, a["classifiers"][0], a["profiles"][0], max_proof_bytes=1024
        )
    with pytest.raises(TypeError):
        a["proofs"][0].validate_inputs(a["body"].inputs[0], a["classifiers"][0], a["profiles"][0])


def test_no_acceptance_stub_or_io(artifacts: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("structural contracts must not inspect files or contact a verifier")

    monkeypatch.setattr(Path, "open", forbidden)
    a = artifacts
    a["signed"].validate_epoch(a["epoch"], now=120)
    a["body"].validate_policy(a["policy"], a["classifiers"], a["profiles"])
    a["proofs"][0].validate_inputs(
        a["body"].inputs[0], a["classifiers"][0], a["profiles"][0], max_proof_bytes=1024
    )
    assert a["proofs"][0].proof.startswith(b"NOT_A_REAL_PROOF")
    for obj in (a["signed"], a["epoch"], a["proofs"][0]):
        assert not any(
            hasattr(obj, name) for name in ("verify", "accepted", "verified", "claim_a", "claim_b")
        )
