"""External registry enrollment. No key discovery, receipt verification or policy adoption."""

import time
from dataclasses import dataclass
from typing import Annotated, Literal, Self

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import Field, WithJsonSchema, model_validator

from hallmark.classifier_manifest import U64
from hallmark.errors import HallmarkError
from hallmark.manifests import ArtifactDigest, Digest32, _Artifact, _Record
from hallmark.policy import B32
from hallmark.wire import H, WireLimits

type EntryKind = Literal["model", "classifier", "policy", "backend", "epoch-measurement"]
MAX_HISTORY = 1024


class Limits(_Record):
    """Caller ceilings; worker RSS enforcement belongs to the verifier worker."""

    bundle_bytes: Annotated[int, Field(gt=0, le=67108864)]
    proof_bytes: Annotated[int, Field(gt=0, le=16777216)]
    nesting: Annotated[int, Field(gt=0, le=16)]
    verify_seconds: Annotated[int, Field(gt=0, le=60)]
    worker_memory_bytes: Annotated[int, Field(gt=0, le=2**31)]


class TrustPolicy(_Artifact):
    """Must come from the relying party's authenticated provisioning channel."""

    _domain = "trust"
    schema_id: Literal["hallmark/trust/1"]
    registry_keys: Annotated[tuple[B32, ...], Field(strict=False, min_length=1, max_length=16)]
    signature_threshold: Annotated[int, Field(ge=1, le=16)]
    min_registry_sequence: U64
    accepted_models: Annotated[
        tuple[Digest32, ...], Field(strict=False, min_length=1, max_length=64)
    ]
    accepted_policies: Annotated[
        tuple[Digest32, ...], Field(strict=False, min_length=1, max_length=64)
    ]
    accepted_backends: Annotated[
        tuple[Digest32, ...], Field(strict=False, min_length=1, max_length=16)
    ]
    hardware_roots: Annotated[tuple[Digest32, ...], Field(strict=False, max_length=64)]
    measurements: Annotated[tuple[Digest32, ...], Field(strict=False, max_length=64)]
    required_claims: Literal["A+B", "B"]
    binding: Literal["B1", "B2"]
    max_age_seconds: Annotated[int, Field(gt=0, le=2**64 - 1)]
    limits: Limits

    @model_validator(mode="after")
    def consistent(self) -> Self:
        for values in (
            self.registry_keys,
            self.accepted_models,
            self.accepted_policies,
            self.accepted_backends,
            self.hardware_roots,
            self.measurements,
        ):
            if len(set(values)) != len(values):
                raise ValueError("duplicate trust identity")
        if self.signature_threshold > len(self.registry_keys):
            raise ValueError("unreachable signature threshold")
        if self.binding == "B2" and self.required_claims != "A+B":
            raise ValueError("B2 requires claim A")
        if self.required_claims == "A+B" and (not self.hardware_roots or not self.measurements):
            raise ValueError("claim A requires external roots and measurements")
        return self


class RegistryEntry(_Record):
    kind: EntryKind
    digest: Digest32
    valid_from: U64
    valid_until: U64
    retired_at: U64 | None
    review: Digest32

    @model_validator(mode="after")
    def interval(self) -> Self:
        if self.valid_from >= self.valid_until:
            raise ValueError("empty validity interval")
        return self

    def validate_time(self, *, issued_at: int, now: int) -> None:
        entry = self._validated()
        _clock(now)
        _clock(issued_at)
        if entry.retired_at is not None and entry.retired_at <= now:
            raise HallmarkError("ARTIFACT_RETIRED", "enroll")
        if not entry.valid_from <= issued_at < entry.valid_until or issued_at > now:
            raise HallmarkError("STALE_EVIDENCE", "enroll")


class RegistryBody(_Artifact):
    _domain = "registry"
    schema_id: Literal["hallmark/registry/1"]
    sequence: U64
    previous: Digest32 | None
    issued_at: U64
    expires_at: U64
    entries: Annotated[
        tuple[RegistryEntry, ...], Field(strict=False, min_length=1, max_length=4096)
    ]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.issued_at >= self.expires_at:
            raise ValueError("empty snapshot interval")
        if (self.sequence == 0) != (self.previous is None):
            raise ValueError("invalid predecessor")
        keys = [(entry.kind, entry.digest) for entry in self.entries]
        if any(a >= b for a, b in zip(keys, keys[1:], strict=False)):
            raise ValueError("entries must be sorted and unique")
        return self

    def signing_bytes(self) -> bytes:
        tag = b"hallmark/v1/sign/registry"
        return len(tag).to_bytes(4, "big") + tag + self.encode()


class RegistrySignature(_Record):
    key_id: Digest32
    signature: Annotated[
        bytes,
        Field(min_length=64, max_length=64, repr=False),
        WithJsonSchema(
            {"type": "string", "pattern": "^[0-9a-fA-F]{128}$", "minLength": 128, "maxLength": 128}
        ),
    ]


class SignedRegistry(_Record):
    schema_id: Literal["hallmark/signed-registry/1"]
    body: RegistryBody
    signatures: Annotated[
        tuple[RegistrySignature, ...], Field(strict=False, min_length=1, max_length=16)
    ]

    @model_validator(mode="after")
    def distinct_signers(self) -> Self:
        if len({signature.key_id for signature in self.signatures}) != len(self.signatures):
            raise ValueError("duplicate registry signer")
        return self

    def verify_signatures(self, trust: TrustPolicy) -> None:
        if type(trust) is not TrustPolicy:
            raise HallmarkError("TRUST_MISSING", "enroll")
        signed, trust = self._validated(), trust._validated()
        _verify_signatures(signed.signatures, signed.body.signing_bytes(), trust)


def _verify_signatures(
    signatures: tuple[RegistrySignature, ...], message: bytes, trust: TrustPolicy
) -> None:
    keys = {H("key", key): key for key in trust.registry_keys}
    if not trust.signature_threshold <= len(signatures) <= 16 or len(
        {signature.key_id for signature in signatures}
    ) != len(signatures):
        raise HallmarkError("SIGNATURE_INVALID", "enroll")
    for signature in signatures:
        if signature.key_id not in keys:
            raise HallmarkError("SIGNATURE_INVALID", "enroll")
        try:
            Ed25519PublicKey.from_public_bytes(keys[signature.key_id]).verify(
                signature.signature, message
            )
        except (InvalidSignature, UnsupportedAlgorithm, ValueError):
            break
    else:
        return
    raise HallmarkError("SIGNATURE_INVALID", "enroll")


class RegistryState(_Record):
    schema_id: Literal["hallmark/registry-state/1"]
    sequence: U64
    digest: Digest32


@dataclass(frozen=True, init=False)
class Enrollment:
    """Process-local result, never a decoded source of trust.

    Admitted identities still require receipt-time validation and resolution of
    the externally pinned policy's classifier identities by the full verifier.
    """

    registry: ArtifactDigest
    state: RegistryState
    trust: ArtifactDigest
    admitted: tuple[RegistryEntry, ...]
    checked_at: int

    def __init__(self) -> None:
        raise TypeError("use enroll with external trust and state")

    def require_entry(self, kind: EntryKind, digest: ArtifactDigest, *, issued_at: int) -> None:
        for entry in self.admitted:
            if entry.kind == kind and entry.digest == digest:
                entry.validate_time(issued_at=issued_at, now=self.checked_at)
                return
        raise HallmarkError("TRUST_MISSING", "enroll")


def _clock(value: int) -> None:
    if type(value) is not int or not 0 <= value <= 2**64 - 1:
        raise HallmarkError("INPUT_INVALID", "enroll")


def enroll(
    snapshot: SignedRegistry,
    trust: TrustPolicy,
    state: RegistryState,
    now: int,
    *,
    history: tuple[SignedRegistry, ...] = (),
) -> Enrollment:
    """Verify every successor after an external checkpoint, then the current snapshot.

    History excludes both the checkpoint and final snapshot. No default roots,
    checkpoint or clock exist. This pure function does not persist acceptance.
    """
    if type(trust) is not TrustPolicy or type(state) is not RegistryState:
        raise HallmarkError("TRUST_MISSING", "enroll")
    if type(snapshot) is not SignedRegistry:
        raise HallmarkError("INPUT_INVALID", "enroll")
    trust, state = trust._validated(), state._validated()
    _clock(now)
    if type(history) is not tuple or len(history) > MAX_HISTORY:
        raise HallmarkError("LIMIT_EXCEEDED", "enroll")
    if any(type(item) is not SignedRegistry for item in history):
        raise HallmarkError("INPUT_INVALID", "enroll")
    deadline = time.monotonic() + trust.limits.verify_seconds
    limits = WireLimits(max_bytes=trust.limits.bundle_bytes, nesting=trust.limits.nesting)
    total_bytes = 0
    current = state
    last_issued = 0
    for index, candidate in enumerate((*history, snapshot)):
        candidate = candidate._validated()
        total_bytes += len(candidate.encode(limits=limits))
        if total_bytes > trust.limits.bundle_bytes or time.monotonic() > deadline:
            raise HallmarkError("LIMIT_EXCEEDED", "enroll")
        body = candidate.body
        identity = body.identity()
        if body.sequence == state.sequence:
            if history or identity != state.digest:
                raise HallmarkError("REGISTRY_INVALID", "enroll")
        elif body.sequence != current.sequence + 1 or body.previous != current.digest:
            raise HallmarkError("REGISTRY_INVALID", "enroll")
        if body.issued_at < last_issued or body.issued_at > now:
            raise HallmarkError("STALE_EVIDENCE", "enroll")
        candidate.verify_signatures(trust)
        if time.monotonic() > deadline:
            raise HallmarkError("LIMIT_EXCEEDED", "enroll")
        current = RegistryState(
            schema_id="hallmark/registry-state/1", sequence=body.sequence, digest=identity
        )
        last_issued = body.issued_at
        if index == len(history):
            if body.sequence < trust.min_registry_sequence:
                raise HallmarkError("REGISTRY_INVALID", "enroll")
            if now >= body.expires_at or now - body.issued_at > trust.max_age_seconds:
                raise HallmarkError("STALE_EVIDENCE", "enroll")
    allowed: dict[EntryKind, tuple[ArtifactDigest, ...]] = {
        "model": trust.accepted_models,
        "policy": trust.accepted_policies,
        "backend": trust.accepted_backends,
        "epoch-measurement": trust.measurements,
    }
    admitted = tuple(
        entry
        for entry in body.entries
        if (entry.kind == "classifier" or entry.digest in allowed[entry.kind])
        and (entry.retired_at is None or entry.retired_at > now)
    )
    if not admitted:
        raise HallmarkError("TRUST_MISSING", "enroll")
    result = object.__new__(Enrollment)
    for key, value in (
        ("registry", current.digest),
        ("state", current),
        ("trust", trust.identity()),
        ("admitted", admitted),
        ("checked_at", now),
    ):
        object.__setattr__(result, key, value)
    return result
