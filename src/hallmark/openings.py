"""Exact v1 openings and complete-input hashes, not evidence or tokenizer verification."""

from typing import Annotated, Literal

from pydantic import Field, field_validator

from hallmark.classifier_manifest import ClassifierManifest, InputProfile
from hallmark.errors import HallmarkError
from hallmark.manifests import ArtifactDigest, Digest32, _Record
from hallmark.policy import B32, RequestExpectation
from hallmark.wire import H, WireError


def _check_b32(*values: bytes) -> None:
    if any(type(value) is not bytes or len(value) != 32 for value in values):
        raise WireError("INPUT_INVALID")


class TranscriptOpening(_Record):
    """Private opening; repr omits content/salt, but serialization discloses them."""

    schema_id: Literal["hallmark/transcript-opening/1"]
    system_ref: Digest32
    prompt: Annotated[
        str, Field(max_length=32768, repr=False, description="Exact UTF-8, at most 32768 bytes.")
    ]
    response: Annotated[
        str, Field(max_length=32768, repr=False, description="Exact UTF-8, at most 32768 bytes.")
    ]
    salt: Annotated[B32, Field(repr=False)]

    @field_validator("prompt", "response")
    @classmethod
    def bounded_utf8(cls, text: str) -> str:
        if len(text.encode("utf-8")) > 32768:
            raise ValueError("text exceeds the UTF-8 byte limit")
        return text

    def commitment(self) -> ArtifactDigest:
        opening = self._validated()
        return ArtifactDigest(
            H(
                "transcript",
                [
                    opening.system_ref,
                    opening.salt,
                    opening.prompt.encode("utf-8"),
                    opening.response.encode("utf-8"),
                ],
            )
        )

    def context(self, expected: RequestExpectation) -> ArtifactDigest:
        """Bind the full external expectation and transcript; no proofs or signatures."""
        if type(expected) is not RequestExpectation:
            raise WireError("INPUT_INVALID")
        return ArtifactDigest(H("context", [expected._wire(), self.commitment()]))

    def verify_commitment(self, expected: ArtifactDigest) -> None:
        """Compare a caller-supplied transcript digest; supplies no enrollment or trust."""
        _check_b32(expected)
        if self.commitment() != expected:
            raise HallmarkError("OPENING_FAILED", "bind")


def derive_input_salt(salt: bytes, classifier: ArtifactDigest) -> bytes:
    """Derive a classifier-specific salt from a privately held 32-byte opening salt."""
    _check_b32(salt, classifier)
    return H("input-salt", [salt, classifier])


def input_commitment(
    opening: TranscriptOpening,
    classifier: ClassifierManifest,
    profile: InputProfile,
    *,
    token_units: tuple[int, ...] | None = None,
    vocabulary_size: int | None = None,
) -> ArtifactDigest:
    """Hash all prompt bytes, or complete tokens independently computed by the caller.

    Tokenization and vocabulary provenance require a qualified local adapter.
    Never supply token units or vocabulary limits taken on trust from a receipt.
    Prefix/suffix/padding are fixed by the profile, not part of original content.
    """
    if (
        type(opening) is not TranscriptOpening
        or type(classifier) is not ClassifierManifest
        or type(profile) is not InputProfile
    ):
        raise WireError("INPUT_INVALID")
    opening = opening._validated()
    classifier = classifier._validated()
    profile = profile._validated()
    encoding = "token-ids" if classifier.kind == "encoder" else "utf8-bytes"
    if classifier.input_profile != profile.identity() or profile.encoding != encoding:
        raise WireError("INPUT_INVALID")
    if profile.encoding == "utf8-bytes":
        if token_units is not None or vocabulary_size is not None:
            raise WireError("INPUT_INVALID")
        units = tuple(opening.prompt.encode("utf-8"))
    else:
        if (
            type(token_units) is not tuple
            or type(vocabulary_size) is not int
            or not 1 <= vocabulary_size <= 2**64
        ):
            raise WireError("INPUT_INVALID")
        units = token_units
        if len(units) > profile.max_units:
            raise WireError("LIMIT_EXCEEDED")
        if any(
            type(unit) is not int or not 0 <= unit < vocabulary_size
            for unit in (*profile.prefix_tokens, *profile.suffix_tokens, profile.padding_id, *units)
        ):
            raise WireError("INPUT_INVALID")
    if len(units) > profile.max_units:
        raise WireError("LIMIT_EXCEEDED")
    salt = derive_input_salt(opening.salt, classifier.identity())
    return ArtifactDigest(H("input", [salt, profile.identity(), len(units), list(units)]))
