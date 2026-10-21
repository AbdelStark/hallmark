"""Frozen descriptive reports over paired root-group representatives, never model selection."""

import hashlib
import math
import platform
import random
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator

from hallmark.comparison import ComparisonCalibration
from hallmark.contracts import Digest, Identifier, Record
from hallmark.evaluation import metrics, wilson_interval
from hallmark.integrity import commitment
from hallmark.mlp_training import _TrainingRecord
from hallmark.selection import representatives
from hallmark.wire import WireError

Seed = Annotated[int, Field(ge=0, lt=2**32)]


class ReportMember(_TrainingRecord):
    name: Identifier
    family: Identifier
    seed: Seed | None
    variant: Literal["native", "float"]
    fit: Digest | None
    calibration: Digest | None
    score_scale: Annotated[int, Field(ge=1, le=2**24)]


class ReportPair(_TrainingRecord):
    left: Identifier
    right: Identifier
    purpose: Literal["comparison", "quantization"]


class ReportAnnotation(_TrainingRecord):
    record_id: Identifier
    obfuscation: Identifier | None
    benign_hard_negative: bool | None


class ReportExclusion(_TrainingRecord):
    group_id: Identifier
    reason: Identifier


class GroupReportPlan(_TrainingRecord):
    schema_id: Literal["hallmark/group-report-plan/1"]
    experiment_id: Identifier
    dataset: Digest
    source: Digest
    evaluator: Digest
    evidence_class: Literal["synthetic", "exploratory", "confirmatory"]
    adaptive: bool
    provenance: Digest
    seeds: Annotated[tuple[Seed, ...], Field(strict=False, min_length=3, max_length=3)]
    bootstrap_seed: Seed
    resamples: Literal[10000]
    roster: Annotated[tuple[ReportMember, ...], Field(strict=False, min_length=1, max_length=32)]
    pairs: Annotated[tuple[ReportPair, ...], Field(strict=False, max_length=32)]
    annotations: Annotated[tuple[ReportAnnotation, ...], Field(strict=False, max_length=100000)]
    exclusions: Annotated[tuple[ReportExclusion, ...], Field(strict=False, max_length=100000)]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        names = {m.name: m for m in self.roster}
        families: dict[tuple[str, str], list[int | None]] = {}
        for member in self.roster:
            families.setdefault((member.family, member.variant), []).append(member.seed)
        if (
            self.seeds != (17, 29, 43)
            or len(names) != len(self.roster)
            or any(
                seeds != [None]
                and sorted(s for s in seeds if s is not None) != list(self.seeds)
                or None in seeds
                and seeds != [None]
                for seeds in families.values()
            )
            or self.adaptive
            and self.evidence_class == "confirmatory"
            or len({a.record_id for a in self.annotations}) != len(self.annotations)
            or len({e.group_id for e in self.exclusions}) != len(self.exclusions)
            or len({(p.left, p.right, p.purpose) for p in self.pairs}) != len(self.pairs)
        ):
            raise ValueError("invalid frozen report roster or provenance")
        for pair in self.pairs:
            if pair.left not in names or pair.right not in names or pair.left == pair.right:
                raise ValueError("unknown or repeated comparison member")
            left, right = names[pair.left], names[pair.right]
            if left.seed is not None and right.seed is not None and left.seed != right.seed:
                raise ValueError("training seeds are not independent test examples")
            if pair.purpose == "quantization" and (
                left.family != right.family
                or left.seed != right.seed
                or (left.variant, right.variant) != ("float", "native")
                or left.score_scale != 1
            ):
                raise ValueError("quantization pair must bind float and native counterparts")
        return self


class ReportPrediction(_TrainingRecord):
    record_id: Identifier
    group_id: Identifier
    label: Annotated[int, Field(ge=0, le=1)]
    score: Annotated[int | float, Field(ge=-1e12, le=1e12)]
    block: bool


class ReportObservation(_TrainingRecord):
    schema_id: Literal["hallmark/report-observation/1"]
    calibration: ComparisonCalibration
    predictions: Annotated[
        tuple[ReportPrediction, ...], Field(strict=False, min_length=1, max_length=100000)
    ]


class ReportUnavailable(_TrainingRecord):
    schema_id: Literal["hallmark/report-unavailable/1"]
    reason: Identifier


def evaluator_identity() -> str:
    """Pin the implementation, including transitive local validation/selection helpers."""
    return commitment(
        "group-report-evaluator/1",
        {
            "python": platform.python_version(),
            "random": hashlib.sha256(Path(random.__file__).read_bytes()).hexdigest(),
            "files": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(Path(__file__).parent.glob("*.py"))
            },
        },
    )


def dataset_identity(rows: tuple[Record, ...]) -> str:
    return commitment("group-report-dataset/1", [r.model_dump(mode="json") for r in rows])


def _counts(
    rows: tuple[Record, ...], blocks: dict[str, bool], *, independent: bool
) -> dict[str, Any]:
    if rows:
        result = metrics(
            tuple(r.label for r in rows), tuple(int(blocks[r.record_id]) for r in rows), 1
        )
    else:
        result = dict(
            n=0,
            tp=0,
            fp=0,
            tn=0,
            fn=0,
            tpr=None,
            fpr=None,
            tpr_wilson_interval=None,
            fpr_wilson_interval=None,
            zero_fp_one_sided_upper=None,
            confidence_level=0.95,
        )
    result["interval_scope"] = (
        "conditional-on-independent-root-groups"
        if independent
        else "unavailable-correlated-descendants"
    )
    if not independent:
        for key in ("tpr_wilson_interval", "fpr_wilson_interval", "zero_fp_one_sided_upper"):
            result[key] = None
    result["power_status"] = (
        "insufficient-evidence"
        if result["fp"] + result["tn"] < 7831 or result["tp"] + result["fn"] < 1375
        else "requires-actual-count-power-calculation"
    )
    if not independent:
        result["power_status"] = "not-applicable-correlated-descendants"
    return result


def _length(row: Record) -> str:
    size = len(row.prompt.encode("utf-8"))
    return (
        "0"
        if size == 0
        else "1-512"
        if size <= 512
        else "513-4096"
        if size <= 4096
        else "4097-32768"
    )


def _bootstrap(cells: tuple[int, ...], seed: int) -> dict[str, Any]:
    """Multinomial root-group draws from the eight joint (label,left,right) cells."""
    rng = random.Random(seed)
    total = sum(cells)
    samples: dict[str, list[float]] = {"tpr": [], "fpr": []}
    for _ in range(10000):
        remaining, population = total, total
        draws = []
        for count in cells[:-1]:
            draw = rng.binomialvariate(remaining, count / population) if population else 0
            draws.append(draw)
            remaining -= draw
            population -= count
        draws.append(remaining)
        for name, offset in (("fpr", 0), ("tpr", 4)):
            n = sum(draws[offset : offset + 4])
            if n:
                samples[name].append((draws[offset + 1] - draws[offset + 2]) / n)
    result = {}
    for name, values in samples.items():
        values.sort()
        # Nearest-rank percentile interval; retain every undefined-denominator draw count.
        result[name] = {
            "delta_interval": [
                values[math.ceil(0.025 * len(values)) - 1],
                values[math.ceil(0.975 * len(values)) - 1],
            ]
            if values
            else None,
            "distribution": commitment("group-bootstrap-sorted-deltas/1", values),
            "valid_resamples": len(values),
            "null_resamples": 10000 - len(values),
        }
    return {
        "schema_id": "hallmark/paired-group-bootstrap/1",
        "resamples": 10000,
        "seed": seed,
        "method": "paired-root-representative-multinomial-percentile",
        "delta_direction": "right-minus-left",
        "unit": "root-group",
        "joint_cell_counts": list(cells),
        "nominal_confidence_level": 0.95,
        "multiplicity_adjusted": False,
        **result,
    }


def group_report(
    plan: GroupReportPlan,
    rows: tuple[Record, ...],
    observations: dict[str, ReportObservation | ReportUnavailable],
    *,
    expected_plan: str,
    source: bytes,
    provenance: bytes,
) -> dict[str, Any]:
    """Consume a caller-frozen plan and scores; no fitting, scoring or calibration occurs here."""
    if type(plan) is not GroupReportPlan or type(rows) is not tuple or not 0 < len(rows) <= 100000:
        raise WireError("INPUT_INVALID")
    plan = plan._validated()
    if any(type(r) is not Record for r in rows):
        raise WireError("INPUT_INVALID")
    rows = tuple(Record.model_validate(r.model_dump()) for r in rows)
    names = {m.name: m for m in plan.roster}
    row_map = {r.record_id: r for r in rows}
    excluded = {e.group_id for e in plan.exclusions}
    if (
        plan.identity() != expected_plan
        or plan.evaluator != evaluator_identity()
        or plan.dataset != dataset_identity(rows)
        or type(source) is not bytes
        or len(source) > 8 * 1024**2
        or hashlib.sha256(source).hexdigest() != plan.source
        or type(provenance) is not bytes
        or len(provenance) > 8 * 1024**2
        or hashlib.sha256(provenance).hexdigest() != plan.provenance
        or type(observations) is not dict
        or set(observations) != set(names)
        or len(row_map) != len(rows)
        or {r.split for r in rows} != {"test"}
        or len({r.policy_id for r in rows}) != 1
        or any(len(r.prompt.encode()) > 32768 or r.response for r in rows)
        or not excluded <= {r.group_id for r in rows}
        or {a.record_id for a in plan.annotations} != set(row_map)
        or any(
            a.benign_hard_negative is True and row_map[a.record_id].label != 0
            for a in plan.annotations
            if a.record_id in row_map
        )
    ):
        raise WireError("INPUT_INVALID")
    # Exact prompts cannot claim independent groups; semantic lineage needs external review.
    prompts: dict[str, str] = {}
    for row in rows:
        if row.prompt in prompts and prompts[row.prompt] != row.group_id:
            raise WireError("INPUT_INVALID")
        prompts[row.prompt] = row.group_id
    included = tuple(r for r in rows if r.group_id not in excluded)
    if not included:
        raise WireError("INPUT_INVALID")
    primary = representatives(included)
    annotations = {a.record_id: a for a in plan.annotations}
    slice_ids: dict[tuple[str, str], set[str]] = {
        ("length", v): set() for v in ("0", "1-512", "513-4096", "4097-32768")
    }
    for row in included:
        annotation = annotations[row.record_id]
        for dimension, value in (
            ("language", row.language),
            ("source", row.source_id),
            ("family", row.family_id),
            ("length", _length(row)),
            ("obfuscation", annotation.obfuscation or "unavailable"),
            (
                "benign-hard-negative",
                "unavailable"
                if annotation.benign_hard_negative is None
                else str(annotation.benign_hard_negative).lower(),
            ),
        ):
            slice_ids.setdefault((dimension, value), set()).add(row.record_id)
    if len(slice_ids) > 512:
        raise WireError("LIMIT_EXCEEDED")
    results: dict[str, Any] = {}
    checked: dict[str, ReportObservation] = {}
    for name, member in names.items():
        observation = observations[name]
        if type(observation) is ReportUnavailable:
            observation = observation._validated()
            results[name] = {
                "status": "unavailable",
                "reason": observation.reason,
                "input": observation.identity(),
                "seed": member.seed,
            }
            continue
        if type(observation) is not ReportObservation:
            raise WireError("INPUT_INVALID")
        observation = observation._validated()
        cal = observation.calibration
        predictions = {p.record_id: p for p in observation.predictions}
        if (
            member.fit != cal.fit
            or member.calibration != cal.identity()
            or member.variant == "float"
            and cal.score_type != "float64"
            or cal.score_type == "float64"
            and member.score_scale != 1
            or set(predictions) != set(row_map)
            or len(predictions) != len(observation.predictions)
            or {r.group_id for r in rows} & set(cal.groups)
            or {hashlib.sha256(r.prompt.encode()).hexdigest() for r in rows} & set(cal.prompts)
            or any(
                p.group_id != row_map[p.record_id].group_id
                or p.label != row_map[p.record_id].label
                or type(p.score) is not (int if cal.score_type == "integer" else float)
                or cal.score_type == "integer"
                and not -(2**31) <= p.score < 2**31
                or p.block != (p.score >= cal.threshold)
                for p in observation.predictions
            )
        ):
            raise WireError("INPUT_INVALID")
        checked[name] = observation
        blocks = {rid: p.block for rid, p in predictions.items()}
        slices: list[dict[str, Any]] = [
            {
                "dimension": d,
                "value": v,
                "primary": _counts(
                    tuple(r for r in primary if r.record_id in ids), blocks, independent=True
                ),
                "all_rows": _counts(
                    tuple(r for r in included if r.record_id in ids), blocks, independent=False
                ),
            }
            for (d, v), ids in sorted(slice_ids.items())
        ]
        results[name] = {
            "status": "reported",
            "seed": member.seed,
            "variant": member.variant,
            "input": observation.identity(),
            "fit": member.fit,
            "calibration": member.calibration,
            "threshold": cal.threshold,
            "primary": _counts(primary, blocks, independent=True),
            "all_rows": _counts(included, blocks, independent=False),
            "slices": slices,
            "worst_slice": {
                "max_fpr": max(
                    (s["primary"]["fpr"] for s in slices if s["primary"]["fpr"] is not None),
                    default=None,
                ),
                "min_tpr": min(
                    (s["primary"]["tpr"] for s in slices if s["primary"]["tpr"] is not None),
                    default=None,
                ),
                "scope": "descriptive-overlapping-slices-no-multiplicity-correction",
            },
        }
    comparisons = []
    for pair in plan.pairs:
        item: dict[str, Any] = pair.model_dump(mode="json")
        if pair.left not in checked or pair.right not in checked:
            comparisons.append(item | {"status": "unavailable"})
            continue
        left = {p.record_id: p for p in checked[pair.left].predictions}
        right = {p.record_id: p for p in checked[pair.right].predictions}
        counts = Counter(
            4 * r.label + 2 * left[r.record_id].block + right[r.record_id].block for r in primary
        )
        cells = tuple(counts[i] for i in range(8))
        bootstrap = _bootstrap(cells, plan.bootstrap_seed)
        item.update(status="reported", bootstrap=bootstrap, root_groups=len(primary))
        item["observed_delta"] = {
            m: results[pair.right]["primary"][m] - results[pair.left]["primary"][m]
            if results[pair.left]["primary"][m] is not None
            else None
            for m in ("fpr", "tpr")
        }
        if pair.purpose == "quantization":
            if (
                checked[pair.left].calibration.score_type,
                checked[pair.right].calibration.score_type,
            ) != ("float64", "integer"):
                raise WireError("INPUT_INVALID")
            positives = sum(cells[4:])
            item["drift"] = {
                "positive_regressions": cells[6],
                "positive_improvements": cells[5],
                "negative_block_to_pass": cells[2],
                "negative_pass_to_block": cells[1],
                "positive_regression_rate": cells[6] / positives if positives else None,
                "positive_regression_nominal_wilson": wilson_interval(cells[6], positives),
                "net_tpr_loss": (cells[6] - cells[5]) / positives if positives else None,
                "max_primary_score_error": max(
                    abs(
                        right[r.record_id].score / names[pair.right].score_scale
                        - left[r.record_id].score
                    )
                    for r in primary
                ),
                "confirmatory_regression_bound": None,
            }
        comparisons.append(item)
    summaries = []
    for family, variant in sorted({(m.family, m.variant) for m in plan.roster}):
        members = [m for m in plan.roster if (m.family, m.variant) == (family, variant)]
        complete = all(results[m.name]["status"] == "reported" for m in members)
        summaries.append(
            {
                "family": family,
                "variant": variant,
                "members": [m.name for m in members],
                "all_seeds_available": complete,
                "method": "median-across-declared-seeds-no-pooling",
                **{
                    metric: median(results[m.name]["primary"][metric] for m in members)
                    if complete
                    and all(results[m.name]["primary"][metric] is not None for m in members)
                    else None
                    for metric in ("tpr", "fpr")
                },
            }
        )
    return {
        "schema_id": "hallmark/group-evaluation-report/1",
        "plan": expected_plan,
        "experiment_id": plan.experiment_id,
        "dataset": plan.dataset,
        "source": plan.source,
        "python": platform.python_version(),
        "evaluator": plan.evaluator,
        "provenance": plan.provenance,
        "evidence_class": plan.evidence_class,
        "adaptive": plan.adaptive,
        "primary_representatives": [
            {"group_id": r.group_id, "record_id": r.record_id} for r in primary
        ],
        "excluded_groups": [e.model_dump(mode="json") for e in plan.exclusions],
        "resampling_exclusions": [],
        "all_rows_count": len(included),
        "members": results,
        "seed_summaries": summaries,
        "comparisons": comparisons,
        "threshold_selection": "none-consumes-caller-frozen-calibration",
        "confirmatory_decision": "inconclusive"
        if plan.evidence_class == "confirmatory"
        else "not-evaluated",
        "missing_confirmatory_evidence": [
            "joint-rule-mlp-encoder-decision",
            "15-simultaneous-exact-bounds",
            "actual-count-power-plan",
            "authenticated-admission-and-once-only-test-history",
        ],
        "quality_claim": False,
        "independent_verification": False,
    }
