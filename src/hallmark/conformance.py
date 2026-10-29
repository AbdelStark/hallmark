"""Frozen component vectors and explicit missing evidence, never a full verifier."""

import hashlib
import os
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, ValidationError, model_validator

from hallmark.classifier_manifest import U64
from hallmark.contracts import Identifier
from hallmark.enrollment import TrustPolicy
from hallmark.errors import ERROR_CODES, ErrorCode, HallmarkError
from hallmark.integrity import parse_json
from hallmark.manifests import (
    ArtifactDigest,
    Digest32,
    FileRef,
    _Artifact,
    _Record,
    _verify_file,
)
from hallmark.policy import RequestExpectation
from hallmark.wire import H, WireError, WireValue

type Check = Literal[
    "wire",
    "wire-small",
    "domains",
    "model",
    "model-files",
    "classifier",
    "input-profile",
    "policy",
    "request",
    "opening",
    "input-bytes",
    "proof-fields",
    "proof-profile",
    "receipt",
    "proof-declaration",
    "bundle",
    "enrollment",
    "entry-time",
    "rotation",
    "arithmetic",
    "linear",
    "diagnostic",
    "unavailable",
]
CHECK_ARITY: dict[str, int] = {
    "wire": 1,
    "wire-small": 1,
    "domains": 1,
    "model": 1,
    "model-files": 2,
    "classifier": 1,
    "input-profile": 1,
    "policy": 4,
    "request": 6,
    "opening": 2,
    "input-bytes": 3,
    "proof-fields": 1,
    "proof-profile": 3,
    "receipt": 1,
    "proof-declaration": 4,
    "bundle": 1,
    "enrollment": 3,
    "entry-time": 2,
    "rotation": 5,
    "arithmetic": 2,
    "linear": 2,
    "diagnostic": 1,
    "unavailable": 0,
}
CHEATS = (
    "altered-prompt",
    "altered-response",
    "swapped-model-file",
    "unregistered-model",
    "classifier-swap",
    "threshold-swap",
    "replay",
    "chain-break",
    "wrong-salt",
    "tokenizer-swap",
    "late-payload",
    "false-gateway-pass",
    "different-receipt-proof",
    "retired-policy",
    "debug-quote",
)
MANDATORY_REQUIREMENTS = frozenset(
    [f"prd.{name}" for name in CHEATS]
    + [f"error.{code}" for code in ERROR_CODES]
    + [
        "wire.canonical",
        "wire.types",
        "wire.utf8",
        "wire.bounds",
        "wire.integer-extrema",
        "identity.domains",
        "identity.immutable",
        "arithmetic.range",
        "arithmetic.threshold",
        "arithmetic.empty",
        "arithmetic.coverage",
        "arithmetic.signed",
        "arithmetic.rounding",
        "arithmetic.mask",
        "registry.rotation",
        "registry.rollback",
        "registry.retirement",
        "binding.B1",
        "binding.B2",
        "claims.separation",
    ]
)
MAX_CORPUS_BYTES = 8 * 1024 * 1024
MAX_INPUT_BYTES = 64 * 1024 * 1024


class Outcome(_Record):
    """accepted means the named component check, never combined evidence acceptance."""

    accepted: bool
    claim_a: Literal["accepted", "rejected", "not-accepted"]
    claim_b: Literal["accepted", "rejected", "not-accepted"]
    code: ErrorCode | None
    input_digests: Annotated[tuple[Digest32, ...], Field(strict=False, max_length=64)]
    integers: Annotated[
        tuple[Annotated[int, Field(ge=-(2**63), le=2**64 - 1)], ...],
        Field(strict=False, max_length=4096),
    ]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.accepted != (self.code is None):
            raise ValueError("accepted check cannot contain an error")
        if (
            (self.code == "PROOF_PENDING" and self.claim_b != "not-accepted")
            or (self.code == "PROOF_INVALID" and self.claim_b != "rejected")
            or (self.code == "ATTESTATION_INVALID" and self.claim_a != "rejected")
            or (self.code == "POLICY_BLOCKED" and self.claim_b != "accepted")
        ):
            raise ValueError("claim state disagrees with error")
        return self


class Case(_Record):
    schema_id: Literal["hallmark/conformance-case/1"]
    case_id: Identifier
    parent: Identifier | None
    mutation: Identifier | None
    evidence_class: Literal["software-vector", "real-proof", "real-hardware", "hybrid"]
    check: Check
    inputs: Annotated[tuple[FileRef, ...], Field(strict=False, max_length=16)]
    trust: Digest32
    expected_request: Digest32
    now: U64
    expected: Outcome
    requirement: Identifier
    unavailable: Annotated[tuple[Identifier, ...], Field(strict=False, max_length=16)]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if len(self.inputs) != CHECK_ARITY[self.check]:
            raise ValueError("wrong component input count")
        if (self.parent is None) != (self.mutation is None):
            raise ValueError("mutation requires its parent")
        if self.check == "unavailable":
            if not self.unavailable or self.evidence_class == "software-vector":
                raise ValueError("missing real evidence must be explicit")
        elif (
            self.evidence_class != "software-vector"
            or self.unavailable
            or self.expected.claim_a != "not-accepted"
            or self.expected.claim_b != "not-accepted"
        ):
            raise ValueError("component checks cannot claim genuine evidence")
        if tuple(sorted(set(self.unavailable))) != self.unavailable:
            raise ValueError("missing dependencies must be sorted and unique")
        return self


class Requirement(_Record):
    id: Identifier
    source: FileRef
    locator: Identifier


class Corpus(_Artifact):
    _domain = "corpus"
    schema_id: Literal["hallmark/conformance-corpus/1"]
    revision: Identifier
    evidence_notice: Literal["public-synthetic-fixtures-only"]
    trust_policies: Annotated[tuple[FileRef, ...], Field(strict=False, min_length=1, max_length=16)]
    expectations: Annotated[tuple[FileRef, ...], Field(strict=False, min_length=1, max_length=16)]
    requirements: Annotated[
        tuple[Requirement, ...], Field(strict=False, min_length=1, max_length=256)
    ]
    cases: Annotated[tuple[Case, ...], Field(strict=False, min_length=1, max_length=1024)]

    @model_validator(mode="after")
    def complete_map(self) -> Self:
        ids = tuple(case.case_id for case in self.cases)
        requirements = tuple(item.id for item in self.requirements)
        if ids != tuple(sorted(set(ids))) or requirements != tuple(sorted(set(requirements))):
            raise ValueError("case and requirement IDs must be sorted and unique")
        if not MANDATORY_REQUIREMENTS <= set(requirements):
            raise ValueError("missing required rejection obligations")
        if {case.requirement for case in self.cases} != set(requirements):
            raise ValueError("every requirement needs cases and every case needs a requirement")
        for case in self.cases:
            if case.requirement.startswith("error.") and case.expected.code != (
                case.requirement.removeprefix("error.")
            ):
                raise ValueError("error obligation requires its exact code")
        for cheat in CHEATS:
            if not any(
                case.requirement == f"prd.{cheat}"
                and not case.expected.accepted
                and case.parent is not None
                and case.evidence_class == "hybrid"
                for case in self.cases
            ):
                raise ValueError("each original cheat needs its full-evidence rejection case")
        by_id = {case.case_id: case for case in self.cases}
        for case in self.cases:
            seen = {case.case_id}
            child = case
            while child.parent is not None:
                parent = by_id.get(child.parent)
                if (
                    parent is None
                    or parent.case_id in seen
                    or parent.check != child.check
                    or parent.evidence_class != child.evidence_class
                ):
                    raise ValueError("invalid mutation ancestry")
                seen.add(parent.case_id)
                if child.check != "unavailable" and (
                    child.inputs,
                    child.trust,
                    child.expected_request,
                    child.now,
                ) == (parent.inputs, parent.trust, parent.expected_request, parent.now):
                    raise ValueError("mutation did not change an input")
                child = parent
        refs: dict[str, FileRef] = {}
        for ref in (
            *self.trust_policies,
            *self.expectations,
            *(item.source for item in self.requirements),
            *(ref for case in self.cases for ref in case.inputs),
        ):
            if ref.path in refs and refs[ref.path] != ref:
                raise ValueError("conflicting file identity")
            refs[ref.path] = ref
        if len(refs) > 4096 or sum(ref.size for ref in refs.values()) > MAX_INPUT_BYTES:
            raise ValueError("corpus input limit exceeded")
        return self


class CaseResult(_Record):
    case_id: Identifier
    status: Literal["matched", "mismatch", "unavailable"]
    observed: Outcome | None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if (self.status == "unavailable") != (self.observed is None):
            raise ValueError("unavailable evidence has no observed result")
        return self


class ConformanceReport(_Record):
    schema_id: Literal["hallmark/conformance-report/1"]
    corpus: Digest32
    primary: Digest32
    independent: None
    scope: Literal["software-components", "all-required-evidence"]
    cases: Annotated[tuple[CaseResult, ...], Field(strict=False, min_length=1, max_length=1024)]
    matched: U64
    mismatched: U64
    unavailable: Annotated[tuple[Identifier, ...], Field(strict=False, max_length=1024)]
    software_passed: bool
    all_required_executed: bool
    self_tested: bool = False

    @model_validator(mode="after")
    def counts(self) -> Self:
        ids = tuple(case.case_id for case in self.cases)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("results must be sorted and unique")
        matched = sum(case.status == "matched" for case in self.cases)
        mismatched = sum(case.status == "mismatch" for case in self.cases)
        missing = tuple(case.case_id for case in self.cases if case.status == "unavailable")
        if (
            self.matched != matched
            or self.mismatched != mismatched
            or self.unavailable != missing
            or self.software_passed != (matched > 0 and mismatched == 0)
            or self.all_required_executed != (not missing)
        ):
            raise ValueError("conformance counts disagree")
        return self

    def exit_code(self) -> int:
        report = self._validated()
        if not report.software_passed:
            return 1
        return 3 if report.scope == "all-required-evidence" and report.unavailable else 0


def _read_file(root: Path, ref: FileRef) -> bytes:
    """Read exactly the pinned regular file; reject symlinks at every path component."""
    ref = ref._validated()
    if ref.size > MAX_INPUT_BYTES:
        raise WireError("LIMIT_EXCEEDED")
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        return _verify_file(root_fd, ref, set(), retain=True)
    except HallmarkError:
        pass
    finally:
        os.close(root_fd)
    raise WireError("INPUT_INVALID")


def load_corpus(path: Path) -> Corpus:
    from hallmark.registry_cli import _read

    raw = _read(path, MAX_CORPUS_BYTES)
    parse_json(raw.decode("utf-8"))
    try:
        return Corpus.model_validate_json(raw)
    except ValidationError:
        pass
    raise WireError("INPUT_INVALID")


def implementation_identity(root: Path) -> ArtifactDigest:
    sources: list[WireValue] = [
        ["hallmark/" + path.name, hashlib.sha256(path.read_bytes()).digest()]
        for path in sorted(Path(__file__).parent.glob("*.py"))
    ]
    sources += [
        [name, hashlib.sha256((root / name).read_bytes()).digest()]
        for name in ("pyproject.toml", "uv.lock")
    ]
    return ArtifactDigest(H("protocol", sources))


def run_corpus(
    corpus: Corpus,
    root: Path,
    *,
    expected_corpus: ArtifactDigest,
    primary: ArtifactDigest,
    software_only: bool = False,
) -> ConformanceReport:
    """Execute pinned component cases. Expected outcomes never enter the implementation."""
    from hallmark.conformance_checks import execute

    corpus = corpus._validated()
    if corpus.identity() != expected_corpus or type(software_only) is not bool:
        raise WireError("INPUT_INVALID")
    cache: dict[str, bytes] = {}

    def read(ref: FileRef) -> bytes:
        if ref.path not in cache:
            try:
                cache[ref.path] = _read_file(root, ref)
            except OSError:
                pass
            else:
                return cache[ref.path]
            raise WireError("INPUT_INVALID")
        return cache[ref.path]

    for requirement in corpus.requirements:
        read(requirement.source)
    trusts = {
        item.identity(): item
        for item in (TrustPolicy.decode(read(ref)) for ref in corpus.trust_policies)
    }
    requests = {
        hashlib.sha256(read(ref)).digest(): RequestExpectation.decode(read(ref))
        for ref in corpus.expectations
    }
    results = []
    for case in corpus.cases:
        if case.trust not in trusts or case.expected_request not in requests:
            raise HallmarkError("TRUST_MISSING", "enroll")
        if case.check == "unavailable":
            results.append(CaseResult(case_id=case.case_id, status="unavailable", observed=None))
            continue
        inputs = tuple(read(ref) for ref in case.inputs)
        observed = execute(
            case.check, inputs, trusts[case.trust], requests[case.expected_request], case.now
        )
        results.append(
            CaseResult(
                case_id=case.case_id,
                status="matched" if observed == case.expected else "mismatch",
                observed=observed,
            )
        )
    matched = sum(result.status == "matched" for result in results)
    mismatched = sum(result.status == "mismatch" for result in results)
    missing = tuple(result.case_id for result in results if result.status == "unavailable")
    return ConformanceReport(
        schema_id="hallmark/conformance-report/1",
        corpus=corpus.identity(),
        primary=primary,
        independent=None,
        scope="software-components" if software_only else "all-required-evidence",
        cases=tuple(results),
        matched=matched,
        mismatched=mismatched,
        unavailable=missing,
        software_passed=matched > 0 and mismatched == 0,
        all_required_executed=not missing,
    )
