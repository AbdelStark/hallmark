"""Frozen study terms and caller-pinned review checks; no execution authority or I/O."""

import hashlib
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from hallmark.classifier_manifest import U64
from hallmark.contracts import Identifier
from hallmark.errors import HallmarkError
from hallmark.manifests import (
    ArtifactDigest,
    Digest32,
    FileHash32,
    FileRef,
    _Artifact,
    _Record,
)
from hallmark.wire import H, WireError

DecimalString = Annotated[str, Field(pattern=r"^(?:0|1|0\.[0-9]{0,17}[1-9])$")]
PositiveU64 = Annotated[int, Field(ge=1, le=2**64 - 1)]
CANDIDATES = (
    "pass-all",
    "block-all",
    "byte-logistic",
    "char-ngram",
    "task-guard",
    "byte-mlp",
    "compact-encoder",
)
MAX_REVIEW_BYTES = 8 * 1024 * 1024
MAX_DOCUMENT_BYTES = 1024 * 1024


class StudyPolicy(_Artifact):
    """Assay/rubric identity before training; distinct from an enrolled runtime Policy."""

    _domain = "policy"
    schema_id: Literal["hallmark/study-policy/1"]
    policy_id: Literal["inj.direct/1"]
    language: Literal["en"]
    scope: Literal["prompt"]
    rubric: FileHash32
    max_prompt_bytes: Annotated[int, Field(ge=1, le=32768)]


class SourceApproval(_Record):
    """Exact metadata/notice/approval document hashes, not inferred legal permission."""

    source_id: Identifier
    revision: FileHash32
    license_text: FileHash32
    purpose: Identifier
    approval_ref: FileHash32
    restrictions: FileRef


class Candidate(_Record):
    id: Identifier
    code: FileHash32
    base_files: Annotated[tuple[FileRef, ...], Field(strict=False, max_length=4096)]
    config: FileHash32

    @model_validator(mode="after")
    def ordered_files(self) -> Self:
        if any(
            a.path >= b.path for a, b in zip(self.base_files, self.base_files[1:], strict=False)
        ):
            raise ValueError("candidate base files must be sorted and unique")
        return self


class BudgetAdmission(_Record):
    """Reviewed limits; this record does not allocate, meter or isolate resources."""

    host: Identifier
    hardware: FileHash32
    max_wall_seconds: PositiveU64
    max_cost_minor: U64
    currency: Identifier
    max_memory_bytes: PositiveU64
    max_disk_bytes: PositiveU64
    threads: PositiveU64
    jobs: PositiveU64
    max_proof_seconds: PositiveU64
    max_verify_seconds: Annotated[int, Field(ge=1, le=60)]
    max_native_overhead_basis_points: PositiveU64
    approved_by: Identifier
    approval_ref: FileHash32

    @model_validator(mode="after")
    def bounded_stages(self) -> Self:
        if max(self.max_proof_seconds, self.max_verify_seconds) > self.max_wall_seconds:
            raise ValueError("stage limit exceeds total wall budget")
        return self


class AdmissionProtocol(_Artifact):
    """Complete measurement terms; drafts with nulls or holds are not protocols."""

    _domain = "protocol"
    schema_id: Literal["hallmark/admission/1"]
    policy: Digest32
    relying_party_role: Identifier
    rubric: FileHash32
    sources: Annotated[tuple[SourceApproval, ...], Field(strict=False, min_length=1, max_length=64)]
    split_manifest: FileHash32
    candidate_roster: Annotated[
        tuple[Candidate, ...], Field(strict=False, min_length=7, max_length=7)
    ]
    seeds: Annotated[tuple[U64, U64, U64], Field(strict=False)]
    evaluator: FileHash32
    target_fpr: DecimalString
    alpha: DecimalString
    min_tpr: DecimalString
    max_quality_loss: DecimalString
    subgroup_rules: FileRef
    power_plan: FileRef
    budget: BudgetAdmission
    approval_ref: Digest32

    @model_validator(mode="after")
    def frozen_roster_and_criteria(self) -> Self:
        if tuple(c.id for c in self.candidate_roster) != CANDIDATES:
            raise ValueError("candidate roster must retain all seven ordered comparisons")
        if len(set(self.seeds)) != 3:
            raise ValueError("three distinct prespecified seeds required")
        names = tuple(s.source_id for s in self.sources)
        if names != tuple(sorted(set(names))):
            raise ValueError("sources must be sorted and unique")
        if self.target_fpr in ("0", "1") or self.alpha in ("0", "1"):
            raise ValueError("FPR and alpha must be strictly between zero and one")
        if self.min_tpr == "0" or self.max_quality_loss == "1":
            raise ValueError("positive minimum TPR and loss below one required")
        for candidate in self.candidate_roster:
            if candidate.id in ("task-guard", "compact-encoder") and not candidate.base_files:
                raise ValueError("external model inventory is required")
        return self

    def review_terms(self) -> ArtifactDigest:
        """Hash all terms except the final review reference, avoiding a review cycle."""
        value = self._wire()
        if not isinstance(value, dict):
            raise WireError("INPUT_INVALID")
        del value["approval_ref"]
        return ArtifactDigest(H("protocol", ["hallmark/admission-terms/1", value]))


class AdmissionReview(_Artifact):
    """Caller-enrolled review dossier; names and document hashes alone prove no approval."""

    _domain = "review"
    schema_id: Literal["hallmark/admission-review/1"]
    terms: Digest32
    owner: Identifier
    relying_party_role: Identifier
    owner_approval: FileRef
    relying_party_approval: FileRef
    evidence: Annotated[tuple[FileRef, ...], Field(strict=False, min_length=1, max_length=256)]

    @model_validator(mode="after")
    def bounded_evidence(self) -> Self:
        if any(a.path >= b.path for a, b in zip(self.evidence, self.evidence[1:], strict=False)):
            raise ValueError("review evidence must be sorted and unique")
        if any(r.size > MAX_DOCUMENT_BYTES for r in self.evidence):
            raise ValueError("review document exceeds limit")
        if sum(r.size for r in self.evidence) > MAX_REVIEW_BYTES:
            raise ValueError("review dossier exceeds limit")
        return self


def validate_reviewed_admission(
    protocol: AdmissionProtocol,
    policy: StudyPolicy,
    review: AdmissionReview,
    *,
    expected_review: ArtifactDigest,
    files: dict[str, bytes],
) -> None:
    """Compare an independently approved review pin and its exact bounded documents.

    The caller authenticates the owner/relying party and supplies the pin outside
    this dossier. This checks declarations, not signatures, statistical adequacy,
    model/data contents or the operating system's enforcement of the budget.
    """
    if (
        type(protocol) is not AdmissionProtocol
        or type(policy) is not StudyPolicy
        or type(review) is not AdmissionReview
    ):
        raise WireError("INPUT_INVALID")
    protocol, policy, review = protocol._validated(), policy._validated(), review._validated()
    if type(expected_review) is not bytes or len(expected_review) != 32:
        raise HallmarkError("TRUST_MISSING", "enroll")
    if expected_review != review.identity() or protocol.approval_ref != expected_review:
        raise HallmarkError("TRUST_MISSING", "enroll")
    if (
        review.terms != protocol.review_terms()
        or review.owner != protocol.budget.approved_by
        or review.relying_party_role != protocol.relying_party_role
        or protocol.policy != policy.identity()
        or protocol.rubric != policy.rubric
    ):
        raise HallmarkError("REQUEST_MISMATCH", "bind")
    references = {ref.path: ref for ref in review.evidence}
    if type(files) is not dict or set(files) != set(references):
        raise HallmarkError("INPUT_INVALID", "verify")
    for path, ref in references.items():
        raw = files[path]
        if (
            type(raw) is not bytes
            or len(raw) != ref.size
            or hashlib.sha256(raw).digest() != ref.sha256
        ):
            raise HallmarkError("INPUT_INVALID", "verify")
    required_refs = (
        review.owner_approval,
        review.relying_party_approval,
        protocol.subgroup_rules,
        protocol.power_plan,
        *(source.restrictions for source in protocol.sources),
    )
    if any(references.get(ref.path) != ref for ref in required_refs):
        raise HallmarkError("TRUST_MISSING", "enroll")
    required_hashes = {
        protocol.rubric,
        protocol.split_manifest,
        protocol.evaluator,
        protocol.budget.hardware,
        protocol.budget.approval_ref,
        *(candidate.code for candidate in protocol.candidate_roster),
        *(candidate.config for candidate in protocol.candidate_roster),
        *(
            value
            for source in protocol.sources
            for value in (source.revision, source.license_text, source.approval_ref)
        ),
    }
    if not required_hashes <= {ref.sha256 for ref in review.evidence}:
        raise HallmarkError("TRUST_MISSING", "enroll")
