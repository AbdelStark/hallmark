"""Strict, bounded input contracts for the executable research baseline."""

from typing import Annotated, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._/-]{0,127}$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Int32 = Annotated[int, Field(strict=True, ge=-(2**31), le=2**31 - 1)]
Int8 = Annotated[int, Field(strict=True, ge=-128, le=127)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)


class Record(Contract):
    schema_id: Literal["hallmark.dataset-record/1"]
    record_id: Identifier
    group_id: Identifier
    family_id: Identifier
    source_id: Identifier
    source_revision: Digest
    license_id: Annotated[str, Field(min_length=1, max_length=128)]
    policy_id: Identifier
    split: Literal["train", "calibration", "test"]
    language: Annotated[str, Field(min_length=2, max_length=32)]
    prompt: Annotated[str, Field(max_length=32768)]
    response: Annotated[str, Field(max_length=32768)]
    label: Annotated[int, Field(strict=True, ge=0, le=1)]


class Experiment(Contract):
    schema_id: Literal["hallmark.experiment/1"]
    experiment_id: Identifier
    dataset: str
    dataset_sha256: Digest
    policy_id: Identifier
    scope: Literal["prompt", "response"]
    seed: Annotated[int, Field(ge=0, le=2**32 - 1)]
    chunk_bytes: Annotated[int, Field(ge=1, le=4096)]
    target_fpr: Annotated[float, Field(gt=0, lt=1)]
    alpha: Annotated[float, Field(gt=0, lt=1)]
    approved_licenses: tuple[str, ...]
    approved_sources: tuple[Identifier, ...]
    evidence_class: Literal["synthetic-fixture", "research"]


class LinearArtifact(Contract):
    schema_id: Literal["hallmark.integer-byte-linear/1"]
    policy_id: Identifier
    scope: Literal["prompt", "response"]
    chunk_bytes: Annotated[int, Field(ge=1, le=4096)]
    weights: Annotated[tuple[Int8, ...], Field(min_length=256, max_length=256)]
    bias: Int32
    threshold: Int32
    scale: Annotated[int, Field(ge=1, le=2**24)]

    @model_validator(mode="after")
    def bounded_accumulator(self) -> "LinearArtifact":
        radius = self.chunk_bytes * max(abs(x) for x in self.weights)
        if not -(2**31) <= self.bias - radius <= self.bias + radius < 2**31:
            raise ValueError("all reachable accumulations must fit signed int32")
        if self.scale & (self.scale - 1):
            raise ValueError("scale must be a power of two")
        return self


C = TypeVar("C", bound=Contract)
ArtifactName = Literal[
    "config.json", "model.json", "results.json", "predictions.json", "source.json"
]


class RunManifest(Contract):
    schema_id: Literal["hallmark.run-manifest/1"]
    status: Literal["complete"]
    artifacts: Annotated[
        dict[ArtifactName, Digest],
        Field(min_length=5, max_length=5),
    ]
