# Data model

## Existing research contracts

The exact executable field definitions remain in [contracts.py](../../src/hallmark/contracts.py); `hallmark schema` emits their JSON schemas. Frozen strict models reject extra fields, nonfinite floats and boolean labels. Dataset rows include record/group/family/source/revision/licence/policy/split/language/prompt/response/label. Dataset size is bounded to 8 MiB; text fields to 32,768 characters. The fixture is 52 records and is not a policy dataset.

Experiment identity pins the raw dataset hash, policy, scope, seed, chunk size, target FPR, alpha and configured allowlists. Integer floor artifacts have 256 int8 weights, int32 bias/threshold, power-of-two scale and safe int32 accumulation. Run manifests require exactly five named artifact hashes. Research report/source schemas are partly implicit today; v1 hardening must make their outputs versioned and validated without relabeling old results.

## v1 types

The implemented primitive `hallmark.wire.WireValue` is `None | bool | int | bytes |
str | list[WireValue] | dict[str, WireValue]`. Integers are bounded to
`[-2^63, 2^64-1]`, strings are strict UTF-8 with no normalization, and containers use
the [codec resource limits](02-public-api.md#v1-supported-interfaces). The artifact
schemas below remain implementation targets except `ModelManifest`, `FileRef`,
`GenerationConfig`, `ClassifierManifest`, `InputProfile`, `Policy`, `Request`,
`RequestExpectation`, `ChainExpectation`, `TranscriptOpening`, `ProofInputs`,
`ReceiptBody`, `SignedReceipt`, `EpochRecord`, `ProofArtifact`, `RegistryBody`,
`RegistryEntry`, `RegistrySignature`, `SignedRegistry`, `TrustPolicy`, `Limits`
and `RegistryState`, implemented in
[manifests.py](../../src/hallmark/manifests.py) and
[classifier_manifest.py](../../src/hallmark/classifier_manifest.py), with
[policy/request contracts](../../src/hallmark/policy.py) and
[opening contracts](../../src/hallmark/openings.py) plus
[receipt/evidence containers](../../src/hallmark/receipts.py) and
[registry enrollment](../../src/hallmark/enrollment.py).
`Enrollment` is an in-process verified result, with no wire decoder or public constructor.
Primitive decoding does not validate fields, versions or cross-field invariants.
The [model JSON schema](../schemas/model-manifest-v1.json) is a hex-byte projection;
the [manifest decision](../decisions/0005-model-manifests.md) defines the executable
path checks, nested records and file-inspection boundary.
The [classifier contract decision](../decisions/0006-classifier-contracts.md)
defines input recipes, typed arithmetic graphs and operator parameter files,
including their separate declaration and parameter-validation boundaries.
The [policy/request decision](../decisions/0007-policy-request-contracts.md)
defines classifier resolution, caller expectations, byte limits and continuity.
The [opening decision](../decisions/0008-transcript-input-openings.md) defines exact
transcript/context/input preimages and the caller's independent tokenization obligation.
The [receipt contract decision](../decisions/0009-receipt-evidence-contracts.md)
defines structural/time checks, public-input packing and opaque evidence boundaries.
The [enrollment decision](../decisions/0010-external-enrollment.md) defines signed
history, trust limits, process-local admission and atomic checkpoint persistence.

Notation below is a normative schema algebra, not executable Python. `B32` is exactly 32 bytes; `Digest=B32`; `U64` is integer 0 through 2^64−1 excluding booleans; `I32` is signed int32; `Id` is the existing restricted ASCII Identifier; `Text` is strict UTF-8. `Vec[T,n]` has exactly n elements, `List[T,a..b]` is bounded, and `Optional[T]` is T or null. Every map has the listed fields only. Each top-level artifact carries `schema_id: Id` with its specific `hallmark/<kind>/1` value. All digest identities use RFC-0001.

| Type | Required fields beyond schema_id |
|---|---|
| `FileRef` | `path:Text`, `size:U64`, `sha256:Digest`; normalized relative path, no `..`, links, duplicate paths or absolute paths |
| `ModelManifest` | `files:List[FileRef,1..4096]` sorted by path; `architecture:Digest`, `tokenizer:Digest`, `chat_template:Digest`, `runtime:Digest`, `numerical_mode:Id`, `generation:GenerationConfig` |
| `GenerationConfig` | `max_new_tokens:U64` in 1..4096, `sampling:Literal["greedy"]`, `seed:U64` fixed to 0; v1 has no stochastic serving contract |
| `ClassifierManifest` | `kind:Literal["rule","mlp","encoder"]`, `program:Digest`, `weights:Optional[Digest]`, `tokenizer:Optional[Digest]`, `input_profile:Digest`, `arithmetic:Digest`, `threshold:I32`, `scope:Literal["prompt"]`, `labels:Vec[Id,2]`, `backend:Digest`, `verifier_key:Digest`, `setup:Digest` |
| `InputProfile` | `encoding:Literal["utf8-bytes","token-ids"]`, `tokenizer_files:List[FileRef,0..64]`, `prefix_tokens:List[U64,0..8]`, `suffix_tokens:List[U64,0..8]`, `chunk_size:U64` in 1..512, `overlap:U64` fixed to 0, `max_units:U64` in 1..32768, `padding_id:U64`, `padding_side:Literal["right"]` |
| `Policy` | `rubric:Digest`, `classifiers:Vec[Digest,3]` in rule/MLP/encoder order, `combination:Literal["all-pass"]`, `language:Literal["en"]`, `scope:Literal["prompt"]`, `max_prompt_bytes:U64` ≤32768, `max_response_bytes:U64` ≤32768 |
| `RequestExpectation` | `audience:Id`, `nonce:B32`, `interaction_id:B32`, `model:Digest`, `policy:Digest`, `continuity:Optional[ChainExpectation]` |
| `Request` | `expected:RequestExpectation`, `prompt:Text`, `system_ref:Digest`; request is admitted once, nonce generated by requester CSPRNG |
| `TranscriptOpening` | `system_ref:Digest`, `prompt:Text`, `response:Text`, `salt:B32` |
| `ProofInputs` | `context:Digest`, `classifier:Digest`, `input_digest:Digest`, `unit_count:U64`, `chunk_count:U64`, `threshold:I32`, `verdict:bool` |
| `ReceiptBody` | `expected:RequestExpectation`, `issued_at:U64`, `expires_at:U64`, `epoch:Digest`, `sequence:U64`, `previous:Optional[Digest]`, `transcript:Digest`, `inputs:Vec[ProofInputs,3]`, `release:Literal["released","blocked"]` |
| `SignedReceipt` | `body:ReceiptBody`, `key_id:Digest`, `signature:bytes[64]` |
| `ProofArtifact` | `backend:Digest`, `verifier_key:Digest`, `public_inputs:ProofInputs`, `proof:bytes` bounded by enrolled limits |
| `EpochRecord` | `epoch_id:B32`, `key:bytes[32]`, `model:Digest`, `measurement:Digest`, `issued_at:U64`, `expires_at:U64`, `cpu_evidence:bytes`, `accelerator_evidence:bytes`, `collateral:List[FileRef,1..256]` |
| `Bundle` | `receipt:SignedReceipt`, `epoch:EpochRecord`, `registry:SignedRegistry`, `history:List[SignedRegistry,0..1024]`, `proofs:Vec[ProofArtifact,3]`, `files:List[EmbeddedFile,1..8192]`; `EmbeddedFile={ref:FileRef,content:bytes}` |
| `ResponseEnvelope` | `receipt:SignedReceipt`, `response:Optional[Text]`, `opening:Optional[TranscriptOpening]`, `proof_status:Literal["pending","ready","blocked","failed","expired"]`; blocked never includes response or opening |

`ChainExpectation={sequence:U64, previous:Optional[Digest]}` pins caller-held receipt continuity when requested; sequence 0 requires null previous, later sequences require a digest. A null continuity expectation makes no chain-continuity claim.

`PreparedInput={units:List[U64,0..32768], chunks:List[List[U64,0..512],1..32768], masks:List[List[bool,0..512],1..32768], digest:Digest}` is internal and checked against `InputProfile`; chunk and mask dimensions match, and nonpadding units exactly reconstruct the complete input. `Witness={prepared:PreparedInput, input_salt:B32, program_files:List[FileRef,1..4096]}` is private and never logged.

`RegistryEntry={kind:Literal["model","classifier","policy","backend","epoch-measurement"], digest:Digest, valid_from:U64, valid_until:U64, retired_at:Optional[U64], review:Digest}`. `RegistryBody={schema_id:"hallmark/registry/1", sequence:U64, previous:Optional[Digest], issued_at:U64, expires_at:U64, entries:List[RegistryEntry,1..4096]}`. `SignedRegistry={body:RegistryBody, signatures:List[{key_id:Digest, signature:bytes[64]},1..16]}`.

`TrustPolicy={schema_id:"hallmark/trust/1", registry_keys:List[bytes[32],1..16], signature_threshold:U64, min_registry_sequence:U64, accepted_models:List[Digest,1..64], accepted_policies:List[Digest,1..64], accepted_backends:List[Digest,1..16], hardware_roots:List[Digest,0..64], measurements:List[Digest,0..64], required_claims:Literal["A+B","B"], binding:Literal["B1","B2"], max_age_seconds:U64, limits:Limits}`. B2 requires claim A and hardware roots; B1 with required B may use empty roots.

`Limits={bundle_bytes:U64≤67108864, proof_bytes:U64≤16777216, nesting:U64≤16, verify_seconds:U64≤60, worker_memory_bytes:U64}`; fields must be positive and no caller can exceed implementation hard limits. `JobBudget={protocol:Digest, host:Id, max_seconds:U64, max_memory_bytes:U64, threads:U64, max_jobs:U64}` requires a separately approved protocol for non-bootstrap work.

`RegistryState={sequence:U64, digest:Digest}` is trusted local rollback state, persisted atomically. `Enrollment={registry:Digest, state:RegistryState, trust:Digest, admitted:List[RegistryEntry,1..4096]}` is created only by verified enrollment.

`VerificationResult={schema_id:"hallmark/verification-result/1", accepted:bool, mode:Literal["B1","B2"], claim_a:Claim, claim_b:Claim, policy_pass:Optional[bool], codes:List[Id,0..64], evidence:List[Digest,0..8192]}`. `Claim={status:Literal["accepted","rejected","not-accepted"], strength:Literal["hardware-attested","cryptographic","none"], assumptions:List[Id,0..64], residuals:List[Id,1..64]}`. `BundleStatus={receipt_id:Digest, state:Literal["pending","ready","blocked","failed","expired"], bundle:Optional[FileRef], error:Optional[Id]}`.

## Invariants

**INV-SCHEMA:** reject extra keys, duplicates, unknown versions, wrong primitive types, noncanonical encodings, trailing bytes, invalid Unicode, bound violations and inconsistent dimensions before cryptographic work.

**INV-IDENTITY:** changing any manifest, input profile, graph, threshold, policy or backend/setup identity creates a new digest. Registry entries are not mutable names for interchangeable artifacts.

**INV-NO-CYCLE:** classifier manifests name the program/key/setup, never themselves; public inputs name the completed manifest. Context excludes proofs and receipt signatures. See [RFC-0001](../rfcs/RFC-0001-wire.md#proposed-design) for the acyclic hash order.

**INV-TIME:** `issued_at < expires_at`, all timestamps are Unix seconds, and verification uses a caller clock. There is no silent skew allowance.

## Evolution

New or changed semantics require a new schema ID, explicit decoder dispatch, migration fixtures and a decision. No “best effort” decoding or coercion. Optional fields are explicitly null; omission is invalid. Artifact paths are identifiers inside a bundle, not permission to access the filesystem. The research JSON format remains distinct from the v1 binary wire format.
