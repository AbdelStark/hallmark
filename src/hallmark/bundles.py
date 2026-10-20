"""Bounded offline containers and reported results; parsing authenticates no evidence."""

import hashlib
from typing import Annotated, Literal, Self

from pydantic import Field, WithJsonSchema, field_validator, model_validator

from hallmark.contracts import Identifier
from hallmark.enrollment import MAX_HISTORY, Limits, SignedRegistry, TrustPolicy
from hallmark.errors import ErrorCode, HallmarkError
from hallmark.manifests import Digest32, FileRef, _Record, _wire_value
from hallmark.openings import TranscriptOpening
from hallmark.receipts import EpochRecord, ProofArtifact, SignedReceipt
from hallmark.wire import DEFAULT_LIMITS, WireError, WireLimits, _Measure, decode

MAX_BUNDLE_BYTES = 64 * 1024 * 1024
type CollectionState = Literal["pending", "ready", "blocked", "failed", "expired"]
_COMMON_RESIDUALS = frozenset(("adaptive-evasion", "policy-errors", "unobserved-traffic"))
_PROOF_ASSUMPTIONS = frozenset(("circuit-correctness", "proof-soundness", "registry-trust"))
_PRIVATE_SCHEMAS = frozenset(("hallmark/transcript-opening/1", "hallmark/response-envelope/1"))


def _private_record(raw: bytes) -> bool:
    try:
        value = decode(raw)
    except WireError:
        return False
    schema = value.get("schema_id") if isinstance(value, dict) else None
    return type(schema) is str and schema in _PRIVATE_SCHEMAS


class EmbeddedFile(_Record):
    """A logical name and exact bytes; never a filesystem or network operation."""

    ref: FileRef
    content: Annotated[
        bytes,
        Field(max_length=MAX_BUNDLE_BYTES, repr=False),
        WithJsonSchema(
            {
                "type": "string",
                "pattern": "^(?:[0-9a-fA-F]{2})*$",
                "maxLength": 2 * MAX_BUNDLE_BYTES,
            }
        ),
    ]

    @model_validator(mode="after")
    def exact_file(self) -> Self:
        if (
            len(self.content) != self.ref.size
            or hashlib.sha256(self.content).digest() != self.ref.sha256
        ):
            raise ValueError("embedded file differs from its reference")
        return self


class Bundle(_Record):
    """Complete-shaped evidence container, with no transcript-opening or trust field."""

    schema_id: Literal["hallmark/bundle/1"]
    receipt: SignedReceipt
    epoch: EpochRecord
    registry: SignedRegistry
    history: Annotated[tuple[SignedRegistry, ...], Field(strict=False, max_length=MAX_HISTORY)]
    proofs: Annotated[tuple[ProofArtifact, ProofArtifact, ProofArtifact], Field(strict=False)]
    files: Annotated[tuple[EmbeddedFile, ...], Field(strict=False, min_length=1, max_length=8192)]

    @model_validator(mode="after")
    def coherent_container(self) -> Self:
        # Measure the validated value tree without allocating a second full encoded bundle.
        _Measure(DEFAULT_LIMITS).visit(_wire_value(self.model_dump(mode="python")))
        paths = [item.ref.path for item in self.files]
        if paths != sorted(set(paths)):
            raise ValueError("embedded paths must be sorted and unique")
        references = {item.ref.path: item.ref for item in self.files}
        if any(references.get(ref.path) != ref for ref in self.epoch.collateral):
            raise ValueError("epoch collateral must be embedded under its exact reference")
        if any(_private_record(item.content) for item in self.files):
            raise ValueError("private opening and response records require a separate exchange")
        if tuple(proof.public_inputs for proof in self.proofs) != self.receipt.body.inputs:
            raise ValueError("proof declarations must match the ordered receipt inputs")
        if (
            self.receipt.body.epoch != self.epoch.identity()
            or self.receipt.body.expected.model != self.epoch.model
            or self.receipt.key_id != self.epoch.key_id()
        ):
            raise ValueError("receipt and epoch declarations disagree")
        return self

    def validate_limits(self, limits: Limits) -> None:
        """Apply caller byte/depth/proof ceilings; this does not verify evidence."""
        if type(limits) is not Limits:
            raise WireError("INPUT_INVALID")
        limits = limits._validated()
        bundle = self._validated()
        if any(len(proof.proof) > limits.proof_bytes for proof in bundle.proofs):
            raise WireError("LIMIT_EXCEEDED")
        _Measure(WireLimits(max_bytes=limits.bundle_bytes, nesting=limits.nesting)).visit(
            _wire_value(bundle.model_dump(mode="python"))
        )


def decode_bundle(raw: bytes, *, limits: Limits) -> Bundle:
    """Bound binary input before decoding, then apply per-proof caller limits."""
    if type(limits) is not Limits:
        raise WireError("INPUT_INVALID")
    limits = limits._validated()
    bundle = Bundle.decode(
        raw, limits=WireLimits(max_bytes=limits.bundle_bytes, nesting=limits.nesting)
    )
    bundle.validate_limits(limits)
    return bundle


class ResponseEnvelope(_Record):
    """Private response channel only; serialization may disclose text and an opening."""

    schema_id: Literal["hallmark/response-envelope/1"]
    receipt: SignedReceipt
    response: Annotated[
        str | None,
        Field(max_length=32768, repr=False, description="Exact UTF-8, at most 32768 bytes."),
    ]
    opening: Annotated[TranscriptOpening | None, Field(repr=False)]
    proof_status: CollectionState

    @field_validator("response")
    @classmethod
    def bounded_utf8(cls, response: str | None) -> str | None:
        if response is not None and len(response.encode("utf-8")) > 32768:
            raise ValueError("response exceeds the UTF-8 byte limit")
        return response

    @model_validator(mode="after")
    def coherent_release(self) -> Self:
        if (self.receipt.body.release == "blocked") != (self.proof_status == "blocked"):
            raise ValueError("receipt release and collection status disagree")
        if self.proof_status in ("blocked", "failed", "expired"):
            if self.response is not None or self.opening is not None:
                raise ValueError("terminal unsuccessful response must omit private payloads")
        elif self.response is None:
            raise ValueError("released response must include response text")
        if self.opening is not None:
            if (
                self.opening.response != self.response
                or self.opening.commitment() != self.receipt.body.transcript
            ):
                raise ValueError("opening and response declarations disagree")
        return self


class BundleStatus(_Record):
    """Reported collection state, not evidence that a referenced bundle was verified."""

    schema_id: Literal["hallmark/bundle-status/1"]
    receipt_id: Digest32
    state: CollectionState
    bundle: FileRef | None
    error: ErrorCode | None

    @model_validator(mode="after")
    def coherent_status(self) -> Self:
        if self.state == "ready":
            if self.bundle is None or self.bundle.size == 0 or self.error is not None:
                raise ValueError("ready requires a nonempty bundle reference and no error")
        elif self.bundle is not None:
            raise ValueError("only ready may reference a complete bundle")
        if self.state == "pending" and self.error is not None:
            raise ValueError("pending is not a failed job")
        if self.state == "blocked" and self.error != "POLICY_BLOCKED":
            raise ValueError("blocked requires its policy code")
        if self.state == "expired" and self.error != "STALE_EVIDENCE":
            raise ValueError("expired requires its freshness code")
        if self.state == "failed" and self.error in (None, "PROOF_PENDING", "POLICY_BLOCKED"):
            raise ValueError("failed requires a failure code")
        return self


class Claim(_Record):
    """A bounded reported claim; decoding it does not establish its truth."""

    status: Literal["accepted", "rejected", "not-accepted"]
    strength: Literal["hardware-attested", "cryptographic", "none"]
    assumptions: Annotated[tuple[Identifier, ...], Field(strict=False, max_length=64)]
    residuals: Annotated[tuple[Identifier, ...], Field(strict=False, min_length=1, max_length=64)]

    @model_validator(mode="after")
    def coherent_claim(self) -> Self:
        if (self.status == "accepted") != (self.strength != "none"):
            raise ValueError("only an accepted claim may report an evidence strength")
        for identifiers in (self.assumptions, self.residuals):
            if list(identifiers) != sorted(set(identifiers)):
                raise ValueError("claim identifiers must be sorted and unique")
        if not _COMMON_RESIDUALS.issubset(self.residuals):
            raise ValueError("common residuals are mandatory for every claim")
        return self


class VerificationResult(_Record):
    """Reported verifier output only. No verifier or acceptance factory is supplied."""

    schema_id: Literal["hallmark/verification-result/1"]
    accepted: bool
    mode: Literal["B1", "B2"]
    claim_a: Claim
    claim_b: Claim
    policy_pass: bool | None
    codes: Annotated[tuple[ErrorCode, ...], Field(strict=False, max_length=64)]
    evidence: Annotated[tuple[Digest32, ...], Field(strict=False, max_length=8192)]

    @model_validator(mode="after")
    def coherent_result(self) -> Self:
        for identifiers in (self.codes, self.evidence):
            if list(identifiers) != sorted(set(identifiers)):
                raise ValueError("result identifiers must be sorted and unique")
        if self.claim_a.strength == "cryptographic" or self.claim_b.strength == "hardware-attested":
            raise ValueError("claim strength belongs to the other claim")
        if "hardware-trust" not in self.claim_a.residuals:
            raise ValueError("claim A must retain hardware trust")
        if self.claim_b.status == "accepted":
            if not _PROOF_ASSUMPTIONS.issubset(self.claim_b.assumptions):
                raise ValueError("accepted B requires proof and registry assumptions")
            if self.mode == "B2" and self.claim_a.status != "accepted":
                raise ValueError("B2 claim B requires accepted claim A")
        elif self.policy_pass is not None:
            raise ValueError("a policy verdict requires accepted claim B")
        if self.mode == "B2":
            if "hardware-input-binding" not in self.claim_b.residuals:
                raise ValueError("B2 must retain hardware input binding")
        elif {"hardware-trust", "hardware-input-binding"}.intersection(
            (*self.claim_b.assumptions, *self.claim_b.residuals)
        ):
            raise ValueError("B1 claim B must not inherit hardware trust")
        if ("POLICY_BLOCKED" in self.codes) != (self.policy_pass is False):
            raise ValueError("policy-blocked code requires an established blocking verdict")
        if "PROOF_PENDING" in self.codes and self.claim_b.status != "not-accepted":
            raise ValueError("pending is not an accepted or rejected proof")
        if "PROOF_INVALID" in self.codes and self.claim_b.status != "rejected":
            raise ValueError("invalid proof requires rejected claim B")
        if "ATTESTATION_INVALID" in self.codes and self.claim_a.status != "rejected":
            raise ValueError("invalid attestation requires rejected claim A")
        if self.accepted:
            if (
                self.codes
                or self.policy_pass is not True
                or self.claim_b.status != "accepted"
                or self.claim_a.status == "rejected"
                or not self.evidence
            ):
                raise ValueError("overall acceptance disagrees with reported evidence")
        elif not self.codes:
            raise ValueError("nonacceptance requires a finite reason code")
        return self

    def validate_requirements(self, trust: TrustPolicy) -> None:
        """Compare reported mode/acceptance to external requirements, without verification."""
        if type(trust) is not TrustPolicy:
            raise HallmarkError("TRUST_MISSING", "verify")
        result, trust = self._validated(), trust._validated()
        if result.mode != trust.binding or (
            result.accepted
            and trust.required_claims == "A+B"
            and result.claim_a.status != "accepted"
        ):
            raise HallmarkError("TRUST_MISSING", "verify")
