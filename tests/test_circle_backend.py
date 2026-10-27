"""Caller admission tests use fake roots/proofs and make no crypto claim."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import circle_backend as backend
import common_input as original
from classifier_comparison import encoded, sha


@pytest.fixture
def enrollment():
    old = encoded(
        original.enroll({kind: bytes([i + 1]) * 5536 for i, kind in enumerate(original.KINDS)})
    )
    records, policy = original.resolve(old, sha(old))
    engines = {
        kind: encoded(
            dict(
                schema="hallmark.circle-enrollment/1",
                external_multiplicities=[1] * 103,
                program_sha256=str(i) * 64,
            )
        )
        for i, kind in enumerate(backend.KINDS)
    }
    raw = backend.enroll(engines, records)
    return raw, records, policy, engines


def test_backend_identities_change_without_changing_native_programs(enrollment):
    raw, originals, old_policy, engines = enrollment
    records, policy, actual = backend.resolve(raw, sha(raw), originals, old_policy)
    assert actual == engines and policy.identity() != old_policy.identity()
    for before, after in zip(originals, records, strict=True):
        assert before["program"] == after["program"]
        assert before["input_profile"] == after["input_profile"]
        assert before["arithmetic"] == after["arithmetic"]
        assert before["classifier"].threshold == after["classifier"].threshold
        assert before["classifier"].identity() != after["classifier"].identity()


def test_caller_pin_and_native_program_admission(enrollment):
    raw, records, policy, engines = enrollment
    with pytest.raises(ValueError, match="pin mismatch"):
        backend.resolve(raw, "0" * 64, records, policy)
    changed = copy.deepcopy(records)
    changed[0]["program"] = records[1]["program"]
    with pytest.raises(ValueError, match="source/program/roster"):
        backend.resolve(raw, sha(raw), changed, policy)
    engines.pop("mlp")
    with pytest.raises(ValueError, match="roster"):
        backend.enroll(engines, records)


def test_enrollment_rejects_unbound_public_wires(enrollment):
    _, records, _, engines = enrollment
    engines["rule"] = encoded(
        dict(
            schema="hallmark.circle-enrollment/1",
            external_multiplicities=[1] * 102 + [0],
            program_sha256="0" * 64,
        )
    )
    with pytest.raises(ValueError, match="engine enrollment"):
        backend.enroll(engines, records)
