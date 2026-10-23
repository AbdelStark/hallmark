# 0072: Authenticate fixed LLM parameters with an external signing key

2026-10-23. Follow-up to issue #19. The native proof workflow gains optional
Ed25519 authorization of the fixed case and verifier source inventory.

## Boundary and format

An enrollment contains the exact case SHA-256, verifier source identity and an
explicit validity interval. The case pins the model, quantization, tokens and
all model/shape roots. The source identity binds the controller, worker, caller,
native patch, package Python sources and locked dependency inventory.
The source identity is the existing v1 `H("program", value)` over
`{"schema_id":"hallmark/llm-verifier-source/1","files":inventory}`, where each
inventory entry maps a relative source path to its lowercase file SHA-256.

The body uses the existing strict canonical CBOR codec. Its signature message is
`u32be(len(tag)) || tag || body_cbor`, with ASCII tag
`hallmark/research/sign/llm-enrollment/1`. Ed25519 is fixed; no algorithm or key
discovery field is accepted. The signed wrapper carries no public key. The
verifier must obtain its 32-byte key through its own authenticated channel.

`LlmEnrollment` and `SignedLlmEnrollment` are separate research records. They do
not replace the v1 registry or change its proof-size limits, entry meanings or
qualification rules. Existing unsigned checkout-case verification remains
available and reports that authority explicitly. Supplying either enrollment
input requires the other; an invalid signature never falls back to that path.

The controller checks enrollment before compilation, immediately before the
proof worker, and after verification. Expiry fails closed. Source hashes must
remain unchanged through the run. Invalid attempts retain their failure records.
The existing STARK/GKR checks and all 38 proof/mutation cases remain required.

## Acceptance and experiment

Baseline: decision 0071's native verifier and retained 23-proof TinyLlama bundle.
Mutable paths are the enrollment module, native controller, focused tests and
documentation. Proofs, arithmetic, quantization and Rust constraints stay frozen.

The smallest fixture must verify an authentic signature and reject a wrong key,
changed body, wrong case/source pin, invalid validity boundary and malformed
record. Missing trust input, wrong-key and expired cases must reject before a
compiler starts. Two fresh bounded native workflows must then pass real proof
verification under a separately supplied public key, preserving every original
proof file. Limits remain four threads, 4 GiB sampled process-group RSS,
30-minute build and 10-minute proof suite, with zero cloud spend.

Integration signers are disposable research keys. Their private objects remain
in the issuer process; they are not operational roots or evidence of owner key
custody. Signing APIs accept caller-owned keys and do not generate, load, publish
or discover them. Operational root provisioning still belongs to the owner.

The relying party supplies a trustworthy clock. This record has no persistent
rollback protection, revocation service or key-rotation protocol; the v1 registry
has separate mechanisms for those requirements. A signature authenticates the
signer's decision and parameter bytes. It does not establish model quality,
independent security review, hiding or hardware provenance.

[Numeric evidence and raw artifact hashes](../../research/evidence/llm-signed-enrollment-2026-10-23.json)
retain the preliminary runs and fresh current-source controls. A signature's JSON
schema was corrected to describe its 128-character hex representation. Its CBOR
format has a public conformance vector; a Node check separately encodes the body,
matches the signature message and verifies the Ed25519 signature. This checks
interoperability and does not establish independent cryptographic review.
Versioned authority/result JSON reports receive a further source identity;
fresh authorization and proof runs validate that final controller.
