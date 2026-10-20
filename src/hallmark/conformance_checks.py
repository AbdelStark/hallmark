"""Primary component adapters. No receipt signature, hardware or proof verifier."""

import tempfile
from pathlib import Path
from typing import cast

from pydantic import ValidationError

from hallmark.bundles import decode_bundle
from hallmark.classifier_manifest import ArithmeticProfile, ClassifierManifest, InputProfile
from hallmark.conformance import Check, Outcome
from hallmark.contracts import LinearArtifact
from hallmark.enrollment import (
    RegistryEntry,
    RegistryState,
    SignedRegistry,
    TrustPolicy,
    enroll,
)
from hallmark.errors import HallmarkError, sanitize_exception
from hallmark.manifests import ArtifactDigest, ModelManifest, verify_model_files
from hallmark.openings import TranscriptOpening, input_commitment
from hallmark.policy import ClassifierSet, Policy, Request, RequestExpectation
from hallmark.receipts import ProofArtifact, ProofInputs, ReceiptBody
from hallmark.reference import decision
from hallmark.registry import SignedTransition, enroll_transition
from hallmark.wire import DOMAINS, H, WireError, WireLimits, decode


def _execute(
    check: Check,
    inputs: tuple[bytes, ...],
    trust: TrustPolicy,
    expected_request: RequestExpectation,
    now: int,
) -> tuple[tuple[ArtifactDigest, ...], tuple[int, ...]]:
    digests: tuple[ArtifactDigest, ...] = ()
    integers: tuple[int, ...] = ()
    if check in ("wire", "wire-small"):
        limits = (
            WireLimits(max_bytes=64, nesting=3, max_items=8)
            if check == "wire-small"
            else (WireLimits())
        )
        digests = (ArtifactDigest(H("protocol", decode(inputs[0], limits=limits))),)
    elif check == "domains":
        value = decode(inputs[0])
        digests = tuple(ArtifactDigest(H(domain, value)) for domain in sorted(DOMAINS))
    elif check == "model":
        digests = (ModelManifest.decode(inputs[0]).identity(),)
    elif check == "model-files":
        model = ModelManifest.decode(inputs[0])
        if len(model.files) != 1:
            raise WireError("INPUT_INVALID")
        with tempfile.TemporaryDirectory(prefix="hallmark-conformance-model-") as directory:
            root = Path(directory)
            path = root / model.files[0].path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(inputs[1])
            verify_model_files(model, root, max_bytes=64 * 1024 * 1024)
    elif check == "classifier":
        digests = (ClassifierManifest.decode(inputs[0]).identity(),)
    elif check == "input-profile":
        digests = (InputProfile.decode(inputs[0]).identity(),)
    elif check == "policy":
        policy = Policy.decode(inputs[0])
        classifiers = cast(
            ClassifierSet, tuple(ClassifierManifest.decode(raw) for raw in inputs[1:])
        )
        policy.validate_classifiers(classifiers)
        digests = (policy.identity(),)
    elif check == "request":
        request = Request.decode(inputs[0])
        model = ModelManifest.decode(inputs[1])
        policy = Policy.decode(inputs[2])
        classifiers = cast(
            ClassifierSet, tuple(ClassifierManifest.decode(raw) for raw in inputs[3:])
        )
        request.validate_against(
            expected_request, model=model, policy=policy, classifiers=classifiers
        )
    elif check == "opening":
        opening = TranscriptOpening.decode(inputs[0])
        opening.verify_commitment(ArtifactDigest(inputs[1]))
        digests = (opening.commitment(), opening.context(expected_request))
    elif check == "input-bytes":
        opening = TranscriptOpening.decode(inputs[0])
        classifier = ClassifierManifest.decode(inputs[1])
        profile = InputProfile.decode(inputs[2])
        digests = (input_commitment(opening, classifier, profile),)
    elif check == "proof-fields":
        fields = decode(inputs[0])
        if not isinstance(fields, list) or any(type(value) is not int for value in fields):
            raise WireError("INPUT_INVALID")
        integers = ProofInputs.from_fields(cast(tuple[int, ...], tuple(fields))).to_fields()
    elif check == "proof-profile":
        public = ProofInputs.decode(inputs[0])
        public.validate_profile(
            ClassifierManifest.decode(inputs[1]), InputProfile.decode(inputs[2])
        )
        integers = public.to_fields()
    elif check == "receipt":
        body = ReceiptBody.decode(inputs[0])
        body.validate_expectation(expected_request, now=now)
        digests = (body.identity(),)
    elif check == "proof-declaration":
        proof = ProofArtifact.decode(inputs[0])
        public = ProofInputs.decode(inputs[1])
        proof.validate_inputs(
            public,
            ClassifierManifest.decode(inputs[2]),
            InputProfile.decode(inputs[3]),
            max_proof_bytes=trust.limits.proof_bytes,
        )
    elif check == "bundle":
        decode_bundle(inputs[0], limits=trust.limits)
    elif check == "enrollment":
        snapshot = SignedRegistry.decode(inputs[0])
        checkpoint = RegistryState.decode(inputs[1])
        required = RegistryEntry.decode(inputs[2])
        result = enroll(snapshot, trust, checkpoint, now)
        result.require_entry(required.kind, required.digest, issued_at=snapshot.body.issued_at)
        digests = (result.registry, result.trust)
    elif check == "entry-time":
        entry = RegistryEntry.decode(inputs[0])
        issued = decode(inputs[1])
        if type(issued) is not int:
            raise WireError("INPUT_INVALID")
        entry.validate_time(issued_at=issued, now=now)
    elif check == "rotation":
        current = SignedRegistry.decode(inputs[0])
        transition = SignedTransition.decode(inputs[1])
        old = TrustPolicy.decode(inputs[2])
        previous = SignedRegistry.decode(inputs[3])
        state = RegistryState.decode(inputs[4])
        result = enroll_transition(current, transition, old, trust, state, now, previous=previous)
        digests = (result.registry, result.trust)
    elif check == "arithmetic":
        graph = ArithmeticProfile.decode(inputs[0])
        files = decode(inputs[1])
        if not isinstance(files, dict) or any(type(raw) is not bytes for raw in files.values()):
            raise WireError("INPUT_INVALID")
        graph.validate_parameters(cast(dict[str, bytes], files))
        digests = (graph.identity(),)
    elif check == "linear":
        linear = LinearArtifact.model_validate_json(inputs[0])
        verdict = decision(linear, inputs[1].decode("utf-8"))
        integers = (int(verdict["score"]), int(verdict["pass"]))
    else:
        raise WireError("INPUT_INVALID")
    return digests, integers


def execute(
    check: Check,
    inputs: tuple[bytes, ...],
    trust: TrustPolicy,
    expected_request: RequestExpectation,
    now: int,
) -> Outcome:
    """Return actual component outcomes; no expected result or requirement is an input."""
    if check == "diagnostic":
        errors = {
            b"input": ValueError("SYNTHETIC_PRIVATE_SENTINEL"),
            b"memory": MemoryError("SYNTHETIC_PRIVATE_SENTINEL"),
            b"storage": PermissionError("SYNTHETIC_PRIVATE_SENTINEL"),
            b"internal": RuntimeError("SYNTHETIC_PRIVATE_SENTINEL"),
        }
        if inputs[0] not in errors:
            raise WireError("INPUT_INVALID")
        error = sanitize_exception(errors[inputs[0]], stage="execute")
        return Outcome(
            accepted=False,
            claim_a="not-accepted",
            claim_b="not-accepted",
            code=error.code,
            input_digests=(),
            integers=(),
        )
    try:
        digests, integers = _execute(check, inputs, trust, expected_request, now)
    except (HallmarkError, ValidationError, UnicodeError) as failure:
        error = sanitize_exception(failure, stage="parse")
        return Outcome(
            accepted=False,
            claim_a="not-accepted",
            claim_b="not-accepted",
            code=error.code,
            input_digests=(),
            integers=(),
        )
    return Outcome(
        accepted=True,
        claim_a="not-accepted",
        claim_b="not-accepted",
        code=None,
        input_digests=digests,
        integers=integers,
    )
