"""Authoring, rotation and local retention; all signing seeds are public fixtures."""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from test_enrollment import KEYS, MODEL, PUBLIC, registry_body, state, trust_policy

from hallmark import cli, registry_history, registry_store
from hallmark.enrollment import RegistryState, SignedRegistry, TrustPolicy, enroll
from hallmark.errors import HallmarkError
from hallmark.registry import (
    RegistryTransition,
    SignedTransition,
    enroll_transition,
    next_snapshot,
    sign_snapshot,
    sign_transition,
    validate_successor,
)
from hallmark.registry_cli import check_registry
from hallmark.registry_history import (
    append_history,
    create_history,
    read_snapshot,
    read_transition,
)
from hallmark.registry_store import provision_state, read_state, rotate_and_store
from hallmark.wire import H, WireError, decode, encode

ROOT = Path(__file__).resolve().parents[1]


def rotation() -> tuple[TrustPolicy, TrustPolicy, SignedRegistry, SignedRegistry, SignedTransition]:
    old = trust_policy(registry_keys=PUBLIC[:2], signature_threshold=2)
    new = trust_policy(registry_keys=PUBLIC[1:], signature_threshold=2, min_registry_sequence=1)
    previous = sign_snapshot(registry_body(), old, KEYS[:2])
    body = next_snapshot(previous.body, previous.body.entries, issued_at=110, expires_at=310)
    current = sign_snapshot(body, new, KEYS[1:])
    proposal = RegistryTransition(
        schema_id="hallmark/registry-transition/1",
        old_trust=old.identity(),
        new_trust=new.identity(),
        old_keys=tuple(sorted(H("key", key) for key in old.registry_keys)),
        new_keys=tuple(sorted(H("key", key) for key in new.registry_keys)),
        activation_sequence=1,
        previous=previous.body.identity(),
        reason="scheduled-rotation",
        review=b"r" * 32,
    )
    transition = sign_transition(
        proposal, old, new, state(previous.body), old_keys=KEYS[:2], new_keys=KEYS[1:]
    )
    return old, new, previous, current, transition


def test_author_signs_exact_canonical_body_and_sorts_signatures() -> None:
    trust = trust_policy(registry_keys=PUBLIC[:2], signature_threshold=2)
    body = registry_body()
    result = sign_snapshot(body, trust, KEYS[:2])
    assert result == sign_snapshot(body, trust, KEYS[:2][::-1])
    assert result.body.encode() == body.encode()
    result.verify_signatures(trust)
    assert SignedRegistry.decode(result.encode()) == result


@pytest.mark.parametrize(
    "keys", [(), KEYS[:1], KEYS[1:], KEYS, (KEYS[0], KEYS[0]), [KEYS[0]], (b"secret",), None]
)
def test_signer_threshold_unknown_duplicates_and_raw_seeds_reject(keys: Any) -> None:
    trust = trust_policy(registry_keys=PUBLIC[:2], signature_threshold=2)
    with pytest.raises(HallmarkError, match="SIGNATURE_INVALID"):
        sign_snapshot(registry_body(), trust, keys)


@pytest.mark.parametrize(
    "change", [{"valid_from": 51}, {"valid_until": 999}, {"review": b"x" * 32}]
)
def test_prior_identity_metadata_cannot_be_rewritten(change: dict[str, Any]) -> None:
    previous = registry_body()
    entries = (previous.entries[0].model_copy(update=change), *previous.entries[1:])
    with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
        next_snapshot(previous, entries, issued_at=110, expires_at=300)


def test_history_retains_expired_entries_and_irreversible_retirements() -> None:
    first = registry_body()
    retired = first.entries[0].model_copy(update={"retired_at": 120})
    second = next_snapshot(first, (retired, *first.entries[1:]), issued_at=110, expires_at=400)
    for changed in (
        second.entries[1:],
        (retired.model_copy(update={"retired_at": None}), *second.entries[1:]),
        (retired.model_copy(update={"retired_at": 121}), *second.entries[1:]),
    ):
        with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
            next_snapshot(second, changed, issued_at=120, expires_at=400)
    earlier = retired.model_copy(update={"retired_at": 100})
    third = next_snapshot(second, (earlier, *second.entries[1:]), issued_at=260, expires_at=400)
    signed = sign_snapshot(third, trust_policy(), KEYS[:1])
    result = enroll(signed, trust_policy(), state(third), 270)
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        result.require_entry("backend", earlier.digest, issued_at=100)
    result.require_entry("model", MODEL, issued_at=249)
    with pytest.raises(HallmarkError, match="STALE_EVIDENCE"):
        result.require_entry("model", MODEL, issued_at=250)


@pytest.mark.parametrize("change", [{"sequence": 2}, {"previous": b"x" * 32}, {"issued_at": 99}])
def test_authoring_checks_sequence_link_and_previous_time(change: dict[str, Any]) -> None:
    first = registry_body()
    second = next_snapshot(first, first.entries, issued_at=110, expires_at=300)
    with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
        validate_successor(first, second.model_copy(update=change))


def test_dual_authorized_rotation_and_new_only_successor() -> None:
    old, new, previous, current, transition = rotation()
    result = enroll_transition(
        current, transition, old, new, state(previous.body), 150, previous=previous
    )
    assert result.trust == new.identity() and result.state == state(current.body)
    with pytest.raises(HallmarkError, match="SIGNATURE_INVALID"):
        enroll(current, old, state(previous.body), 150)
    with pytest.raises(HallmarkError, match="SIGNATURE_INVALID"):
        previous.verify_signatures(new)
    with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
        transition.verify(old, new, result.state)
    third = next_snapshot(current.body, current.body.entries, issued_at=120, expires_at=310)
    enroll(sign_snapshot(third, new, KEYS[1:]), new, result.state, 150)


@pytest.mark.parametrize("side", ["old", "new"])
@pytest.mark.parametrize("mutation", ["empty", "one", "duplicate", "swapped", "invalid", "domain"])
def test_both_transition_authorizations_are_required(side: str, mutation: str) -> None:
    old, new, previous, current, transition = rotation()
    signatures = getattr(transition, side + "_signatures")
    if mutation == "empty":
        signatures = ()
    elif mutation == "one":
        signatures = signatures[:1]
    elif mutation == "duplicate":
        signatures = (signatures[0],) * 2
    elif mutation == "swapped":
        signatures = getattr(transition, ("new" if side == "old" else "old") + "_signatures")
    else:
        raw = b"x" * 64 if mutation == "invalid" else KEYS[0].sign(transition.body.encode())
        signatures = (signatures[0].model_copy(update={"signature": raw}), *signatures[1:])
    bad = transition.model_copy(update={side + "_signatures": signatures})
    with pytest.raises(HallmarkError):
        enroll_transition(current, bad, old, new, state(previous.body), 150, previous=previous)


@pytest.mark.parametrize(
    "change",
    [
        {"old_trust": b"x" * 32},
        {"new_trust": b"x" * 32},
        {"previous": b"x" * 32},
        {"activation_sequence": 2},
        {"old_keys": (b"x" * 32,)},
        {"new_keys": (b"x" * 32,)},
        {"reason": "changed-review"},
        {"review": b"x" * 32},
    ],
)
def test_transition_binds_complete_policies_activation_reason_and_review(
    change: dict[str, Any],
) -> None:
    old, new, previous, _, transition = rotation()
    bad = transition.model_copy(update={"body": transition.body.model_copy(update=change)})
    with pytest.raises(HallmarkError):
        bad.verify(old, new, state(previous.body))


@pytest.mark.parametrize(
    "change",
    [
        {"min_registry_sequence": 0},
        {"min_registry_sequence": 2},
        {"required_claims": "A+B", "hardware_roots": (b"h" * 32,), "measurements": (b"m" * 32,)},
        {"accepted_models": (b"x" * 32,)},
        {"signature_threshold": 1},
    ],
)
def test_new_external_policy_cannot_be_substituted(change: dict[str, Any]) -> None:
    old, new, previous, _, transition = rotation()
    altered = TrustPolicy.model_validate(new.model_dump(mode="python") | change)
    with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
        transition.verify(old, altered, state(previous.body))


def test_new_policy_must_activate_at_link_even_when_both_sets_sign() -> None:
    old, new, previous, _, transition = rotation()
    for minimum in (0, 2):
        altered = new.model_copy(update={"min_registry_sequence": minimum})
        proposal = transition.body.model_copy(update={"new_trust": altered.identity()})
        with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
            sign_transition(
                proposal, old, altered, state(previous.body), old_keys=KEYS[:2], new_keys=KEYS[1:]
            )
    unchanged = old.model_copy(update={"min_registry_sequence": 1})
    proposal = transition.body.model_copy(
        update={"new_trust": unchanged.identity(), "new_keys": transition.body.old_keys}
    )
    with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
        sign_transition(
            proposal, old, unchanged, state(previous.body), old_keys=KEYS[:2], new_keys=KEYS[:2]
        )


def test_shared_key_does_not_reuse_old_role_signature_for_new_role() -> None:
    old, new, previous, _, transition = rotation()
    shared = H("key", PUBLIC[1])
    old_signature = next(s for s in transition.old_signatures if s.key_id == shared)
    bad = transition.model_copy(
        update={
            "new_signatures": tuple(
                old_signature if s.key_id == shared else s for s in transition.new_signatures
            )
        }
    )
    with pytest.raises(HallmarkError, match="SIGNATURE_INVALID"):
        bad.verify(old, new, state(previous.body))


@pytest.mark.parametrize(
    "change",
    [
        {"activation_sequence": 0},
        {"activation_sequence": True},
        {"old_keys": ()},
        {"new_keys": (b"x" * 32, b"x" * 32)},
        {"reason": "PRIVATE\nSENTINEL"},
        {"review": b"x"},
        {"schema_id": "hallmark/registry-transition/2"},
        {"extra": "PRIVATE_SENTINEL"},
    ],
)
def test_transition_schemas_reject_ambiguous_values(change: dict[str, Any]) -> None:
    proposal = rotation()[4].body
    with pytest.raises(ValidationError):
        RegistryTransition.model_validate(proposal.model_dump(mode="python") | change)
    with pytest.raises(WireError) as error:
        RegistryTransition.decode(encode(decode(proposal.encode()) | change))
    assert "PRIVATE" not in str(error.value) and error.value.__context__ is None


@pytest.mark.parametrize("bad", [None, {}, b"bundle-trust"])
def test_rotation_requires_external_policies_and_checkpoint(bad: Any) -> None:
    old, new, previous, current, transition = rotation()
    for arguments in (
        (bad, new, state(previous.body)),
        (old, bad, state(previous.body)),
        (old, new, bad),
    ):
        with pytest.raises(HallmarkError, match="TRUST_MISSING"):
            enroll_transition(current, transition, *arguments, 150, previous=previous)


def test_rotation_revalidates_previous_snapshot_freshness_and_complete_entries() -> None:
    old, new, previous, current, transition = rotation()
    substituted = sign_snapshot(registry_body(expires_at=301), old, KEYS[:2])
    with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
        enroll_transition(
            current, transition, old, new, state(previous.body), 150, previous=substituted
        )
    missing = current.body.model_copy(update={"entries": current.body.entries[1:]})
    with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
        enroll_transition(
            sign_snapshot(missing, new, KEYS[1:]),
            transition,
            old,
            new,
            state(previous.body),
            150,
            previous=previous,
        )
    for now in (109, 211, 310):
        with pytest.raises(HallmarkError, match="STALE_EVIDENCE"):
            enroll_transition(
                current, transition, old, new, state(previous.body), now, previous=previous
            )


def test_signing_and_rotation_enforce_caller_wire_limits() -> None:
    old, new, previous, current, transition = rotation()
    low = old.model_copy(update={"limits": old.limits.model_copy(update={"bundle_bytes": 100})})
    with pytest.raises(HallmarkError, match="LIMIT_EXCEEDED"):
        sign_snapshot(previous.body, low, KEYS[:2])
    combined = sum(len(r.encode()) for r in (previous, current, transition))
    low = new.model_copy(
        update={"limits": new.limits.model_copy(update={"bundle_bytes": combined - 1})}
    )
    proposal = transition.body.model_copy(update={"new_trust": low.identity()})
    signed = sign_transition(
        proposal, old, low, state(previous.body), old_keys=KEYS[:2], new_keys=KEYS[1:]
    )
    with pytest.raises(HallmarkError, match="LIMIT_EXCEEDED"):
        enroll_transition(current, signed, old, low, state(previous.body), 150, previous=previous)


def test_rotation_total_elapsed_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    old, new, previous, current, transition = rotation()
    clock = iter((0, 0, 0, 0, 61))
    monkeypatch.setattr("hallmark.registry.time.monotonic", lambda: next(clock))
    with pytest.raises(HallmarkError, match="LIMIT_EXCEEDED"):
        enroll_transition(
            current, transition, old, new, state(previous.body), 150, previous=previous
        )


def test_history_requires_exact_initial_pin_and_database_role(tmp_path: Path) -> None:
    old, _, previous, _, _ = rotation()
    path = tmp_path / "history.sqlite"
    pin = state(previous.body)
    with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
        create_history(path, previous, old, pin.model_copy(update={"digest": b"x" * 32}), 150)
    assert not path.exists()
    create_history(path, previous, old, pin, 150)
    with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
        read_state(path)
    other = tmp_path / "checkpoint.sqlite"
    provision_state(other, pin)
    with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
        read_snapshot(other, pin)


def test_retained_history_survives_rotation_and_rejects_rewrites(tmp_path: Path) -> None:
    old, new, previous, current, transition = rotation()
    path = tmp_path / "history.sqlite"
    start = state(previous.body)
    create_history(path, previous, old, start, 150)
    before = path.read_bytes()
    with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
        create_history(path, previous, old, start, 150)
    assert path.read_bytes() == before
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        append_history(path, current, new, start, 150)
    assert path.read_bytes() == before
    result = append_history(path, current, new, start, 150, transition=transition, old_trust=old)
    assert read_snapshot(path, start) == previous
    assert read_snapshot(path, result.state) == current
    assert read_transition(path, start) is None
    assert read_transition(path, result.state) == transition
    before = path.read_bytes()
    with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
        append_history(path, current, new, start, 150, transition=transition, old_trust=old)
    assert path.read_bytes() == before
    body = next_snapshot(current.body, current.body.entries, issued_at=120, expires_at=320)
    third = sign_snapshot(body, new, KEYS[1:])
    final = append_history(path, third, new, result.state, 150)
    assert read_snapshot(path, start) == previous and read_snapshot(path, final.state) == third
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT count(*) FROM snapshots").fetchone() == (3,)
        for sql in ("UPDATE snapshots SET snapshot=x'01'", "DELETE FROM snapshots"):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(sql)
    assert read_snapshot(path, final.state) == third


def test_history_same_digest_changed_bytes_and_unequal_digest_reject(tmp_path: Path) -> None:
    old, _, previous, _, _ = rotation()
    path = tmp_path / "history.sqlite"
    original = state(previous.body)
    create_history(path, previous, old, original, 150)
    with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
        read_snapshot(path, original.model_copy(update={"digest": b"x" * 32}))
    altered = sign_snapshot(registry_body(expires_at=301), old, KEYS[:2])
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER refuse_UPDATE")
        connection.execute("UPDATE snapshots SET snapshot=?", (altered.encode(),))
    with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
        read_snapshot(path, original)


@pytest.mark.parametrize("problem", ["link", "hardlink", "mode", "missing", "directory"])
def test_history_rejects_unsafe_paths(tmp_path: Path, problem: str) -> None:
    old, _, previous, _, _ = rotation()
    path = tmp_path / "history.sqlite"
    create_history(path, previous, old, state(previous.body), 150)
    target = tmp_path / "unsafe"
    if problem == "link":
        target.symlink_to(path)
    elif problem == "hardlink":
        os.link(path, target)
    elif problem == "mode":
        path.chmod(0o644)
        target = path
    elif problem == "directory":
        target.mkdir()
    with pytest.raises(HallmarkError, match="STORAGE_FAILED"):
        read_snapshot(target, state(previous.body))
    if problem == "missing":
        assert not target.exists()


@pytest.mark.parametrize("operation", ["archive", "checkpoint"])
@pytest.mark.parametrize(
    "failure", ["stale", "invalid", "locked", "statement", "commit", "ignored"]
)
def test_failed_rotation_preserves_history_and_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str, failure: str
) -> None:
    old, new, previous, current, transition = rotation()
    path = tmp_path / "state.sqlite"
    start = state(previous.body)
    if operation == "archive":
        create_history(path, previous, old, start, 150)
        module = registry_history
        table, event = "snapshots", "INSERT"
    else:
        provision_state(path, start)
        module = registry_store
        table, event = "checkpoint", "UPDATE"
    saved_connect = module._connect
    if failure in ("statement", "ignored"):
        action = "RAISE(ABORT,'PRIVATE_SENTINEL')" if failure == "statement" else "RAISE(IGNORE)"
        with sqlite3.connect(path) as connection:
            connection.execute(
                f"CREATE TRIGGER reject_write BEFORE {event} ON {table} BEGIN SELECT {action}; END"
            )
    if failure == "commit":

        def deferred(target: Path) -> sqlite3.Connection:
            connection = saved_connect(target)
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("CREATE TEMP TABLE parent(id PRIMARY KEY)")
            connection.execute(
                "CREATE TEMP TABLE child(id REFERENCES parent(id) DEFERRABLE INITIALLY DEFERRED)"
            )
            connection.execute(
                f"CREATE TEMP TRIGGER commit_failure AFTER {event} ON main.{table} "
                "BEGIN INSERT INTO child VALUES (1); END"
            )
            return connection

        monkeypatch.setattr(module, "_connect", deferred)
    before = path.read_bytes()
    expected = start.model_copy(update={"digest": b"x" * 32}) if failure == "stale" else start
    if failure == "invalid":
        transition = transition.model_copy(update={"old_signatures": ()})
    locker = sqlite3.connect(path)
    try:
        if failure == "locked":
            locker.execute("BEGIN IMMEDIATE")
        with pytest.raises(HallmarkError) as error:
            if operation == "archive":
                append_history(
                    path, current, new, expected, 150, transition=transition, old_trust=old
                )
            else:
                rotate_and_store(
                    path, current, transition, old, new, expected, 150, previous=previous
                )
        assert "PRIVATE_SENTINEL" not in str(error.value)
        assert error.value.__context__ is None
    finally:
        locker.close()
    monkeypatch.setattr(module, "_connect", saved_connect)
    assert path.read_bytes() == before
    if operation == "archive":
        assert read_snapshot(path, start) == previous
        with sqlite3.connect(path) as connection:
            assert connection.execute("SELECT count(*) FROM snapshots").fetchone() == (1,)
    else:
        assert read_state(path) == start


def test_rotation_checkpoint_rejects_replay_and_old_keys(tmp_path: Path) -> None:
    old, new, previous, current, transition = rotation()
    path = tmp_path / "checkpoint.sqlite"
    start = state(previous.body)
    provision_state(path, start)
    result = rotate_and_store(path, current, transition, old, new, start, 150, previous=previous)
    assert read_state(path) == result.state == state(current.body)
    with pytest.raises(HallmarkError, match="REGISTRY_INVALID"):
        rotate_and_store(path, current, transition, old, new, start, 150, previous=previous)
    third = next_snapshot(current.body, current.body.entries, issued_at=120, expires_at=320)
    old_signed = sign_snapshot(third, old, KEYS[:2])
    with pytest.raises(HallmarkError, match="SIGNATURE_INVALID"):
        registry_store.enroll_and_store(path, old_signed, new, result.state, 150)
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        registry_store.enroll_and_store(path, old_signed, old, result.state, 150)
    assert read_state(path) == result.state


def test_checkpoint_trust_binding_migrates_atomically_and_requires_reenrollment(
    tmp_path: Path,
) -> None:
    old, new, previous, current, transition = rotation()
    path = tmp_path / "checkpoint.sqlite"
    start = state(previous.body)
    provision_state(path, start)
    registry_store.enroll_and_store(path, previous, old, start, 150)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT digest FROM trust_binding").fetchall() == [
            (old.identity(),)
        ]
    unrelated = old.model_copy(update={"max_age_seconds": 101})
    before = path.read_bytes()
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        registry_store.enroll_and_store(path, previous, unrelated, start, 150)
    assert path.read_bytes() == before
    rotate_and_store(path, current, transition, old, new, start, 150, previous=previous)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT digest FROM trust_binding").fetchall() == [
            (new.identity(),)
        ]


@pytest.mark.parametrize("operation", ["archive", "checkpoint"])
def test_process_exit_before_commit_recovers_both_records(tmp_path: Path, operation: str) -> None:
    old, new, previous, current, transition = rotation()
    path = tmp_path / "state.sqlite"
    start = state(previous.body)
    if operation == "archive":
        create_history(path, previous, old, start, 150)
    else:
        provision_state(path, start)
        registry_store.enroll_and_store(path, previous, old, start, 150)
    for name, record in (
        ("old", old),
        ("new", new),
        ("previous", previous),
        ("current", current),
        ("transition", transition),
    ):
        (tmp_path / name).write_bytes(record.encode())
    script = """
import os, sqlite3, sys
from pathlib import Path
from hallmark.enrollment import TrustPolicy, SignedRegistry, RegistryState
from hallmark.registry import SignedTransition
from hallmark import registry_history as archive, registry_store as checkpoint
root=Path(sys.argv[1]); operation=sys.argv[2]
old,new=(TrustPolicy.decode((root/name).read_bytes()) for name in ('old','new'))
previous,current=(SignedRegistry.decode((root/name).read_bytes())
                  for name in ('previous','current'))
transition=SignedTransition.decode((root/'transition').read_bytes())
state=RegistryState(schema_id='hallmark/registry-state/1',sequence=0,digest=previous.body.identity())
module=archive if operation=='archive' else checkpoint
original=module._connect
def terminate(path):
    connection=original(path)
    connection.create_function('terminate',0,lambda:os._exit(77))
    table,event=('snapshots','INSERT') if operation=='archive' else ('checkpoint','UPDATE')
    connection.execute(f'CREATE TEMP TRIGGER terminate AFTER {event} ON main.{table} '
                       'BEGIN SELECT terminate(); END')
    return connection
module._connect=terminate
if operation=='archive':
    archive.append_history(root/'state.sqlite',current,new,state,150,
                           transition=transition,old_trust=old)
else:
    checkpoint.rotate_and_store(root/'state.sqlite',current,transition,old,new,state,150,
                                previous=previous)
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path), operation],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 77
    if operation == "archive":
        assert read_snapshot(path, start) == previous
        with sqlite3.connect(path) as connection:
            assert connection.execute("SELECT count(*) FROM snapshots").fetchone() == (1,)
    else:
        assert read_state(path) == start
        with sqlite3.connect(path) as connection:
            assert connection.execute("SELECT digest FROM trust_binding").fetchall() == [
                (old.identity(),)
            ]


def write_cli_inputs(tmp_path: Path) -> tuple[list[str], RegistryState]:
    old, new, previous, current, transition = rotation()
    for name, record in (
        ("old", old),
        ("trust", new),
        ("previous", previous),
        ("snapshot", current),
        ("transition", transition),
    ):
        (tmp_path / name).write_bytes(record.encode())
    provision_state(tmp_path / "state", state(previous.body))
    return [
        "registry-check",
        str(tmp_path / "snapshot"),
        "--trust",
        str(tmp_path / "trust"),
        "--state",
        str(tmp_path / "state"),
        "--now",
        "150",
        "--old-trust",
        str(tmp_path / "old"),
        "--previous",
        str(tmp_path / "previous"),
        "--transition",
        str(tmp_path / "transition"),
    ], state(current.body)


def test_cli_rotation_offline_and_normal_successor(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    argv, expected = write_cli_inputs(tmp_path)

    def no_network(*args: Any, **kwargs: Any) -> None:
        pytest.fail("registry check must be offline")

    monkeypatch.setattr("socket.socket", no_network)
    assert cli.main(argv) == 0
    output = capsys.readouterr()
    record = json.loads(output.out)
    assert output.err == "" and record == {
        "schema_id": "hallmark/registry-check/1",
        "registry": expected.digest.hex(),
        "sequence": 1,
        "trust": rotation()[1].identity().hex(),
        "checked_at": 150,
    }
    assert read_state(tmp_path / "state") == expected
    assert cli.main(argv[:8]) == 0
    capsys.readouterr()
    new = rotation()[1]
    current = rotation()[3]
    second = next_snapshot(current.body, current.body.entries, issued_at=120, expires_at=310)
    third = next_snapshot(second, second.entries, issued_at=130, expires_at=310)
    (tmp_path / "snapshot").write_bytes(sign_snapshot(third, new, KEYS[1:]).encode())
    (tmp_path / "history").write_bytes(sign_snapshot(second, new, KEYS[1:]).encode())
    assert cli.main(argv[:8] + ["--history", str(tmp_path / "history")]) == 0
    assert json.loads(capsys.readouterr().out)["sequence"] == 3


@pytest.mark.parametrize(
    "mutation",
    [
        "partial",
        "history-and-rotation",
        "bad-signature",
        "missing-state",
        "future",
        "malformed",
        "duplicate-map",
        "link",
        "fifo",
        "too-large",
        "missing-now",
    ],
)
def test_cli_failures_are_private_and_do_not_advance_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], mutation: str
) -> None:
    argv, _ = write_cli_inputs(tmp_path)
    path = tmp_path / "state"
    before = path.read_bytes()
    snapshot = tmp_path / "snapshot"
    if mutation == "partial":
        argv = argv[:-2]
    elif mutation == "history-and-rotation":
        argv += ["--history", str(tmp_path / "previous")]
    elif mutation == "bad-signature":
        raw = SignedRegistry.decode(snapshot.read_bytes())
        bad = raw.signatures[0].model_copy(update={"signature": b"x" * 64})
        snapshot.write_bytes(
            raw.model_copy(update={"signatures": (bad, *raw.signatures[1:])}).encode()
        )
    elif mutation == "missing-state":
        argv[5] = str(tmp_path / "PRIVATE_SENTINEL")
    elif mutation == "future":
        argv[7] = "99"
    elif mutation in ("malformed", "duplicate-map"):
        snapshot.write_bytes(
            b"PRIVATE_SENTINEL" if mutation == "malformed" else b"\xa2aa\x01aa\x02"
        )
    elif mutation in ("link", "fifo"):
        snapshot.unlink()
        if mutation == "link":
            snapshot.symlink_to(tmp_path / "previous")
        else:
            os.mkfifo(snapshot)
    elif mutation == "too-large":
        with snapshot.open("wb") as handle:
            handle.truncate(67108865)
    elif mutation == "missing-now":
        del argv[6:8]
    assert cli.main(argv) in (1, 2, 3)
    output = capsys.readouterr()
    assert output.out == "" and "PRIVATE_SENTINEL" not in output.err
    assert str(tmp_path) not in output.err
    assert json.loads(output.err)["schema_id"] == "hallmark/error/1"
    assert path.read_bytes() == before


def test_cli_history_count_is_bounded_before_file_io(tmp_path: Path) -> None:
    with pytest.raises(HallmarkError, match="LIMIT_EXCEEDED"):
        check_registry(tmp_path, tmp_path, tmp_path, 150, history_paths=(tmp_path,) * 1025)


def test_schema_snapshots_and_golden_rotation() -> None:
    vector = json.loads((ROOT / "fixtures/wire/registry-rotation-v1.json").read_text())
    for name, cls in (
        ("registry-transition", RegistryTransition),
        ("signed-transition", SignedTransition),
    ):
        assert json.loads((ROOT / f"docs/schemas/{name}-v1.json").read_text()) == (
            cls.model_json_schema()
        )
    old, new, previous, current, transition = rotation()
    for name, obj in (
        ("old_trust", old),
        ("new_trust", new),
        ("previous", previous),
        ("snapshot", current),
        ("transition", transition),
    ):
        assert obj.encode().hex() == vector[name]["cbor_hex"]
        assert type(obj).decode(bytes.fromhex(vector[name]["cbor_hex"])) == obj
    for role in ("old", "new"):
        assert transition.body.signing_bytes(role).hex() == vector["signing_bytes"][role]
    assert vector["evidence_class"] == "public-fixture-keys"
