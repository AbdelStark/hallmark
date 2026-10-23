"""Detached authorization of fixed LLM parameters by a caller-provisioned key."""

from typing import Annotated, Literal, Self

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from pydantic import Field, WithJsonSchema, model_validator

from hallmark.classifier_manifest import U64
from hallmark.errors import HallmarkError
from hallmark.manifests import Digest32, FileHash32, _Record
from hallmark.wire import WireLimits

LIMITS = WireLimits(max_bytes=16384, nesting=8)


class LlmEnrollment(_Record):
    """Exact case/source authorization; no security-review or key-custody verdict."""

    schema_id: Literal["hallmark/llm-enrollment/1"]
    case_sha256: FileHash32
    verifier: Digest32
    not_before: U64
    expires_at: U64

    @model_validator(mode="after")
    def valid_interval(self) -> Self:
        if self.not_before >= self.expires_at:
            raise ValueError("empty enrollment interval")
        return self

    def signing_bytes(self) -> bytes:
        tag = b"hallmark/research/sign/llm-enrollment/1"
        return len(tag).to_bytes(4, "big") + tag + self.encode(limits=LIMITS)


class SignedLlmEnrollment(_Record):
    schema_id: Literal["hallmark/signed-llm-enrollment/1"]
    body: LlmEnrollment
    signature: Annotated[
        bytes,
        Field(min_length=64, max_length=64, repr=False),
        WithJsonSchema(
            {"type": "string", "pattern": "^[0-9a-fA-F]{128}$", "minLength": 128, "maxLength": 128}
        ),
    ]


def sign_llm_enrollment(body: LlmEnrollment, key: Ed25519PrivateKey) -> SignedLlmEnrollment:
    """Sign a reviewed body with a caller-owned key; never generate or load keys."""
    if type(body) is not LlmEnrollment or not isinstance(key, Ed25519PrivateKey):
        raise HallmarkError("INPUT_INVALID", "enroll")
    body = body._validated()
    return SignedLlmEnrollment(
        schema_id="hallmark/signed-llm-enrollment/1",
        body=body,
        signature=key.sign(body.signing_bytes()),
    )


def verify_llm_enrollment(
    raw: bytes,
    *,
    trusted_key: bytes,
    expected_case: bytes,
    expected_verifier: bytes,
    now: int,
) -> LlmEnrollment:
    """Authenticate exact parameters under an external key and the caller's clock.

    This has no key discovery, revocation service or persistent rollback state.
    A signature authenticates the signer's authorization, not scientific validity.
    """
    if (
        any(
            type(value) is not bytes or len(value) != 32
            for value in (trusted_key, expected_case, expected_verifier)
        )
        or type(now) is not int
        or not 0 <= now < 2**64
    ):
        raise HallmarkError("INPUT_INVALID", "enroll")
    signed = SignedLlmEnrollment.decode(raw, limits=LIMITS)
    try:
        Ed25519PublicKey.from_public_bytes(trusted_key).verify(
            signed.signature, signed.body.signing_bytes()
        )
    except InvalidSignature:
        raise HallmarkError("SIGNATURE_INVALID", "enroll") from None
    body = signed.body
    if body.case_sha256 != expected_case or body.verifier != expected_verifier:
        raise HallmarkError("REQUEST_MISMATCH", "bind")
    if not body.not_before <= now < body.expires_at:
        raise HallmarkError("STALE_EVIDENCE", "enroll")
    return body
