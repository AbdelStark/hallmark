"""Complete synthetic encoder traces, independent tables, coverage and bindings."""

import hashlib
import itertools
import json
import runpy
from decimal import Decimal, localcontext
from pathlib import Path

import pytest
from pydantic import ValidationError

from hallmark.integer_encoder import EncoderConstants, EncoderResult, execute_encoder
from hallmark.integer_graph import IntegerGraph
from hallmark.openings import input_commitment
from hallmark.wire import WireError

ROOT = Path(__file__).resolve().parents[1]
BUILDER = runpy.run_path(str(ROOT / "scripts/build_encoder_fixture.py"))


@pytest.fixture(scope="module")
def artifacts():
    return BUILDER["export"]()


def execute(artifacts, text="", **changes):
    classifier, program, inputs, arithmetic, weights, tokenizer, parameters = artifacts
    args = dict(
        opening=BUILDER["opening"](text),
        classifier=classifier,
        program=program,
        inputs=inputs,
        arithmetic=arithmetic,
        weights=weights,
        tokenizer=tokenizer,
        parameters=parameters,
    )
    return execute_encoder(**(args | changes))


def test_fixture_reproduction_and_installed_checker():
    path = ROOT / "fixtures/wire/integer-encoder-v1.json"
    assert json.dumps(BUILDER["build"](), indent=2, sort_keys=True) + "\n" == path.read_text()
    pin = (ROOT / "fixtures/wire/integer-encoder-v1.sha256").read_text().strip()
    checker = runpy.run_path(str(ROOT / "scripts/check_encoder_vectors.py"))["check"]
    result = checker(path, pin)
    assert result["cases"] == 8 and result["tensors"] == 546 and not result["qualified_backend"]
    with pytest.raises(ValueError):
        checker(path, "0" * 64)


def test_all_embedding_classes_and_masks(artifacts):
    constants = EncoderConstants.decode(artifacts[4]).tensors
    assert constants["embedding-table"] == tuple(
        x for b in range(256) for x in BUILDER["EMBEDDING"][b % 4]
    )
    graph = IntegerGraph(artifacts[3], parameters=artifacts[6], constants=constants)
    for a, b, ma, mb in itertools.product(range(4), range(4), range(2), range(2)):
        actual = graph.evaluate({"tokens": (a, b), "mask": (ma, mb)})
        assert actual == BUILDER["oracle"]((a, b), (ma, mb), artifacts[3])
        for i, mask in enumerate((ma, mb)):
            if not mask:
                for replacement in range(4):
                    tokens = [a, b]
                    tokens[i] = replacement
                    assert (
                        graph.evaluate({"tokens": tuple(tokens), "mask": (ma, mb)})["score"]
                        == actual["score"]
                    )


def test_every_normalization_table_entry_against_decimal(artifacts):
    constants = EncoderConstants.decode(artifacts[4]).tensors
    specs = {t.name: t for t in artifacts[3].tensors}
    with localcontext() as ctx:
        ctx.prec = 80
        for name, source in (("norm1", "residual"), ("norm2", "residual2")):
            lo, hi = specs[source].minimum, specs[source].maximum
            width = hi - lo + 1
            table = constants[name + "-table"]
            for a, b in itertools.product(range(lo, hi + 1), repeat=2):
                mean = int((Decimal(a + b) / 2).to_integral_value())
                left, right = a - mean, b - mean
                variance = int((Decimal(left * left + right * right) / 2).to_integral_value())
                inv = int((Decimal(256) / Decimal(variance + 1).sqrt()).to_integral_value())
                pos = (a - lo) * width + b - lo
                assert table[pos] == left * inv + 256
                assert table[pos + width * width] == -2 * right * inv - 256


@pytest.mark.parametrize("text", ["", "A", "AB", "ABC", "é🙂", "\x00A\r\nB"])
def test_full_input_commitment_and_threshold(artifacts, text):
    result = execute(artifacts, text)
    assert tuple(
        n for c in result.chunks for n, m in zip(c.tokens, c.mask, strict=True) if m
    ) == tuple(text.encode())
    assert result.input_digest == input_commitment(
        BUILDER["opening"](text),
        artifacts[0],
        artifacts[2],
        token_units=tuple(text.encode()),
        vocabulary_size=256,
    )
    assert result.score == max(c.score for c in result.chunks)
    for threshold, verdict in (
        (result.score, False),
        (result.score + 1, True),
        (result.score - 1, False),
    ):
        candidate = artifacts[0].model_copy(update={"threshold": threshold})
        assert execute(artifacts, text, classifier=candidate).verdict is verdict


@pytest.mark.parametrize("prefix,suffix", [((65,), ()), ((), (66,))])
def test_special_tokens_every_chunk_and_empty(prefix, suffix):
    artifacts = BUILDER["export"](prefix=prefix, suffix=suffix)
    for text in ("", "éA"):
        result = execute(artifacts, text)
        raw = text.encode()
        assert len(result.chunks) == max(1, len(raw))
        for i, c in enumerate(result.chunks):
            active = prefix + tuple(raw[i : i + 1]) + suffix
            assert c.tokens == active + (0,) * (2 - len(active))
            assert c.mask == (1,) * len(active) + (0,) * (2 - len(active))
            assert c.tensors == BUILDER["oracle"](c.tokens, c.mask, artifacts[3])


def test_actual_padding_rebinding_does_not_change_score(artifacts):
    changed = BUILDER["export"](padding=65)
    for text in ("", "A", "éA"):
        original, rebound = execute(artifacts, text), execute(changed, text)
        assert original.score == rebound.score
        assert original.input_digest != rebound.input_digest


@pytest.mark.parametrize(
    "what", ["weights", "tokenizer", "parameter", "program", "classifier", "input", "arithmetic"]
)
def test_changed_bindings_reject(artifacts, what):
    classifier, program, inputs, arithmetic, weights, tokenizer, parameters = artifacts
    changes = {
        "weights": dict(weights=weights + b"\x00"),
        "tokenizer": dict(tokenizer=tokenizer + b"\n"),
        "parameter": dict(parameters={k: v + b"\x00" for k, v in parameters.items()}),
        "program": dict(program=program.model_copy(update={"token_input": "mask"})),
        "classifier": dict(classifier=classifier.model_copy(update={"arithmetic": b"x" * 32})),
        "input": dict(inputs=inputs.model_copy(update={"padding_id": 1})),
        "arithmetic": dict(arithmetic=arithmetic.model_copy(update={"output": "norm2"})),
    }
    with pytest.raises(WireError):
        execute(artifacts, **changes[what])


def test_unknown_tokenizer_even_with_rehashed_files_rejects(artifacts):
    classifier, program, inputs, *_ = artifacts
    raw = artifacts[5].replace(b"byte-values", b"other-ids!!")
    ref = program.tokenizer.model_copy(
        update={"size": len(raw), "sha256": hashlib.sha256(raw).digest()}
    )
    inputs = inputs.model_copy(update={"tokenizer_files": (ref,)})
    program = program.model_copy(update={"tokenizer": ref, "input_profile": inputs.identity()})
    classifier = classifier.model_copy(
        update={
            "tokenizer": ref.sha256,
            "program": program.identity(),
            "input_profile": inputs.identity(),
        }
    )
    with pytest.raises(WireError):
        execute(artifacts, tokenizer=raw, classifier=classifier, program=program, inputs=inputs)


def test_omitted_tail_and_nonprefix_mask_result_reject(artifacts):
    result = execute(artifacts, "ABCDE")
    for changes in (
        {"chunks": result.chunks[:-1]},
        {"unit_count": 2},
        {"score": result.score + 1},
        {"verdict": not result.verdict},
        {"chunks": (result.chunks[0].model_copy(update={"mask": (0, 1)}), *result.chunks[1:])},
    ):
        with pytest.raises(ValidationError):
            EncoderResult.model_validate(result.model_copy(update=changes))


def test_maximum_length_and_late_tail(artifacts):
    for size in (32767, 32768):
        text = "x" * (size - 1) + "A"
        result = execute(artifacts, text)
        assert result.unit_count == size and len(result.chunks) == 16384
        assert sum(c.unit_count for c in result.chunks) == size
        assert result.chunks[-1].tokens[result.chunks[-1].unit_count - 1] == 65
        for c in result.chunks:
            assert c.tensors["score"] == BUILDER["oracle"](c.tokens, c.mask, artifacts[3])["score"]
    with pytest.raises(ValidationError):
        execute(artifacts, "x" * 32769)
    small = artifacts[2].model_copy(update={"max_units": 4})
    program = artifacts[1].model_copy(update={"input_profile": small.identity()})
    classifier = artifacts[0].model_copy(
        update={"program": program.identity(), "input_profile": small.identity()}
    )
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        execute(artifacts, "ABCDE", inputs=small, program=program, classifier=classifier)


def test_late_chunk_can_change_the_verdict(artifacts):
    prefix, complete = execute(artifacts, "AB"), execute(artifacts, "ABAA")
    assert prefix.score < complete.score
    classifier = artifacts[0].model_copy(update={"threshold": complete.score})
    assert execute(artifacts, "AB", classifier=classifier).verdict
    assert not execute(artifacts, "ABAA", classifier=classifier).verdict


def test_schema_snapshots():
    from hallmark.integer_encoder import EncoderProgram

    for name, cls in (
        ("program", EncoderProgram),
        ("constants", EncoderConstants),
        ("result", EncoderResult),
    ):
        assert (
            json.loads((ROOT / f"docs/schemas/encoder-{name}-v1.json").read_text())
            == cls.model_json_schema()
        )


@pytest.mark.parametrize("kind", ["missing", "extra", "boolean", "range", "length"])
def test_rehashed_constants_still_obey_graph_contract(artifacts, kind):
    values = EncoderConstants.decode(artifacts[4]).model_dump(mode="python")
    constants = values["tensors"]
    if kind == "missing":
        del constants["ones"]
    elif kind == "extra":
        constants["unexpected"] = (0,)
    elif kind == "boolean":
        constants["ones"] = (True,)
    elif kind == "range":
        constants["ones"] = (2,)
    else:
        constants["ones"] = (1, 1)
    from hallmark.wire import encode

    # Encode canonical malformed values without the constant schema rejecting them first.
    values["tensors"] = {k: list(v) for k, v in constants.items()}
    raw = encode(values)
    ref = artifacts[1].weights.model_copy(
        update={"size": len(raw), "sha256": hashlib.sha256(raw).digest()}
    )
    program = artifacts[1].model_copy(update={"weights": ref})
    classifier = artifacts[0].model_copy(
        update={"weights": ref.sha256, "program": program.identity()}
    )
    with pytest.raises(WireError):
        execute(artifacts, weights=raw, program=program, classifier=classifier)


def test_prepared_graph_keeps_validated_constants(artifacts):
    constants = EncoderConstants.decode(artifacts[4]).tensors
    parameters = artifacts[6].copy()
    graph = IntegerGraph(artifacts[3], parameters=parameters, constants=constants)
    expected = graph.evaluate({"tokens": (65, 66), "mask": (1, 1)})
    constants["ones"] = (2,)
    parameters.clear()
    assert graph.evaluate({"tokens": (65, 66), "mask": (1, 1)}) == expected


def test_private_result_roundtrip(artifacts):
    result = execute(artifacts, "ABé")
    assert EncoderResult.decode(result.encode()) == result
    assert EncoderResult.model_validate_json(result.model_dump_json()) == result
