"""V1 receipt/evidence containers and declared bindings, without cryptographic acceptance."""

from typing import Annotated, Literal, Self

from pydantic import Field, ValidationError, WithJsonSchema, model_validator

from hallmark.classifier_manifest import U64, ClassifierManifest, InputProfile
from hallmark.contracts import Int32
from hallmark.errors import HallmarkError
from hallmark.manifests import ArtifactDigest, Digest32, FileRef, _Artifact, _Record
from hallmark.policy import B32, ClassifierSet, Policy, RequestExpectation
from hallmark.wire import H, WireError

MAX_PROOF_BYTES = 16 * 1024 * 1024
MAX_EVIDENCE_BYTES = 16 * 1024 * 1024
B64 = Annotated[
    bytes,
    Field(min_length=64, max_length=64),
    WithJsonSchema(
        {"type": "string", "pattern": "^[0-9a-fA-F]{128}$", "minLength": 128, "maxLength": 128}
    ),
]
_OPAQUE_JSON = WithJsonSchema(
    {"type": "string", "pattern": "^(?:[0-9a-fA-F]{2})*$", "minLength": 2, "maxLength": 33554432}
)
ProfileSet = tuple[InputProfile, InputProfile, InputProfile]


def _current(issued_at: int, expires_at: int, now: int) -> None:
    if type(now) is not int or not 0 <= now < 2**64:
        raise WireError("INPUT_INVALID")
    if not issued_at <= now < expires_at:
        raise HallmarkError("STALE_EVIDENCE", "bind")


class ProofInputs(_Record):
    schema_id: Literal["hallmark/proof-inputs/1"]
    context: Digest32
    classifier: Digest32
    input_digest: Digest32
    unit_count: Annotated[int, Field(ge=0, le=32768)]
    chunk_count: Annotated[int, Field(ge=1, le=32768)]
    threshold: Int32
    verdict: bool

    @model_validator(mode="after")
    def coverage_shape(self) -> Self:
        if self.chunk_count > max(1, self.unit_count):
            raise ValueError("chunk count exceeds original content units")
        return self

    def to_fields(self) -> tuple[int, ...]:
        """Return 100 exact integers; a backend must constrain every field's range."""
        inputs = self._validated()
        return (
            *inputs.context,
            *inputs.classifier,
            *inputs.input_digest,
            inputs.unit_count,
            inputs.chunk_count,
            inputs.threshold + 2**31,
            int(inputs.verdict),
        )

    @classmethod
    def from_fields(cls, fields: tuple[int, ...]) -> Self:
        """Reject field aliases instead of reducing or interpreting signed residues."""
        if (
            type(fields) is not tuple
            or len(fields) != 100
            or any(type(value) is not int for value in fields)
            or any(not 0 <= value <= 255 for value in fields[:96])
            or not 0 <= fields[98] < 2**32
            or fields[99] not in (0, 1)
        ):
            raise WireError("INPUT_INVALID")
        try:
            return cls.model_validate(
                {
                    "schema_id": "hallmark/proof-inputs/1",
                    "context": bytes(fields[:32]),
                    "classifier": bytes(fields[32:64]),
                    "input_digest": bytes(fields[64:96]),
                    "unit_count": fields[96],
                    "chunk_count": fields[97],
                    "threshold": fields[98] - 2**31,
                    "verdict": bool(fields[99]),
                }
            )
        except ValidationError:
            pass
        raise WireError("INPUT_INVALID")

    def validate_profile(self, classifier: ClassifierManifest, profile: InputProfile) -> None:
        """Check declared identities, threshold and exact content chunk count only."""
        inputs = self._validated()
        if type(classifier) is not ClassifierManifest or type(profile) is not InputProfile:
            raise WireError("INPUT_INVALID")
        classifier, profile = classifier._validated(), profile._validated()
        capacity = profile.chunk_size - len(profile.prefix_tokens) - len(profile.suffix_tokens)
        encoding = "token-ids" if classifier.kind == "encoder" else "utf8-bytes"
        if (
            inputs.classifier != classifier.identity()
            or classifier.input_profile != profile.identity()
            or profile.encoding != encoding
            or inputs.threshold != classifier.threshold
            or inputs.unit_count > profile.max_units
            or inputs.chunk_count != max(1, (inputs.unit_count + capacity - 1) // capacity)
        ):
            raise HallmarkError("INPUT_BINDING_FAILED", "bind")


class EpochRecord(_Artifact):
    """Bounded opaque evidence; key/quote validity requires a qualified verifier."""

    _domain = "epoch"
    schema_id: Literal["hallmark/epoch/1"]
    epoch_id: B32
    key: B32
    model: Digest32
    measurement: Digest32
    issued_at: U64
    expires_at: U64
    cpu_evidence: Annotated[
        bytes, Field(min_length=1, max_length=MAX_EVIDENCE_BYTES, repr=False), _OPAQUE_JSON
    ]
    accelerator_evidence: Annotated[
        bytes, Field(min_length=1, max_length=MAX_EVIDENCE_BYTES, repr=False), _OPAQUE_JSON
    ]
    collateral: Annotated[tuple[FileRef, ...], Field(strict=False, min_length=1, max_length=256)]

    @model_validator(mode="after")
    def epoch_shape(self) -> Self:
        if not 0 < self.expires_at - self.issued_at <= 3600:
            raise ValueError("epoch lifetime must be positive and at most one hour")
        paths = [ref.path for ref in self.collateral]
        if paths != sorted(set(paths)):
            raise ValueError("collateral paths must be sorted and unique")
        return self

    def challenge(self) -> ArtifactDigest:
        epoch = self._validated()
        return ArtifactDigest(
            H(
                "epoch",
                [
                    epoch.epoch_id,
                    epoch.key,
                    epoch.model,
                    epoch.measurement,
                    epoch.issued_at,
                    epoch.expires_at,
                ],
            )
        )

    def key_id(self) -> ArtifactDigest:
        return ArtifactDigest(H("key", self._validated().key))

    def validate_time(self, now: int) -> None:
        epoch = self._validated()
        _current(epoch.issued_at, epoch.expires_at, now)


class ReceiptBody(_Artifact):
    _domain = "receipt"
    schema_id: Literal["hallmark/receipt/1"]
    expected: RequestExpectation
    issued_at: U64
    expires_at: U64
    epoch: Digest32
    sequence: U64
    previous: Digest32 | None
    transcript: Digest32
    inputs: Annotated[tuple[ProofInputs, ProofInputs, ProofInputs], Field(strict=False)]
    release: Literal["released", "blocked"]

    @model_validator(mode="after")
    def receipt_shape(self) -> Self:
        if self.issued_at >= self.expires_at:
            raise ValueError("receipt lifetime must be positive")
        if (self.sequence == 0) != (self.previous is None):
            raise ValueError("sequence and predecessor disagree")
        chain = self.expected.continuity
        if chain is not None and (self.sequence, self.previous) != (chain.sequence, chain.previous):
            raise ValueError("receipt disagrees with its continuity expectation")
        if len({inputs.classifier for inputs in self.inputs}) != 3:
            raise ValueError("classifier identities must be distinct")
        context = H("context", [self.expected._wire(), self.transcript])
        if any(inputs.context != context for inputs in self.inputs):
            raise ValueError("receipt inputs disagree with its context")
        if (self.release == "released") != all(inputs.verdict for inputs in self.inputs):
            raise ValueError("release disagrees with declared all-pass verdicts")
        return self

    def signing_bytes(self) -> bytes:
        """Return the exact Ed25519 message; does not create or check a signature."""
        tag = b"hallmark/v1/sign/receipt"
        return len(tag).to_bytes(4, "big") + tag + self.encode()

    def validate_expectation(self, expected: RequestExpectation, *, now: int) -> None:
        body = self._validated()
        if type(expected) is not RequestExpectation:
            raise WireError("INPUT_INVALID")
        if body.expected != expected._validated():
            raise HallmarkError("REQUEST_MISMATCH", "bind")
        _current(body.issued_at, body.expires_at, now)

    def validate_policy(
        self, policy: Policy, classifiers: ClassifierSet, profiles: ProfileSet
    ) -> None:
        """Resolve the declared three-way policy; no enrollment or verdict execution."""
        body = self._validated()
        if (
            type(policy) is not Policy
            or type(profiles) is not tuple
            or len(profiles) != 3
            or any(type(profile) is not InputProfile for profile in profiles)
        ):
            raise WireError("INPUT_INVALID")
        policy = policy._validated()
        policy.validate_classifiers(classifiers)
        if (
            body.expected.policy != policy.identity()
            or tuple(inputs.classifier for inputs in body.inputs) != policy.classifiers
        ):
            raise HallmarkError("INPUT_BINDING_FAILED", "bind")
        for inputs, classifier, profile in zip(body.inputs, classifiers, profiles, strict=True):
            inputs.validate_profile(classifier, profile)


class SignedReceipt(_Record):
    """Signature-shaped container only; no signature verification is implemented here."""

    schema_id: Literal["hallmark/signed-receipt/1"]
    body: ReceiptBody
    key_id: Digest32
    signature: Annotated[B64, Field(repr=False)]

    def validate_epoch(self, epoch: EpochRecord, *, now: int) -> None:
        """Compare declared key/model/epoch and time; does not authenticate any of them."""
        receipt = self._validated()
        if type(epoch) is not EpochRecord:
            raise WireError("INPUT_INVALID")
        epoch = epoch._validated()
        if (
            receipt.key_id != epoch.key_id()
            or receipt.body.epoch != epoch.identity()
            or receipt.body.expected.model != epoch.model
        ):
            raise HallmarkError("INPUT_BINDING_FAILED", "bind")
        epoch.validate_time(now)
        _current(receipt.body.issued_at, receipt.body.expires_at, now)
        _current(epoch.issued_at, epoch.expires_at, receipt.body.issued_at)


class ProofArtifact(_Record):
    """Opaque proof bytes and declared inputs; parsing never verifies a proof."""

    schema_id: Literal["hallmark/proof-artifact/1"]
    backend: Digest32
    verifier_key: Digest32
    public_inputs: ProofInputs
    proof: Annotated[
        bytes, Field(min_length=1, max_length=MAX_PROOF_BYTES, repr=False), _OPAQUE_JSON
    ]

    def validate_inputs(
        self,
        expected: ProofInputs,
        classifier: ClassifierManifest,
        profile: InputProfile,
        *,
        max_proof_bytes: int,
    ) -> None:
        """Compare external declared inputs and apply a caller's lower byte budget."""
        artifact = self._validated()
        if type(max_proof_bytes) is not int or not 1 <= max_proof_bytes <= MAX_PROOF_BYTES:
            raise WireError("INPUT_INVALID")
        if len(artifact.proof) > max_proof_bytes:
            raise WireError("LIMIT_EXCEEDED")
        if type(expected) is not ProofInputs:
            raise WireError("INPUT_INVALID")
        expected = expected._validated()
        expected.validate_profile(classifier, profile)
        if (
            artifact.public_inputs != expected
            or artifact.backend != classifier.backend
            or artifact.verifier_key != classifier.verifier_key
        ):
            raise HallmarkError("INPUT_BINDING_FAILED", "bind")
