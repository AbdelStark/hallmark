"""Run the fixed authored-marker comparison pipeline; no real measurement admission."""

import hashlib
import json
import sys
from pathlib import Path

from hallmark._worker import json_new
from hallmark.baselines import baseline_runtime, split_rows, training_rows
from hallmark.cli import _Parser
from hallmark.comparison import calibrate_fitted, evaluate_fitted
from hallmark.contracts import Record
from hallmark.data import validate_splits
from hallmark.errors import HallmarkError, sanitize_exception
from hallmark.integrity import parse_json, read_bytes
from hallmark.selection import SelectionPlan, fit_candidate, grouped_selection


def check(path, expected, output=None):
    raw = read_bytes(path)
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("fixture pin mismatch")
    fixture = parse_json(raw.decode("utf-8"))
    if (
        fixture["schema_id"] != "hallmark/grouped-selection-fixture/1"
        or fixture["fixture_only"] is not True
    ):
        raise ValueError("not the software fixture")
    plan = SelectionPlan.model_validate_json(json.dumps(fixture["plan"]))
    if plan.bounds.policy_id != "fixture.selection":
        raise ValueError("not the fixture policy")
    training, calibration, test = (
        tuple(Record.model_validate_json(json.dumps(r)) for r in fixture[key])
        for key in ("records", "calibration_records", "test_records")
    )
    training_rows(training, plan.bounds)
    split_rows(calibration, plan.bounds, "calibration")
    split_rows(test, plan.bounds, "test")
    validate_splits((*training, *calibration, *test))
    if output is None:
        return {
            "schema_id": "hallmark/grouped-selection-contract-result/1",
            "status": "matched",
            "training_executed": False,
            "fixture_only": True,
        }
    output.mkdir(mode=0o700)
    completed = []
    try:
        json_new(output / "fixture.json", fixture)
        json_new(output / "environment.json", baseline_runtime())
        selection = grouped_selection(training, plan)
        json_new(output / "selection.json", selection)
        by_id = {c.id: c for c in plan.candidates}
        for winner in selection["selected"]:
            if winner["candidate"] is None:
                raise ValueError("fixture has no eligible candidate")
            directory = output / f"{winner['kind']}-{winner['seed']}"
            directory.mkdir(mode=0o700)
            fitted = fit_candidate(training, by_id[winner["candidate"]], plan, winner["seed"])
            # Retain the final model identity before calibrating its threshold.
            json_new(directory / "fit.json", fitted.record)
            fit_pin = fitted.record["identity"]
            calibrated = calibrate_fitted(
                fitted, calibration, expected_fit=fit_pin, target_fpr="0.01"
            )
            json_new(directory / "calibration.json", calibrated.model_dump(mode="json"))
            evaluation = evaluate_fitted(
                fitted,
                calibrated,
                test,
                expected_fit=fit_pin,
                expected_calibration=calibrated.identity(),
            )
            json_new(directory / "evaluation.json", evaluation)
            completed.append(
                {
                    **winner,
                    "fit": fit_pin,
                    "calibration": calibrated.identity(),
                    "primary": evaluation["primary"],
                    "all_rows": evaluation["all_rows"],
                }
            )
        rotations = [r for c in selection["candidates"] for r in c["rotations"]]
        if len(rotations) != 75 or len(completed) != 9:
            raise ValueError("incomplete fixture roster")
        if sum(r["status"] == "nonconverged" for r in rotations) != 15:
            raise ValueError("missing convergence failure evidence")
        if sum(r["status"] == "passed" for r in rotations) != 60:
            raise ValueError("failed fixture fit")
        result = {
            "schema_id": "hallmark/grouped-selection-fixture-result/1",
            "status": "passed",
            "fixture_only": True,
            "quality_claim": False,
            "fixture_sha256": expected,
            "rotations": len(rotations),
            "nonconverged": 15,
            "evaluated": completed,
            "unavailable": [r["kind"] for r in selection["roster"] if r["status"] == "unavailable"],
            "w15_complete": False,
        }
        json_new(output / "result.json", result)
        return result
    except BaseException:
        json_new(
            output / "failure.json",
            {
                "schema_id": "hallmark/grouped-selection-fixture-failure/1",
                "status": "failed",
                "completed": completed,
            },
        )
        raise


def main():
    parser = _Parser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--expected-fixture", required=True)
    parser.add_argument("--output", type=Path)
    try:
        args = parser.parse_args()
        result = check(args.fixture, args.expected_fixture, args.output)
    except (Exception, KeyboardInterrupt) as exc:
        error = (
            HallmarkError("RESOURCE_EXHAUSTED", "execute")
            if isinstance(exc, KeyboardInterrupt)
            else sanitize_exception(exc, stage="execute")
        )
        print(json.dumps(error.as_dict()), file=sys.stderr)
        return error.exit_code
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
