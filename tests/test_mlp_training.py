"""Numerical/trust-boundary software checks; the labels are harmless authored markers."""

import builtins
import json
import math
import runpy
from pathlib import Path

import pytest

from hallmark.classifier_manifest import ClassifierManifest, InputProfile
from hallmark.contracts import Record
from hallmark.integer_mlp import MlpWeights, execute_mlp
from hallmark.manifests import FileRef, FileSHA256
from hallmark.mlp_export import compile_mlp
from hallmark.mlp_training import (
    MlpCheckpoint,
    MlpFitConfig,
    _objective,
    fit_mlp,
    quantize_mlp,
    score_float_mlp,
)
from hallmark.openings import TranscriptOpening
from hallmark.wire import WireError

ROOT = Path(__file__).resolve().parents[1]


def config(**changes):
    value = dict(
        schema_id="hallmark/mlp-fit-config/1",
        policy_id="fixture.mlp-training",
        seed=17,
        hidden_width=4,
        chunk_bytes=4,
        max_prompt_bytes=64,
        max_rows=32,
        max_feature_values=32768,
        epochs=80,
        learning_rate=0.05,
        momentum=0.8,
        l2=0.001,
        tolerance=0.0,
    )
    return MlpFitConfig.model_validate(value | changes)


def rows():
    texts = (
        "",
        "A",
        "AAAA",
        "AAAAAAAA",
        "éAA",
        "AXAXAX",
        "B",
        "BBBB",
        "AAAABBBB",
        "BBBB\x00",
        "AAAAAAAABBBB",
        "BBBBBBBB",
    )
    return tuple(
        Record(
            schema_id="hallmark.dataset-record/1",
            record_id=f"r-{i:02d}",
            group_id=f"g-{i:02d}",
            family_id="fixture",
            source_id="authored-markers",
            source_revision="0" * 64,
            license_id="fixture-only",
            policy_id="fixture.mlp-training",
            split="train",
            language="en",
            prompt=text,
            response="",
            label=int("B" in text),
        )
        for i, text in enumerate(texts)
    )


@pytest.mark.parametrize("split", ["calibration", "test"])
def test_nontraining_rejects_before_label_serialization_or_numpy(split, monkeypatch):
    data = (*rows()[:-1], rows()[-1].model_copy(update={"split": split}))
    original = Record.model_dump

    def dump(self, *args, **kwargs):
        assert self.split == "train", "nontraining labels reached fitting"
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Record, "model_dump", dump)
    importer = builtins.__import__

    def protected(name, *args, **kwargs):
        assert name != "numpy", "optional runtime reached before rejection"
        return importer(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", protected)
    with pytest.raises(WireError):
        fit_mlp(data, config())


@pytest.mark.parametrize(
    "fault",
    [
        "one-class",
        "duplicate",
        "policy",
        "language",
        "response",
        "oversize",
        "rows",
        "features",
        "native-envelope",
        "nan",
        "bool-seed",
    ],
)
def test_invalid_training_boundaries(fault):
    data, options = rows(), {}
    if fault == "one-class":
        data = data[:6]
    elif fault == "duplicate":
        data = (*data, data[0])
    elif fault in {"policy", "language", "response", "oversize"}:
        field, value = {
            "policy": ("policy_id", "other"),
            "language": ("language", "fr"),
            "response": ("response", "not input"),
            "oversize": ("prompt", "😀" * 17),
        }[fault]
        data = (data[0].model_copy(update={field: value}), *data[1:])
    else:
        options = {
            "rows": {"max_rows": 2},
            "features": {"max_feature_values": 256},
            "native-envelope": {"max_prompt_bytes": 32768, "chunk_bytes": 1},
            "nan": {"learning_rate": math.nan},
            "bool-seed": {"seed": True},
        }[fault]
    with pytest.raises((ValueError, WireError)):
        fit_mlp(data, config(**options))


@pytest.mark.train
def test_actual_fit_resume_roundtrip_and_input_order():
    pytest.importorskip("numpy")
    cfg, data = config(), rows()
    complete, samples = fit_mlp(data, cfg)
    partial, first = fit_mlp(data, cfg, steps=31)
    restored = MlpCheckpoint.model_validate_json(partial.model_dump_json())
    resumed, second = fit_mlp(
        data, cfg, checkpoint=restored, expected_checkpoint=partial.identity()
    )
    repeated, again = fit_mlp(tuple(reversed(data)), cfg)
    assert resumed == repeated == complete
    assert (*first, *second) == again == samples
    assert complete.epoch == cfg.epochs and complete.converged is False
    assert samples[-1].loss < samples[0].loss
    assert complete.identity() == restored.model_copy(update=complete.model_dump()).identity()
    assert all(math.isfinite(x.gradient_norm) for x in samples)


@pytest.mark.train
@pytest.mark.parametrize(
    "fault", ["pin", "data", "config", "runtime", "loss", "weights", "width", "missing-pin"]
)
def test_resume_rejects_changed_identity(monkeypatch, fault):
    pytest.importorskip("numpy")
    import hallmark.mlp_training as training

    cfg, data = config(), rows()
    checkpoint, _ = fit_mlp(data, cfg, steps=3)
    pin = checkpoint.identity()
    if fault == "pin":
        pin = "0" * 64
    elif fault == "missing-pin":
        pin = None
    elif fault == "data":
        data = (data[0].model_copy(update={"prompt": "AAAA"}), *data[1:])
    elif fault == "config":
        cfg = config(learning_rate=0.1)
    elif fault == "runtime":
        monkeypatch.setattr(training, "runtime_record", lambda: {"changed": True})
    elif fault == "loss":
        checkpoint = checkpoint.model_copy(update={"loss": checkpoint.loss + 1})
        pin = checkpoint.identity()
    elif fault == "width":
        checkpoint = checkpoint.model_copy(
            update={"parameters": checkpoint.parameters.model_copy(update={"hidden_bias": (0.0,)})}
        )
    else:
        checkpoint = checkpoint.model_copy(
            update={
                "parameters": checkpoint.parameters.model_copy(
                    update={"output_bias": checkpoint.parameters.output_bias + 1}
                )
            }
        )
    with pytest.raises((ValueError, WireError)):
        fit_mlp(data, cfg, checkpoint=checkpoint, expected_checkpoint=pin)


@pytest.mark.train
def test_record_max_gradient_matches_numerical_derivative():
    np = pytest.importorskip("numpy")
    arrays = [
        np.asarray([[2.0, -1.0], [0.3, 0.4]]),
        np.asarray([0.3, 0.2]),
        np.asarray([1.2, 0.7]),
        np.asarray(-0.2),
    ]
    x, starts, y = (
        np.asarray([[0.1, 0.1], [1.0, 0.0], [0.3, 0.2]]),
        np.asarray([0, 2]),
        np.asarray([1.0, 0.0]),
    )
    loss, gradients, scores = _objective(arrays, x, starts, y, 0.03)
    logits = [
        sum(
            max(sum(a * b for a, b in zip(row, weights, strict=True)) + bias, 0) * out
            for weights, bias, out in zip(arrays[0], arrays[1], arrays[2], strict=True)
        )
        + arrays[3]
        for row in x
    ]
    assert scores.tolist() == pytest.approx([max(logits[:2]), logits[2]])
    assert loss > 0
    for p, expected in zip(arrays, gradients, strict=True):
        for index in np.ndindex(p.shape):
            original = p[index].item()
            p[index] = original + 1e-6
            plus = _objective(arrays, x, starts, y, 0.03)[0]
            p[index] = original - 1e-6
            minus = _objective(arrays, x, starts, y, 0.03)[0]
            p[index] = original
            assert float(expected[index]) == pytest.approx((plus - minus) / 2e-6, abs=2e-8)


@pytest.mark.train
def test_max_ties_choose_first_chunk_without_labelling_all_chunks():
    np = pytest.importorskip("numpy")
    arrays = [np.asarray([[1.0, 1.0]]), np.asarray([0.0]), np.asarray([1.0]), np.asarray(0.0)]
    _, gradients, scores = _objective(arrays, np.eye(2), np.asarray([0]), np.asarray([1.0]), 0.0)
    assert scores.tolist() == [1.0]
    assert gradients[0][0, 0] < 0 and gradients[0][0, 1] == 0


@pytest.mark.train
def test_integer_export_executes_native_full_input_and_unchanged_fixture():
    pytest.importorskip("numpy")
    cfg = config()
    checkpoint, _ = fit_mlp(rows(), cfg)
    quantized = quantize_mlp(checkpoint, cfg)
    profile = InputProfile(
        schema_id="hallmark/input-profile/1",
        encoding="utf8-bytes",
        tokenizer_files=(),
        prefix_tokens=(),
        suffix_tokens=(),
        chunk_size=cfg.chunk_bytes,
        overlap=0,
        max_units=cfg.max_prompt_bytes,
        padding_id=0,
        padding_side="right",
    )
    program, arithmetic, raw, params = compile_mlp(
        quantized.weights,
        profile,
        first_fraction=quantized.first_fraction,
        hidden_fraction=0,
        last_fraction=quantized.last_fraction,
    )
    # Explicit public test markers, never enrollment or a proof backend claim.
    classifier = ClassifierManifest(
        schema_id="hallmark/classifier/1",
        kind="mlp",
        program=program.identity(),
        weights=program.weights.sha256,
        tokenizer=None,
        input_profile=profile.identity(),
        arithmetic=arithmetic.identity(),
        threshold=0,
        scope="prompt",
        labels=("benign", "marker"),
        backend=b"b" * 32,
        verifier_key=b"k" * 32,
        setup=b"s" * 32,
    )
    for prompt in [*(r.prompt for r in rows()), "A" * 60 + "BBBB", "A" * 64, "\x00", "😀"]:
        opening = TranscriptOpening(
            schema_id="hallmark/transcript-opening/1",
            salt=b"s" * 32,
            system_ref=b"c" * 32,
            prompt=prompt,
            response="",
        )
        result = execute_mlp(
            opening, classifier, program, profile, arithmetic, weights=raw, parameters=params
        )
        assert result.unit_count == len(prompt.encode())
        assert sum(c.unit_count for c in result.chunks) == len(prompt.encode())
        assert (
            abs(
                result.score / quantized.score_scale
                - score_float_mlp(checkpoint.parameters, cfg, prompt)
            )
            < 0.08
        )
    assert runpy.run_path(str(ROOT / "scripts/build_mlp_fixture.py"))["build"]() == json.loads(
        (ROOT / "fixtures/wire/integer-mlp-v1.json").read_text()
    )


@pytest.mark.train
def test_native_maximum_prompt_after_training():
    pytest.importorskip("numpy")
    cfg = config(chunk_bytes=512, max_prompt_bytes=32768, epochs=3)
    state, _ = fit_mlp(rows(), cfg)
    q = quantize_mlp(state, cfg)
    profile = InputProfile(
        schema_id="hallmark/input-profile/1",
        encoding="utf8-bytes",
        tokenizer_files=(),
        prefix_tokens=(),
        suffix_tokens=(),
        chunk_size=512,
        overlap=0,
        max_units=32768,
        padding_id=0,
        padding_side="right",
    )
    program, arithmetic, raw, params = compile_mlp(
        q.weights,
        profile,
        first_fraction=q.first_fraction,
        hidden_fraction=0,
        last_fraction=q.last_fraction,
    )
    classifier = ClassifierManifest(
        schema_id="hallmark/classifier/1",
        kind="mlp",
        program=program.identity(),
        weights=program.weights.sha256,
        tokenizer=None,
        input_profile=profile.identity(),
        arithmetic=arithmetic.identity(),
        threshold=0,
        scope="prompt",
        labels=("benign", "marker"),
        backend=b"b" * 32,
        verifier_key=b"k" * 32,
        setup=b"s" * 32,
    )
    opening = TranscriptOpening(
        schema_id="hallmark/transcript-opening/1",
        salt=b"s" * 32,
        system_ref=b"c" * 32,
        prompt="A" * 32767 + "B",
        response="",
    )
    result = execute_mlp(
        opening, classifier, program, profile, arithmetic, weights=raw, parameters=params
    )
    assert len(result.chunks) == 64 and sum(c.unit_count for c in result.chunks) == 32768
    assert result.chunks[-1].counts[ord("B")] == 1
    with pytest.raises(WireError):
        execute_mlp(
            opening.model_copy(update={"prompt": opening.prompt + "B"}),
            classifier,
            program,
            profile,
            arithmetic,
            weights=raw,
            parameters=params,
        )


@pytest.mark.train
def test_converged_checkpoint_does_not_restart_or_consume_extra_epochs():
    pytest.importorskip("numpy")
    cfg = config(tolerance=1.0)
    state, samples = fit_mlp(rows(), cfg)
    assert state.converged and state.epoch == 1 and len(samples) == 1
    again, more = fit_mlp(rows(), cfg, checkpoint=state, expected_checkpoint=state.identity())
    assert again == state and more == ()


def test_fixture_and_schema_reproduction():
    import hashlib

    from hallmark.mlp_training import MlpQuantization

    expected = json.loads((ROOT / "fixtures/mlp-training.json").read_bytes())
    assert (
        runpy.run_path(str(ROOT / "scripts/build_mlp_training_fixture.py"))["build"]() == expected
    )
    assert (
        hashlib.sha256((ROOT / "fixtures/mlp-training.json").read_bytes()).hexdigest()
        == (ROOT / "fixtures/mlp-training.sha256").read_text().strip()
    )
    for name, model in (
        ("mlp-fit-config", MlpFitConfig),
        ("mlp-checkpoint", MlpCheckpoint),
        ("mlp-quantization", MlpQuantization),
    ):
        assert model.model_json_schema() == json.loads(
            (ROOT / f"docs/schemas/{name}-v1.json").read_bytes()
        )


@pytest.mark.parametrize("fault", ["tokens", "fraction"])
def test_export_rejects_nonbyte_profiles_and_invalid_fractions(fault):
    fixture = json.loads((ROOT / "fixtures/wire/integer-mlp-v1.json").read_bytes())
    weights = MlpWeights.decode(bytes.fromhex(fixture["weights_cbor_hex"]))
    profile = InputProfile.decode(bytes.fromhex(fixture["records"]["input_profile"]["cbor_hex"]))
    if fault == "tokens":
        profile = profile.model_copy(
            update={
                "encoding": "token-ids",
                "tokenizer_files": (
                    FileRef(path="tokenizer.json", size=1, sha256=FileSHA256(b"t" * 32)),
                ),
            }
        )
    with pytest.raises(WireError):
        compile_mlp(
            weights,
            profile,
            first_fraction=True if fault == "fraction" else 1,
            hidden_fraction=0,
            last_fraction=1,
        )


def test_fixture_preflight_and_failure_retention(tmp_path):
    module = runpy.run_path(str(ROOT / "scripts/check_mlp_training.py"))
    check = module["check"]
    fixture = ROOT / "fixtures/mlp-training.json"
    pin = (ROOT / "fixtures/mlp-training.sha256").read_text().strip()
    output = tmp_path / "result"
    with pytest.raises(ValueError):
        check(fixture, "0" * 64, output)
    assert not output.exists()
    assert check(fixture, pin)["training_executed"] is False

    def fail(*args, **kwargs):
        raise RuntimeError("public failure marker")

    check.__globals__["runtime_record"] = lambda: {"software_mock": True}
    check.__globals__["fit_mlp"] = fail
    with pytest.raises(RuntimeError):
        check(fixture, pin, output)
    assert (output / "failure.json").exists() and not (output / "result.json").exists()
    with pytest.raises(FileExistsError):
        check(fixture, pin, output)


@pytest.mark.train
def test_actual_three_seed_fixture(tmp_path):
    pytest.importorskip("numpy")
    check = runpy.run_path(str(ROOT / "scripts/check_mlp_training.py"))["check"]
    result = check(
        ROOT / "fixtures/mlp-training.json",
        (ROOT / "fixtures/mlp-training.sha256").read_text().strip(),
        tmp_path / "result",
    )
    assert result["status"] == "passed" and not result["quality_claim"]
    assert [r["seed"] for r in result["seeds"]] == [17, 29, 43]
    assert all(r["resume_equal"] for r in result["seeds"])
    assert all(
        next(p for p in r["scores"] if p["name"] == "last-byte")["unit_count"] == 32768
        for r in result["seeds"]
    )


def test_fixture_cli_sanitizes_paths(tmp_path):
    import subprocess
    import sys

    secret = str(tmp_path / "private-marker")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_mlp_training.py"),
            secret,
            "--expected-fixture",
            "bad",
        ],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode != 0 and secret not in result.stderr + result.stdout
