# Public API

Implementation status is stated for each interface below. Use
[STATE](../../research/STATE.md) for delivery evidence and
[the contributor workflow](../../CONTRIBUTING.md) for checks. The section/work
mapping is structural traceability, not a promise that proposed functions exist.

## Existing v0.1 surface

The existing research CLI is:

```text
hallmark schema {record,experiment,model,run}
hallmark validate-data DATASET
hallmark run CONFIG --output FRESH_DIRECTORY
hallmark audit-run DIRECTORY --dataset DATASET --expected-manifest SHA256
hallmark predict MODEL TEXT_FILE
```

Success writes one JSON object on stdout and exits 0. CLI failures write one
`hallmark/error/1` JSON object to stderr: `code`, `stage`, `retryable` and
`diagnostic_id` (null except for an unexpected failure). Invalid input/arguments
exit 2; storage, resource and unexpected execution failures exit 3. Messages,
paths, argument values, exception notes/causes and subprocess output are omitted.
Unexpected failures get a fresh random diagnostic ID. See the
[error contract](04-error-model.md#implemented-diagnostic-boundary).
Research `predict` returns `{score: int, pass: bool}`. `audit-run` returns
`research-replay-matched`, which is not a proof acceptance.

Current importable contracts are `Record`, `Experiment`, `LinearArtifact`, `RunManifest` in `hallmark.contracts`. Internal helpers are not a stable SDK. Do not promise stability for `dict[str, Any]` research reports beyond their schema ID.

## v1 supported interfaces

The primitive codec in `hallmark.wire` is implemented:

```python
def encode(value: WireValue, *, limits: WireLimits = DEFAULT_LIMITS) -> bytes: ...
def decode(raw: bytes, *, limits: WireLimits = DEFAULT_LIMITS) -> WireValue: ...
def H(kind: Domain, value: WireValue, *, limits: WireLimits = DEFAULT_LIMITS) -> bytes: ...
```

`WireValue`, `Domain`, `DOMAINS`, `WireLimits`, `DEFAULT_LIMITS` and `WireError` are
exported by that module. Only exact built-in host types are accepted; tuples,
subclasses, floats and non-text map keys fail. `H` returns 32 raw bytes and accepts
only the 22 RFC-0001 domains. `WireError` carries `code` (`INPUT_INVALID` or
`LIMIT_EXCEEDED`), `stage="parse"` and `retryable=False`, with no offending value.

`WireLimits(max_bytes=67108864, nesting=16, max_items=1048576)` can only lower these
hard limits. Nesting counts containers (including empty ones); item count includes
containers, leaves and map keys. Both encode and decode enforce these bounds.
Limits are resource policy, not part of an artifact's identity.

`hallmark.manifests` implements `ModelManifest`, `FileRef`, `GenerationConfig`,
`ArtifactDigest` and `FileSHA256`. The frozen model offers:

```python
ModelManifest.decode(raw: bytes, *, limits: WireLimits = DEFAULT_LIMITS) -> ModelManifest
model.encode(*, limits: WireLimits = DEFAULT_LIMITS) -> bytes
model.identity() -> ArtifactDigest
verify_model_files(model: ModelManifest, root: Path, *, max_bytes: int) -> None
```

Model decoding validates both canonical bytes and the exact schema without opening
files. Its identity binds every field. The separate file check needs an explicit
root and byte budget; it does not load a model or confer trust. See
[model manifest decision](../decisions/0005-model-manifests.md) for path rules,
platform and concurrency limits, and the JSON projection.

`hallmark.classifier_manifest` implements `InputProfile`, `ClassifierManifest`,
`TensorSpec`, `NodeSpec` and `ArithmeticProfile`. The three top-level artifacts
have the same `encode`, `decode` and `identity` methods as model manifests, in
their own fixed domains. `PARAMETERS` exposes the typed operator-parameter schema.

```python
arithmetic.validate_parameters(files: dict[str, bytes]) -> None
classifier.validate_profiles(
    inputs: InputProfile, arithmetic: ArithmeticProfile, *, parameters: dict[str, bytes]
) -> None
```

Parsing validates fields, ranges, arity and graph topology. The explicit parameter
step verifies raw file hashes and then parameter-dependent shapes, scales,
conservative range bounds and masks; it performs no I/O or classifier execution.
`validate_profiles` also checks the classifier's profile identities and scalar
score/encoding obligations. See [exact semantics and limits](../decisions/0006-classifier-contracts.md).
These checks do not qualify a graph/backend or authenticate supplied references.

`hallmark.policy` implements `Policy`, `ChainExpectation`, `RequestExpectation`
and `Request`. They expose the same checked CBOR `encode`/`decode` methods.
Only `Policy` has an `identity` method, in the `policy` domain.

```python
policy.validate_classifiers(
    classifiers: tuple[ClassifierManifest, ClassifierManifest, ClassifierManifest]
) -> None
request.validate_against(
    expected: RequestExpectation, *, model: ModelManifest, policy: Policy,
    classifiers: tuple[ClassifierManifest, ClassifierManifest, ClassifierManifest]
) -> None
```

These calls check resolved classifier order/identities, explicit caller
expectations, supplied model/policy identities and prompt byte limits.
They do not enroll artifacts, consume a nonce or adopt a policy. See
[policy/request semantics and snapshots](../decisions/0007-policy-request-contracts.md).

`hallmark.openings` implements `TranscriptOpening` with checked CBOR encode/decode:

```python
opening.commitment() -> ArtifactDigest
opening.verify_commitment(expected: ArtifactDigest) -> None
opening.context(expected: RequestExpectation) -> ArtifactDigest
derive_input_salt(salt: bytes, classifier: ArtifactDigest) -> bytes
input_commitment(
    opening: TranscriptOpening, classifier: ClassifierManifest, profile: InputProfile,
    *, token_units: tuple[int, ...] | None = None, vocabulary_size: int | None = None,
) -> ArtifactDigest
```

Byte inputs are reconstructed from the complete prompt. Encoder inputs require
independently computed content tokens and an explicit vocabulary bound. These
functions perform deterministic hash reconstruction only; they do not qualify a
tokenizer, enroll inputs or verify proofs. See [exact preimages, B1 obligations,
privacy and v0 migration](../decisions/0008-transcript-input-openings.md).

`hallmark.receipts` implements `ProofInputs`, `ReceiptBody`, `SignedReceipt`,
`EpochRecord` and `ProofArtifact` with checked CBOR encode/decode:

```python
inputs.to_fields() -> tuple[int, ...]
ProofInputs.from_fields(fields: tuple[int, ...]) -> ProofInputs
inputs.validate_profile(classifier: ClassifierManifest, profile: InputProfile) -> None
body.identity() -> ArtifactDigest
body.signing_bytes() -> bytes
body.validate_expectation(expected: RequestExpectation, *, now: int) -> None
body.validate_policy(policy: Policy, classifiers: ClassifierSet, profiles: ProfileSet) -> None
epoch.identity() -> ArtifactDigest
epoch.challenge() -> ArtifactDigest
epoch.key_id() -> ArtifactDigest
epoch.validate_time(now: int) -> None
signed.validate_epoch(epoch: EpochRecord, *, now: int) -> None
artifact.validate_inputs(
    expected: ProofInputs, classifier: ClassifierManifest, profile: InputProfile,
    *, max_proof_bytes: int,
) -> None
```

`ClassifierSet` and `ProfileSet` are exact three-element tuples in rule/MLP/encoder
order. These methods check structural and declared-reference consistency only.
No signature, attestation or proof is verified. See [record semantics, exact
100-field layout, time checks and payload caps](../decisions/0009-receipt-evidence-contracts.md).

The primitive value decoder alone does not validate an artifact schema or authenticity.
`hallmark.enrollment` implements `Limits`, `TrustPolicy`, `RegistryEntry`,
`RegistryBody`, `RegistrySignature`, `SignedRegistry`, `RegistryState` and the
process-local `Enrollment` result:

```python
snapshot.verify_signatures(trust: TrustPolicy) -> None
entry.validate_time(*, issued_at: int, now: int) -> None
enroll(
    snapshot: SignedRegistry, trust: TrustPolicy, state: RegistryState, now: int,
    *, history: tuple[SignedRegistry, ...] = (),
) -> Enrollment
enrollment.require_entry(kind: EntryKind, digest: ArtifactDigest, *, issued_at: int) -> None
```

Trust and registry bodies expose complete typed identities; the wire records
use checked `encode`/`decode`. `Enrollment` has no decoder or public constructor.
`hallmark.registry_store` implements `provision_state(path, external_state)`,
`read_state(path)` and `enroll_and_store(path, snapshot, trust, expected_state,
now, *, history=())`. These functions require an owner-controlled local POSIX
path, never infer a checkpoint from a bundle, and return only after a verified
update commits. See [semantics and limits](../decisions/0010-external-enrollment.md)
and [provisioning](../OPERATIONS.md#external-registry-checkpoint-provisioning).

`hallmark.registry` implements explicit authoring and key transitions:

```python
sign_snapshot(body: RegistryBody, trust: TrustPolicy,
              keys: tuple[Ed25519PrivateKey, ...]) -> SignedRegistry
next_snapshot(previous: RegistryBody, entries: tuple[RegistryEntry, ...],
              *, issued_at: int, expires_at: int) -> RegistryBody
validate_successor(previous: RegistryBody, candidate: RegistryBody) -> None
transition.verify(old: TrustPolicy, new: TrustPolicy, state: RegistryState) -> None
sign_transition(body: RegistryTransition, old: TrustPolicy, new: TrustPolicy,
                state: RegistryState, *, old_keys: tuple[Ed25519PrivateKey, ...],
                new_keys: tuple[Ed25519PrivateKey, ...]) -> SignedTransition
enroll_transition(snapshot: SignedRegistry, transition: SignedTransition,
                  old: TrustPolicy, new: TrustPolicy, state: RegistryState,
                  now: int, *, previous: SignedRegistry) -> Enrollment
```

`RegistryTransition` and `SignedTransition` have checked `encode`/`decode` and JSON
schema snapshots. The body exposes `signing_bytes("old" | "new")`; each role has
a distinct signature domain. Signing never creates keys or adopts a trust policy.
`registry_store.rotate_and_store(path, snapshot, transition, old, new,
expected_state, now, *, previous)` commits the transition and checkpoint together.
The checkpoint store now remembers its external trust digest on first successful
enrollment; ordinary enrollment cannot silently replace that policy.

`hallmark.registry_history` provides `create_history(path, snapshot, trust,
external_state, now)`, `append_history(path, snapshot, trust, expected_state, now,
*, transition=None, old_trust=None)`, `read_snapshot(path, state)` and
`read_transition(path, state)`. It retains exact snapshots and authorizations
in a separate local database. See [rotation, retirement and store semantics](../decisions/0012-registry-authoring-rotation.md).

The implemented v1 command is:

```text
hallmark registry-check SNAPSHOT --trust TRUST --state STATE --now SECONDS [--history FILE ...]
```

For one rotation, replace `--history` with all three flags `--old-trust OLD`,
`--transition TRANSITION` and `--previous PREVIOUS`. Inputs are canonical CBOR;
STATE is an already provisioned local SQLite checkpoint. Success emits only
`{schema_id:"hallmark/registry-check/1", registry:hex32, sequence:U64,
trust:hex32, checked_at:U64}` after persistence. It makes no receipt/proof claim.
The [operating guide](../OPERATIONS.md#registry-authoring-and-key-rotation) includes
an offline public-fixture command and the operational enrollment gate.

`hallmark.bundles` implements the offline containers and reported results:

```python
from hallmark.bundles import (
    Bundle, EmbeddedFile, ResponseEnvelope, BundleStatus, Claim, VerificationResult,
    decode_bundle,
)

decode_bundle(raw: bytes, *, limits: Limits) -> Bundle
bundle.validate_limits(limits: Limits) -> None
reported_result.validate_requirements(trust: TrustPolicy) -> None
```

All six record types expose checked `encode`/`decode`. Use `decode_bundle` at the
untrusted binary boundary to apply external byte/depth/proof limits. It performs
no file/network I/O, signature verification, enrollment, attestation or proof
verification. `validate_requirements` only compares reported mode/claim
acceptance to external requirements. A decoded `VerificationResult` is a report
whose authenticity must be established separately, not a verifier invocation.
See [field rules, opening exchange and limits](../decisions/0011-offline-bundle-contracts.md).

`hallmark.backend` implements the RFC-0005 backend declaration and caller-pinned
file checks:

```python
from hallmark.backend import BackendQualification, validate_backend_files

validate_backend_files(
    backend: BackendQualification, *,
    expected_backend: ArtifactDigest,
    required_programs: tuple[ArtifactDigest, ...],
    require_zero_knowledge: bool,
    files: dict[str, bytes],
    max_bytes: int,
) -> None
```

The record exposes checked `encode`, `decode` and `identity`. The function
compares an externally enrolled record pin, declared program coverage, the
claimed hiding flag and every dependency/security/layout file within the caller
byte budget. It performs no I/O or proof verification and returns no acceptance
result. Other evidence identities remain opaque. A matching record or true
`zero_knowledge` declaration does not qualify a backend; see
[decision 0023](../decisions/0023-backend-declaration-contract.md).

Generic schema dispatch and the following interfaces remain targets. Their types are
defined in [data model](03-data-model.md#v1-types); see [codec decision](../decisions/0003-v1-codec.md).

```python
def decode(raw: bytes, schema: type[T], limits: Limits) -> T: ...
def prepare_input(opening: TranscriptOpening, classifier: ClassifierManifest) -> PreparedInput: ...
def prove(
    manifest: ClassifierManifest, inputs: ProofInputs, witness: Witness, budget: JobBudget
) -> ProofArtifact: ...
def verify_proof(
    manifest: ClassifierManifest, inputs: ProofInputs, proof: ProofArtifact, budget: JobBudget
) -> ProofResult: ...
def verify(
    bundle: Bundle,
    trust: TrustPolicy,
    expected: RequestExpectation,
    now: int,
    opening: TranscriptOpening | None = None,
) -> VerificationResult: ...
```

Protocol functions accept admitted immutable values, never implicit trust from the bundle. `T` is a concrete versioned schema, not arbitrary object construction. `WireValue` is the restricted value algebra in RFC-0001. `ProofResult` is `{valid: bool, code: ErrorCode | None}`; an adapter timeout or exception maps to an error, never `valid=True`. Verification is deterministic given bundle, trust, expected request, clock and exact verifier artifacts.

```text
hallmark verify BUNDLE --trust TRUST --expected REQUEST [--opening OPENING]
hallmark inspect BUNDLE
```

`verify` writes one versioned `VerificationResult` JSON document, exits 0 only if the caller's required claims and policy pass, 1 on a validly parsed but rejected claim, 2 on invalid input/configuration, and 3 on unavailable/failed execution. `inspect` outputs bounded identifiers and evidence presence with `verified:false`; it must not infer authenticity. These commands remain targets; `registry-check` is implemented above.

The gateway is a local/controlled-host library boundary, not a general hosted API:

```python
def handle(request: Request, enrollment: Enrollment, budget: JobBudget) -> ResponseEnvelope: ...
def collect(receipt_id: Digest, store: ReceiptStore) -> BundleStatus: ...
```

There is no default network fetch, credential discovery or automatic paid fallback. Proof collection is explicit; a foreground worker is bounded and stops when its admitted queue is exhausted.

The implemented corpus API is `hallmark.conformance.load_corpus(path)` and
`run_corpus(corpus, root, expected_corpus=..., primary=..., software_only=False)`.
It returns a `ConformanceReport` for named component checks, with no accepted
hardware/proof claim. Default scope fails on unavailable required evidence;
the explicit software scope retains unavailable counts. See
[runner semantics and bounds](../decisions/0013-frozen-conformance-corpus.md).

`hallmark.integer_mlp` implements `MlpWeights`, `MlpProgram`, `MlpResult` and:

```python
def execute_mlp(
    opening: TranscriptOpening,
    classifier: ClassifierManifest,
    program: MlpProgram,
    inputs: InputProfile,
    arithmetic: ArithmeticProfile,
    *,
    weights: bytes,
    parameters: dict[str, bytes],
) -> MlpResult: ...
```

This checks exact export identities and executes all prompt bytes. Its native
verdict and private intermediate traces are not proof/hardware acceptance.
No file/network retrieval, training or calibration occurs. See the
[numerical profile, limits and export contract](../decisions/0014-integer-mlp-runtime.md).

`hallmark.events` implements bounded local `EventLog(path, max_bytes=...)` with
`attempt()` and `stage(stage)` context managers, plus
`inspect_events(path, max_bytes=...) -> EventSummary`. Its strict `Event` and
`AttemptRecord` schemas are metadata only; a completion summary is a local storage
result, not verified execution. See [usage and limits](../decisions/0015-private-event-storage.md).

`hallmark.admission` implements proposed `StudyPolicy`, `AdmissionProtocol`,
`AdmissionReview`, `SourceApproval`, `Candidate` and `BudgetAdmission` records.
The three top-level artifacts expose checked CBOR encoding/decoding and identity.

```python
protocol.review_terms() -> ArtifactDigest
validate_reviewed_admission(
    protocol: AdmissionProtocol, policy: StudyPolicy, review: AdmissionReview,
    *, expected_review: ArtifactDigest, files: dict[str, bytes],
) -> None
```

The caller authenticates both reviewers and supplies an independently enrolled
review pin. The check binds exact terms, role names and bounded document bytes.
It performs no I/O, asset validation, signature verification or budget enforcement.
Source revision/code/configuration fields hash manifest documents; model file
inventories are declarations. The [draft proposal](../../research/proposals/inj-direct-v1/README.md)
is intentionally inadmissible while choices remain null. See
[decision 0018](../decisions/0018-admission-proposal.md) for the distinction from
runtime policy, the acyclic review hash and the missing operational authority.

`hallmark.rule` implements `RuleProgram` and private `RuleResult` records:

```python
execute_rule(
    opening: TranscriptOpening,
    classifier: ClassifierManifest,
    program: RuleProgram,
    inputs: InputProfile,
    arithmetic: ArithmeticProfile,
    *,
    provenance: bytes,
    parameters: dict[str, bytes],
) -> RuleResult: ...
```

It checks exact identities and supplied files, then scans the complete prompt with
bounded suffix state. Score one blocks at threshold one. No source retrieval,
enrollment, task quality or proof verification occurs. The literal matcher is
part of the program, not the scalar score-projection DAG; see
[semantics, provenance and limits](../decisions/0020-complete-byte-rule.md).

`hallmark.data_admission` supplies the local W14 import surface:

```python
build_dataset(
    plan, policy, *, expected_plan, documents, raw_files
) -> tuple[DatasetManifest, dict[str, bytes]]
verify_dataset(
    manifest, files, plan, policy, *,
    expected_dataset, expected_plan, documents, raw_files
) -> None
write_dataset(directory, manifest, files) -> None
near_duplicate_candidates(rows) -> tuple[tuple[str, ...], ...]
```

The caller authenticates and externally pins the plan and resulting dataset.
Evidence/raw dictionaries contain exact logical paths and bytes. Imports preserve
lineage and text, group before splitting and reject changed source bytes or
rehashed output mutations. Writing requires a fresh trusted local directory.
See [contracts, recipe, limits and review obligations](../decisions/0021-lineage-data-admission.md);
the marker fixture establishes no real-data quality or human review.

## Compatibility

Keep existing commands and schema IDs until an explicit migration release. New v1 protocol commands must reject research run bundles. Export supported types from `hallmark.api` only when implemented and typed; `py.typed` remains required. Add CLI examples, generated schema snapshots and installed-wheel tests with each new command. See [versioning](09-release-and-versioning.md#compatibility).

**INV-EXTERNAL-EXPECTATION:** CLI flags that select trust and expected request are mandatory for verification; bundle fields never fill them silently.
