"""Policy resolution and explicit caller-expectation boundaries, using local fixtures."""

import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from hallmark.classifier_manifest import ClassifierManifest
from hallmark.errors import HallmarkError
from hallmark.manifests import ModelManifest
from hallmark.policy import ChainExpectation, Policy, Request, RequestExpectation
from hallmark.wire import WireError, decode, encode

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def vector() -> dict[str, Any]:
    return json.loads((ROOT / "fixtures/wire/policy-request-v1.json").read_text())


@pytest.fixture
def artifacts(vector: dict[str, Any]) -> tuple[Any, ...]:
    model = ModelManifest.decode(bytes.fromhex(vector["model_cbor_hex"]))
    classifiers = tuple(
        ClassifierManifest.decode(bytes.fromhex(raw)) for raw in vector["classifiers_cbor_hex"]
    )
    policy = Policy.decode(bytes.fromhex(vector["policy"]["cbor_hex"]))
    expected = RequestExpectation.decode(bytes.fromhex(vector["expectation"]["cbor_hex"]))
    request = Request.decode(bytes.fromhex(vector["request"]["cbor_hex"]))
    return model, classifiers, policy, expected, request


def test_fixed_vectors_and_snapshots(vector: dict[str, Any], artifacts: Any) -> None:
    model, classifiers, policy, expected, request = artifacts
    for name, obj in (("policy", policy), ("expectation", expected), ("request", request)):
        raw = bytes.fromhex(vector[name]["cbor_hex"])
        assert obj.encode() == raw
        assert type(obj).model_validate_json(obj.model_dump_json()) == obj
        snapshot_name = "request-expectation" if name == "expectation" else name
        assert type(obj).model_json_schema() == json.loads(
            (ROOT / f"docs/schemas/{snapshot_name}-v1.json").read_text()
        )
    tag = b"hallmark/v1/policy"
    raw = policy.encode()
    assert policy.identity().hex() == vector["policy"]["identity_hex"]
    assert hashlib.sha256(len(tag).to_bytes(4, "big") + tag + raw).digest() == policy.identity()
    assert not hasattr(expected, "identity") and not hasattr(request, "identity")
    policy.validate_classifiers(classifiers)
    request.validate_against(expected, model=model, policy=policy, classifiers=classifiers)


@pytest.mark.parametrize(
    "order", [order for order in itertools.permutations(range(3)) if order != (0, 1, 2)]
)
def test_reordered_classifiers_are_rejected_even_with_matching_digests(
    artifacts: Any, order: Any
) -> None:
    _, classifiers, policy, _, _ = artifacts
    reordered = tuple(classifiers[index] for index in order)
    with pytest.raises(WireError):
        policy.validate_classifiers(reordered)
    changed = policy.model_copy(
        update={"classifiers": tuple(item.identity() for item in reordered)}
    )
    assert changed.identity() != policy.identity()
    with pytest.raises(WireError):
        changed.validate_classifiers(reordered)


def test_duplicate_kinds_with_distinct_identities_are_rejected(artifacts: Any) -> None:
    _, classifiers, policy, _, _ = artifacts
    extra_rule = ClassifierManifest.model_validate(
        classifiers[0].model_dump() | {"program": b"\xff" * 32}
    )
    duplicated = (classifiers[0], extra_rule, classifiers[2])
    changed = policy.model_copy(
        update={"classifiers": tuple(item.identity() for item in duplicated)}
    )
    assert len(set(changed.classifiers)) == 3
    with pytest.raises(WireError):
        changed.validate_classifiers(duplicated)


def test_classifier_identity_and_shape_must_match(artifacts: Any) -> None:
    _, classifiers, policy, _, _ = artifacts
    changed = classifiers[1].model_copy(update={"threshold": classifiers[1].threshold + 1})
    with pytest.raises(WireError):
        policy.validate_classifiers((classifiers[0], changed, classifiers[2]))
    for supplied in (
        classifiers[:2],
        classifiers + (classifiers[0],),
        list(classifiers),
        (classifiers[0], None, classifiers[2]),
    ):
        with pytest.raises(WireError):
            policy.validate_classifiers(supplied)
    invalid = classifiers[1].model_copy(update={"scope": "response"})
    with pytest.raises(WireError):
        policy.validate_classifiers((classifiers[0], invalid, classifiers[2]))


@pytest.mark.parametrize(
    "field,bad",
    [
        ("combination", "any-pass"),
        ("language", "fr"),
        ("scope", "response"),
        ("max_prompt_bytes", -1),
        ("max_prompt_bytes", 32769),
        ("max_prompt_bytes", True),
        ("max_prompt_bytes", 1.0),
        ("max_response_bytes", -1),
        ("max_response_bytes", 32769),
        ("max_response_bytes", False),
        ("max_response_bytes", "1"),
        ("rubric", b"x" * 31),
        ("rubric", b"x" * 33),
        ("rubric", "00" * 32),
        ("classifiers", []),
        ("classifiers", [b"x" * 32] * 3),
        ("classifiers", [b"x" * 32] * 4),
    ],
)
def test_policy_rejections(artifacts: Any, field: str, bad: Any) -> None:
    value = decode(artifacts[2].encode())
    with pytest.raises(WireError):
        Policy.decode(encode(value | {field: bad}))


@pytest.mark.parametrize(
    "field,new",
    [
        ("rubric", b"\xff" * 32),
        ("max_prompt_bytes", 123),
        ("max_response_bytes", 234),
    ],
)
def test_policy_identity_fields(artifacts: Any, field: str, new: Any) -> None:
    policy = artifacts[2]
    assert (
        Policy.decode(encode(decode(policy.encode()) | {field: new})).identity()
        != policy.identity()
    )


@pytest.mark.parametrize("index", range(3))
def test_each_classifier_digest_is_bound(artifacts: Any, index: int) -> None:
    policy = artifacts[2]
    value = decode(policy.encode())
    value["classifiers"][index] = b"\xfe" * 32
    assert Policy.decode(encode(value)).identity() != policy.identity()


@pytest.mark.parametrize(
    "field,new",
    [
        ("audience", "another/auditor"),
        ("nonce", b"\xfe" * 32),
        ("interaction_id", b"\xfe" * 32),
        ("model", b"\xfe" * 32),
        ("policy", b"\xfe" * 32),
        ("continuity", {"sequence": 0, "previous": None}),
        ("continuity", {"sequence": 1, "previous": b"\xfe" * 32}),
    ],
)
def test_every_external_expectation_mismatch_is_rejected(
    artifacts: Any, field: str, new: Any
) -> None:
    model, classifiers, policy, expected, request = artifacts
    changed = RequestExpectation.decode(encode(decode(expected.encode()) | {field: new}))
    assert changed.encode() != expected.encode()
    with pytest.raises(HallmarkError) as error:
        request.validate_against(changed, model=model, policy=policy, classifiers=classifiers)
    assert (error.value.code, error.value.stage) == ("REQUEST_MISMATCH", "bind")
    with pytest.raises(HallmarkError, match="REQUEST_MISMATCH"):
        request.model_copy(update={"expected": changed}).validate_against(
            expected, model=model, policy=policy, classifiers=classifiers
        )


def test_external_expectation_and_artifacts_are_mandatory(artifacts: Any) -> None:
    model, classifiers, policy, expected, request = artifacts
    with pytest.raises(TypeError):
        request.validate_against(model=model, policy=policy, classifiers=classifiers)
    for supplied in (None, expected.model_dump(), expected.model_copy(update={"nonce": b"x"})):
        with pytest.raises(WireError):
            request.validate_against(supplied, model=model, policy=policy, classifiers=classifiers)
    for bad_model, bad_policy in ((None, policy), (model, None)):
        with pytest.raises(WireError):
            request.validate_against(
                expected, model=bad_model, policy=bad_policy, classifiers=classifiers
            )
    changed_model = model.model_copy(update={"runtime": b"\xff" * 32})
    changed_policy = policy.model_copy(update={"max_response_bytes": 0})
    for supplied_model, supplied_policy in ((changed_model, policy), (model, changed_policy)):
        with pytest.raises(HallmarkError, match="REQUEST_MISMATCH"):
            request.validate_against(
                expected, model=supplied_model, policy=supplied_policy, classifiers=classifiers
            )


@pytest.mark.parametrize("field", ["nonce", "interaction_id", "model", "policy"])
@pytest.mark.parametrize("bad", [b"x" * 31, b"x" * 33, "00" * 32, False])
def test_expectation_byte_fields(artifacts: Any, field: str, bad: Any) -> None:
    with pytest.raises(WireError):
        RequestExpectation.decode(encode(decode(artifacts[3].encode()) | {field: bad}))


@pytest.mark.parametrize("audience", ["", "a" * 129, "a b", "é", b"auditor"])
def test_audience_constraints(artifacts: Any, audience: Any) -> None:
    with pytest.raises(WireError):
        RequestExpectation.decode(encode(decode(artifacts[3].encode()) | {"audience": audience}))


@pytest.mark.parametrize("sequence,previous", [(0, None), (1, b"x" * 32), (2**64 - 1, b"x" * 32)])
def test_continuity_roundtrips_and_matches(artifacts: Any, sequence: int, previous: Any) -> None:
    model, classifiers, policy, expected, request = artifacts
    chain = ChainExpectation(sequence=sequence, previous=previous)
    expected = RequestExpectation.model_validate(expected.model_dump() | {"continuity": chain})
    request = Request.model_validate(request.model_dump() | {"expected": expected})
    request.validate_against(expected, model=model, policy=policy, classifiers=classifiers)
    assert Request.decode(request.encode()) == request
    if sequence:
        changed = expected.model_copy(
            update={"continuity": chain.model_copy(update={"previous": b"y" * 32})}
        )
        with pytest.raises(HallmarkError, match="REQUEST_MISMATCH"):
            request.validate_against(changed, model=model, policy=policy, classifiers=classifiers)


@pytest.mark.parametrize(
    "sequence,previous",
    [
        (0, b"x" * 32),
        (1, None),
        (-1, b"x" * 32),
        (2**64, b"x" * 32),
        (False, None),
        (True, b"x" * 32),
        (0.0, None),
        ("0", None),
        (1, b"x" * 31),
    ],
)
def test_invalid_continuity(sequence: Any, previous: Any) -> None:
    with pytest.raises(ValidationError):
        ChainExpectation(sequence=sequence, previous=previous)


@pytest.mark.parametrize("prompt", ["", "a" * 32768, "é" * 16384, "🙂" * 8192, " e\u0301\x00\r\n "])
def test_prompt_bytes_are_preserved(artifacts: Any, prompt: str) -> None:
    request = Request.model_validate(artifacts[4].model_dump() | {"prompt": prompt})
    assert Request.decode(request.encode()).prompt == prompt
    assert decode(request.encode())["prompt"].encode("utf-8") == prompt.encode("utf-8")


@pytest.mark.parametrize(
    "prompt", ["a" * 32769, "é" * 16385, "🙂" * 8193, "\ud800", b"hello", None]
)
def test_invalid_prompt(artifacts: Any, prompt: Any) -> None:
    with pytest.raises(ValidationError):
        Request.model_validate(artifacts[4].model_dump() | {"prompt": prompt})


@pytest.mark.parametrize(
    "cap,prompt,allowed",
    [
        (0, "", True),
        (0, "a", False),
        (2, "é", True),
        (1, "é", False),
        (4, "🙂", True),
        (3, "🙂", False),
    ],
)
def test_policy_byte_cap(artifacts: Any, cap: int, prompt: str, allowed: bool) -> None:
    model, classifiers, policy, expected, request = artifacts
    policy = policy.model_copy(update={"max_prompt_bytes": cap, "max_response_bytes": 0})
    expected = expected.model_copy(update={"policy": policy.identity()})
    request = Request.model_validate(
        request.model_dump() | {"prompt": prompt, "expected": expected}
    )
    if allowed:
        request.validate_against(expected, model=model, policy=policy, classifiers=classifiers)
    else:
        with pytest.raises(HallmarkError) as error:
            request.validate_against(expected, model=model, policy=policy, classifiers=classifiers)
        assert (error.value.code, error.value.stage) == ("LIMIT_EXCEEDED", "bind")


def test_exact_fields_versions_and_missing_expectations(artifacts: Any) -> None:
    for obj in artifacts[2:]:
        value = decode(obj.encode())
        for field in value:
            changed = {key: item for key, item in value.items() if key != field}
            with pytest.raises(WireError):
                type(obj).decode(encode(changed))
        for changed in (
            value | {"extra": "PRIVATE_SENTINEL"},
            value | {"schema_id": "hallmark/unknown/2"},
        ):
            with pytest.raises(WireError) as error:
                type(obj).decode(encode(changed))
            assert "PRIVATE_SENTINEL" not in str(error.value)
            assert error.value.__context__ is None
    with pytest.raises(WireError):
        Request.decode(encode(decode(artifacts[4].encode()) | {"expected": None}))


def test_nested_continuity_keys_are_required_and_exact(artifacts: Any) -> None:
    value = decode(artifacts[3].encode())
    for bad in (
        {},
        {"sequence": 0},
        {"previous": None},
        {"sequence": 0, "previous": None, "extra": 1},
    ):
        with pytest.raises(WireError):
            RequestExpectation.decode(encode(value | {"continuity": bad}))


def test_unchecked_copies_and_mutation(artifacts: Any) -> None:
    model, classifiers, policy, expected, request = artifacts
    invalid = [
        policy.model_copy(update={"max_prompt_bytes": False}),
        expected.model_copy(
            update={"continuity": ChainExpectation.model_construct(sequence=1, previous=None)}
        ),
        request.model_copy(update={"expected": expected.model_copy(update={"nonce": b"x"})}),
        request.model_copy(update={"prompt": "\ud800"}),
    ]
    for obj in invalid:
        with pytest.raises(WireError):
            obj.encode()
    with pytest.raises(WireError):
        invalid[0].identity()
    with pytest.raises(WireError):
        invalid[2].validate_against(expected, model=model, policy=policy, classifiers=classifiers)
    for obj, field, new in (
        (policy, "rubric", b"x" * 32),
        (expected, "audience", "changed"),
        (request, "prompt", "changed"),
        (request.expected, "nonce", b"x" * 32),
    ):
        with pytest.raises(ValidationError):
            setattr(obj, field, new)


def test_request_content_is_encoded_without_normalization(artifacts: Any) -> None:
    request = artifacts[4]
    composed = request.model_copy(update={"prompt": "é"})
    decomposed = request.model_copy(update={"prompt": "e\u0301"})
    assert composed.encode() != decomposed.encode()
    assert request.model_copy(update={"system_ref": b"\xff" * 32}).encode() != request.encode()
    with pytest.raises(WireError):
        Request.decode(encode(decode(request.encode()) | {"system_ref": b"x"}))


def test_prompt_repr_and_error_privacy(artifacts: Any) -> None:
    request = artifacts[4].model_copy(update={"prompt": "PRIVATE_PROMPT_SENTINEL"})
    assert "PRIVATE_PROMPT_SENTINEL" not in repr(request)
    raw = encode(decode(request.encode()) | {"system_ref": False})
    with pytest.raises(WireError) as error:
        Request.decode(raw)
    assert "PRIVATE_PROMPT_SENTINEL" not in str(error.value)
    assert error.value.__context__ is None


def test_validation_performs_no_io_or_nonce_consumption(
    artifacts: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("contract validation must not access files")

    monkeypatch.setattr(Path, "open", forbidden)
    model, classifiers, policy, expected, request = artifacts
    for _ in range(2):
        request.validate_against(expected, model=model, policy=policy, classifiers=classifiers)
