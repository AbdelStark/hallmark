"""Complete byte rules against an independent slice oracle and malformed exports."""

import hashlib
import json
import random
import re
import runpy
from pathlib import Path

import pytest
from pydantic import ValidationError

from hallmark.classifier_manifest import InputProfile
from hallmark.openings import TranscriptOpening, input_commitment
from hallmark.rule import MAX_PROVENANCE_BYTES, RuleProgram, RuleResult, execute_rule
from hallmark.wire import WireError

ROOT = Path(__file__).resolve().parents[1]
BUILDER = runpy.run_path(str(ROOT / "scripts/build_rule_fixture.py"))
export, oracle = BUILDER["export"], BUILDER["oracle"]


def profile(**changes):
    return InputProfile.model_validate(
        dict(
            schema_id="hallmark/input-profile/1",
            encoding="utf8-bytes",
            tokenizer_files=(),
            prefix_tokens=(),
            suffix_tokens=(),
            chunk_size=4,
            overlap=0,
            max_units=32768,
            padding_id=0,
            padding_side="right",
        )
        | changes
    )


def opening(text="", **changes):
    return TranscriptOpening.model_validate(
        dict(
            schema_id="hallmark/transcript-opening/1",
            system_ref=b"r" * 32,
            prompt=text,
            response="Unused response.",
            salt=b"t" * 32,
        )
        | changes
    )


def execute(artifacts, text="", **changes):
    classifier, program, inputs, arithmetic, provenance, parameters = artifacts
    return execute_rule(
        **(
            dict(
                opening=opening(text),
                classifier=classifier,
                program=program,
                inputs=inputs,
                arithmetic=arithmetic,
                provenance=provenance,
                parameters=parameters,
            )
            | changes
        )
    )


@pytest.mark.parametrize("size", [1, 2, 3, 4, 7, 511, 512])
@pytest.mark.parametrize(
    "text", ["", "mark", "xMARKy", "xéy", "xe\u0301y", "\0", "x" * 513 + "MARK"]
)
def test_boundaries_match_complete_byte_oracle(size, text):
    patterns = (b"\0", b"MARK", "é".encode())
    artifacts = export(patterns, profile(chunk_size=size))
    result = execute(artifacts, text)
    assert list(result.chunk_scores) == oracle(text, patterns, size)
    assert result.score == int(any(pattern in text.encode() for pattern in patterns))
    assert result.verdict == (result.score < 1)
    assert result.unit_count == len(text.encode())
    assert result.input_digest == input_commitment(opening(text), artifacts[0], artifacts[2])
    assert RuleResult.decode(result.encode()) == result


def test_seeded_programs_and_every_chunk_agree_with_slice_oracle():
    rng = random.Random(17)
    for _ in range(1000):
        text = "".join(chr(rng.randrange(8)) for _ in range(rng.randrange(80)))
        patterns = tuple(
            set(bytes(rng.randrange(8) for _ in range(rng.randrange(1, 12))) for _ in range(6))
        )
        size = rng.randrange(1, 12)
        result = execute(export(patterns, profile(chunk_size=size)), text)
        assert list(result.chunk_scores) == oracle(text, patterns, size)
        assert result.score == int(any(pattern in text.encode() for pattern in patterns))


def test_longest_pattern_spans_many_chunks_and_maximum_input_has_no_truncation():
    pattern = b"x" * 4095 + b"Y"
    result = execute(export((pattern,), profile(chunk_size=1)), "z" * 28672 + pattern.decode())
    assert result.unit_count == len(result.chunk_scores) == 32768
    assert sum(result.chunk_scores) == result.score == 1
    assert result.chunk_scores[-1] == 1
    assert result.verdict is False


def test_single_byte_pattern_does_not_retain_or_rematch_old_content():
    result = execute(export((b"A",), profile(chunk_size=1)), "AzzzA")
    assert result.chunk_scores == (1, 0, 0, 0, 1)


def test_short_matches_in_long_suffix_are_not_recounted_and_partial_utf8_bytes_match():
    patterns = (b"A", b"\xa9", b"zzzzzz")
    result = execute(export(patterns, profile(chunk_size=1)), "Aébb")
    assert result.chunk_scores == (1, 0, 1, 0, 0)


def test_padding_never_creates_matches_but_real_nul_does():
    for padding in (0, 65, 255):
        artifacts = export((b"\0", b"AA"), profile(padding_id=padding))
        assert execute(artifacts, "").score == execute(artifacts, "A").score == 0
        assert execute(artifacts, "\0").score == 1


def test_response_is_not_a_rule_input_and_late_bytes_are_bound():
    artifacts = export((b"MARK",), profile())
    a = execute(artifacts, "ordinary", opening=opening("ordinary", response="MARK"))
    b = execute(artifacts, "ordinary")
    assert a == b
    changed = execute(artifacts, "ordinaryX")
    assert changed.input_digest != b.input_digest


def test_oversize_profile_rejects_instead_of_truncating():
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        execute(export((b"MARK",), profile(max_units=3)), "xMARK")


@pytest.mark.parametrize(
    "patterns",
    [(), (b"",), (b"a", b"a"), (b"b", b"a"), (b"x" * 4097,), (b"x" * 2048, b"y" * 2049), ("a",)],
)
def test_invalid_pattern_lists_reject(patterns):
    program = export((b"a",), profile())[1]
    with pytest.raises(ValidationError):
        RuleProgram.model_validate(program.model_dump() | {"patterns": patterns})
    with pytest.raises(WireError, match="INPUT_INVALID"):
        execute(
            export((b"a",), profile()), program=program.model_copy(update={"patterns": patterns})
        )


@pytest.mark.parametrize(
    "field",
    ["classifier", "program", "input_profile", "arithmetic", "provenance", "parameters", "opening"],
)
def test_exact_types_and_missing_artifacts_reject(field):
    argument = "inputs" if field == "input_profile" else field
    with pytest.raises(WireError, match="INPUT_INVALID"):
        execute(export((b"a",), profile()), **{argument: None})


@pytest.mark.parametrize(
    "field", ["program", "input_profile", "arithmetic", "weights", "threshold"]
)
def test_unsafe_classifier_mutations_reject(field):
    artifacts = export((b"a",), profile())
    value = 0 if field == "threshold" else b"x" * 32
    changed = artifacts[0].model_copy(update={field: value})
    with pytest.raises(WireError, match="INPUT_INVALID"):
        execute(artifacts, classifier=changed)


@pytest.mark.parametrize("which", ["missing", "extra", "changed", "wrong-type"])
def test_parameter_inventory_and_exact_bytes_reject(which):
    artifacts = export((b"a",), profile())
    files = dict(artifacts[-1])
    if which == "missing":
        files.clear()
    elif which == "extra":
        files["unexpected"] = b""
    elif which == "changed":
        files["params/relu.cbor"] += b"\0"
    else:
        files["params/relu.cbor"] = bytearray(files["params/relu.cbor"])
    with pytest.raises(WireError, match="INPUT_INVALID"):
        execute(artifacts, parameters=files)


@pytest.mark.parametrize(
    "raw", [b"", b"changed", bytearray(b"x"), b"x" * (MAX_PROVENANCE_BYTES + 1)]
)
def test_provenance_is_required_bounded_and_byte_exact(raw):
    with pytest.raises(WireError):
        execute(export((b"a",), profile()), provenance=raw)


def test_rebound_arithmetic_cannot_change_the_boolean_projection():
    artifacts = export((b"a",), profile())
    classifier, program, inputs, arithmetic, provenance, parameters = artifacts
    for change in ({"signed_bits": 8}, {"fractional_bits": 1}, {"shape": (2,)}, {"minimum": -1}):
        altered = arithmetic.model_copy(
            update={"tensors": tuple(t.model_copy(update=change) for t in arithmetic.tensors)}
        )
        changed_program = program.model_copy(update={"arithmetic": altered.identity()})
        changed_classifier = classifier.model_copy(
            update={"arithmetic": altered.identity(), "program": changed_program.identity()}
        )
        with pytest.raises(WireError, match="INPUT_INVALID"):
            execute((changed_classifier, changed_program, inputs, altered, provenance, parameters))


def test_provenance_cannot_alias_operator_file():
    artifacts = export((b"a",), profile())
    program = artifacts[1].model_copy(
        update={
            "provenance": artifacts[1].provenance.model_copy(update={"path": "params/relu.cbor"})
        }
    )
    classifier = artifacts[0].model_copy(update={"program": program.identity()})
    with pytest.raises(WireError, match="INPUT_INVALID"):
        execute(artifacts, classifier=classifier, program=program)


@pytest.mark.parametrize(
    "changes",
    [
        {"chunk_scores": ()},
        {"chunk_scores": (1,)},
        {"chunk_scores": (0, 0, 0)},
        {"chunk_scores": (True, 0)},
        {"score": 2},
        {"score": 0},
        {"threshold": 0},
        {"threshold": True},
        {"verdict": True},
        {"unit_count": 0},
    ],
)
def test_incomplete_or_inconsistent_results_reject(changes):
    result = execute(export((b"A",), profile(chunk_size=1)), "Az")
    with pytest.raises(ValidationError):
        RuleResult.model_validate(result.model_dump() | changes)


def test_program_json_schema_covers_the_maximum_hex_encoded_pattern():
    program = export((b"x" * 4096,), profile())[1]
    raw = program.model_dump_json()
    assert RuleProgram.model_validate_json(raw) == program
    value = json.loads(raw)
    encoded = value["patterns"][0]
    schema = RuleProgram.model_json_schema()["properties"]["patterns"]["items"]
    assert schema["minLength"] <= len(encoded) <= schema["maxLength"]
    assert re.fullmatch(schema["pattern"], encoded)
    value["patterns"] = ["f"]
    assert not re.fullmatch(schema["pattern"], "f")
    with pytest.raises(ValidationError):
        RuleProgram.model_validate_json(json.dumps(value))


def test_fixed_fixture_and_schemas_reproduce_and_installed_checker_runs(monkeypatch):
    vector = json.loads((ROOT / "fixtures/wire/rule-v1.json").read_text())
    assert BUILDER["build"]() == vector
    assert vector["fixture_only"] is True
    for cls, name in ((RuleProgram, "rule-program"), (RuleResult, "rule-result")):
        assert cls.model_json_schema() == json.loads(
            (ROOT / f"docs/schemas/{name}-v1.json").read_text()
        )
    check = runpy.run_path(str(ROOT / "scripts/check_rule_vectors.py"))["check"]
    check(ROOT / "fixtures/wire/rule-v1.json")
    artifacts = export((b"A",), profile())

    def forbidden(*args, **kwargs):
        raise AssertionError("native execution must not open files or use the network")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    assert execute(artifacts, "A").score == 1
    assert hashlib.sha256(artifacts[4]).digest() == artifacts[1].provenance.sha256
