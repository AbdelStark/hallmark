"""Caller-pinned native calibration/evaluation after train-only candidate selection."""

import hashlib
from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator

from hallmark.admission import DecimalString
from hallmark.baselines import split_rows
from hallmark.contracts import Digest, Identifier, Record
from hallmark.evaluation import metrics
from hallmark.integrity import commitment
from hallmark.mlp_training import _TrainingRecord
from hallmark.selection import Fitted, representatives, score_fitted, threshold
from hallmark.wire import WireError


class ComparisonCalibration(_TrainingRecord):
    schema_id: Literal["hallmark/comparison-calibration/1"]
    fit: Digest
    calibration: Digest
    target_fpr: DecimalString
    score_type: Literal["integer", "float64"]
    threshold: int | float
    groups: Annotated[tuple[Identifier, ...], Field(strict=False, min_length=1, max_length=100000)]
    prompts: Annotated[tuple[Digest, ...], Field(strict=False, min_length=1, max_length=100000)]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if (
            self.target_fpr not in ("0.01", "0.0035")
            or self.groups != tuple(sorted(set(self.groups)))
            or self.prompts != tuple(sorted(set(self.prompts)))
            or (
                self.score_type == "integer"
                and (type(self.threshold) is not int or not -(2**31) <= self.threshold < 2**31)
            )
            or (self.score_type == "float64" and type(self.threshold) is not float)
        ):
            raise ValueError("invalid calibrated comparison")
        return self


def _checked_fit(fitted: Fitted, expected: str) -> None:
    if type(fitted) is not Fitted or type(expected) is not str:
        raise WireError("INPUT_INVALID")
    record = {k: v for k, v in fitted.record.items() if k != "identity"}
    if (
        commitment("comparison-fit", record) != expected
        or fitted.record.get("identity") != expected
        or fitted.record.get("converged") is not True
        or fitted.record.get("model") != fitted.model.model_dump(mode="json")
        or fitted.record.get("bounds") != fitted.bounds.model_dump(mode="json")
        or fitted.mlp_config is not None
        and fitted.record.get("config") != fitted.mlp_config.model_dump(mode="json")
    ):
        raise WireError("INPUT_INVALID")


def _disjoint(
    rows: tuple[Record, ...],
    groups: list[str] | tuple[str, ...],
    prompts: list[str] | tuple[str, ...],
) -> None:
    group_set, prompt_set = set(groups), set(prompts)
    if any(
        r.group_id in group_set or hashlib.sha256(r.prompt.encode()).hexdigest() in prompt_set
        for r in rows
    ):
        raise WireError("INPUT_INVALID")


def calibrate_fitted(
    fitted: Fitted, rows: tuple[Record, ...], *, expected_fit: str, target_fpr: str
) -> ComparisonCalibration:
    """Freeze the native threshold using only separate benign calibration scores."""
    _checked_fit(fitted, expected_fit)
    rows = split_rows(rows, fitted.bounds, "calibration")
    _disjoint(rows, fitted.record["training_groups"], fitted.record["training_prompts"])
    scores = score_fitted(fitted, tuple(r.prompt for r in rows))
    cut = threshold(scores, tuple(r.label for r in rows), target_fpr)
    return ComparisonCalibration(
        schema_id="hallmark/comparison-calibration/1",
        fit=expected_fit,
        calibration=commitment(
            "comparison-calibration-rows", [r.model_dump(mode="json") for r in rows]
        ),
        target_fpr=target_fpr,
        score_type="integer" if type(cut) is int else "float64",
        threshold=cut,
        groups=tuple(sorted({r.group_id for r in rows})),
        prompts=tuple(sorted({hashlib.sha256(r.prompt.encode()).hexdigest() for r in rows})),
    )


def evaluate_fitted(
    fitted: Fitted,
    calibration: ComparisonCalibration,
    rows: tuple[Record, ...],
    *,
    expected_fit: str,
    expected_calibration: str,
) -> dict[str, Any]:
    """Evaluate a frozen decision; admission and once-only run control are caller obligations."""
    _checked_fit(fitted, expected_fit)
    if type(calibration) is not ComparisonCalibration:
        raise WireError("INPUT_INVALID")
    calibration = calibration._validated()
    if (
        type(expected_calibration) is not str
        or calibration.identity() != expected_calibration
        or calibration.fit != expected_fit
    ):
        raise WireError("INPUT_INVALID")
    rows = split_rows(rows, fitted.bounds, "test")
    _disjoint(rows, fitted.record["training_groups"], fitted.record["training_prompts"])
    _disjoint(rows, calibration.groups, calibration.prompts)
    scores = score_fitted(fitted, tuple(r.prompt for r in rows))
    expected_type = int if calibration.score_type == "integer" else float
    if any(type(s) is not expected_type for s in scores):
        raise WireError("INPUT_INVALID")
    predictions: list[dict[str, Any]] = [
        {
            "record_id": r.record_id,
            "group_id": r.group_id,
            "label": r.label,
            "score": s,
            "block": s >= calibration.threshold,
        }
        for r, s in zip(rows, scores, strict=True)
    ]
    chosen = {r.record_id for r in representatives(rows)}
    primary = [p for p in predictions if p["record_id"] in chosen]
    return {
        "schema_id": "hallmark/comparison-evaluation/1",
        "fit": expected_fit,
        "calibration": expected_calibration,
        "test": commitment("comparison-test-rows", [r.model_dump(mode="json") for r in rows]),
        "threshold": calibration.threshold,
        "predictions": predictions,
        "primary": metrics(
            tuple(p["label"] for p in primary), tuple(int(p["block"]) for p in primary), 1
        ),
        "all_rows": metrics(
            tuple(r.label for r in rows), tuple(int(p["block"]) for p in predictions), 1
        ),
        "quality_claim": False,
        "independent_verification": False,
    }
