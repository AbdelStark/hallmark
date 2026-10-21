"""Exercise the core-only frozen report API on authored, correlated software controls."""

import hashlib
import json
import sys
from pathlib import Path

from hallmark.cli import _Parser
from hallmark.comparison import ComparisonCalibration
from hallmark.contracts import Record
from hallmark.errors import sanitize_exception
from hallmark.group_evaluation import (
    GroupReportPlan,
    ReportAnnotation,
    ReportMember,
    ReportObservation,
    ReportPair,
    ReportPrediction,
    ReportUnavailable,
    dataset_identity,
    evaluator_identity,
    group_report,
)
from hallmark.integrity import commitment
from hallmark.selection import threshold


def fixture():
    source = b"Authored correlated software controls; no task-quality labels.\n"
    provenance = b"Synthetic fixture; no adaptive search, human review or model training.\n"
    rows = tuple(
        Record(
            schema_id="hallmark.dataset-record/1",
            record_id=f"r-{i:02d}-{j}",
            group_id=f"g-{i:02d}",
            family_id=f"family-{i % 2}",
            source_id="authored",
            source_revision=hashlib.sha256(source).hexdigest(),
            license_id="fixture",
            policy_id="fixture.group-report",
            split="test",
            language="en",
            prompt=f"marker {i:02d} descendant {j}",
            response="",
            label=i % 2,
        )
        for i in range(12)
        for j in range(3)
    )
    members, observations, pairs = [], {}, []
    for seed in (17, 29, 43):
        for variant in ("float", "native"):
            name = f"toy-{variant}-{seed}"
            fit = commitment("report-fixture-fit", name)
            scores = (1.0, 1.0) if variant == "float" else (2, 2)
            cal = ComparisonCalibration(
                schema_id="hallmark/comparison-calibration/1",
                fit=fit,
                calibration=commitment("fixture-calibration", [seed, variant]),
                target_fpr="0.01",
                score_type="float64" if variant == "float" else "integer",
                threshold=threshold(scores, (0, 0), "0.01"),
                groups=("calibration-group",),
                prompts=(hashlib.sha256(b"calibration").hexdigest(),),
            )
            predictions = []
            for row in rows:
                i = int(row.group_id.split("-")[1])
                # Deliberate float->integer positive regression and benign false positive.
                score = float(2 * row.label) if variant == "float" else 4 * row.label
                if variant == "native" and i == 1:
                    score = 2
                if variant == "native" and i == 2:
                    score = 3
                predictions.append(
                    ReportPrediction(
                        record_id=row.record_id,
                        group_id=row.group_id,
                        label=row.label,
                        score=score,
                        block=score >= cal.threshold,
                    )
                )
            members.append(
                ReportMember(
                    name=name,
                    family="toy",
                    seed=seed,
                    variant=variant,
                    fit=fit,
                    calibration=cal.identity(),
                    score_scale=1 if variant == "float" else 2,
                )
            )
            observations[name] = ReportObservation(
                schema_id="hallmark/report-observation/1",
                calibration=cal,
                predictions=tuple(predictions),
            )
        name = f"encoder-{seed}"
        members.append(
            ReportMember(
                name=name,
                family="encoder",
                seed=seed,
                variant="native",
                fit=None,
                calibration=None,
                score_scale=1,
            )
        )
        observations[name] = ReportUnavailable(
            schema_id="hallmark/report-unavailable/1", reason="W16-not-executed"
        )
        pairs.append(
            ReportPair(left=f"toy-float-{seed}", right=f"toy-native-{seed}", purpose="quantization")
        )
    plan = GroupReportPlan(
        schema_id="hallmark/group-report-plan/1",
        experiment_id="fixture.group-report",
        dataset=dataset_identity(rows),
        source=hashlib.sha256(source).hexdigest(),
        evaluator=evaluator_identity(),
        evidence_class="synthetic",
        adaptive=False,
        provenance=hashlib.sha256(provenance).hexdigest(),
        seeds=(17, 29, 43),
        bootstrap_seed=113,
        resamples=10000,
        roster=tuple(members),
        pairs=tuple(pairs),
        annotations=tuple(
            ReportAnnotation(record_id=r.record_id, obfuscation=None, benign_hard_negative=None)
            for r in rows
        ),
        exclusions=(),
    )
    return plan, rows, observations, source, provenance


def check(output=None):
    plan, rows, observations, source, provenance = fixture()
    if output is not None:
        output.mkdir(mode=0o700)
        # Persist the complete protocol before the first report call.
        (output / "plan.json").write_text(plan.model_dump_json(indent=2) + "\n")
        (output / "plan.id").write_text(plan.identity() + "\n")
    result = group_report(
        plan,
        rows,
        observations,
        expected_plan=plan.identity(),
        source=source,
        provenance=provenance,
    )
    assert len(result["primary_representatives"]) == 12 and result["all_rows_count"] == 36
    assert len(result["members"]) == 9 and len(result["comparisons"]) == 3
    assert all(
        c["bootstrap"]["resamples"] == 10000 and c["drift"]["positive_regressions"] == 1
        for c in result["comparisons"]
    )
    assert not result["quality_claim"] and result["confirmatory_decision"] == "not-evaluated"
    if output is not None:
        (output / "report.json").write_text(
            json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
        )
    return {
        "schema_id": "hallmark/group-report-fixture-result/1",
        "status": "matched",
        "root_groups": 12,
        "descendants": 36,
        "resamples_per_pair": 10000,
        "pairs": 3,
        "seeds": [17, 29, 43],
        "quality_claim": False,
    }


def main():
    parser = _Parser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.output), sort_keys=True, allow_nan=False))
        return 0
    except Exception as exc:
        print(json.dumps(sanitize_exception(exc, stage="execute").as_dict()), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
