"""Grouped fitting, vocabulary isolation and exact decision-boundary checks."""

import builtins
import json
import math
import runpy
from pathlib import Path

import pytest

from hallmark.baselines import NgramModel, fit_ngram, score_ngram, training_rows
from hallmark.contracts import Record
from hallmark.selection import (
    SelectionPlan,
    fit_candidate,
    grouped_folds,
    grouped_selection,
    representatives,
    score_fitted,
    threshold,
)
from hallmark.wire import WireError

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    value = runpy.run_path(str(ROOT / "scripts/build_selection_fixture.py"))["build"]()
    return (
        tuple(Record.model_validate_json(json.dumps(r)) for r in value["records"]),
        SelectionPlan.model_validate_json(json.dumps(value["plan"])),
    )


@pytest.mark.parametrize("split", ["calibration", "test"])
def test_selection_rejects_outer_labels_before_serialization_or_optional_import(split, monkeypatch):
    rows, plan = fixture()
    rows = (*rows[:-1], rows[-1].model_copy(update={"split": split}))
    original_dump, original_import = Record.model_dump, builtins.__import__

    def dump(self, *args, **kwargs):
        assert self.split == "train"
        return original_dump(self, *args, **kwargs)

    def importer(name, *args, **kwargs):
        assert not name.startswith(("numpy", "sklearn", "scipy"))
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(Record, "model_dump", dump)
    monkeypatch.setattr(builtins, "__import__", importer)
    with pytest.raises(WireError):
        grouped_selection(rows, plan)
    with pytest.raises(WireError):
        fit_ngram(rows, plan.candidates[1].ngram, plan.bounds, seed=17)


def test_groups_and_representatives_are_order_and_label_independent():
    rows, plan = fixture()
    folds = grouped_folds(rows, plan.bounds)
    changed = tuple(r.model_copy(update={"label": 1 - r.label}) for r in reversed(rows))
    assert grouped_folds(changed, plan.bounds) == folds
    assert len(folds) == 50 and [list(folds.values()).count(i) for i in range(5)] == [10] * 5
    assert [r.record_id for r in representatives(rows)] == [
        r.record_id for r in representatives(changed)
    ]
    assert len(representatives(rows)) == 50


@pytest.mark.parametrize("field,value", [("seeds", [17.0, 29, 43]), ("folds", 5.0)])
def test_plan_rejects_numeric_type_coercion(field, value):
    _, plan = fixture()
    raw = plan.model_dump(mode="json") | {field: value}
    with pytest.raises(ValueError):
        SelectionPlan.model_validate_json(json.dumps(raw))


@pytest.mark.parametrize(
    "fault",
    [
        "ids",
        "prompt-groups",
        "policy",
        "language",
        "response",
        "row-limit",
        "byte-limit",
        "total-limit",
        "classes",
    ],
)
def test_training_boundaries(fault):
    rows, plan = fixture()
    bounds = plan.bounds
    if fault == "ids":
        rows = (*rows, rows[0])
    elif fault == "prompt-groups":
        rows = (rows[0].model_copy(update={"prompt": rows[2].prompt}), *rows[1:])
    elif fault in ("policy", "language", "response"):
        key, value = {
            "policy": ("policy_id", "other"),
            "language": ("language", "fr"),
            "response": ("response", "x"),
        }[fault]
        rows = (rows[0].model_copy(update={key: value}), *rows[1:])
    elif fault == "classes":
        rows = tuple(r for r in rows if r.label == 0)
    else:
        key, value = {
            "row-limit": ("max_rows", 2),
            "byte-limit": ("max_prompt_bytes", 2),
            "total-limit": ("max_total_bytes", 2),
        }[fault]
        bounds = bounds.model_copy(update={key: value})
    with pytest.raises(WireError):
        training_rows(rows, bounds)


@pytest.mark.parametrize(
    "scores,labels,rate",
    [
        ((), (), "0.01"),
        ((True,), (0,), "0.01"),
        ((math.nan,), (0,), "0.01"),
        ((1, 2.0), (0, 0), "0.01"),
        ((2**31 - 1,), (0,), "0.01"),
        ((2**10000,), (0,), "0.01"),
        ((1,), (1,), "0.01"),
        ((1,), (0,), "0.5"),
    ],
)
def test_threshold_rejects_invalid_or_unrepresentable_input(scores, labels, rate):
    with pytest.raises(WireError):
        threshold(scores, labels, rate)


def test_threshold_exact_allowance_and_blocking_ties():
    scores = tuple(range(2000))
    cut = threshold(scores, (0,) * len(scores), "0.0035")
    assert cut == 1993 and sum(s >= cut for s in scores) == 7
    assert threshold((4, 4, 3), (0, 0, 1), "0.01") == 5
    cut = threshold((4.0, 4.0, 3.0), (0, 0, 1), "0.01")
    assert cut == math.nextafter(4.0, math.inf) and 4.0 < cut


def test_raw_unicode_and_whitespace_scoring_without_optional_runtime():
    model = NgramModel(
        schema_id="hallmark/character-logistic/1",
        min_n=2,
        max_n=2,
        max_prompt_bytes=128,
        vocabulary=("  ", "é😀"),
        coefficients=(2.0, 3.0),
        intercept=0.5,
    )
    assert score_ngram(model, "é😀") == 3.5
    assert score_ngram(model, "  ") == 2.5
    assert score_ngram(model, " ") == 0.5 and score_ngram(model, "") == 0.5
    with pytest.raises(WireError):
        score_ngram(model, "😀" * 33)


@pytest.mark.train
def test_ngram_fit_uses_only_given_rows_and_preserves_state():
    pytest.importorskip("sklearn")
    rows, plan = fixture()
    config = plan.candidates[1].ngram
    fitted = fit_ngram(rows, config, plan.bounds, seed=17)
    repeated = fit_ngram(tuple(reversed(rows)), config, plan.bounds, seed=17)
    assert fitted == repeated and fitted.converged
    assert "Ω" not in fitted.model.vocabulary
    assert score_ngram(fitted.model, "ΩΩΩ") == fitted.model.intercept
    assert fitted.resume == "not-supported-cold-fit"
    failed = fit_ngram(
        rows, config.model_copy(update={"max_iter": 1, "tolerance": 1e-12}), plan.bounds, seed=17
    )
    assert not failed.converged and failed.iterations == 1
    with pytest.raises(WireError):
        fit_ngram(rows, config.model_copy(update={"max_events": 1}), plan.bounds, seed=17)


@pytest.mark.train
def test_grouped_fit_isolation_actual_controls_and_fixed_ties(monkeypatch):
    pytest.importorskip("sklearn")
    import hallmark.selection as selection

    rows, plan = fixture()
    folds = grouped_folds(rows, plan.bounds)
    original = selection.fit_candidate
    seen = []

    def fit(fitting, candidate, current, seed):
        present = {folds[r.group_id] for r in fitting}
        assert len(present) == 3
        seen.append((seed, candidate.id, present))
        return original(fitting, candidate, current, seed)

    monkeypatch.setattr(selection, "fit_candidate", fit)
    result = grouped_selection(rows, plan)
    assert len(seen) == 75
    assert result["controls"]["pass-all"]["fp"] == 0
    assert result["controls"]["block-all"]["fn"] == 0
    for item in result["selected"]:
        assert (
            item["candidate"]
            == {"byte-logistic": "floor", "char-ngram": "char-a", "byte-mlp": "mlp"}[item["kind"]]
        )
    for candidate in result["candidates"]:
        for rotation in candidate["rotations"]:
            ids = [set(rotation[key]) for key in ("fitting_ids", "threshold_ids", "validation_ids")]
            assert not (ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])
            if candidate["kind"] == "char-ngram":
                vocabulary = rotation["fit"]["model"]["model"]["vocabulary"]
                fitting_prompts = [r.prompt for r in rows if r.record_id in ids[0]]
                assert all(any(term in prompt for prompt in fitting_prompts) for term in vocabulary)
            if candidate["candidate"] == "mlp-nonconverged":
                assert rotation["status"] == "nonconverged" and not candidate["eligible"]
    assert [r["kind"] for r in result["roster"] if r["status"] == "unavailable"] == [
        "task-guard",
        "compact-encoder",
    ]


@pytest.mark.train
def test_legacy_long_training_remains_rejected_and_mlp_covers_it():
    pytest.importorskip("sklearn")
    rows, plan = fixture()
    rows = (rows[0].model_copy(update={"prompt": "A" * 80}), *rows[1:])
    with pytest.raises(ValueError, match="one chunk"):
        fit_candidate(rows, plan.candidates[0], plan, 17)
    fitted = fit_candidate(rows, plan.candidates[3], plan, 17)
    scores = score_fitted(fitted, ("A" * 127 + "B", "A" * 128, ""))
    assert len(scores) == 3 and all(type(s) is int for s in scores)
    with pytest.raises(WireError):
        score_fitted(fitted, ("A" * 129,))


def outer_rows(rows, split):
    return tuple(
        r.model_copy(
            update={
                "record_id": f"{split}-{r.record_id}",
                "group_id": f"{split}-{r.group_id}",
                "split": split,
                "prompt": r.prompt + " " + split,
            }
        )
        for r in rows[:20]
    )


@pytest.mark.train
@pytest.mark.parametrize("candidate_index", [0, 1, 3])
def test_actual_outer_calibration_and_native_evaluation(candidate_index):
    pytest.importorskip("sklearn")
    from hallmark.comparison import calibrate_fitted, evaluate_fitted

    rows, plan = fixture()
    fitted = fit_candidate(rows, plan.candidates[candidate_index], plan, 17)
    identity = fitted.record["identity"]
    calibrated = calibrate_fitted(
        fitted, outer_rows(rows, "calibration"), expected_fit=identity, target_fpr="0.01"
    )
    result = evaluate_fitted(
        fitted,
        calibrated,
        outer_rows(rows, "test"),
        expected_fit=identity,
        expected_calibration=calibrated.identity(),
    )
    assert result["primary"]["n"] == 10 and result["all_rows"]["n"] == 20
    assert result["quality_claim"] is False
    assert all(p["block"] == (p["score"] >= calibrated.threshold) for p in result["predictions"])
    assert calibrated.score_type == ("float64" if candidate_index == 1 else "integer")


@pytest.mark.train
@pytest.mark.parametrize(
    "fault",
    [
        "fit-pin",
        "calibration-pin",
        "calibration-threshold",
        "fit-state",
        "calibration-split",
        "test-split",
        "training-group",
        "calibration-group",
        "training-prompt",
        "calibration-prompt",
    ],
)
def test_frozen_comparison_rejects_identity_and_split_leakage(fault):
    pytest.importorskip("sklearn")
    from dataclasses import replace

    from hallmark.comparison import calibrate_fitted, evaluate_fitted

    rows, plan = fixture()
    fitted = fit_candidate(rows, plan.candidates[1], plan, 17)
    calibration_rows, test_rows = outer_rows(rows, "calibration"), outer_rows(rows, "test")
    fit_pin = fitted.record["identity"]
    calibrated = calibrate_fitted(fitted, calibration_rows, expected_fit=fit_pin, target_fpr="0.01")
    cal_pin = calibrated.identity()
    if fault == "fit-pin":
        fit_pin = "0" * 64
    elif fault == "calibration-pin":
        cal_pin = "0" * 64
    elif fault == "calibration-threshold":
        calibrated = calibrated.model_copy(update={"threshold": calibrated.threshold + 1.0})
    elif fault == "fit-state":
        fitted = replace(fitted, record={**fitted.record, "seed": 43})
    elif fault == "calibration-split":
        with pytest.raises(WireError):
            calibrate_fitted(fitted, test_rows, expected_fit=fit_pin, target_fpr="0.01")
        return
    elif fault == "test-split":
        test_rows = calibration_rows
    else:
        key, value = {
            "training-group": ("group_id", rows[0].group_id),
            "calibration-group": ("group_id", calibration_rows[0].group_id),
            "training-prompt": ("prompt", rows[0].prompt),
            "calibration-prompt": ("prompt", calibration_rows[0].prompt),
        }[fault]
        test_rows = (test_rows[0].model_copy(update={key: value}), *test_rows[1:])
    with pytest.raises(WireError):
        evaluate_fitted(
            fitted, calibrated, test_rows, expected_fit=fit_pin, expected_calibration=cal_pin
        )


@pytest.mark.train
def test_selection_repeats_and_keeps_unsupported_floor_failures():
    pytest.importorskip("sklearn")
    rows, plan = fixture()
    rows = tuple(r.model_copy(update={"prompt": r.prompt + "x" * 40}) for r in rows)
    first = grouped_selection(rows, plan)
    repeated = grouped_selection(tuple(reversed(rows)), plan)
    assert first == repeated
    floors = [r for r in first["candidates"] if r["kind"] == "byte-logistic"]
    assert len(floors) == 3
    assert all(
        not r["eligible"] and all(f["status"] == "failed" for f in r["rotations"]) for r in floors
    )
    assert all(s["candidate"] is None for s in first["selected"] if s["kind"] == "byte-logistic")
    assert all(
        f["cause"] == "legacy-single-chunk-training-limit" for r in floors for f in r["rotations"]
    )


def test_fixture_and_schemas_reproduce():
    import hashlib

    from hallmark.baselines import NgramConfig, NgramFit
    from hallmark.comparison import ComparisonCalibration

    raw = (ROOT / "fixtures/grouped-selection.json").read_bytes()
    value = runpy.run_path(str(ROOT / "scripts/build_selection_fixture.py"))["build"]()
    assert value == json.loads(raw)
    assert (
        hashlib.sha256(raw).hexdigest()
        == (ROOT / "fixtures/grouped-selection.sha256").read_text().strip()
    )
    for name, model in (
        ("ngram-fit-config", NgramConfig),
        ("ngram-model", NgramModel),
        ("ngram-fit", NgramFit),
        ("grouped-selection-plan", SelectionPlan),
        ("comparison-calibration", ComparisonCalibration),
    ):
        assert model.model_json_schema() == json.loads(
            (ROOT / f"docs/schemas/{name}-v1.json").read_bytes()
        )


def test_controller_preflight_and_failure_retention(tmp_path):
    check = runpy.run_path(str(ROOT / "scripts/check_selection.py"))["check"]
    fixture_path = ROOT / "fixtures/grouped-selection.json"
    pin = (ROOT / "fixtures/grouped-selection.sha256").read_text().strip()
    output = tmp_path / "result"
    with pytest.raises(ValueError):
        check(fixture_path, "0" * 64, output)
    assert not output.exists()
    assert not check(fixture_path, pin)["training_executed"]
    check.__globals__["baseline_runtime"] = lambda: {"software_mock": True}

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic failure")

    check.__globals__["grouped_selection"] = fail
    with pytest.raises(RuntimeError):
        check(fixture_path, pin, output)
    assert (output / "failure.json").exists() and not (output / "result.json").exists()
    with pytest.raises(FileExistsError):
        check(fixture_path, pin, output)


@pytest.mark.train
def test_actual_grouped_selection_controller(tmp_path):
    pytest.importorskip("sklearn")
    check = runpy.run_path(str(ROOT / "scripts/check_selection.py"))["check"]
    result = check(
        ROOT / "fixtures/grouped-selection.json",
        (ROOT / "fixtures/grouped-selection.sha256").read_text().strip(),
        tmp_path / "result",
    )
    assert result["status"] == "passed" and result["nonconverged"] == 15
    assert len(result["evaluated"]) == 9 and not result["w15_complete"]
