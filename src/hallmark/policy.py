"""V1 all-pass policies and caller-pinned requests; validation supplies no trust."""

from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from hallmark.classifier_manifest import U64, ClassifierManifest
from hallmark.contracts import Identifier
from hallmark.errors import HallmarkError
from hallmark.manifests import _DIGEST_JSON, Digest32, ModelManifest, _Artifact, _Record
from hallmark.wire import WireError

B32 = Annotated[bytes, Field(min_length=32, max_length=32), _DIGEST_JSON]
ClassifierSet = tuple[ClassifierManifest, ClassifierManifest, ClassifierManifest]


class Policy(_Artifact):
    """An ordered rule/MLP/encoder declaration, not policy admission or a verdict."""

    _domain = "policy"
    schema_id: Literal["hallmark/policy/1"]
    rubric: Digest32
    classifiers: Annotated[tuple[Digest32, Digest32, Digest32], Field(strict=False)]
    combination: Literal["all-pass"]
    language: Literal["en"]
    scope: Literal["prompt"]
    max_prompt_bytes: Annotated[int, Field(ge=0, le=32768)]
    max_response_bytes: Annotated[int, Field(ge=0, le=32768)]

    @model_validator(mode="after")
    def distinct_classifiers(self) -> Self:
        if len(set(self.classifiers)) != 3:
            raise ValueError("classifier identities must be distinct")
        return self

    def validate_classifiers(self, classifiers: ClassifierSet) -> None:
        """Resolve opaque digests to exactly one validated manifest of each kind."""
        policy = self._validated()
        if (
            type(classifiers) is not tuple
            or len(classifiers) != 3
            or any(type(item) is not ClassifierManifest for item in classifiers)
        ):
            raise WireError("INPUT_INVALID")
        checked = tuple(item._validated() for item in classifiers)
        if (
            tuple(item.kind for item in checked) != ("rule", "mlp", "encoder")
            or tuple(item.identity() for item in checked) != policy.classifiers
        ):
            raise WireError("INPUT_INVALID")


class ChainExpectation(_Record):
    sequence: U64
    previous: Digest32 | None

    @model_validator(mode="after")
    def predecessor(self) -> Self:
        if (self.sequence == 0) != (self.previous is None):
            raise ValueError("sequence zero has no predecessor; later sequences require one")
        return self


class RequestExpectation(_Record):
    """Required caller expectations; encoding cannot attest to nonce randomness."""

    schema_id: Literal["hallmark/request-expectation/1"]
    audience: Identifier
    nonce: B32
    interaction_id: B32
    model: Digest32
    policy: Digest32
    continuity: ChainExpectation | None


class Request(_Record):
    schema_id: Literal["hallmark/request/1"]
    expected: RequestExpectation
    prompt: Annotated[
        str,
        Field(max_length=32768, repr=False, description="Exact UTF-8, at most 32768 bytes."),
    ]
    system_ref: Digest32

    @field_validator("prompt")
    @classmethod
    def bounded_utf8(cls, prompt: str) -> str:
        if len(prompt.encode("utf-8")) > 32768:
            raise ValueError("prompt exceeds the UTF-8 byte limit")
        return prompt

    def validate_against(
        self,
        expected: RequestExpectation,
        *,
        model: ModelManifest,
        policy: Policy,
        classifiers: ClassifierSet,
    ) -> None:
        """Compare independent caller expectations and declared artifact identities.

        Does not enroll artifacts, load a model, consume a nonce, or verify evidence.
        """
        request = self._validated()
        if (
            type(expected) is not RequestExpectation
            or type(model) is not ModelManifest
            or type(policy) is not Policy
        ):
            raise WireError("INPUT_INVALID")
        expected = expected._validated()
        model = model._validated()
        policy = policy._validated()
        policy.validate_classifiers(classifiers)
        if (
            request.expected != expected
            or expected.model != model.identity()
            or expected.policy != policy.identity()
        ):
            raise HallmarkError("REQUEST_MISMATCH", "bind")
        if len(request.prompt.encode("utf-8")) > policy.max_prompt_bytes:
            raise HallmarkError("LIMIT_EXCEEDED", "bind")
