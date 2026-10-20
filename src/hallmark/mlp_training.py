"""Train-only record-level MLP fitting; optional NumPy, no dataset access or evaluation."""

import hashlib
import importlib
import importlib.metadata
import json
import math
import platform
import sys
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import ConfigDict, Field, ValidationError, model_validator

from hallmark.contracts import Contract, Digest, Identifier, Record
from hallmark.integer_mlp import MAX_CHUNKS, MAX_PRODUCTS, MlpWeights
from hallmark.integrity import commitment
from hallmark.wire import WireError

MAX_FEATURE_VALUES = 2_097_152
Float = Annotated[float, Field(ge=-1e12, le=1e12)]
Row = Annotated[tuple[Float, ...], Field(strict=False, min_length=256, max_length=256)]
Vector = Annotated[tuple[Float, ...], Field(strict=False, min_length=1, max_length=64)]


class _TrainingRecord(Contract):
    model_config = ConfigDict(revalidate_instances="always", hide_input_in_errors=True)

    def _validated(self) -> Self:
        try:
            return type(self).model_validate(self)
        except ValidationError:
            pass
        raise WireError("INPUT_INVALID")

    def identity(self) -> str:
        # Research records contain floats; they never enter the float-free v1 wire codec.
        return commitment("mlp-training-record", self._validated().model_dump(mode="json"))


class MlpFitConfig(_TrainingRecord):
    schema_id: Literal["hallmark/mlp-fit-config/1"]
    policy_id: Identifier
    seed: Annotated[int, Field(ge=0, lt=2**32)]
    hidden_width: Annotated[int, Field(ge=1, le=64)]
    chunk_bytes: Annotated[int, Field(ge=1, le=512)]
    max_prompt_bytes: Annotated[int, Field(ge=1, le=32768)]
    max_rows: Annotated[int, Field(ge=2, le=100000)]
    max_feature_values: Annotated[int, Field(ge=256, le=MAX_FEATURE_VALUES)]
    epochs: Annotated[int, Field(ge=1, le=10000)]
    learning_rate: Annotated[float, Field(gt=0, le=1)]
    momentum: Annotated[float, Field(ge=0, lt=1)]
    l2: Annotated[float, Field(ge=0, le=1)]
    tolerance: Annotated[float, Field(ge=0, le=1)]

    @model_validator(mode="after")
    def native_envelope(self) -> Self:
        chunks = (self.max_prompt_bytes + self.chunk_bytes - 1) // self.chunk_bytes
        if chunks > MAX_CHUNKS or chunks * self.hidden_width * 257 > MAX_PRODUCTS:
            raise ValueError("declared input exceeds native MLP envelope")
        return self


class FloatMlp(_TrainingRecord):
    hidden_weights: Annotated[tuple[Row, ...], Field(strict=False, min_length=1, max_length=64)]
    hidden_bias: Vector
    output_weights: Vector
    output_bias: Float

    @model_validator(mode="after")
    def shape(self) -> Self:
        if not len(self.hidden_weights) == len(self.hidden_bias) == len(self.output_weights):
            raise ValueError("MLP dimensions disagree")
        return self


class EpochSample(_TrainingRecord):
    epoch: Annotated[int, Field(ge=1, le=10000)]
    loss: Annotated[float, Field(ge=0, le=1e12)]
    gradient_norm: Annotated[float, Field(ge=0, le=1e12)]


class MlpCheckpoint(_TrainingRecord):
    schema_id: Literal["hallmark/mlp-checkpoint/1"]
    config: Digest
    training: Digest
    runtime: Digest
    epoch: Annotated[int, Field(ge=0, le=10000)]
    parameters: FloatMlp
    momentum: FloatMlp
    initialization_rng_json: Annotated[str, Field(min_length=1, max_length=1024)]
    loss: Annotated[float, Field(ge=0, le=1e12)]
    converged: bool

    @model_validator(mode="after")
    def shape(self) -> Self:
        if len(self.parameters.hidden_bias) != len(self.momentum.hidden_bias):
            raise ValueError("optimizer dimensions disagree")
        return self


def _training(rows: tuple[Record, ...], config: MlpFitConfig) -> tuple[tuple[Record, ...], str]:
    if type(rows) is not tuple or not 2 <= len(rows) <= config.max_rows:
        raise WireError("INPUT_INVALID")
    if any(type(row) is not Record or row.split != "train" for row in rows):
        raise WireError("INPUT_INVALID")
    for row in rows:
        try:
            Record.model_validate(row.model_dump())
        except ValidationError:
            raise WireError("INPUT_INVALID") from None
        if (
            row.split != "train"
            or row.policy_id != config.policy_id
            or row.response
            or row.language != "en"
        ):
            raise WireError("INPUT_INVALID")
        if len(row.prompt.encode("utf-8")) > config.max_prompt_bytes:
            raise WireError("LIMIT_EXCEEDED")
    ordered = tuple(sorted(rows, key=lambda row: row.record_id))
    if len({r.record_id for r in ordered}) != len(ordered) or {r.label for r in ordered} != {0, 1}:
        raise WireError("INPUT_INVALID")
    count = sum(
        max(1, (len(r.prompt.encode()) + config.chunk_bytes - 1) // config.chunk_bytes)
        for r in ordered
    )
    if count * 256 > config.max_feature_values:
        raise WireError("LIMIT_EXCEEDED")
    document = [r.model_dump(mode="json") for r in ordered]
    return ordered, commitment("mlp-training-rows", document)


def runtime_record() -> dict[str, Any]:
    """Record the numerical/source environment; it is not an attestation."""
    implementation = importlib.import_module("numpy._core._multiarray_umath")
    extension_name = implementation.__file__
    if extension_name is None:
        raise ValueError("missing NumPy implementation")
    extension = Path(extension_name)
    return {
        "schema_id": "hallmark.mlp-training-runtime/1",
        "python": sys.version,
        "numpy": importlib.metadata.version("numpy"),
        "pydantic": importlib.metadata.version("pydantic"),
        "cbor2": importlib.metadata.version("cbor2"),
        "cpu_features": dict(sorted(implementation.__cpu_features__.items())),
        "machine": platform.machine(),
        "platform": platform.platform(),
        "byteorder": sys.byteorder,
        "dtype": "float64",
        "contraction": "einsum-optimize-false",
        "initialization": "numpy-PCG64-normal",
        "numpy_extension_sha256": hashlib.sha256(extension.read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def _features(rows: tuple[Record, ...], config: MlpFitConfig) -> tuple[Any, Any, Any]:
    import numpy as np

    counts: list[list[float]] = []
    starts: list[int] = []
    for row in rows:
        starts.append(len(counts))
        raw = row.prompt.encode("utf-8")
        for start in range(0, max(1, len(raw)), config.chunk_bytes):
            content = raw[start : start + config.chunk_bytes]
            counts.append([content.count(byte) / config.chunk_bytes for byte in range(256)])
    return (
        np.asarray(counts, dtype=np.float64),
        np.asarray(starts, dtype=np.int64),
        np.asarray([r.label for r in rows], dtype=np.float64),
    )


def _arrays(parameters: FloatMlp) -> list[Any]:
    import numpy as np

    return [
        np.asarray(value, dtype=np.float64)
        for value in (
            parameters.hidden_weights,
            parameters.hidden_bias,
            parameters.output_weights,
            parameters.output_bias,
        )
    ]


def _parameters(arrays: list[Any]) -> FloatMlp:
    return FloatMlp(
        hidden_weights=tuple(tuple(float(x) for x in row) for row in arrays[0]),
        hidden_bias=tuple(float(x) for x in arrays[1]),
        output_weights=tuple(float(x) for x in arrays[2]),
        output_bias=float(arrays[3]),
    )


def _objective(
    arrays: list[Any], x: Any, starts: Any, labels: Any, l2: float
) -> tuple[float, list[Any], Any]:
    """One loss per record; a deterministic first-max subgradient on chunk ties."""
    import numpy as np

    w1, b1, w2, b2 = arrays
    hidden = np.einsum("nd,hd->nh", x, w1, optimize=False) + b1
    activated = np.maximum(hidden, 0)
    logits = np.einsum("nh,h->n", activated, w2, optimize=False) + b2
    ends = [*starts[1:], len(logits)]
    chosen = np.asarray(
        [
            int(start) + int(np.argmax(logits[start:end]))
            for start, end in zip(starts, ends, strict=True)
        ]
    )
    scores = logits[chosen]
    loss = float(
        np.mean(np.logaddexp(0, scores) - labels * scores)
        + l2 / 2 * (np.sum(w1 * w1) + np.sum(w2 * w2))
    )
    probabilities = np.exp(-np.logaddexp(0, -scores))
    residual = (probabilities - labels) / len(labels)
    dh = residual[:, None] * w2[None, :] * (hidden[chosen] > 0)
    gradients = [
        np.einsum("nh,nd->hd", dh, x[chosen], optimize=False) + l2 * w1,
        np.sum(dh, axis=0),
        np.einsum("n,nh->h", residual, activated[chosen], optimize=False) + l2 * w2,
        np.sum(residual),
    ]
    if not math.isfinite(loss) or any(not np.isfinite(g).all() for g in gradients):
        raise ValueError("nonfinite optimization result")
    return loss, gradients, scores


def fit_mlp(
    rows: tuple[Record, ...],
    config: MlpFitConfig,
    *,
    checkpoint: MlpCheckpoint | None = None,
    expected_checkpoint: str | None = None,
    steps: int | None = None,
) -> tuple[MlpCheckpoint, tuple[EpochSample, ...]]:
    """Fit only supplied training records; caller retains returned checkpoints and samples."""
    if type(config) is not MlpFitConfig:
        raise WireError("INPUT_INVALID")
    config = config._validated()
    rows, training = _training(rows, config)
    if steps is not None and (type(steps) is not int or not 1 <= steps <= config.epochs):
        raise WireError("INPUT_INVALID")
    if checkpoint is None and expected_checkpoint is not None:
        raise WireError("INPUT_INVALID")
    if checkpoint is not None:
        if type(checkpoint) is not MlpCheckpoint:
            raise WireError("INPUT_INVALID")
        checkpoint = checkpoint._validated()
        if (
            type(expected_checkpoint) is not str
            or len(expected_checkpoint) != 64
            or checkpoint.identity() != expected_checkpoint
            or checkpoint.config != config.identity()
            or checkpoint.training != training
            or len(checkpoint.parameters.hidden_bias) != config.hidden_width
            or checkpoint.epoch > config.epochs
        ):
            raise WireError("INPUT_INVALID")
    import numpy as np

    runtime = commitment("mlp-training-runtime", runtime_record())
    if checkpoint is not None and checkpoint.runtime != runtime:
        raise WireError("INPUT_INVALID")
    x, starts, labels = _features(rows, config)
    if checkpoint is None:
        rng = np.random.Generator(np.random.PCG64(config.seed))
        arrays = [
            rng.normal(0, math.sqrt(2 / 256), (config.hidden_width, 256)),
            np.zeros(config.hidden_width),
            rng.normal(0, math.sqrt(2 / config.hidden_width), config.hidden_width),
            np.asarray(0.0),
        ]
        velocities = [np.zeros_like(p) for p in arrays]
        rng_json = json.dumps(rng.bit_generator.state, sort_keys=True)
        epoch, converged = 0, False
    else:
        arrays, velocities = _arrays(checkpoint.parameters), _arrays(checkpoint.momentum)
        rng_json = checkpoint.initialization_rng_json
        epoch, converged = checkpoint.epoch, checkpoint.converged
    loss, gradients, _ = _objective(arrays, x, starts, labels, config.l2)
    if checkpoint is not None and loss != checkpoint.loss:
        raise WireError("INPUT_INVALID")
    samples = []
    target = min(config.epochs, epoch + (steps if steps is not None else config.epochs))
    while epoch < target and not converged:
        norm = math.sqrt(sum(float(np.sum(g * g)) for g in gradients))
        velocities = [config.momentum * v + g for v, g in zip(velocities, gradients, strict=True)]
        arrays = [p - config.learning_rate * v for p, v in zip(arrays, velocities, strict=True)]
        _parameters(arrays)
        previous = loss
        loss, gradients, _ = _objective(arrays, x, starts, labels, config.l2)
        epoch += 1
        converged = abs(previous - loss) <= config.tolerance
        samples.append(EpochSample(epoch=epoch, loss=loss, gradient_norm=norm))
    return MlpCheckpoint(
        schema_id="hallmark/mlp-checkpoint/1",
        config=config.identity(),
        training=training,
        runtime=runtime,
        epoch=epoch,
        parameters=_parameters(arrays),
        momentum=_parameters(velocities),
        initialization_rng_json=rng_json,
        loss=loss,
        converged=converged,
    ), tuple(samples)


class MlpQuantization(_TrainingRecord):
    schema_id: Literal["hallmark.mlp-quantization/1"]
    checkpoint: Digest
    weights: MlpWeights
    first_fraction: Annotated[int, Field(ge=0, le=30)]
    last_fraction: Annotated[int, Field(ge=0, le=30)]
    hidden_scale: Annotated[int, Field(ge=1, le=256)]
    score_scale: Annotated[int, Field(ge=1, le=4096)]

    @model_validator(mode="after")
    def powers(self) -> Self:
        if self.hidden_scale & (self.hidden_scale - 1) or self.score_scale & (self.score_scale - 1):
            raise ValueError("export scales must be powers of two")
        return self


def quantize_mlp(checkpoint: MlpCheckpoint, config: MlpFitConfig) -> MlpQuantization:
    """Power-of-two PTQ; caller builds/validates the native profile before calibration."""
    if type(checkpoint) is not MlpCheckpoint or type(config) is not MlpFitConfig:
        raise WireError("INPUT_INVALID")
    checkpoint, config = checkpoint._validated(), config._validated()
    if (
        checkpoint.config != config.identity()
        or len(checkpoint.parameters.hidden_bias) != config.hidden_width
    ):
        raise WireError("INPUT_INVALID")
    values = checkpoint.parameters
    first = tuple(tuple(w / config.chunk_bytes for w in row) for row in values.hidden_weights)

    def fraction(weights: tuple[float, ...]) -> int:
        maximum = max(abs(w) for w in weights)
        if maximum == 0:
            return 0
        result = min(24, math.floor(math.log2(127 / maximum)))
        if result < 0:
            raise ValueError("weights do not fit int8 with a nonnegative binary fraction")
        return result

    f1 = fraction(tuple(w for row in first for w in row))
    f2 = fraction(values.output_weights)
    hidden_bits = min(8, f1)
    score_bits = min(12, hidden_bits + f2)
    weights = MlpWeights(
        schema_id="hallmark/mlp-weights/1",
        hidden_weights=tuple(tuple(round(w * 2**f1) for w in row) for row in first),
        hidden_bias=tuple(round(b * 2**f1) for b in values.hidden_bias),
        output_weights=tuple(round(w * 2**f2) for w in values.output_weights),
        output_bias=round(values.output_bias * 2 ** (f2 + hidden_bits)),
    )
    return MlpQuantization(
        schema_id="hallmark.mlp-quantization/1",
        checkpoint=checkpoint.identity(),
        weights=weights,
        first_fraction=f1 - hidden_bits,
        last_fraction=f2 + hidden_bits - score_bits,
        hidden_scale=2**hidden_bits,
        score_scale=2**score_bits,
    )


def score_float_mlp(parameters: FloatMlp, config: MlpFitConfig, prompt: str) -> float:
    """Score complete prompt bytes without accepting any split or label information."""
    if (
        type(parameters) is not FloatMlp
        or type(config) is not MlpFitConfig
        or type(prompt) is not str
    ):
        raise WireError("INPUT_INVALID")
    parameters, config = parameters._validated(), config._validated()
    raw = prompt.encode("utf-8")
    count = max(1, (len(raw) + config.chunk_bytes - 1) // config.chunk_bytes)
    if (
        len(parameters.hidden_bias) != config.hidden_width
        or len(raw) > config.max_prompt_bytes
        or count * 256 > config.max_feature_values
    ):
        raise WireError("LIMIT_EXCEEDED")
    import numpy as np

    x = np.asarray(
        [
            [
                raw[start : start + config.chunk_bytes].count(byte) / config.chunk_bytes
                for byte in range(256)
            ]
            for start in range(0, max(1, len(raw)), config.chunk_bytes)
        ],
        dtype=np.float64,
    )
    _, _, scores = _objective(_arrays(parameters), x, np.asarray([0]), np.asarray([0.0]), 0.0)
    return float(scores[0])
