# Public API

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

Generic schema dispatch and the following artifact interfaces remain targets. Their types are
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
hallmark registry-check SNAPSHOT --trust TRUST --state STATE
hallmark qualify PROTOCOL --output FRESH_DIRECTORY
```

`verify` writes one versioned `VerificationResult` JSON document, exits 0 only if the caller's required claims and policy pass, 1 on a validly parsed but rejected claim, 2 on invalid input/configuration, and 3 on unavailable/failed execution. `inspect` outputs bounded identifiers and evidence presence with `verified:false`; it must not infer authenticity. `registry-check` advances local enrollment state only after full verification and atomic persistence. `qualify` requires a preapproved resource protocol.

The gateway is a local/controlled-host library boundary, not a general hosted API:

```python
def handle(request: Request, enrollment: Enrollment, budget: JobBudget) -> ResponseEnvelope: ...
def collect(receipt_id: Digest, store: ReceiptStore) -> BundleStatus: ...
```

There is no default network fetch, credential discovery or automatic paid fallback. Proof collection is explicit; a foreground worker is bounded and stops when its admitted queue is exhausted.

## Compatibility

Keep existing commands and schema IDs until an explicit migration release. New v1 protocol commands must reject research run bundles. Export supported types from `hallmark.api` only when implemented and typed; `py.typed` remains required. Add CLI examples, generated schema snapshots and installed-wheel tests with each new command. See [versioning](09-release-and-versioning.md#compatibility).

**INV-EXTERNAL-EXPECTATION:** CLI flags that select trust and expected request are mandatory for verification; bundle fields never fill them silently.
