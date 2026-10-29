"""Offline, public test keys only. No operational roots or policy adoption."""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import cbor2
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from hallmark import enrollment, registry_store
from hallmark.enrollment import (
    Enrollment,
    Limits,
    RegistryBody,
    RegistryEntry,
    RegistrySignature,
    RegistryState,
    SignedRegistry,
    TrustPolicy,
    enroll,
)
from hallmark.errors import HallmarkError
from hallmark.registry_store import enroll_and_store, provision_state, read_state
from hallmark.wire import H, WireError, decode, encode

ROOT = Path(__file__).resolve().parents[1]
# Public deterministic fixture seeds. Never use these for operational signing.
KEYS = tuple(Ed25519PrivateKey.from_private_bytes(bytes([i]) * 32) for i in range(1, 4))
PUBLIC = tuple(key.public_key().public_bytes_raw() for key in KEYS)
MODEL, POLICY, BACKEND, CLASSIFIER, MEASUREMENT = (bytes([i]) * 32 for i in range(10, 15))
KINDS = ("backend", "classifier", "epoch-measurement", "model", "policy")
DIGESTS = (BACKEND, CLASSIFIER, MEASUREMENT, MODEL, POLICY)


def trust_policy(**changes: Any) -> TrustPolicy:
    return TrustPolicy.model_validate(
        {
            "schema_id": "hallmark/trust/1",
            "registry_keys": (PUBLIC[0],),
            "signature_threshold": 1,
            "min_registry_sequence": 0,
            "accepted_models": (MODEL,),
            "accepted_policies": (POLICY,),
            "accepted_backends": (BACKEND,),
            "hardware_roots": (),
            "measurements": (),
            "required_claims": "B",
            "binding": "B1",
            "max_age_seconds": 100,
            "limits": Limits(
                bundle_bytes=67108864,
                proof_bytes=16777216,
                nesting=16,
                verify_seconds=60,
                worker_memory_bytes=2**31,
            ),
        }
        | changes
    )


def registry_body(**changes: Any) -> RegistryBody:
    return RegistryBody.model_validate(
        {
            "schema_id": "hallmark/registry/1",
            "sequence": 0,
            "previous": None,
            "issued_at": 100,
            "expires_at": 300,
            "entries": tuple(
                RegistryEntry(
                    kind=kind,
                    digest=digest,
                    valid_from=50,
                    valid_until=250,
                    retired_at=None,
                    review=b"r" * 32,
                )
                for kind, digest in zip(KINDS, DIGESTS, strict=True)
            ),
        }
        | changes
    )


def sign(body: RegistryBody, keys: Any = KEYS[:1]) -> SignedRegistry:
    return SignedRegistry(
        schema_id="hallmark/signed-registry/1",
        body=body,
        signatures=tuple(
            RegistrySignature(
                key_id=H("key", key.public_key().public_bytes_raw()),
                signature=key.sign(body.signing_bytes()),
            )
            for key in keys
        ),
    )


def state(body: RegistryBody) -> RegistryState:
    return RegistryState(
        schema_id="hallmark/registry-state/1", sequence=body.sequence, digest=body.identity()
    )


def chain(length: int = 3) -> tuple[SignedRegistry, ...]:
    bodies = [registry_body()]
    for sequence in range(1, length):
        bodies.append(registry_body(sequence=sequence, previous=bodies[-1].identity()))
    return tuple(sign(body) for body in bodies)


def test_current_checkpoint_and_complete_history() -> None:
    snapshots = chain()
    trust = trust_policy()
    first = enroll(snapshots[0], trust, state(snapshots[0].body), 150)
    assert first.registry == snapshots[0].body.identity()
    assert first.trust == trust.identity()
    assert first.checked_at == 150
    assert {e.kind for e in first.admitted} == {"model", "policy", "backend", "classifier"}
    result = enroll(snapshots[2], trust, first.state, 150, history=(snapshots[1],))
    assert result.state == state(snapshots[2].body)
    result.require_entry("model", MODEL, issued_at=100)
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        result.require_entry("epoch-measurement", MEASUREMENT, issued_at=100)
    with pytest.raises(TypeError):
        Enrollment()
    with pytest.raises(AttributeError):
        result.checked_at = 200
    assert not hasattr(result, "decode") and not hasattr(result, "accepted")


@pytest.mark.parametrize("missing", ["trust", "state", "now"])
def test_no_implicit_external_arguments(missing: str) -> None:
    body = registry_body()
    args = dict(snapshot=sign(body), trust=trust_policy(), state=state(body), now=150)
    del args[missing]
    with pytest.raises(TypeError):
        enroll(**args)


@pytest.mark.parametrize("value", [None, {}, {"registry_keys": PUBLIC}, b"bundle-trust"])
@pytest.mark.parametrize("field", ["trust", "state"])
def test_bundle_cannot_supply_external_objects(field: str, value: Any) -> None:
    body = registry_body()
    args = dict(snapshot=sign(body), trust=trust_policy(), state=state(body), now=150)
    args[field] = value
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        enroll(**args)


@pytest.mark.parametrize("now", [True, -1, 2**64, 150.0, "150", None])
def test_strict_clock(now: Any) -> None:
    body = registry_body()
    with pytest.raises(HallmarkError, match="INPUT_INVALID"):
        enroll(sign(body), trust_policy(), state(body), now)


@pytest.mark.parametrize("now", [99, 201, 300])
def test_freshness_boundaries(now: int) -> None:
    body = registry_body()
    with pytest.raises(HallmarkError, match="STALE_EVIDENCE"):
        enroll(sign(body), trust_policy(), state(body), now)


def test_freshness_inclusive_age_exclusive_expiry_and_historical_expiry() -> None:
    body = registry_body(expires_at=201)
    enroll(sign(body), trust_policy(), state(body), 200)
    with pytest.raises(HallmarkError, match="STALE_EVIDENCE"):
        enroll(sign(body), trust_policy(), state(body), 201)
    first = registry_body(expires_at=101)
    second = registry_body(sequence=1, previous=first.identity(), expires_at=102)
    third = registry_body(sequence=2, previous=second.identity(), issued_at=140)
    result = enroll(sign(third), trust_policy(), state(first), 150, history=(sign(second),))
    assert result.state.sequence == 2


def test_rollback_equivocation_minimum_and_skipped_history() -> None:
    zero, one, two = chain()
    cases = (
        (zero, trust_policy(), state(one.body), ()),
        (sign(registry_body(expires_at=301)), trust_policy(), state(zero.body), ()),
        (zero, trust_policy(min_registry_sequence=1), state(zero.body), ()),
        (two, trust_policy(), state(zero.body), ()),
        (two, trust_policy(), state(zero.body), (zero, one)),
        (two, trust_policy(), state(zero.body), (one, one)),
        (two, trust_policy(), state(zero.body), (two, one)),
        (
            two,
            trust_policy(),
            state(zero.body),
            (sign(registry_body(sequence=1, previous=b"x" * 32)),),
        ),
    )
    for snapshot, trust, checkpoint, history in cases:
        with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
            enroll(snapshot, trust, checkpoint, 150, history=history)


def test_history_enforces_successor_rules() -> None:
    zero = registry_body()
    entries = zero.entries
    retired = (*entries[:3], entries[3].model_copy(update={"retired_at": 120}), entries[4])
    one = registry_body(sequence=1, previous=zero.identity(), entries=retired)
    revived = registry_body(sequence=2, previous=one.identity())
    dropped = registry_body(sequence=2, previous=one.identity(), entries=(*retired[:3], retired[4]))
    for final in (revived, dropped):
        with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
            enroll(sign(final), trust_policy(), state(zero), 150, history=(sign(one),))
    earlier = (*entries[:3], entries[3].model_copy(update={"retired_at": 110}), entries[4])
    two = registry_body(sequence=2, previous=one.identity(), entries=earlier)
    three = registry_body(sequence=3, previous=two.identity(), entries=earlier)
    result = enroll(sign(three), trust_policy(), state(zero), 150, history=(sign(one), sign(two)))
    assert "model" not in {entry.kind for entry in result.admitted}


def test_intermediate_signatures_future_and_nonmonotonic_times() -> None:
    zero, one, two = chain()
    invalid = one.model_copy(
        update={"signatures": (one.signatures[0].model_copy(update={"signature": b"x" * 64}),)}
    )
    with pytest.raises(HallmarkError, match="SIGNATURE_INVALID"):
        enroll(two, trust_policy(), state(zero.body), 150, history=(invalid,))
    intermediate = registry_body(sequence=1, previous=zero.body.identity(), issued_at=151)
    final = registry_body(sequence=2, previous=intermediate.identity(), issued_at=140)
    for now in (150, 160):
        with pytest.raises(HallmarkError, match="STALE_EVIDENCE"):
            enroll(
                sign(final), trust_policy(), state(zero.body), now, history=(sign(intermediate),)
            )


def test_threshold_unknown_duplicate_invalid_and_malleable_signatures() -> None:
    body = registry_body()
    trust = trust_policy(registry_keys=PUBLIC[:2], signature_threshold=2)
    good = sign(body, KEYS[:2])
    good.verify_signatures(trust)
    sign(body, KEYS[:2][::-1]).verify_signatures(trust)
    with pytest.raises(ValidationError):
        sign(body, (KEYS[0], KEYS[0]))
    for bad in (sign(body), sign(body, KEYS[1:]), sign(body, KEYS)):
        with pytest.raises(HallmarkError, match="SIGNATURE_INVALID"):
            bad.verify_signatures(trust)
    signature = good.signatures[0]
    order = 2**252 + 27742317777372353535851937790883648493
    mutated = (
        b"\0" * 64,
        signature.signature[:32]
        + (int.from_bytes(signature.signature[32:], "little") + order).to_bytes(32, "little"),
        signature.signature[:-1] + bytes([signature.signature[-1] ^ 1]),
        KEYS[0].sign(body.encode()),
    )
    for value in mutated:
        bad = good.model_copy(
            update={
                "signatures": (
                    signature.model_copy(update={"signature": value}),
                    good.signatures[1],
                )
            }
        )
        with pytest.raises(HallmarkError, match="SIGNATURE_INVALID") as exc:
            bad.verify_signatures(trust)
        assert exc.value.__context__ is None
    altered = good.model_copy(update={"body": registry_body(expires_at=301)})
    with pytest.raises(HallmarkError, match="SIGNATURE_INVALID"):
        altered.verify_signatures(trust)


@pytest.mark.parametrize(
    "field",
    [
        "registry_keys",
        "accepted_models",
        "accepted_policies",
        "accepted_backends",
        "hardware_roots",
        "measurements",
    ],
)
def test_duplicate_trust_identities(field: str) -> None:
    value = PUBLIC[0] if field == "registry_keys" else MODEL
    with pytest.raises(ValidationError):
        trust_policy(**{field: (value, value)})


@pytest.mark.parametrize(
    "change",
    [
        {"signature_threshold": 0},
        {"signature_threshold": 2},
        {"signature_threshold": True},
        {"registry_keys": ()},
        {"accepted_models": ()},
        {"accepted_policies": ()},
        {"accepted_backends": ()},
        {"max_age_seconds": 0},
        {"min_registry_sequence": -1},
        {"binding": "B2"},
        {"required_claims": "A+B"},
        {"max_age_seconds": 2**64},
        {"required_claims": "A+B", "hardware_roots": (MODEL,)},
        {"required_claims": "A+B", "measurements": (MEASUREMENT,)},
    ],
)
def test_invalid_trust(change: Any) -> None:
    with pytest.raises(ValidationError):
        trust_policy(**change)


def test_hardware_configuration_and_external_allowlists() -> None:
    trust = trust_policy(
        required_claims="A+B", binding="B2", hardware_roots=(MODEL,), measurements=(MEASUREMENT,)
    )
    body = registry_body()
    result = enroll(sign(body), trust, state(body), 150)
    result.require_entry("epoch-measurement", MEASUREMENT, issued_at=100)
    result = enroll(sign(body), trust_policy(accepted_models=(b"x" * 32,)), state(body), 150)
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        result.require_entry("model", MODEL, issued_at=100)


@pytest.mark.parametrize(
    "field,cap",
    [
        ("bundle_bytes", 67108864),
        ("proof_bytes", 16777216),
        ("nesting", 16),
        ("verify_seconds", 60),
        ("worker_memory_bytes", 2**31),
    ],
)
@pytest.mark.parametrize("which", ["zero", "bool", "overflow"])
def test_limits_cannot_expand_hard_caps(field: str, cap: int, which: str) -> None:
    values = trust_policy().limits.model_dump()
    values[field] = {"zero": 0, "bool": True, "overflow": cap + 1}[which]
    with pytest.raises(ValidationError):
        Limits.model_validate(values)


def test_history_byte_nesting_and_deadline_limits(monkeypatch: Any) -> None:
    zero, one, two = chain()
    trust = trust_policy()
    for history in ([one], (one,) * 1025):
        with pytest.raises(HallmarkError, match="LIMIT_EXCEEDED"):
            enroll(two, trust, state(zero.body), 150, history=history)
    with pytest.raises(HallmarkError, match="INPUT_INVALID"):
        enroll(two, trust, state(zero.body), 150, history=(None,))
    for budget in (100, len(one.encode()) + len(two.encode()) - 1):
        small = trust_policy(limits=trust.limits.model_copy(update={"bundle_bytes": budget}))
        with pytest.raises(HallmarkError, match="LIMIT_EXCEEDED"):
            enroll(two, small, state(zero.body), 150, history=(one,))
    shallow = trust_policy(limits=trust.limits.model_copy(update={"nesting": 1}))
    with pytest.raises(HallmarkError, match="LIMIT_EXCEEDED"):
        enroll(zero, shallow, state(zero.body), 150)
    clocks = iter((0, 1, 61))
    monkeypatch.setattr(enrollment.time, "monotonic", lambda: next(clocks))
    with pytest.raises(HallmarkError, match="LIMIT_EXCEEDED"):
        enroll(zero, trust, state(zero.body), 150)


def test_retirement_and_receipt_validity_are_distinct() -> None:
    entry = registry_body().entries[0]
    entry.validate_time(issued_at=50, now=250)
    entry.validate_time(issued_at=249, now=250)
    for issued in (49, 250, 300):
        with pytest.raises(HallmarkError, match="STALE_EVIDENCE"):
            entry.validate_time(issued_at=issued, now=250)
    retired = entry.model_copy(update={"retired_at": 150})
    retired.validate_time(issued_at=100, now=149)
    with pytest.raises(HallmarkError, match="ARTIFACT_RETIRED"):
        retired.validate_time(issued_at=100, now=150)
    body = registry_body(entries=(retired, *registry_body().entries[1:]))
    result = enroll(sign(body), trust_policy(), state(body), 150)
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        result.require_entry("backend", BACKEND, issued_at=100)
    result.require_entry("model", MODEL, issued_at=100)
    with pytest.raises(HallmarkError, match="STALE_EVIDENCE"):
        result.require_entry("model", MODEL, issued_at=49)


@pytest.mark.parametrize(
    "change",
    [
        {"sequence": True},
        {"sequence": -1},
        {"sequence": 1},
        {"previous": MODEL},
        {"issued_at": 300},
        {"entries": ()},
        {"unknown": "PRIVATE_SENTINEL"},
        {"schema_id": "hallmark/registry/2"},
    ],
)
def test_registry_schema_rejections(change: Any) -> None:
    with pytest.raises(ValidationError):
        registry_body(**change)


def test_sorted_complete_entries_and_no_duplicate_signer_counting() -> None:
    body = registry_body()
    for entries in (body.entries[::-1], (body.entries[0], *body.entries)):
        with pytest.raises(ValidationError):
            registry_body(entries=entries)
    signed = sign(body)
    bypass = signed.model_copy(update={"signatures": (signed.signatures[0],) * 2})
    with pytest.raises(WireError):
        enroll(bypass, trust_policy(), state(body), 150)
    for obj in (body, signed, trust_policy(), state(body)):
        raw = decode(obj.encode())
        raw["unknown"] = "PRIVATE_SENTINEL"
        with pytest.raises(WireError) as exc:
            type(obj).decode(encode(raw))
        assert "PRIVATE_SENTINEL" not in str(exc.value)
        assert exc.value.__context__ is None
        with pytest.raises(ValidationError):
            obj.schema_id = "changed"


def test_state_store_success_compare_and_swap_and_no_implicit_creation(tmp_path: Path) -> None:
    zero, one, two = chain()
    path = tmp_path / "checkpoint.sqlite"
    with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
        read_state(path)
    with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
        enroll_and_store(path, zero, trust_policy(), state(zero.body), 150)
    assert not path.exists()
    provision_state(path, state(zero.body))
    original = path.read_bytes()
    with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
        provision_state(path, state(one.body))
    assert path.read_bytes() == original
    result = enroll_and_store(path, one, trust_policy(), state(zero.body), 150)
    assert read_state(path) == result.state
    with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
        enroll_and_store(path, two, trust_policy(), state(zero.body), 150, history=(one,))
    assert read_state(path) == result.state
    enroll_and_store(path, two, trust_policy(), result.state, 150)
    assert read_state(path) == state(two.body)


def test_failed_verification_or_write_preserves_original_state(tmp_path: Path) -> None:
    zero, one, two = chain()
    path = tmp_path / "checkpoint.sqlite"
    provision_state(path, state(zero.body))
    original = path.read_bytes()
    with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
        enroll_and_store(path, two, trust_policy(), state(zero.body), 150)
    assert path.read_bytes() == original
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TRIGGER fail_update BEFORE UPDATE ON checkpoint "
            "BEGIN SELECT RAISE(ABORT, 'PRIVATE_SENTINEL'); END"
        )
    original = path.read_bytes()
    with pytest.raises(HallmarkError, match="STORAGE_FAILED") as exc:
        enroll_and_store(path, one, trust_policy(), state(zero.body), 150)
    assert exc.value.__context__ is None
    assert path.read_bytes() == original
    assert read_state(path) == state(zero.body)


def test_commit_failure_rolls_back_staged_update(tmp_path: Path, monkeypatch: Any) -> None:
    zero, one, _ = chain()
    path = tmp_path / "checkpoint.sqlite"
    provision_state(path, state(zero.body))
    original = path.read_bytes()
    real_connect = registry_store._connect

    def with_deferred_constraint(target: Path) -> sqlite3.Connection:
        connection = real_connect(target)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("CREATE TEMP TABLE parent (id PRIMARY KEY)")
        connection.execute(
            "CREATE TEMP TABLE child (id REFERENCES parent(id) DEFERRABLE INITIALLY DEFERRED)"
        )
        connection.execute(
            "CREATE TEMP TRIGGER commit_failure AFTER UPDATE ON main.checkpoint "
            "BEGIN INSERT INTO child VALUES (1); END"
        )
        return connection

    monkeypatch.setattr(registry_store, "_connect", with_deferred_constraint)
    with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
        enroll_and_store(path, one, trust_policy(), state(zero.body), 150)
    monkeypatch.setattr(registry_store, "_connect", real_connect)
    assert path.read_bytes() == original
    assert read_state(path) == state(zero.body)


def test_concurrent_writer_is_rejected_without_waiting(tmp_path: Path) -> None:
    zero, one, _ = chain()
    path = tmp_path / "checkpoint.sqlite"
    provision_state(path, state(zero.body))
    with sqlite3.connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
            enroll_and_store(path, one, trust_policy(), state(zero.body), 150)
    assert read_state(path) == state(zero.body)


def test_process_exit_before_commit_recovers_original_checkpoint(tmp_path: Path) -> None:
    zero, one, _ = chain()
    path = tmp_path / "checkpoint.sqlite"
    provision_state(path, state(zero.body))
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os, sqlite3, sys; "
            "c = sqlite3.connect(sys.argv[1]); "
            "c.execute('BEGIN IMMEDIATE'); "
            "c.execute('UPDATE checkpoint SET state=? WHERE id=1', "
            "(bytes.fromhex(sys.argv[2]),)); "
            "os._exit(23)",
            str(path),
            state(one.body).encode().hex(),
        ],
        timeout=5,
        check=False,
    )
    assert child.returncode == 23
    assert read_state(path) == state(zero.body)


def test_silent_update_suppression_never_returns_success(tmp_path: Path) -> None:
    zero, one, _ = chain()
    path = tmp_path / "checkpoint.sqlite"
    provision_state(path, state(zero.body))
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TRIGGER ignore_update BEFORE UPDATE ON checkpoint "
            "BEGIN SELECT RAISE(IGNORE); END"
        )
    with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
        enroll_and_store(path, one, trust_policy(), state(zero.body), 150)
    assert read_state(path) == state(zero.body)


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "permissions", "directory", "corrupt"])
def test_unsafe_checkpoint_storage(tmp_path: Path, kind: str) -> None:
    original = tmp_path / "original.sqlite"
    path = tmp_path / "checkpoint.sqlite"
    provision_state(original, state(registry_body()))
    if kind == "symlink":
        path.symlink_to(original)
    elif kind == "hardlink":
        os.link(original, path)
    elif kind == "permissions":
        path.write_bytes(original.read_bytes())
        path.chmod(0o644)
    elif kind == "directory":
        path.mkdir()
    else:
        path.write_bytes(b"PRIVATE_SENTINEL")
        path.chmod(0o600)
    with pytest.raises(HallmarkError, match="STORAGE_FAILED") as exc:
        read_state(path)
    assert exc.value.__context__ is None


@pytest.mark.parametrize("raw", [b"wrong", b"x" * 257, None, "text"])
def test_corrupt_checkpoint_record_fails_closed(tmp_path: Path, raw: Any) -> None:
    path = tmp_path / "checkpoint.sqlite"
    provision_state(path, state(registry_body()))
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE checkpoint")
        connection.execute("CREATE TABLE checkpoint(id, state)")
        connection.execute("INSERT INTO checkpoint VALUES (1, ?)", (raw,))
    with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
        read_state(path)


def test_schema_and_signed_golden_vectors() -> None:
    vectors = json.loads((ROOT / "fixtures/wire/enrollment-v1.json").read_text())
    models = {
        "trust": TrustPolicy,
        "registry": RegistryBody,
        "signed-registry": SignedRegistry,
        "registry-state": RegistryState,
    }
    for name, cls in models.items():
        assert cls.model_json_schema() == json.loads(
            (ROOT / f"docs/schemas/{name}-v1.json").read_text()
        )
        obj = cls.decode(bytes.fromhex(vectors[name]["cbor_hex"]))
        assert json.loads(obj.model_dump_json()) == vectors[name]["json"]
        assert obj.encode().hex() == vectors[name]["cbor_hex"]
    signed = SignedRegistry.decode(bytes.fromhex(vectors["signed-registry"]["cbor_hex"]))
    trust = TrustPolicy.decode(bytes.fromhex(vectors["trust"]["cbor_hex"]))
    checkpoint = RegistryState.decode(bytes.fromhex(vectors["registry-state"]["cbor_hex"]))
    enroll(signed, trust, checkpoint, vectors["now"])
    tag = b"hallmark/v1/sign/registry"
    assert signed.body.signing_bytes() == (len(tag).to_bytes(4, "big") + tag + signed.body.encode())
    assert signed.body.signing_bytes().hex() == vectors["registry"]["signing_bytes_hex"]
    for kind, obj in (("registry", signed.body), ("trust", trust)):
        tag = ("hallmark/v1/" + kind).encode()
        expected = hashlib.sha256(
            len(tag).to_bytes(4, "big") + tag + cbor2.dumps(decode(obj.encode()), canonical=True)
        ).digest()
        assert obj.identity() == expected
        assert expected.hex() == vectors[kind]["identity_hex"]
