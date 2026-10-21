"""Train-only character baseline with explicit JSON state; no model or data downloads."""

import hashlib
import importlib
import importlib.metadata
import math
import warnings
from collections import Counter
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, ValidationError, model_validator

from hallmark.contracts import Digest, Identifier, Record
from hallmark.integrity import commitment
from hallmark.mlp_training import _TrainingRecord, runtime_record
from hallmark.wire import WireError


class TrainingBounds(_TrainingRecord):
    policy_id: Identifier
    max_rows: Annotated[int, Field(ge=2, le=100000)]
    max_prompt_bytes: Annotated[int, Field(ge=1, le=32768)]
    max_total_bytes: Annotated[int, Field(ge=1, le=32 * 1024 * 1024)]


def split_rows(
    rows: tuple[Record, ...], bounds: TrainingBounds, split: Literal["train", "calibration", "test"]
) -> tuple[Record, ...]:
    """Reject wrong splits before inspecting their serialized labels or optional imports."""
    if type(bounds) is not TrainingBounds or type(rows) is not tuple:
        raise WireError("INPUT_INVALID")
    bounds = bounds._validated()
    if (
        split not in ("train", "calibration", "test")
        or not 1 <= len(rows) <= bounds.max_rows
        or any(type(row) is not Record or row.split != split for row in rows)
    ):
        raise WireError("INPUT_INVALID")
    total = 0
    ids: set[str] = set()
    prompts: dict[str, str] = {}
    for row in rows:
        try:
            Record.model_validate(row.model_dump())
        except ValidationError:
            raise WireError("INPUT_INVALID") from None
        if row.policy_id != bounds.policy_id or row.response or row.language != "en":
            raise WireError("INPUT_INVALID")
        if row.record_id in ids or prompts.setdefault(row.prompt, row.group_id) != row.group_id:
            raise WireError("INPUT_INVALID")
        ids.add(row.record_id)
        size = len(row.prompt.encode("utf-8"))
        total += size
        if size > bounds.max_prompt_bytes or total > bounds.max_total_bytes:
            raise WireError("LIMIT_EXCEEDED")
    return tuple(sorted(rows, key=lambda row: row.record_id))


def training_rows(rows: tuple[Record, ...], bounds: TrainingBounds) -> tuple[Record, ...]:
    rows = split_rows(rows, bounds, "train")
    if {row.label for row in rows} != {0, 1}:
        raise WireError("INPUT_INVALID")
    return rows


def training_identity(rows: tuple[Record, ...]) -> str:
    return commitment("baseline-training-rows", [row.model_dump(mode="json") for row in rows])


class NgramConfig(_TrainingRecord):
    schema_id: Literal["hallmark/ngram-fit-config/1"]
    min_n: Annotated[int, Field(ge=1, le=5)]
    max_n: Annotated[int, Field(ge=1, le=5)]
    max_features: Annotated[int, Field(ge=1, le=65536)]
    max_events: Annotated[int, Field(ge=1, le=4_194_304)]
    c: Annotated[float, Field(gt=0, le=1000)]
    tolerance: Annotated[float, Field(ge=1e-12, le=1)]
    max_iter: Annotated[int, Field(ge=1, le=10000)]

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.min_n > self.max_n:
            raise ValueError("inverted n-gram range")
        return self


class NgramModel(_TrainingRecord):
    schema_id: Literal["hallmark/character-logistic/1"]
    min_n: Annotated[int, Field(ge=1, le=5)]
    max_n: Annotated[int, Field(ge=1, le=5)]
    max_prompt_bytes: Annotated[int, Field(ge=1, le=32768)]
    vocabulary: Annotated[tuple[str, ...], Field(strict=False, min_length=1, max_length=65536)]
    coefficients: Annotated[tuple[float, ...], Field(strict=False, min_length=1, max_length=65536)]
    intercept: float

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if (
            self.min_n > self.max_n
            or len(self.vocabulary) != len(self.coefficients)
            or self.vocabulary != tuple(sorted(set(self.vocabulary)))
            or any(not self.min_n <= len(term) <= self.max_n for term in self.vocabulary)
        ):
            raise ValueError("invalid vocabulary or coefficient dimensions")
        return self


class NgramFit(_TrainingRecord):
    schema_id: Literal["hallmark/ngram-fit/1"]
    config: NgramConfig
    bounds: TrainingBounds
    seed: Annotated[int, Field(ge=0, lt=2**32)]
    training: Digest
    runtime: Digest
    model: NgramModel
    iterations: Annotated[int, Field(ge=1, le=10000)]
    converged: bool
    optimizer: Literal["liblinear-l2-float64"]
    resume: Literal["not-supported-cold-fit"]


def _counts(text: str, min_n: int, max_n: int) -> Counter[str]:
    return Counter(
        text[index : index + n]
        for n in range(min_n, max_n + 1)
        for index in range(len(text) - n + 1)
    )


def _positions(text: str, min_n: int, max_n: int) -> int:
    return max(1, sum(max(0, len(text) - n + 1) for n in range(min_n, max_n + 1)))


def baseline_runtime() -> dict[str, object]:
    return {
        "numerical": runtime_record(),
        "sklearn": importlib.metadata.version("scikit-learn"),
        "scipy": importlib.metadata.version("scipy"),
        "baseline_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def fit_ngram(
    rows: tuple[Record, ...], config: NgramConfig, bounds: TrainingBounds, *, seed: int
) -> NgramFit:
    if type(config) is not NgramConfig or type(seed) is not int or not 0 <= seed < 2**32:
        raise WireError("INPUT_INVALID")
    config = config._validated()
    rows = training_rows(rows, bounds)
    events = sum(_positions(r.prompt, config.min_n, config.max_n) for r in rows)
    if events > config.max_events:
        raise WireError("LIMIT_EXCEEDED")
    counts = [_counts(r.prompt, config.min_n, config.max_n) for r in rows]
    totals: Counter[str] = Counter()
    for values in counts:
        totals.update(values)
    vocabulary = tuple(
        sorted(sorted(totals, key=lambda term: (-totals[term], term))[: config.max_features])
    )
    if not vocabulary:
        raise WireError("INPUT_INVALID")
    columns = {term: i for i, term in enumerate(vocabulary)}
    data, indices, pointers = [], [], [0]
    for row, values in zip(rows, counts, strict=True):
        denominator = _positions(row.prompt, config.min_n, config.max_n)
        for term in sorted(values):
            if term in columns:
                data.append(values[term] / denominator)
                indices.append(columns[term])
        pointers.append(len(data))
    import numpy as np
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.linear_model import LogisticRegression

    sparse = importlib.import_module("scipy.sparse")
    matrix = sparse.csr_matrix(
        (np.asarray(data, dtype=np.float64), indices, pointers),
        shape=(len(rows), len(vocabulary)),
        dtype=np.float64,
    )
    estimator = LogisticRegression(
        solver="liblinear",
        C=config.c,
        tol=config.tolerance,
        max_iter=config.max_iter,
        random_state=seed,
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        estimator.fit(matrix, np.asarray([r.label for r in rows], dtype=np.int64))
    return NgramFit(
        schema_id="hallmark/ngram-fit/1",
        config=config,
        bounds=bounds,
        seed=seed,
        training=training_identity(rows),
        runtime=commitment("baseline-runtime", baseline_runtime()),
        model=NgramModel(
            schema_id="hallmark/character-logistic/1",
            min_n=config.min_n,
            max_n=config.max_n,
            max_prompt_bytes=bounds.max_prompt_bytes,
            vocabulary=vocabulary,
            coefficients=tuple(float(x) for x in estimator.coef_[0]),
            intercept=float(estimator.intercept_[0]),
        ),
        iterations=int(estimator.n_iter_[0]),
        converged=not any(issubclass(w.category, ConvergenceWarning) for w in caught),
        optimizer="liblinear-l2-float64",
        resume="not-supported-cold-fit",
    )


def score_ngram(model: NgramModel, prompt: str) -> float:
    if type(model) is not NgramModel or type(prompt) is not str:
        raise WireError("INPUT_INVALID")
    model = model._validated()
    if len(prompt.encode("utf-8")) > model.max_prompt_bytes:
        raise WireError("LIMIT_EXCEEDED")
    counts = _counts(prompt, model.min_n, model.max_n)
    denominator = _positions(prompt, model.min_n, model.max_n)
    value = model.intercept + math.fsum(
        coefficient * (counts[term] / denominator)
        for term, coefficient in zip(model.vocabulary, model.coefficients, strict=True)
    )
    if not math.isfinite(value):
        raise WireError("INPUT_INVALID")
    return value
