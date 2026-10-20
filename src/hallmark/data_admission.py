"""Pinned local source import, complete lineage grouping and frozen split artifacts."""

import hashlib
import json
import os
from collections import defaultdict, deque
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, ValidationError, field_validator, model_validator

from hallmark.admission import MAX_DOCUMENT_BYTES, MAX_REVIEW_BYTES, SourceApproval, StudyPolicy
from hallmark.contracts import Identifier, Record
from hallmark.errors import HallmarkError
from hallmark.integrity import parse_json
from hallmark.manifests import (
    ArtifactDigest,
    Digest32,
    FileHash32,
    FileRef,
    FileSHA256,
    _Artifact,
    _Record,
)
from hallmark.wire import WireError

MAX_ROWS = 100_000
MAX_RAW_BYTES = 128 * 1024 * 1024
MAX_OUTPUT_BYTES = 256 * 1024 * 1024
Names = Annotated[tuple[Identifier, ...], Field(strict=False, max_length=MAX_ROWS)]
Bit = Annotated[int, Field(ge=0, le=1)]
Label = Annotated[str, Field(min_length=1, max_length=128)]
Split = Literal["train", "calibration", "test"]


def _sha(raw: bytes) -> FileSHA256:
    return FileSHA256(hashlib.sha256(raw).digest())


def _json(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode()


def _ordered(values: tuple[str, ...]) -> bool:
    return values == tuple(sorted(set(values)))


class SourceRow(_Record):
    """Reviewed adapter output; text is unchanged by this importer."""

    schema_id: Literal["hallmark/source-row/1"]
    record_id: Identifier
    family_id: Identifier
    language: Literal["en"]
    prompt: Annotated[str, Field(max_length=32768, repr=False)]
    response: Annotated[str, Field(max_length=32768, repr=False)]
    source_label: Label
    parents: Annotated[Names, Field(max_length=64)]
    history_id: Identifier | None
    difficult_negative: bool

    @field_validator("prompt", "response")
    @classmethod
    def byte_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 32768:
            raise ValueError("text exceeds byte limit")
        return value

    @model_validator(mode="after")
    def parent_ids(self) -> Self:
        if not _ordered(self.parents) or self.record_id in self.parents:
            raise ValueError("parents must be unique, ordered and distinct from the child")
        return self


class LabelMapping(_Record):
    source_label: Label
    label: Bit
    review: FileHash32


class SourceManifest(_Record):
    schema_id: Literal["hallmark/source-manifest/1"]
    source_id: Identifier
    upstream_revision: Annotated[str, Field(min_length=1, max_length=512)]
    license_id: Label
    policy: Digest32
    purpose: Literal["inj.direct-study"]
    privacy: Literal["public", "synthetic"]
    review_kind: Literal["human", "fixture"]
    raw_files: Annotated[tuple[FileRef, ...], Field(strict=False, min_length=1, max_length=64)]
    label_mapping: Annotated[
        tuple[LabelMapping, ...], Field(strict=False, min_length=1, max_length=128)
    ]
    annotation_review: FileHash32
    transformation_recipe: FileHash32
    data_card: FileHash32

    @model_validator(mode="after")
    def ordered_inventory(self) -> Self:
        if (
            not _ordered(tuple(ref.path for ref in self.raw_files))
            or not _ordered(tuple(item.source_label for item in self.label_mapping))
            or any(not 1 <= ref.size <= MAX_RAW_BYTES for ref in self.raw_files)
        ):
            raise ValueError("source inventory or label mapping is not bounded and canonical")
        return self


class NearDuplicateReview(_Record):
    schema_id: Literal["hallmark/near-duplicate-review/1"]
    candidate_inventory: FileHash32
    review_kind: Literal["human", "fixture"]
    reviewer: Identifier
    evidence: FileHash32
    disposition: Literal["retain-and-group-all-candidates"]


class DataImportPlan(_Artifact):
    _domain = "protocol"
    schema_id: Literal["hallmark/data-import/1"]
    policy: Digest32
    design: Literal["inj-direct-design/1"]
    fixture_only: bool
    sources: Annotated[tuple[SourceApproval, ...], Field(strict=False, min_length=1, max_length=64)]
    near_duplicate_review: FileRef
    held_out_sources: Annotated[Names, Field(max_length=64)]
    held_out_families: Names
    evidence: Annotated[tuple[FileRef, ...], Field(strict=False, min_length=1, max_length=256)]

    @model_validator(mode="after")
    def complete_inventory(self) -> Self:
        if (
            not _ordered(tuple(s.source_id for s in self.sources))
            or not _ordered(tuple(ref.path for ref in self.evidence))
            or not _ordered(self.held_out_sources)
            or not _ordered(self.held_out_families)
            or any(not 1 <= ref.size <= MAX_DOCUMENT_BYTES for ref in self.evidence)
            or sum(ref.size for ref in self.evidence) > MAX_REVIEW_BYTES
            or self.near_duplicate_review not in self.evidence
        ):
            raise ValueError("import plan inventory is not bounded and canonical")
        return self


class LineageEntry(_Record):
    schema_id: Literal["hallmark/lineage/1"]
    record_id: Identifier
    source_id: Identifier
    source_manifest: FileHash32
    source_file: FileRef
    source_row: Annotated[int, Field(ge=1, le=MAX_ROWS)]
    raw_row: FileHash32
    parents: Annotated[Names, Field(max_length=64)]
    history_id: Identifier | None
    transformation_recipe: FileHash32
    label_mapping_review: FileHash32
    annotation_review: FileHash32
    difficult_negative: bool


class SplitGroup(_Record):
    group_id: Identifier
    members: Annotated[Names, Field(min_length=1)]
    sources: Annotated[Names, Field(min_length=1, max_length=64)]
    families: Annotated[Names, Field(min_length=1)]
    split: Split
    cohort: Literal["primary", "held-out"]
    representative: Identifier

    @model_validator(mode="after")
    def membership(self) -> Self:
        if (
            any(not _ordered(value) for value in (self.members, self.sources, self.families))
            or self.representative not in self.members
            or (self.cohort == "held-out" and self.split != "test")
        ):
            raise ValueError("inconsistent split group")
        return self


class SplitManifest(_Record):
    schema_id: Literal["hallmark/split-manifest/1"]
    plan: Digest32
    groups: Annotated[
        tuple[SplitGroup, ...], Field(strict=False, min_length=1, max_length=MAX_ROWS)
    ]
    near_duplicate_review: FileHash32
    near_duplicate_candidates: Annotated[
        tuple[Names, ...], Field(strict=False, max_length=MAX_ROWS)
    ]


class DatasetManifest(_Artifact):
    _domain = "corpus"
    schema_id: Literal["hallmark/dataset-manifest/1"]
    plan: Digest32
    policy: Digest32
    fixture_only: bool
    records: FileRef
    lineage: FileRef
    splits: FileRef
    record_count: Annotated[int, Field(ge=1, le=MAX_ROWS)]
    group_count: Annotated[int, Field(ge=1, le=MAX_ROWS)]

    @model_validator(mode="after")
    def artifact_inventory(self) -> Self:
        refs = (self.records, self.lineage, self.splits)
        if (
            tuple(ref.path for ref in refs) != ("records.jsonl", "lineage.jsonl", "splits.json")
            or any(not 1 <= ref.size <= MAX_OUTPUT_BYTES for ref in refs)
            or sum(ref.size for ref in refs) > MAX_OUTPUT_BYTES
            or self.group_count > self.record_count
        ):
            raise ValueError("invalid dataset artifact inventory")
        return self


def _files(refs: tuple[FileRef, ...], files: dict[str, bytes], cap: int) -> None:
    if (
        type(files) is not dict
        or len({ref.path for ref in refs}) != len(refs)
        or set(files) != {ref.path for ref in refs}
        or any(type(raw) is not bytes for raw in files.values())
    ):
        raise WireError("INPUT_INVALID")
    if sum(map(len, files.values())) > cap:
        raise WireError("LIMIT_EXCEEDED")
    for ref in refs:
        if len(files[ref.path]) != ref.size or _sha(files[ref.path]) != ref.sha256:
            raise WireError("INPUT_INVALID")


# Fixed byte normalization for candidate discovery only; independent of Unicode version.
_ASCII_REVIEW = bytes(
    32 if byte in (9, 10, 11, 12, 13, 32) else byte + 32 if 65 <= byte <= 90 else byte
    for byte in range(256)
)


def near_duplicate_candidates(rows: tuple[SourceRow, ...]) -> tuple[tuple[str, ...], ...]:
    """Flag ASCII case/whitespace equivalents without changing or deleting model inputs."""
    if type(rows) is not tuple or len(rows) > MAX_ROWS:
        raise WireError("LIMIT_EXCEEDED")
    buckets: dict[bytes, list[SourceRow]] = defaultdict(list)
    seen = set()
    total = 0
    for candidate in rows:
        if type(candidate) is not SourceRow:
            raise WireError("INPUT_INVALID")
        row = candidate._validated()
        total += len(row.prompt.encode()) + len(row.response.encode())
        if total > MAX_RAW_BYTES:
            raise WireError("LIMIT_EXCEEDED")
        if row.record_id in seen:
            raise WireError("INPUT_INVALID")
        seen.add(row.record_id)
        key = b" ".join(filter(None, row.prompt.encode().translate(_ASCII_REVIEW).split(b" ")))
        buckets[key].append(row)
    return tuple(
        sorted(
            tuple(sorted(row.record_id for row in bucket))
            for bucket in buckets.values()
            if len({row.prompt for row in bucket}) > 1
        )
    )


def _groups(
    rows: dict[str, SourceRow], candidates: tuple[tuple[str, ...], ...]
) -> tuple[tuple[str, ...], ...]:
    parents = {name: name for name in rows}
    sizes = dict.fromkeys(rows, 1)

    def root(name: str) -> str:
        while parents[name] != name:
            parents[name] = parents[parents[name]]
            name = parents[name]
        return name

    def union(a: str, b: str) -> None:
        a, b = root(a), root(b)
        if a != b:
            if sizes[a] < sizes[b]:
                a, b = b, a
            parents[b] = a
            sizes[a] += sizes[b]

    children: dict[str, list[str]] = defaultdict(list)
    degrees = {}
    histories: dict[str, str] = {}
    prompts: dict[str, str] = {}
    for name, row in rows.items():
        degrees[name] = len(row.parents)
        for parent in row.parents:
            if parent not in rows:
                raise WireError("INPUT_INVALID")
            union(name, parent)
            children[parent].append(name)
        if row.history_id is not None:
            union(name, histories.setdefault(row.history_id, name))
        union(name, prompts.setdefault(row.prompt, name))
    queue = deque(name for name, degree in degrees.items() if degree == 0)
    visited = 0
    while queue:
        name = queue.popleft()
        visited += 1
        for child in children[name]:
            degrees[child] -= 1
            if degrees[child] == 0:
                queue.append(child)
    if visited != len(rows):
        raise WireError("INPUT_INVALID")
    for members in candidates:
        for name in members[1:]:
            union(members[0], name)
    groups: dict[str, list[str]] = defaultdict(list)
    for name in sorted(rows):
        groups[root(name)].append(name)
    return tuple(sorted(tuple(members) for members in groups.values()))


def _splits(
    plan: DataImportPlan,
    rows: dict[str, SourceRow],
    source_ids: dict[str, str],
    candidates: tuple[tuple[str, ...], ...],
) -> tuple[SplitGroup, ...]:
    held_sources, held_families = set(plan.held_out_sources), set(plan.held_out_families)
    if not held_sources <= set(source_ids.values()) or not held_families <= {
        row.family_id for row in rows.values()
    }:
        raise WireError("INPUT_INVALID")
    groups = []
    strata: dict[tuple[str, str] | None, list[int]] = defaultdict(list)
    for members in _groups(rows, candidates):
        sources = tuple(sorted({source_ids[name] for name in members}))
        families = tuple(sorted({rows[name].family_id for name in members}))
        held = bool(held_sources.intersection(sources) or held_families.intersection(families))
        group = SplitGroup(
            group_id="g-" + _sha(_json(members)).hex(),
            members=members,
            sources=sources,
            families=families,
            split="test",
            cohort="held-out" if held else "primary",
            representative=min(
                members,
                key=lambda name: (
                    _sha(b"inj-direct-design/1|representative|" + name.encode()),
                    name,
                ),
            ),
        )
        groups.append(group)
        if not held:
            stratum = (sources[0], families[0]) if len(sources) == len(families) == 1 else None
            strata[stratum].append(len(groups) - 1)
    for indices in strata.values():
        indices.sort(
            key=lambda index: (
                _sha(b"inj-direct-design/1|split|" + groups[index].group_id.encode()),
                groups[index].group_id,
            )
        )
        for rank, index in enumerate(indices):
            split = (
                "train"
                if rank < 3 * len(indices) // 5
                else ("calibration" if rank < 4 * len(indices) // 5 else "test")
            )
            groups[index] = groups[index].model_copy(update={"split": split})
    if {group.split for group in groups if group.cohort == "primary"} != {
        "train",
        "calibration",
        "test",
    }:
        raise WireError("INPUT_INVALID")
    return tuple(sorted(groups, key=lambda group: group.group_id))


def build_dataset(
    plan: DataImportPlan,
    policy: StudyPolicy,
    *,
    expected_plan: ArtifactDigest,
    documents: dict[str, bytes],
    raw_files: dict[str, bytes],
) -> tuple[DatasetManifest, dict[str, bytes]]:
    """Import exact approved bytes; the caller authenticates review and enrolls the plan.

    Hash checks cannot establish human review, legal rights, upstream truth or task
    quality. Source adapters, data access and final measurement admission are separate.
    """
    if type(plan) is not DataImportPlan or type(policy) is not StudyPolicy:
        raise WireError("INPUT_INVALID")
    plan, policy = plan._validated(), policy._validated()
    if (
        type(expected_plan) is not bytes
        or len(expected_plan) != 32
        or expected_plan != plan.identity()
    ):
        raise HallmarkError("TRUST_MISSING", "enroll")
    if plan.policy != policy.identity():
        raise HallmarkError("REQUEST_MISMATCH", "bind")
    _files(plan.evidence, documents, MAX_REVIEW_BYTES)
    try:
        return _build(plan, policy, documents, raw_files)
    except (ValidationError, ValueError, KeyError, UnicodeError):
        pass
    raise WireError("INPUT_INVALID")


def _build(
    plan: DataImportPlan,
    policy: StudyPolicy,
    documents: dict[str, bytes],
    raw_files: dict[str, bytes],
) -> tuple[DatasetManifest, dict[str, bytes]]:
    docs = {ref.sha256: documents[ref.path] for ref in plan.evidence}
    required = {policy.rubric}
    sources = {}
    raw_refs: list[FileRef] = []
    for approval in plan.sources:
        source = SourceManifest.decode(docs[approval.revision])
        if (
            source.source_id != approval.source_id
            or source.policy != policy.identity()
            or source.purpose != approval.purpose
            or approval.restrictions not in plan.evidence
            or source.review_kind != ("fixture" if plan.fixture_only else "human")
            or source.privacy != ("synthetic" if plan.fixture_only else "public")
        ):
            raise WireError("INPUT_INVALID")
        required.update(
            (
                approval.revision,
                approval.license_text,
                approval.approval_ref,
                approval.restrictions.sha256,
                source.annotation_review,
                source.transformation_recipe,
                source.data_card,
                *(mapping.review for mapping in source.label_mapping),
            )
        )
        sources[source.source_id] = (source, approval)
        raw_refs.extend(source.raw_files)
    review = NearDuplicateReview.decode(docs[plan.near_duplicate_review.sha256])
    required.update((plan.near_duplicate_review.sha256, review.evidence))
    if (
        required != docs.keys()
        or review.review_kind != ("fixture" if plan.fixture_only else "human")
        or {ref.path for ref in raw_refs} & {ref.path for ref in plan.evidence}
    ):
        raise WireError("INPUT_INVALID")
    _files(tuple(raw_refs), raw_files, MAX_RAW_BYTES)
    rows: dict[str, SourceRow] = {}
    source_ids = {}
    labels = {}
    lineage = {}
    for source, approval in sources.values():
        mapping = {item.source_label: item for item in source.label_mapping}
        for ref in source.raw_files:
            for ordinal, raw in enumerate(raw_files[ref.path].splitlines(keepends=True), 1):
                if len(rows) >= MAX_ROWS:
                    raise WireError("LIMIT_EXCEEDED")
                text = raw.decode("utf-8")
                parse_json(text)
                row = SourceRow.model_validate_json(text)
                label = mapping[row.source_label]
                if (
                    row.record_id in rows
                    or len(row.prompt.encode()) > policy.max_prompt_bytes
                    or (row.difficult_negative and label.label != 0)
                ):
                    raise WireError("INPUT_INVALID")
                rows[row.record_id], source_ids[row.record_id] = row, source.source_id
                labels[row.record_id] = label.label
                lineage[row.record_id] = LineageEntry(
                    schema_id="hallmark/lineage/1",
                    record_id=row.record_id,
                    source_id=source.source_id,
                    source_manifest=approval.revision,
                    source_file=ref,
                    source_row=ordinal,
                    raw_row=_sha(raw),
                    parents=row.parents,
                    history_id=row.history_id,
                    transformation_recipe=source.transformation_recipe,
                    label_mapping_review=label.review,
                    annotation_review=source.annotation_review,
                    difficult_negative=row.difficult_negative,
                )
    if not rows:
        raise WireError("INPUT_INVALID")
    candidates = near_duplicate_candidates(tuple(rows.values()))
    if review.candidate_inventory != _sha(_json(candidates)):
        raise WireError("INPUT_INVALID")
    groups = _splits(plan, rows, source_ids, candidates)
    assignments = {name: group for group in groups for name in group.members}
    records = []
    for name, row in sorted(rows.items()):
        source, approval = sources[source_ids[name]]
        group = assignments[name]
        records.append(
            Record(
                schema_id="hallmark.dataset-record/1",
                record_id=name,
                group_id=group.group_id,
                family_id=row.family_id,
                source_id=source.source_id,
                source_revision=approval.revision.hex(),
                license_id=source.license_id,
                policy_id=policy.policy_id,
                split=group.split,
                language=row.language,
                prompt=row.prompt,
                response=row.response,
                label=labels[name],
            )
        )
    splits = SplitManifest(
        schema_id="hallmark/split-manifest/1",
        plan=plan.identity(),
        groups=groups,
        near_duplicate_review=plan.near_duplicate_review.sha256,
        near_duplicate_candidates=candidates,
    )
    files = {
        "records.jsonl": b"".join(_json(row.model_dump(mode="json")) for row in records),
        "lineage.jsonl": b"".join(
            _json(lineage[name].model_dump(mode="json")) for name in sorted(lineage)
        ),
        "splits.json": _json(splits.model_dump(mode="json")),
    }
    if sum(map(len, files.values())) > MAX_OUTPUT_BYTES:
        raise WireError("LIMIT_EXCEEDED")
    return DatasetManifest(
        schema_id="hallmark/dataset-manifest/1",
        plan=plan.identity(),
        policy=policy.identity(),
        fixture_only=plan.fixture_only,
        record_count=len(records),
        group_count=len(groups),
        **{
            name: FileRef(path=path, size=len(files[path]), sha256=_sha(files[path]))
            for name, path in (
                ("records", "records.jsonl"),
                ("lineage", "lineage.jsonl"),
                ("splits", "splits.json"),
            )
        },
    ), files


def verify_dataset(
    manifest: DatasetManifest,
    files: dict[str, bytes],
    plan: DataImportPlan,
    policy: StudyPolicy,
    *,
    expected_dataset: ArtifactDigest,
    expected_plan: ArtifactDigest,
    documents: dict[str, bytes],
    raw_files: dict[str, bytes],
) -> None:
    """Reproduce the import from pinned source evidence; not independent scientific review."""
    if type(manifest) is not DatasetManifest:
        raise WireError("INPUT_INVALID")
    manifest = manifest._validated()
    if (
        type(expected_dataset) is not bytes
        or len(expected_dataset) != 32
        or expected_dataset != manifest.identity()
    ):
        raise HallmarkError("TRUST_MISSING", "enroll")
    _files((manifest.records, manifest.lineage, manifest.splits), files, MAX_OUTPUT_BYTES)
    actual, actual_files = build_dataset(
        plan, policy, expected_plan=expected_plan, documents=documents, raw_files=raw_files
    )
    if actual != manifest or actual_files != files:
        raise WireError("INPUT_INVALID")


def write_dataset(directory: Path, manifest: DatasetManifest, files: dict[str, bytes]) -> None:
    """Create a private, new directory; preserve partial failures and never overwrite."""
    if type(manifest) is not DatasetManifest:
        raise WireError("INPUT_INVALID")
    manifest = manifest._validated()
    _files((manifest.records, manifest.lineage, manifest.splits), files, MAX_OUTPUT_BYTES)
    directory.mkdir(mode=0o700)
    for name, raw in (
        *sorted(files.items()),
        ("manifest.pending", _json(manifest.model_dump(mode="json"))),
    ):
        with os.fdopen(
            os.open(directory / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb"
        ) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    os.link(directory / "manifest.pending", directory / "manifest.json")
    (directory / "manifest.pending").unlink()
