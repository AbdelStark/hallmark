"""Fixed, train-internal grouped comparisons; no outer calibration or test input."""

import hashlib
import math
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator

from hallmark.admission import CANDIDATES, DecimalString
from hallmark.baselines import (
    NgramConfig,
    NgramFit,
    TrainingBounds,
    baseline_runtime,
    fit_ngram,
    score_ngram,
    training_identity,
    training_rows,
)
from hallmark.classifier_manifest import ClassifierManifest, InputProfile
from hallmark.contracts import Experiment, Identifier, LinearArtifact, Record
from hallmark.errors import sanitize_exception
from hallmark.evaluation import metrics
from hallmark.integer_mlp import execute_mlp
from hallmark.integrity import commitment
from hallmark.manifests import ArtifactDigest
from hallmark.mlp_export import compile_mlp
from hallmark.mlp_training import (
    MlpCheckpoint,
    MlpFitConfig,
    _TrainingRecord,
    fit_mlp,
    quantize_mlp,
)
from hallmark.openings import TranscriptOpening
from hallmark.reference import score as linear_score
from hallmark.training import train_linear
from hallmark.wire import WireError

KINDS = ("byte-logistic", "char-ngram", "byte-mlp")


class FitCandidate(_TrainingRecord):
    id: Identifier
    kind: Literal["byte-logistic", "char-ngram", "byte-mlp"]
    ngram: NgramConfig | None
    mlp: MlpFitConfig | None

    @model_validator(mode="after")
    def parameters(self) -> Self:
        if (self.ngram is not None) != (self.kind == "char-ngram") or (
            (self.mlp is not None) != (self.kind == "byte-mlp")
        ):
            raise ValueError("candidate config disagrees with family")
        return self


class SelectionPlan(_TrainingRecord):
    schema_id: Literal["hallmark/grouped-selection-plan/1"]
    bounds: TrainingBounds
    chunk_bytes: Annotated[int, Field(ge=1, le=512)]
    seeds: Annotated[tuple[int, ...], Field(strict=False, min_length=3, max_length=3)]
    folds: Annotated[int, Field(ge=5, le=5)]
    target_fpr: DecimalString
    candidates: Annotated[
        tuple[FitCandidate, ...], Field(strict=False, min_length=3, max_length=16)
    ]

    @model_validator(mode="after")
    def roster(self) -> Self:
        if (
            self.target_fpr != "0.01"
            or self.seeds != (17, 29, 43)
            or {c.kind for c in self.candidates} != set(KINDS)
            or len({c.id for c in self.candidates}) != len(self.candidates)
        ):
            raise ValueError("invalid fixed candidate roster")
        for candidate in self.candidates:
            if candidate.mlp is not None and (
                candidate.mlp.policy_id != self.bounds.policy_id
                or candidate.mlp.chunk_bytes != self.chunk_bytes
                or candidate.mlp.max_prompt_bytes != self.bounds.max_prompt_bytes
            ):
                raise ValueError("MLP input contract differs from comparison")
        return self


def grouped_folds(rows: tuple[Record, ...], bounds: TrainingBounds) -> dict[str, int]:
    rows = training_rows(rows, bounds)
    groups = sorted(
        {r.group_id for r in rows},
        key=lambda group: (
            hashlib.sha256(("inj-direct-design/1|fold|" + group).encode()).digest(),
            group,
        ),
    )
    if len(groups) < 5:
        raise WireError("INPUT_INVALID")
    return {group: i % 5 for i, group in enumerate(groups)}


def representatives(rows: tuple[Record, ...]) -> tuple[Record, ...]:
    chosen: dict[str, Record] = {}

    def key(row: Record) -> tuple[bytes, str]:
        return hashlib.sha256(
            ("inj-direct-design/1|representative|" + row.record_id).encode()
        ).digest(), row.record_id

    for row in rows:
        if row.group_id not in chosen or key(row) < key(chosen[row.group_id]):
            chosen[row.group_id] = row
    return tuple(chosen[group] for group in sorted(chosen))


def threshold(
    scores: tuple[int, ...] | tuple[float, ...], labels: tuple[int, ...], rate: str
) -> int | float:
    """Exact decimal allowance, blocking equality, and no integer/float coercion."""
    if (
        type(scores) is not tuple
        or type(labels) is not tuple
        or not scores
        or len(scores) != len(labels)
        or any(type(y) is not int or y not in (0, 1) for y in labels)
        or type(rate) is not str
        or rate not in ("0.01", "0.0035")
        or len({type(s) for s in scores}) != 1
        or any(
            type(s) not in (int, float)
            or type(s) is int
            and not -(2**31) <= s < 2**31
            or type(s) is float
            and not math.isfinite(s)
            for s in scores
        )
    ):
        raise WireError("INPUT_INVALID")
    integer = type(scores[0]) is int
    benign = sorted((s for s, y in zip(scores, labels, strict=True) if y == 0), reverse=True)
    if not benign:
        raise WireError("INPUT_INVALID")
    allowance = Fraction(rate) * len(benign)
    boundary = benign[allowance.numerator // allowance.denominator]
    value = int(boundary) + 1 if integer else math.nextafter(float(boundary), math.inf)
    if not math.isfinite(value) or integer and not -(2**31) <= value < 2**31:
        raise WireError("INPUT_INVALID")
    return value


@dataclass(frozen=True)
class Fitted:
    """In-process fit state. Persist its explicit record, never pickle this object."""

    record: dict[str, Any]
    model: NgramFit | LinearArtifact | MlpCheckpoint
    bounds: TrainingBounds
    mlp_config: MlpFitConfig | None = None


def fit_candidate(
    rows: tuple[Record, ...], candidate: FitCandidate, plan: SelectionPlan, seed: int
) -> Fitted:
    if type(candidate) is not FitCandidate or type(plan) is not SelectionPlan:
        raise WireError("INPUT_INVALID")
    candidate, plan = candidate._validated(), plan._validated()
    if type(seed) is not int or seed not in plan.seeds or candidate not in plan.candidates:
        raise WireError("INPUT_INVALID")
    rows = training_rows(rows, plan.bounds)
    training = training_identity(rows)
    record: dict[str, Any] = {
        "schema_id": "hallmark/comparison-fit/1",
        "candidate": candidate.model_dump(mode="json"),
        "plan": plan.identity(),
        "seed": seed,
        "training": training,
        "runtime": commitment("baseline-runtime", baseline_runtime()),
        "selector_source": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "bounds": plan.bounds.model_dump(mode="json"),
        "backend_enrolled": False,
        "training_groups": sorted({r.group_id for r in rows}),
        "training_prompts": sorted({hashlib.sha256(r.prompt.encode()).hexdigest() for r in rows}),
    }
    mlp_config = None
    model: NgramFit | LinearArtifact | MlpCheckpoint
    if candidate.kind == "char-ngram":
        assert candidate.ngram is not None
        model = fit_ngram(rows, candidate.ngram, plan.bounds, seed=seed)
        record.update(converged=model.converged, optimizer=model.optimizer, resume=model.resume)
    elif candidate.kind == "byte-mlp":
        assert candidate.mlp is not None
        mlp_config = candidate.mlp.model_copy(update={"seed": seed})._validated()
        model, history = fit_mlp(rows, mlp_config)
        record.update(
            converged=model.converged,
            optimizer="float64-full-batch-sgd-momentum",
            resume="pinned-mlp-checkpoint",
            config=mlp_config.model_dump(mode="json"),
            epochs=[sample.model_dump(mode="json") for sample in history],
        )
    else:
        config = Experiment(
            schema_id="hallmark.experiment/1",
            experiment_id=candidate.id,
            dataset="supplied-training-rows",
            dataset_sha256=training,
            policy_id=plan.bounds.policy_id,
            scope="prompt",
            seed=seed,
            chunk_bytes=plan.chunk_bytes,
            target_fpr=0.01,
            alpha=0.05,
            approved_licenses=tuple(sorted({r.license_id for r in rows})),
            approved_sources=tuple(sorted({r.source_id for r in rows})),
            evidence_class="research",
        )
        model, metadata = train_linear(rows, config)
        record.update(
            converged=True,
            optimizer="legacy-liblinear-float64",
            resume="not-supported-cold-fit",
            config=config.model_dump(mode="json"),
            metadata=metadata,
        )
    record["model"] = model.model_dump(mode="json")
    record["identity"] = commitment("comparison-fit", record)
    return Fitted(record, model, plan.bounds, mlp_config)


def score_fitted(fitted: Fitted, prompts: tuple[str, ...]) -> tuple[int, ...] | tuple[float, ...]:
    if (
        type(fitted) is not Fitted
        or type(prompts) is not tuple
        or any(type(p) is not str for p in prompts)
    ):
        raise WireError("INPUT_INVALID")
    bounds = fitted.bounds._validated()
    if (
        len(prompts) > bounds.max_rows
        or any(len(p.encode("utf-8")) > bounds.max_prompt_bytes for p in prompts)
        or sum(len(p.encode("utf-8")) for p in prompts) > bounds.max_total_bytes
    ):
        raise WireError("LIMIT_EXCEEDED")
    if isinstance(fitted.model, NgramFit):
        return tuple(score_ngram(fitted.model.model, prompt) for prompt in prompts)
    if isinstance(fitted.model, LinearArtifact):
        return tuple(linear_score(fitted.model, prompt) for prompt in prompts)
    assert fitted.mlp_config is not None
    q = quantize_mlp(fitted.model, fitted.mlp_config)
    profile = InputProfile(
        schema_id="hallmark/input-profile/1",
        encoding="utf8-bytes",
        tokenizer_files=(),
        prefix_tokens=(),
        suffix_tokens=(),
        chunk_size=fitted.mlp_config.chunk_bytes,
        overlap=0,
        max_units=fitted.mlp_config.max_prompt_bytes,
        padding_id=0,
        padding_side="right",
    )
    program, arithmetic, weights, parameters = compile_mlp(
        q.weights,
        profile,
        first_fraction=q.first_fraction,
        hidden_fraction=0,
        last_fraction=q.last_fraction,
    )
    # Research native arithmetic only: these markers do not enroll a proof backend.
    classifier = ClassifierManifest(
        schema_id="hallmark/classifier/1",
        kind="mlp",
        program=program.identity(),
        weights=ArtifactDigest(program.weights.sha256),
        tokenizer=None,
        input_profile=profile.identity(),
        arithmetic=arithmetic.identity(),
        threshold=0,
        scope="prompt",
        labels=("benign", "positive"),
        backend=ArtifactDigest(b"b" * 32),
        verifier_key=ArtifactDigest(b"k" * 32),
        setup=ArtifactDigest(b"s" * 32),
    )
    return tuple(
        execute_mlp(
            TranscriptOpening(
                schema_id="hallmark/transcript-opening/1",
                salt=b"s" * 32,
                system_ref=ArtifactDigest(b"c" * 32),
                prompt=prompt,
                response="",
            ),
            classifier,
            program,
            profile,
            arithmetic,
            weights=weights,
            parameters=parameters,
        ).score
        for prompt in prompts
    )


def grouped_selection(rows: tuple[Record, ...], plan: SelectionPlan) -> dict[str, Any]:
    if type(plan) is not SelectionPlan:
        raise WireError("INPUT_INVALID")
    plan = plan._validated()
    rows = training_rows(rows, plan.bounds)
    folds = grouped_folds(rows, plan.bounds)
    results = []
    for seed in plan.seeds:
        for candidate in sorted(plan.candidates, key=lambda c: c.id):
            rotations = []
            for fold in range(5):
                fitting = tuple(r for r in rows if folds[r.group_id] not in (fold, (fold + 1) % 5))
                calibration = tuple(r for r in rows if folds[r.group_id] == (fold + 1) % 5)
                validation = representatives(tuple(r for r in rows if folds[r.group_id] == fold))
                result: dict[str, Any] = {
                    "fold": fold,
                    "fitting_ids": [r.record_id for r in fitting],
                    "threshold_ids": [r.record_id for r in calibration],
                    "validation_ids": [r.record_id for r in validation],
                }
                try:
                    if {r.label for r in validation} != {0, 1}:
                        raise WireError("INPUT_INVALID")
                    trained = fit_candidate(fitting, candidate, plan, seed)
                    result["fit"] = trained.record
                    scores = score_fitted(trained, tuple(r.prompt for r in calibration))
                    cut = threshold(scores, tuple(r.label for r in calibration), plan.target_fpr)
                    scores = score_fitted(trained, tuple(r.prompt for r in validation))
                    decisions = tuple(int(s >= cut) for s in scores)
                    result.update(
                        status="passed" if trained.record["converged"] else "nonconverged",
                        threshold=cut,
                        scores=list(scores),
                        decisions=list(decisions),
                        metrics=metrics(tuple(r.label for r in validation), decisions, 1),
                    )
                except (ValueError, WireError, RuntimeError) as exc:
                    result.update(
                        status="failed",
                        error=sanitize_exception(exc, stage="execute").as_dict(),
                        cause=(
                            "legacy-single-chunk-training-limit"
                            if candidate.kind == "byte-logistic"
                            and any(len(r.prompt.encode()) > plan.chunk_bytes for r in fitting)
                            else "fit-threshold-or-export-rejection"
                        ),
                    )
                rotations.append(result)
            result = {
                "candidate": candidate.id,
                "kind": candidate.kind,
                "seed": seed,
                "rotations": rotations,
            }
            if all(r["status"] == "passed" for r in rotations):
                counts = {
                    key: sum(r["metrics"][key] for r in rotations)
                    for key in ("tp", "fp", "tn", "fn")
                }
                result["counts"] = counts
                result["eligible"] = (
                    counts["tp"] + counts["fn"] > 0 and counts["fp"] + counts["tn"] > 0
                )
            else:
                result["eligible"] = False
            results.append(result)
    selected = []
    for seed in plan.seeds:
        for kind in KINDS:
            eligible = [
                r for r in results if r["eligible"] and r["seed"] == seed and r["kind"] == kind
            ]

            def rank(item: dict[str, Any]) -> tuple[Fraction, Fraction, str]:
                c = item["counts"]
                return (
                    -Fraction(c["tp"], c["tp"] + c["fn"]),
                    Fraction(c["fp"], c["fp"] + c["tn"]),
                    item["candidate"],
                )

            winner = min(eligible, key=rank)["candidate"] if eligible else None
            selected.append({"seed": seed, "kind": kind, "candidate": winner})
    labels = tuple(r.label for r in representatives(rows))
    return {
        "schema_id": "hallmark/grouped-selection-result/1",
        "plan": plan.identity(),
        "training": training_identity(rows),
        "folds": folds,
        "candidates": results,
        "selected": selected,
        "quality_claim": False,
        "roster": [
            {
                "kind": kind,
                "status": (
                    "fixed-control"
                    if kind in ("pass-all", "block-all")
                    else "implemented"
                    if kind in KINDS
                    else "unavailable"
                ),
            }
            for kind in CANDIDATES
        ],
        "controls": {
            kind: metrics(labels, (value,) * len(labels), 1)
            for kind, value in (("pass-all", 0), ("block-all", 1))
        },
    }
