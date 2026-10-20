# Public API

## Existing v0.1 surface

“Public” here means supported caller interface inside the private repository, not a public release. The existing CLI is:

```text
hallmark schema {record,experiment,model,run}
hallmark validate-data DATASET
hallmark run CONFIG --output FRESH_DIRECTORY
hallmark audit-run DIRECTORY --dataset DATASET --expected-manifest SHA256
hallmark predict MODEL TEXT_FILE
```

Success writes one JSON object on stdout and exits 0. Current handled input/runtime/filesystem failures write text to stderr and exit 2; argument errors also exit 2. Current diagnostics are not a complete redaction contract. Research `predict` returns `{score: int, pass: bool}`. `audit-run` returns `research-replay-matched`, which is not a proof acceptance.

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

This value decoder validates canonical bytes, not an artifact schema or authenticity.
Schema dispatch and the following artifact interfaces remain targets. Their types are
defined in [data model](03-data-model.md#v1-types); see [codec decision](../decisions/0003-v1-codec.md).

```python
def decode(raw: bytes, schema: type[T], limits: Limits) -> T: ...
def enroll(
    snapshot: SignedRegistry, trust: TrustPolicy, state: RegistryState, now: int
) -> Enrollment: ...
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
