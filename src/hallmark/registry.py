"""Offline registry authoring with caller-owned keys and externally enrolled trust."""

import time
from typing import Annotated, Literal, Self

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import Field, model_validator

from hallmark.classifier_manifest import U64
from hallmark.contracts import Identifier
from hallmark.enrollment import (
    Enrollment,
    RegistryBody,
    RegistryEntry,
    RegistrySignature,
    RegistryState,
    SignedRegistry,
    TrustPolicy,
    _verify_signatures,
    enroll,
    validate_successor,
)
from hallmark.errors import HallmarkError
from hallmark.manifests import ArtifactDigest, Digest32, _Record
from hallmark.wire import H, WireLimits

type Signatures = Annotated[
    tuple[RegistrySignature, ...], Field(strict=False, min_length=1, max_length=16)
]
type KeyIDs = Annotated[tuple[Digest32, ...], Field(strict=False, min_length=1, max_length=16)]


def _trust(trust: TrustPolicy) -> TrustPolicy:
    if type(trust) is not TrustPolicy:
        raise HallmarkError("TRUST_MISSING", "enroll")
    return trust._validated()


def _sign(
    message: bytes, trust: TrustPolicy, keys: tuple[Ed25519PrivateKey, ...]
) -> tuple[RegistrySignature, ...]:
    if (
        type(keys) is not tuple
        or not trust.signature_threshold <= len(keys) <= 16
        or any(not isinstance(key, Ed25519PrivateKey) for key in keys)
    ):
        raise HallmarkError("SIGNATURE_INVALID", "enroll")
    ids = tuple(H("key", key.public_key().public_bytes_raw()) for key in keys)
    if len(set(ids)) != len(ids) or not set(ids) <= {H("key", k) for k in trust.registry_keys}:
        raise HallmarkError("SIGNATURE_INVALID", "enroll")
    try:
        return tuple(
            RegistrySignature(key_id=ArtifactDigest(key_id), signature=key.sign(message))
            for key_id, key in sorted(zip(ids, keys, strict=True), key=lambda pair: pair[0])
        )
    except (ValueError, UnsupportedAlgorithm):
        pass
    raise HallmarkError("SIGNATURE_INVALID", "enroll")


def sign_snapshot(
    body: RegistryBody, trust: TrustPolicy, keys: tuple[Ed25519PrivateKey, ...]
) -> SignedRegistry:
    """Sign exactly the reviewed body. No key generation, loading or adoption."""
    trust = _trust(trust)
    if type(body) is not RegistryBody:
        raise HallmarkError("INPUT_INVALID", "enroll")
    body = body._validated()
    signed = SignedRegistry(
        schema_id="hallmark/signed-registry/1",
        body=body,
        signatures=_sign(body.signing_bytes(), trust, keys),
    )
    signed.verify_signatures(trust)
    signed.encode(
        limits=WireLimits(max_bytes=trust.limits.bundle_bytes, nesting=trust.limits.nesting)
    )
    return signed


def next_snapshot(
    previous: RegistryBody,
    entries: tuple[RegistryEntry, ...],
    *,
    issued_at: int,
    expires_at: int,
) -> RegistryBody:
    """Build the next complete snapshot; caller supplies explicit review references."""
    if type(previous) is not RegistryBody:
        raise HallmarkError("INPUT_INVALID", "enroll")
    previous = previous._validated()
    candidate = RegistryBody(
        schema_id="hallmark/registry/1",
        sequence=previous.sequence + 1,
        previous=previous.identity(),
        issued_at=issued_at,
        expires_at=expires_at,
        entries=entries,
    )
    validate_successor(previous, candidate)
    return candidate


class RegistryTransition(_Record):
    """A proposal binding two complete external policies and one activation link."""

    schema_id: Literal["hallmark/registry-transition/1"]
    old_trust: Digest32
    new_trust: Digest32
    old_keys: KeyIDs
    new_keys: KeyIDs
    activation_sequence: Annotated[U64, Field(ge=1)]
    previous: Digest32
    reason: Identifier
    review: Digest32

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.old_trust == self.new_trust:
            raise ValueError("unchanged trust policy")
        for ids in (self.old_keys, self.new_keys):
            if tuple(sorted(set(ids))) != ids:
                raise ValueError("key IDs must be sorted and unique")
        return self

    def signing_bytes(self, role: Literal["old", "new"]) -> bytes:
        if role not in ("old", "new"):
            raise HallmarkError("INPUT_INVALID", "enroll")
        tag = b"hallmark/v1/sign/registry-transition/" + role.encode("ascii")
        return len(tag).to_bytes(4, "big") + tag + self.encode()

    def validate_against(self, old: TrustPolicy, new: TrustPolicy, state: RegistryState) -> None:
        body, old, new = self._validated(), _trust(old), _trust(new)
        if type(state) is not RegistryState:
            raise HallmarkError("TRUST_MISSING", "enroll")
        state = state._validated()
        if (
            body.old_trust != old.identity()
            or body.new_trust != new.identity()
            or body.old_keys != tuple(sorted(H("key", key) for key in old.registry_keys))
            or body.new_keys != tuple(sorted(H("key", key) for key in new.registry_keys))
            or body.previous != state.digest
            or body.activation_sequence != state.sequence + 1
            or old.min_registry_sequence > state.sequence
            or new.min_registry_sequence != body.activation_sequence
            or (
                set(old.registry_keys) == set(new.registry_keys)
                and old.signature_threshold == new.signature_threshold
            )
        ):
            raise HallmarkError("REGISTRY_INVALID", "enroll")


class SignedTransition(_Record):
    schema_id: Literal["hallmark/signed-transition/1"]
    body: RegistryTransition
    old_signatures: Signatures
    new_signatures: Signatures

    @model_validator(mode="after")
    def distinct_signers(self) -> Self:
        for signatures in (self.old_signatures, self.new_signatures):
            if len({signature.key_id for signature in signatures}) != len(signatures):
                raise ValueError("duplicate transition signer")
        return self

    def verify(self, old: TrustPolicy, new: TrustPolicy, state: RegistryState) -> None:
        signed, old, new = self._validated(), _trust(old), _trust(new)
        signed.body.validate_against(old, new, state)
        limits = WireLimits(
            max_bytes=min(old.limits.bundle_bytes, new.limits.bundle_bytes),
            nesting=min(old.limits.nesting, new.limits.nesting),
        )
        signed.encode(limits=limits)
        _verify_signatures(signed.old_signatures, signed.body.signing_bytes("old"), old)
        _verify_signatures(signed.new_signatures, signed.body.signing_bytes("new"), new)


def sign_transition(
    body: RegistryTransition,
    old: TrustPolicy,
    new: TrustPolicy,
    state: RegistryState,
    *,
    old_keys: tuple[Ed25519PrivateKey, ...],
    new_keys: tuple[Ed25519PrivateKey, ...],
) -> SignedTransition:
    if type(body) is not RegistryTransition:
        raise HallmarkError("INPUT_INVALID", "enroll")
    body, old, new = body._validated(), _trust(old), _trust(new)
    body.validate_against(old, new, state)
    signed = SignedTransition(
        schema_id="hallmark/signed-transition/1",
        body=body,
        old_signatures=_sign(body.signing_bytes("old"), old, old_keys),
        new_signatures=_sign(body.signing_bytes("new"), new, new_keys),
    )
    signed.verify(old, new, state)
    return signed


def enroll_transition(
    snapshot: SignedRegistry,
    transition: SignedTransition,
    old: TrustPolicy,
    new: TrustPolicy,
    state: RegistryState,
    now: int,
    *,
    previous: SignedRegistry,
) -> Enrollment:
    """Check one dual-authorized activation; never discover or install new roots."""
    if (
        type(transition) is not SignedTransition
        or type(snapshot) is not SignedRegistry
        or type(previous) is not SignedRegistry
    ):
        raise HallmarkError("INPUT_INVALID", "enroll")
    old, new = _trust(old), _trust(new)
    deadline = time.monotonic() + min(old.limits.verify_seconds, new.limits.verify_seconds)
    transition.verify(old, new, state)
    previous, snapshot = previous._validated(), snapshot._validated()
    limits = WireLimits(
        max_bytes=min(old.limits.bundle_bytes, new.limits.bundle_bytes),
        nesting=min(old.limits.nesting, new.limits.nesting),
    )
    if sum(len(item.encode(limits=limits)) for item in (previous, transition, snapshot)) > (
        limits.max_bytes
    ):
        raise HallmarkError("LIMIT_EXCEEDED", "enroll")
    if previous.body.identity() != state.digest or previous.body.sequence != state.sequence:
        raise HallmarkError("REGISTRY_INVALID", "enroll")
    previous.verify_signatures(old)
    validate_successor(previous.body, snapshot.body)
    result = enroll(snapshot, new, state, now)
    if time.monotonic() > deadline:
        raise HallmarkError("LIMIT_EXCEEDED", "enroll")
    return result
