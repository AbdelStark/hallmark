"""V1 opening hashes and complete-input boundaries; no hardware or tokenizer trust."""

import hashlib
import json
from pathlib import Path
from typing import Any

import cbor2
import pytest
from pydantic import ValidationError

from hallmark.classifier_manifest import ClassifierManifest, InputProfile
from hallmark.errors import HallmarkError
from hallmark.integrity import transcript_commitment
from hallmark.openings import TranscriptOpening, derive_input_salt, input_commitment
from hallmark.policy import RequestExpectation
from hallmark.wire import WireError, decode, encode

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def vectors() -> dict[str, Any]:
    return json.loads((ROOT / "fixtures/wire/openings-v1.json").read_text())


@pytest.fixture
def artifacts(vectors: Any) -> tuple[Any, ...]:
    opening = TranscriptOpening.decode(bytes.fromhex(vectors["cases"][1]["opening"]["cbor_hex"]))
    expected = RequestExpectation.decode(bytes.fromhex(vectors["expected"]["cbor_hex"]))
    classifiers = {
        name: ClassifierManifest.decode(bytes.fromhex(record["cbor_hex"]))
        for name, record in vectors["classifiers"].items()
    }
    profiles = {
        name: InputProfile.decode(bytes.fromhex(record["cbor_hex"]))
        for name, record in vectors["profiles"].items()
    }
    return opening, expected, classifiers, profiles


def oracle(domain: str, value: Any) -> bytes:
    tag = ("hallmark/v1/" + domain).encode("ascii")
    return hashlib.sha256(
        len(tag).to_bytes(4, "big") + tag + cbor2.dumps(value, canonical=True)
    ).digest()


def test_fixed_vectors_and_schema(vectors: Any, artifacts: Any) -> None:
    _, expected, classifiers, profiles = artifacts
    assert TranscriptOpening.model_json_schema() == json.loads(
        (ROOT / "docs/schemas/transcript-opening-v1.json").read_text()
    )
    for case in vectors["cases"]:
        opening = TranscriptOpening.decode(bytes.fromhex(case["opening"]["cbor_hex"]))
        assert opening.encode().hex() == case["opening"]["cbor_hex"]
        assert json.loads(opening.model_dump_json()) == case["opening"]["json"]
        assert TranscriptOpening.model_validate_json(opening.model_dump_json()) == opening
        transcript = [
            opening.system_ref,
            opening.salt,
            opening.prompt.encode("utf-8"),
            opening.response.encode("utf-8"),
        ]
        assert encode(transcript).hex() == case["transcript_preimage_cbor_hex"]
        assert opening.commitment() == oracle("transcript", transcript)
        assert opening.commitment().hex() == case["transcript_hex"]
        opening.verify_commitment(bytes.fromhex(case["transcript_hex"]))
        context = [decode(expected.encode()), opening.commitment()]
        assert encode(context).hex() == case["context_preimage_cbor_hex"]
        assert opening.context(expected) == oracle("context", context)
        assert opening.context(expected).hex() == case["context_hex"]
        for item in case["inputs"]:
            classifier, profile = classifiers[item["classifier"]], profiles[item["profile"]]
            units = tuple(int(unit) for unit in item["units_decimal"])
            vocab = item["vocabulary_size_decimal"]
            supplied = (
                {"token_units": units, "vocabulary_size": int(vocab)} if vocab is not None else {}
            )
            salt_preimage = [opening.salt, classifier.identity()]
            salt = derive_input_salt(*salt_preimage)
            assert salt == oracle("input-salt", salt_preimage)
            assert encode(salt_preimage).hex() == item["salt_preimage_cbor_hex"]
            assert salt.hex() == item["salt_hex"]
            preimage = [salt, profile.identity(), len(units), list(units)]
            assert encode(preimage).hex() == item["input_preimage_cbor_hex"]
            digest = input_commitment(opening, classifier, profile, **supplied)
            assert digest == oracle("input", preimage)
            assert digest.hex() == item["digest_hex"]


@pytest.mark.parametrize(
    "field,new",
    [("prompt", "e\u0301"), ("response", "ok"), ("system_ref", b"x" * 32), ("salt", b"x" * 32)],
)
def test_every_opening_field_is_bound(artifacts: Any, field: str, new: Any) -> None:
    opening, expected, _, _ = artifacts
    changed = opening.model_copy(update={field: new})
    assert changed.commitment() != opening.commitment()
    assert changed.context(expected) != opening.context(expected)
    with pytest.raises(HallmarkError) as error:
        changed.verify_commitment(opening.commitment())
    assert (error.value.code, error.value.stage) == ("OPENING_FAILED", "bind")


def test_role_boundaries_and_v0_are_distinct(artifacts: Any) -> None:
    opening = artifacts[0]
    variants = [
        opening.model_copy(update={"prompt": prompt, "response": response})
        for prompt, response in (("ab", "c"), ("a", "bc"), ("c", "ab"))
    ]
    assert len({item.commitment() for item in variants}) == 3
    for item in variants:
        assert item.commitment().hex() != transcript_commitment(
            item.prompt, item.response, item.salt, item.system_ref
        )
    assert transcript_commitment("ab", "c", bytes(32)) == (
        "2a6c50c687495a59b064f7680a323cf4c221b888d1e796ea0b24e94cf727a451"
    )


@pytest.mark.parametrize(
    "field,new",
    [
        ("audience", "other/auditor"),
        ("nonce", b"x" * 32),
        ("interaction_id", b"x" * 32),
        ("model", b"x" * 32),
        ("policy", b"x" * 32),
        ("continuity", {"sequence": 0, "previous": None}),
        ("continuity", {"sequence": 1, "previous": b"x" * 32}),
        ("continuity", {"sequence": 2, "previous": b"y" * 32}),
    ],
)
def test_every_context_expectation_is_bound(artifacts: Any, field: str, new: Any) -> None:
    opening, expected, _, _ = artifacts
    changed = RequestExpectation.model_validate(expected.model_dump() | {field: new})
    assert opening.context(changed) != opening.context(expected)


@pytest.mark.parametrize("text", ["", "a" * 32768, "é" * 16384, "🙂" * 8192, " \x00\r\ne\u0301 "])
@pytest.mark.parametrize("field", ["prompt", "response"])
def test_exact_text_bytes_roundtrip(artifacts: Any, field: str, text: str) -> None:
    opening = TranscriptOpening.model_validate(artifacts[0].model_dump() | {field: text})
    assert getattr(TranscriptOpening.decode(opening.encode()), field) == text
    assert len(opening.commitment()) == 32


@pytest.mark.parametrize("text", ["a" * 32769, "é" * 16385, "🙂" * 8193, "\ud800", b"x", 1, None])
@pytest.mark.parametrize("field", ["prompt", "response"])
def test_invalid_or_oversize_text(artifacts: Any, field: str, text: Any) -> None:
    with pytest.raises(ValidationError):
        TranscriptOpening.model_validate(artifacts[0].model_dump() | {field: text})
    with pytest.raises(WireError):
        artifacts[0].model_copy(update={field: text}).commitment()


@pytest.mark.parametrize("bad", [None, b"x" * 31, b"x" * 33, "00" * 32, bytearray(32), False])
def test_digest_and_salt_boundaries(artifacts: Any, bad: Any) -> None:
    opening, _, classifiers, _ = artifacts
    for salt, classifier in ((bad, classifiers["rule"].identity()), (opening.salt, bad)):
        with pytest.raises(WireError):
            derive_input_salt(salt, classifier)
    with pytest.raises(WireError):
        opening.verify_commitment(bad)
    for field in ("salt", "system_ref"):
        with pytest.raises(WireError):
            opening.model_copy(update={field: bad}).commitment()


def test_required_fields_versions_and_private_diagnostics(artifacts: Any) -> None:
    opening, expected, _, _ = artifacts
    opening = opening.model_copy(
        update={"prompt": "PRIVATE_PROMPT", "response": "PRIVATE_RESPONSE", "salt": b"s" * 32}
    )
    assert all(
        value not in repr(opening) for value in ("PRIVATE_PROMPT", "PRIVATE_RESPONSE", "sss")
    )
    value = decode(opening.encode())
    invalid = [{key: item for key, item in value.items() if key != missing} for missing in value]
    invalid += [value | {"extra": "PRIVATE_EXTRA"}, value | {"schema_id": "hallmark/transcript/0"}]
    for changed in invalid:
        with pytest.raises(WireError) as error:
            TranscriptOpening.decode(encode(changed))
        assert error.value.__context__ is None
        assert "PRIVATE_" not in str(error.value)
    for bad in (None, expected.model_dump(), expected.model_copy(update={"nonce": b"x"})):
        with pytest.raises(WireError):
            opening.context(bad)
    with pytest.raises(TypeError):
        opening.context()
    for field in ("prompt", "response", "salt", "system_ref"):
        with pytest.raises(ValidationError):
            setattr(opening, field, getattr(opening, field))


def test_complete_bytes_are_derived_and_counted_without_truncation(artifacts: Any) -> None:
    opening, _, classifiers, profiles = artifacts
    classifier, profile = classifiers["mlp"], profiles["bytes"]
    for prompt in ("", "é", "a" * 32767 + "!", "a" * 32768):
        changed = opening.model_copy(update={"prompt": prompt})
        units = list(prompt.encode("utf-8"))
        assert input_commitment(changed, classifier, profile) == oracle(
            "input",
            [
                derive_input_salt(changed.salt, classifier.identity()),
                profile.identity(),
                len(units),
                units,
            ],
        )
    tail = opening.model_copy(update={"prompt": "a" * 32767 + "!"})
    before = tail.model_copy(update={"prompt": "a" * 32768})
    assert input_commitment(tail, classifier, profile) != input_commitment(
        before, classifier, profile
    )
    assert input_commitment(opening, classifiers["rule"], profile) != input_commitment(
        opening, classifier, profile
    )
    for kwargs in ({"token_units": ()}, {"vocabulary_size": 256}):
        with pytest.raises(WireError):
            input_commitment(opening, classifier, profile, **kwargs)


def test_prompt_only_content_but_full_context(artifacts: Any) -> None:
    opening, expected, classifiers, profiles = artifacts
    for field, value in (("response", "changed"), ("system_ref", b"x" * 32)):
        changed = opening.model_copy(update={field: value})
        assert input_commitment(
            changed, classifiers["rule"], profiles["bytes"]
        ) == input_commitment(opening, classifiers["rule"], profiles["bytes"])
        assert changed.context(expected) != opening.context(expected)


def test_profile_classifier_and_opening_salt_bind_inputs(artifacts: Any) -> None:
    opening, _, classifiers, profiles = artifacts
    classifier, profile = classifiers["mlp"], profiles["bytes"]
    digest = input_commitment(opening, classifier, profile)
    changed_profile = profile.model_copy(update={"chunk_size": profile.chunk_size + 1})
    with pytest.raises(WireError):
        input_commitment(opening, classifier, changed_profile)
    changed_classifier = classifier.model_copy(update={"input_profile": changed_profile.identity()})
    assert input_commitment(opening, changed_classifier, changed_profile) != digest
    changed_classifier = classifier.model_copy(update={"threshold": classifier.threshold + 1})
    assert input_commitment(opening, changed_classifier, profile) != digest
    assert (
        input_commitment(opening.model_copy(update={"salt": b"x" * 32}), classifier, profile)
        != digest
    )


@pytest.mark.parametrize("size", [None, 0, -1, True, 3.0, "3", 2**64 + 1])
def test_explicit_vocabulary_bound(artifacts: Any, size: Any) -> None:
    opening, _, classifiers, profiles = artifacts
    with pytest.raises(WireError):
        input_commitment(
            opening,
            classifiers["encoder"],
            profiles["tokens"],
            token_units=(),
            vocabulary_size=size,
        )


@pytest.mark.parametrize("units", [None, [], [1], b"\x01", (True,), (-1,), (3,), (1.0,), ("1",)])
def test_token_types_and_bounds(artifacts: Any, units: Any) -> None:
    opening, _, classifiers, profiles = artifacts
    with pytest.raises(WireError):
        input_commitment(
            opening,
            classifiers["encoder"],
            profiles["tokens"],
            token_units=units,
            vocabulary_size=3,
        )


def test_token_tail_count_order_and_padding_recipe(artifacts: Any) -> None:
    opening, _, classifiers, profiles = artifacts
    classifier, profile = classifiers["encoder"], profiles["tokens"]
    digests = {
        input_commitment(opening, classifier, profile, token_units=units, vocabulary_size=2**64)
        for units in ((), (0,), (0, 1), (1, 0), (0, 1, 2**64 - 1), (0, 1, 2**64 - 2))
    }
    assert len(digests) == 6
    # Special and padding tokens also need to fit the independently supplied vocabulary.
    for field, value in (("prefix_tokens", (3,)), ("suffix_tokens", (3,)), ("padding_id", 3)):
        bad = profile.model_copy(update={field: value})
        matched = classifier.model_copy(update={"input_profile": bad.identity()})
        with pytest.raises(WireError):
            input_commitment(opening, matched, bad, token_units=(), vocabulary_size=3)


@pytest.mark.parametrize("encoding,kind", [("bytes", "mlp"), ("tokens", "encoder")])
def test_profile_capacity_never_truncates(artifacts: Any, encoding: str, kind: str) -> None:
    opening, _, classifiers, profiles = artifacts
    profile = profiles[encoding].model_copy(update={"max_units": 1})
    classifier = classifiers[kind].model_copy(update={"input_profile": profile.identity()})
    kwargs = {"token_units": (0, 1), "vocabulary_size": 3} if kind == "encoder" else {}
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        input_commitment(opening, classifier, profile, **kwargs)
    if kind == "encoder":
        maximum = (0,) * 32768
        assert (
            len(
                input_commitment(
                    opening,
                    classifiers[kind],
                    profiles[encoding],
                    token_units=maximum,
                    vocabulary_size=3,
                )
            )
            == 32
        )
        with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
            input_commitment(
                opening,
                classifiers[kind],
                profiles[encoding],
                token_units=maximum + (0,),
                vocabulary_size=3,
            )


def test_invalid_types_and_unchecked_contracts(artifacts: Any) -> None:
    opening, _, classifiers, profiles = artifacts
    classifier, profile = classifiers["mlp"], profiles["bytes"]
    for values in (
        (None, classifier, profile),
        (opening, None, profile),
        (opening, classifier, None),
        (opening.model_copy(update={"salt": b"x"}), classifier, profile),
        (opening, classifier.model_copy(update={"scope": "response"}), profile),
        (opening, classifier, profile.model_copy(update={"max_units": True})),
        (
            opening,
            classifiers["encoder"].model_copy(update={"input_profile": profile.identity()}),
            profile,
        ),
    ):
        with pytest.raises(WireError):
            input_commitment(*values)

    def forbidden_generator() -> Any:
        pytest.fail("unbounded iterables must not be consumed")
        yield 1

    with pytest.raises(WireError):
        input_commitment(
            opening,
            classifiers["encoder"],
            profiles["tokens"],
            token_units=forbidden_generator(),
            vocabulary_size=3,
        )


def test_hash_reconstruction_requires_no_io_or_hardware(
    artifacts: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("opening reconstruction must not access files or hardware")

    monkeypatch.setattr(Path, "open", forbidden)
    opening, expected, classifiers, profiles = artifacts
    opening.verify_commitment(opening.commitment())
    assert len(opening.context(expected)) == 32
    assert len(input_commitment(opening, classifiers["mlp"], profiles["bytes"])) == 32
