"""Exact native layers against byte-sum/division formulas; no proof or quality evidence."""

import hashlib
import json
import random
import runpy
import socket
from pathlib import Path

import cbor2
import pytest
from pydantic import ValidationError

from hallmark.classifier_manifest import InputProfile
from hallmark.integer_mlp import (
    I32_MAX,
    I32_MIN,
    MAX_CHUNKS,
    MAX_PRODUCTS,
    MlpProgram,
    MlpResult,
    MlpWeights,
    execute_mlp,
)
from hallmark.manifests import ArtifactDigest
from hallmark.openings import TranscriptOpening, input_commitment
from hallmark.wire import WireError

ROOT = Path(__file__).resolve().parents[1]
BUILDER = runpy.run_path(str(ROOT / "scripts/build_mlp_fixture.py"))
export = BUILDER["export"]
formula = BUILDER["formula"]


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
            max_units=4096,
            padding_id=65,
            padding_side="right",
        )
        | changes
    )


def weights(width=1, **changes):
    return MlpWeights.model_validate(
        dict(
            schema_id="hallmark/mlp-weights/1",
            hidden_weights=tuple((0,) * 256 for _ in range(width)),
            hidden_bias=(0,) * width,
            output_weights=(1,) * width,
            output_bias=0,
        )
        | changes
    )


def opening(text="", **changes):
    return TranscriptOpening.model_validate(
        dict(
            schema_id="hallmark/transcript-opening/1",
            system_ref=b"r" * 32,
            prompt=text,
            response="Harmless response.",
            salt=b"t" * 32,
        )
        | changes
    )


def execute(artifacts, text="", **changes):
    classifier, program, inputs, arithmetic, raw, parameters = artifacts
    arguments = dict(
        opening=opening(text),
        classifier=classifier,
        program=program,
        inputs=inputs,
        arithmetic=arithmetic,
        weights=raw,
        parameters=parameters,
    )
    return execute_mlp(**(arguments | changes))


def rebind(artifacts, *, raw=None, inputs=None, arithmetic=None):
    classifier, program, old_inputs, old_arithmetic, old_raw, parameters = artifacts
    raw = old_raw if raw is None else raw
    inputs = old_inputs if inputs is None else inputs
    arithmetic = old_arithmetic if arithmetic is None else arithmetic
    ref = program.weights.model_copy(
        update={"size": len(raw), "sha256": hashlib.sha256(raw).digest()}
    )
    program = program.model_copy(
        update={
            "weights": ref,
            "input_profile": inputs.identity(),
            "arithmetic": arithmetic.identity(),
        }
    )
    classifier = classifier.model_copy(
        update={
            "program": program.identity(),
            "weights": ArtifactDigest(ref.sha256),
            "input_profile": inputs.identity(),
            "arithmetic": arithmetic.identity(),
        }
    )
    return classifier, program, inputs, arithmetic, raw, parameters


def alter_tensor(artifacts, name, **changes):
    arithmetic = artifacts[3]
    arithmetic = arithmetic.model_copy(
        update={
            "tensors": tuple(
                t.model_copy(update=changes) if t.name == name else t for t in arithmetic.tensors
            ),
        }
    )
    return rebind(artifacts, arithmetic=arithmetic)


@pytest.fixture
def basic():
    rows = [[0] * 256]
    rows[0][ord("A")] = 1
    return export(
        weights(hidden_weights=tuple(tuple(r) for r in rows)),
        profile(),
        first_fraction=0,
        last_fraction=0,
    )


def test_smallest_fixture_and_complete_tail(basic):
    empty = execute(basic)
    assert (empty.score, empty.verdict, len(empty.chunks)) == (0, True, 1)
    assert empty.chunks[0].counts == (0,) * 256
    exact = execute(basic, "AAAA")
    assert (exact.score, exact.verdict, len(exact.chunks)) == (4, False, 1)
    late = execute(basic, "xxxxAA")
    assert [chunk.score for chunk in late.chunks] == [0, 2]
    assert late.score == late.threshold == 2 and not late.verdict
    assert late.input_digest == input_commitment(opening("xxxxAA"), basic[0], basic[2])


def test_fixed_vectors_and_reproduction(tmp_path):
    raw = (ROOT / "fixtures/wire/integer-mlp-v1.json").read_text()
    assert json.dumps(BUILDER["build"](), indent=2, sort_keys=True) + "\n" == raw
    check = runpy.run_path(str(ROOT / "scripts/check_mlp_vectors.py"))["check"]
    check(ROOT / "fixtures/wire/integer-mlp-v1.json")


@pytest.mark.parametrize("value", [-9, -7, -5, -3, -1, 1, 3, 5, 7, 9])
def test_negative_and_positive_halfway_rounding(value):
    model = weights(hidden_bias=(value,), output_weights=(1,))
    exported = export(model, profile(), first_fraction=1, last_fraction=0)
    result = execute(exported)
    expected = formula("", model, 4, 1, 0, 0)[0]
    assert result.chunks[0].model_dump(mode="json") == expected
    assert result.chunks[0].hidden_accumulators == (value,)


@pytest.mark.parametrize(
    "hidden_bias,output_bias",
    [
        (I32_MIN, I32_MIN),
        (I32_MAX, I32_MAX),
        (0, I32_MIN),
        (0, I32_MAX),
    ],
)
def test_signed_extrema_without_wrapping(hidden_bias, output_bias):
    model = weights(hidden_bias=(hidden_bias,), output_weights=(0,), output_bias=output_bias)
    result = execute(export(model, profile(), first_fraction=0, last_fraction=0))
    assert result.chunks[0].hidden == (hidden_bias,)
    assert result.chunks[0].activated == (max(0, hidden_bias),)
    assert result.score == output_bias


def test_int8_extrema_are_executed_exactly():
    model = weights(
        2,
        hidden_weights=((127,) * 256, (-128,) * 256),
        hidden_bias=(-1, 1),
        output_weights=(127, -128),
    )
    result = execute(export(model, profile(), first_fraction=0, last_fraction=0), "AAAA")
    assert result.chunks[0].hidden == (507, -511)
    assert result.chunks[0].activated == (507, 0)
    assert result.score == 64389


def test_generated_formula_agrees_at_every_layer():
    rng = random.Random(20261020)
    for _ in range(60):
        width = rng.randint(1, 4)
        model = weights(
            width,
            hidden_weights=tuple(
                tuple(rng.randint(-3, 3) for _ in range(256)) for _ in range(width)
            ),
            hidden_bias=tuple(rng.randint(-11, 11) for _ in range(width)),
            output_weights=tuple(rng.randint(-3, 3) for _ in range(width)),
            output_bias=rng.randint(-11, 11),
        )
        first, hidden, last = rng.randint(0, 3), rng.randint(0, 2), rng.randint(0, 3)
        size = rng.randint(1, 16)
        text = "".join(rng.choice(["A", "x", "\x00", "é", "🦊"]) for _ in range(rng.randint(0, 24)))
        artifacts = export(
            model,
            profile(chunk_size=size),
            first_fraction=first,
            hidden_fraction=hidden,
            last_fraction=last,
            threshold=rng.randint(-3, 3),
        )
        result = execute(artifacts, text)
        expected = formula(text, model, size, first, hidden, last)
        assert [c.model_dump(mode="json") for c in result.chunks] == expected
        assert result.score == max(c["score"] for c in expected)
        assert result.verdict == (result.score < artifacts[0].threshold)


def test_padding_is_masked_but_actual_nul_is_counted(basic):
    original = execute(basic, "\x00A")
    other = execute(rebind(basic, inputs=profile(padding_id=0)), "\x00A")
    assert original.score == other.score == 1
    assert original.chunks == other.chunks and original.input_digest != other.input_digest
    assert original.chunks[0].counts[0] == original.chunks[0].counts[65] == 1
    assert original.chunks[0].unit_count == 2


def test_complete_utf8_and_boundary_crossing(basic):
    result = execute(basic, "AAAé")
    assert result.unit_count == 5 and [c.unit_count for c in result.chunks] == [4, 1]
    assert result.chunks[0].counts[195] == result.chunks[1].counts[169] == 1
    assert result.score == 3


def test_profile_limit_and_maximum_utf8_byte_length():
    model = weights()
    exported = export(
        model, profile(chunk_size=512, max_units=32768), first_fraction=0, last_fraction=0
    )
    result = execute(exported, "é" * 16384)
    assert result.unit_count == 32768 and len(result.chunks) == 64
    small = rebind(exported, inputs=profile(chunk_size=512, max_units=1024))
    assert execute(small, "x" * 1024).unit_count == 1024
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        execute(small, "x" * 1025)


def test_resource_budgets_reject_before_chunk_execution(monkeypatch):
    exported = export(weights(64), profile(chunk_size=1), first_fraction=0, last_fraction=0)
    maximum = MAX_PRODUCTS // (64 * 257)
    assert len(execute(exported, "x" * maximum).chunks) == maximum
    skinny = export(weights(), profile(chunk_size=1), first_fraction=0, last_fraction=0)
    assert len(execute(skinny, "x" * MAX_CHUNKS).chunks) == MAX_CHUNKS

    def forbidden(*args):
        pytest.fail("budget failure reached arithmetic execution")

    monkeypatch.setattr("hallmark.integer_mlp._affine", forbidden)
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        execute(exported, "x" * (maximum + 1))
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        execute(skinny, "x" * (MAX_CHUNKS + 1))


@pytest.mark.parametrize("coefficient", [2, -3])
def test_raw_accumulator_overflow_cannot_hide_behind_rescaling(coefficient):
    model = weights(hidden_bias=(2**30,), output_weights=(coefficient,))
    exported = export(model, profile(), first_fraction=0, last_fraction=2)
    # Stored output would fit after division by four, but the int32 accumulator does not.
    with pytest.raises(WireError, match="INPUT_INVALID"):
        execute(exported)


def test_cancelling_weights_cannot_hide_intermediate_overflow():
    model = weights(3, hidden_bias=(2**30,) * 3, output_weights=(1, 1, -1))
    exported = export(model, profile(), first_fraction=0, last_fraction=2)
    with pytest.raises(WireError, match="INPUT_INVALID"):
        execute(exported)


@pytest.mark.parametrize(
    "field,value",
    [
        ("hidden_weights", ((True,) * 256,)),
        ("hidden_weights", ((128,) * 256,)),
        ("hidden_weights", ((-129,) * 256,)),
        ("hidden_weights", ((0,) * 255,)),
        ("hidden_weights", ((0,) * 257,)),
        ("hidden_weights", ((0,) * 256,) * 65),
        ("hidden_bias", (2**31,)),
        ("hidden_bias", (-(2**31) - 1,)),
        ("hidden_bias", (0.0,)),
        ("hidden_bias", ()),
        ("output_weights", (False,)),
        ("output_weights", (1, 2)),
        ("output_bias", True),
    ],
)
def test_export_rejects_wrong_types_shapes_and_ranges(field, value):
    with pytest.raises(ValidationError):
        weights(**{field: value})


@pytest.mark.parametrize("field", ["program", "weights", "input_profile", "arithmetic"])
def test_classifier_cannot_select_unbound_artifacts(basic, field):
    altered = basic[0].model_copy(update={field: b"x" * 32})
    with pytest.raises(WireError, match="INPUT_INVALID"):
        execute(basic, classifier=altered)


@pytest.mark.parametrize("field", ["input_profile", "arithmetic"])
def test_program_cannot_override_classifier_profiles(basic, field):
    altered = basic[1].model_copy(update={field: b"x" * 32})
    classifier = basic[0].model_copy(update={"program": altered.identity()})
    with pytest.raises(WireError, match="INPUT_INVALID"):
        execute(basic, program=altered, classifier=classifier)


@pytest.mark.parametrize("replacement", [b"", b"x", b"x" * 65537])
def test_changed_or_oversize_weight_bytes(basic, replacement):
    with pytest.raises(WireError):
        execute(basic, weights=replacement)


def test_pinned_malformed_weights_are_still_rejected(basic):
    value = cbor2.loads(basic[4])
    value["hidden_weights"][0][0] = True
    with pytest.raises(WireError):
        execute(rebind(basic, raw=cbor2.dumps(value, canonical=True)))


@pytest.mark.parametrize(
    "tensor,changes",
    [
        ("counts", {"minimum": -1}),
        ("counts", {"maximum": 3}),
        ("counts", {"fractional_bits": 1}),
        ("w1", {"signed_bits": 16}),
        ("w2", {"signed_bits": 16}),
        ("hidden", {"signed_bits": 16}),
        ("counts", {"shape": (1, 256)}),
        ("relu", {"fractional_bits": 1}),
        ("score", {"fractional_bits": 1}),
        ("b1", {"fractional_bits": 1}),
    ],
)
def test_unsupported_numerical_profiles_are_rejected(basic, tensor, changes):
    with pytest.raises(WireError):
        execute(alter_tensor(basic, tensor, **changes))


def test_actual_weights_must_fit_the_declared_tensor_envelope(basic):
    value = cbor2.loads(basic[4])
    value["hidden_weights"][0][0] = 2
    with pytest.raises(WireError):
        execute(rebind(basic, raw=cbor2.dumps(value, canonical=True)))


def test_only_affine_relu_affine_graph_executes(basic):
    arithmetic = basic[3]
    relu = arithmetic.nodes[1].model_copy(update={"op": "reshape"})
    altered = arithmetic.model_copy(
        update={"nodes": (arithmetic.nodes[0], relu, arithmetic.nodes[2])}
    )
    with pytest.raises(WireError):
        execute(rebind(basic, arithmetic=altered))


def test_omitted_and_changed_operator_parameters(basic):
    with pytest.raises(WireError):
        execute(basic, parameters={})
    with pytest.raises(WireError):
        execute(basic, parameters={name: b"changed" for name in basic[5]})


def test_weight_file_cannot_alias_operator_parameter_path(basic):
    program = basic[1].model_copy(
        update={
            "weights": basic[1].weights.model_copy(update={"path": next(iter(basic[5]))}),
        }
    )
    classifier = basic[0].model_copy(update={"program": program.identity()})
    with pytest.raises(WireError):
        execute(basic, program=program, classifier=classifier)


def test_result_cannot_omit_chunks_or_flip_threshold(basic):
    result = execute(basic, "xxxxAA")
    for change in (
        {"chunks": result.chunks[:1]},
        {"unit_count": 4},
        {"score": 0},
        {"verdict": True},
        {"chunks": tuple(reversed(result.chunks))},
    ):
        with pytest.raises(WireError):
            result.model_copy(update=change).encode()
    chunk = result.chunks[0].model_copy(update={"counts": (0,) * 256})
    with pytest.raises(WireError):
        result.model_copy(update={"chunks": (chunk, result.chunks[1])}).encode()


def test_execution_never_fetches_files_or_network(basic, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("native arithmetic attempted external I/O")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    assert execute(basic, "AA").score == 2


@pytest.mark.parametrize(
    "field", ["opening", "classifier", "program", "inputs", "arithmetic", "weights"]
)
def test_runtime_rejects_wrong_argument_types(basic, field):
    with pytest.raises(WireError):
        execute(basic, **{field: None})


def test_runtime_never_classifies_response_or_accepts_encoder(basic):
    one = execute(basic, "AA")
    two = execute(basic, opening=opening("AA", response="x" * 512))
    assert one == two
    classifier = basic[0].model_copy(update={"kind": "encoder", "tokenizer": b"t" * 32})
    with pytest.raises(WireError):
        execute(basic, classifier=classifier)


def test_trace_and_weights_repr_omit_private_values(basic):
    result = execute(basic, "SYNTHETIC_PRIVATE_SENTINEL")
    assert "chunks=" not in repr(result)
    assert "counts=" not in repr(result.chunks[0])
    assert "hidden=" not in repr(result.chunks[0])
    assert "hidden_weights=" not in repr(MlpWeights.decode(basic[4]))
    forged = opening().model_copy(update={"prompt": "SYNTHETIC_PRIVATE_SENTINEL\ud800"})
    with pytest.raises(WireError) as exc:
        execute(basic, opening=forged)
    assert "SENTINEL" not in str(exc.value) and exc.value.__context__ is None


@pytest.mark.parametrize(
    "name,cls",
    [
        ("mlp-program", MlpProgram),
        ("mlp-weights", MlpWeights),
        ("mlp-result", MlpResult),
    ],
)
def test_schema_snapshots(name, cls):
    assert (
        json.loads((ROOT / f"docs/schemas/{name}-v1.json").read_text()) == cls.model_json_schema()
    )
