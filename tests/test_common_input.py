"""Composition boundaries; fake proof payloads test binding only, never cryptography."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import common_input as common

from hallmark._gnark_probe import digest
from hallmark.errors import HallmarkError
from hallmark.openings import TranscriptOpening
from hallmark.policy import RequestExpectation
from hallmark.receipts import ProofArtifact


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


@pytest.fixture(scope="module")
def fixture():
    enrollment = encoded(
        common.enroll({kind: bytes([i + 1]) * 5536 for i, kind in enumerate(common.KINDS)})
    )
    pin = digest(enrollment)
    records, policy = common.resolve(enrollment, pin)
    expected = RequestExpectation(
        schema_id="hallmark/request-expectation/1",
        audience="local-test",
        nonce=b"n" * 32,
        interaction_id=b"i" * 32,
        model=b"m" * 32,
        policy=policy.identity(),
        continuity=None,
    )
    opening = TranscriptOpening(
        schema_id="hallmark/transcript-opening/1",
        system_ref=b"s" * 32,
        prompt="okayxxxx",
        response="Synthetic response.",
        salt=b"t" * 32,
    )
    rows = common.evaluate(records, policy, opening, expected)
    value = common.bundle(records, policy, opening, expected, rows, [b"p" * 292] * 3)
    return enrollment, pin, records, policy, expected, opening, value


def test_native_all_pass_and_block_roster(fixture):
    enrollment, pin, records, policy, expected, opening, value = fixture
    jobs = common.check_bundle(enrollment, pin, opening, expected, encoded(value))
    assert len(jobs) == 3 and len({tuple(job["public"][:32]) for job in jobs}) == 1
    assert len({tuple(job["public"][64:96]) for job in jobs}) == 3
    assert [job["expected_key_sha256"] for job in jobs] == [digest(n["key"]) for n in records]
    for (name, prompt), verdicts in zip(
        common.CASES.items(), ((1, 1, 1), (0, 1, 1), (1, 0, 1)), strict=True
    ):
        rows = common.evaluate(
            records, policy, opening.model_copy(update={"prompt": prompt}), expected
        )
        assert tuple(row["public"][99] for row in rows) == verdicts, name


@pytest.mark.parametrize(
    "field,value",
    [
        ("prompt", "otherxxx"),
        ("response", "Different response"),
        ("salt", b"u" * 32),
        ("system_ref", b"r" * 32),
    ],
)
def test_opening_substitution(fixture, field, value):
    enrollment, pin, _, _, expected, opening, bundle = fixture
    with pytest.raises((ValueError, HallmarkError)):
        common.check_bundle(
            enrollment, pin, opening.model_copy(update={field: value}), expected, encoded(bundle)
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("audience", "another"),
        ("nonce", b"z" * 32),
        ("interaction_id", b"z" * 32),
        ("model", b"z" * 32),
        ("policy", b"z" * 32),
    ],
)
def test_request_substitution(fixture, field, value):
    enrollment, pin, _, _, expected, opening, bundle = fixture
    with pytest.raises((ValueError, HallmarkError)):
        common.check_bundle(
            enrollment, pin, opening, expected.model_copy(update={field: value}), encoded(bundle)
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "extra",
        "duplicate",
        "reorder",
        "release",
        "classifier",
        "backend",
        "key",
        "public",
        "oversize",
        "enrollment",
    ],
)
def test_composition_substitution(fixture, mutation):
    enrollment, pin, _, _, expected, opening, original = fixture
    value = copy.deepcopy(original)
    if mutation == "missing":
        value["proofs"].pop()
    elif mutation == "extra":
        value["proofs"].append(value["proofs"][0])
    elif mutation == "duplicate":
        value["proofs"][1] = value["proofs"][0]
    elif mutation == "reorder":
        value["proofs"].reverse()
    elif mutation == "release":
        value["release"] = False
    elif mutation == "classifier":
        value["proofs"][0]["classifier_cbor_hex"] = "00"
    elif mutation == "enrollment":
        pin = "0" * 64
    else:
        artifact = ProofArtifact.decode(bytes.fromhex(value["proofs"][0]["artifact_cbor_hex"]))
        update = {"backend": b"x" * 32} if mutation == "backend" else {"verifier_key": b"x" * 32}
        if mutation == "public":
            update = {
                "public_inputs": artifact.public_inputs.model_copy(update={"context": b"x" * 32})
            }
        elif mutation == "oversize":
            update = {"proof": b"p" * 293}
        value["proofs"][0]["artifact_cbor_hex"] = artifact.model_copy(update=update).encode().hex()
    with pytest.raises((ValueError, HallmarkError)):
        common.check_bundle(enrollment, pin, opening, expected, encoded(value))


@pytest.mark.parametrize("field", ["program", "circuit_sha256", "kind"])
def test_rehashed_wrong_program_enrollment(fixture, field):
    enrollment, _, *_ = fixture
    value = json.loads(enrollment)
    value["programs"][0][field] = "0" * 64
    raw = encoded(value)
    with pytest.raises(ValueError, match="program enrollment"):
        common.resolve(raw, digest(raw))


def test_byte_capacity_and_duplicate_json(fixture):
    enrollment, pin, records, policy, expected, opening, value = fixture
    with pytest.raises(ValueError, match="capacity"):
        common.evaluate(records, policy, opening.model_copy(update={"prompt": "é" * 5}), expected)
    raw = encoded(value)[:-1] + b',"release":true}'
    with pytest.raises(ValueError):
        common.check_bundle(enrollment, pin, opening, expected, raw)


@pytest.mark.parametrize(
    "field",
    ["backend", "setup", "verifier_key", "program", "arithmetic", "input_profile", "threshold"],
)
def test_well_formed_but_unenrolled_classifier(fixture, field):
    enrollment, pin, records, _, expected, opening, original = fixture
    value = copy.deepcopy(original)
    index = 1 if field == "threshold" else 0
    changed = records[index]["classifier"].model_copy(
        update={field: 3 if field == "threshold" else b"z" * 32}
    )
    value["proofs"][index]["classifier_cbor_hex"] = changed.encode().hex()
    with pytest.raises(ValueError, match="classifier enrollment"):
        common.check_bundle(enrollment, pin, opening, expected, encoded(value))


def test_cryptography_is_not_inferred_from_binding(fixture):
    enrollment, pin, _, _, expected, opening, original = fixture
    value = copy.deepcopy(original)
    artifact = ProofArtifact.decode(bytes.fromhex(value["proofs"][0]["artifact_cbor_hex"]))
    value["proofs"][0]["artifact_cbor_hex"] = (
        artifact.model_copy(update={"proof": b"q" * 292}).encode().hex()
    )
    jobs = common.check_bundle(enrollment, pin, opening, expected, encoded(value))
    assert jobs[0]["proof_hex"] == (b"q" * 292).hex()
    assert all("accepted" not in job and "qualified_backend" not in job for job in jobs)


def test_controller_rejects_wrong_host_before_opening_files(tmp_path, monkeypatch):
    import run_common_input as controller

    monkeypatch.setattr(controller.platform, "system", lambda: "Linux")
    with pytest.raises(ValueError, match="Mac host"):
        controller.run(tmp_path / "absent", "0" * 64, tmp_path / "python", tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_controller_rejects_wrong_binary_before_running_python(tmp_path, monkeypatch):
    import run_common_input as controller

    monkeypatch.setattr(controller.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(controller.platform, "machine", lambda: "arm64")
    binary = tmp_path / "binary"
    binary.write_bytes(b"untrusted fixture")
    with pytest.raises(ValueError, match="binary enrollment"):
        controller.run(binary, "0" * 64, tmp_path / "absent-python", tmp_path / "output")
    assert not (tmp_path / "output").exists()
