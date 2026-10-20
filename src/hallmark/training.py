"""Optional, offline scikit-learn floor baseline; no checkpoint or dataset downloads."""

import math
import warnings
from typing import Any

from hallmark.contracts import Experiment, LinearArtifact, Record
from hallmark.reference import byte_counts


def train_linear(
    rows: tuple[Record, ...], config: Experiment
) -> tuple[LinearArtifact, dict[str, Any]]:
    try:
        import numpy as np
        from sklearn.exceptions import ConvergenceWarning
        from sklearn.linear_model import LogisticRegression
    except ImportError as exc:
        raise RuntimeError("training requires: uv sync --extra train") from exc

    training = [row for row in rows if row.split == "train"]
    if {row.label for row in training} != {0, 1}:
        raise ValueError("training requires both classes")
    texts = [getattr(row, config.scope).encode("utf-8") for row in training]
    if any(len(text) > config.chunk_bytes for text in texts):
        raise ValueError("baseline training requires one chunk per labelled record")
    x = np.asarray([byte_counts(text) for text in texts], dtype=np.float64)
    y = np.asarray([row.label for row in training], dtype=np.int64)
    estimator = LogisticRegression(solver="liblinear", random_state=config.seed, max_iter=1000)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        estimator.fit(x, y)
    weights = [float(w) for w in estimator.coef_[0]]
    bias = float(estimator.intercept_[0])
    maximum = max(abs(w) for w in weights)
    if not maximum or not all(math.isfinite(w) for w in [*weights, bias]):
        raise ValueError("degenerate or non-finite baseline")
    exponent = min(24, math.floor(math.log2(127 / maximum)))
    if exponent < 0:
        raise ValueError("baseline cannot fit int8 without a sub-unit scale")
    scale = 2**exponent
    artifact = LinearArtifact(
        schema_id="hallmark.integer-byte-linear/1",
        policy_id=config.policy_id,
        scope=config.scope,
        chunk_bytes=config.chunk_bytes,
        weights=tuple(round(w * scale) for w in weights),
        bias=round(bias * scale),
        threshold=0,
        scale=scale,
    )
    return artifact, {
        "algorithm": "sklearn.linear_model.LogisticRegression",
        "solver": "liblinear",
        "C": 1.0,
        "max_iter": 1000,
        "seed": config.seed,
        "float_weights": weights,
        "float_bias": bias,
        "quantization": "round-nearest-ties-even, int8 weights, int32 accumulation, no clipping",
    }
