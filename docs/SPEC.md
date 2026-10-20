# Baseline technical specification, v0.1

Entry point: [canonical specification corpus](../SPEC.md). This file preserves the existing research contract; its future-interface sketches are superseded for proposed v1 by the new RFCs.

Status: normative for the software baseline only. Hardware, registry and proving sections specify proposed interfaces, not implemented integrations. AI-assisted technical design, reviewed against the executable baseline on 2026-10-20.

## 1. Claims and system boundary

Hallmark targets two separable statements about one prompt/response transcript:

- A: measured inference software using a committed model produced this response. The proposed evidence is hardware attestation, with hardware, measurement, firmware, key custody and input/output-path assumptions.
- B: an enrolled classifier, tokenizer and decision policy computed a verdict over the committed text. The proposed evidence is a ZK proof of execution under exact integer semantics.

Neither statement proves the classifier is a good safety policy, the policy covers all relevant harm, all lab activity was observed, or nothing else ran. Model provenance is not resource exhaustion. The current executable implements neither A nor a ZK proof of B: it checks a small software classifier and replays its reports.

Proposed flow: enrollment -> measured inference -> transcript commitment -> classifier execution/proof -> combined receipt -> relying-party verification. A relying party must reject a partial bundle whenever its application requires both claims. Individual validity is insufficient if transcript identities differ.

## 2. Enrollment and identities

Before an interaction, a relying party enrolls the expected model manifest, classifier manifests, policy version, accepted hardware measurements and verifier keys through an authenticated channel. A manifest included by the prover is not its own trust anchor. A production registry needs signatures, monotonic versions, revocation, key rotation and downgrade rules; none is implemented.

Model manifest: exact ordered weight-shard hashes, architecture/configuration, tokenizer files and revision, chat template, inference implementation/measurement, numerical mode, generation parameters and sampling semantics. Hardware evidence must bind this manifest to the actual execution path; measuring a loader alone does not show the loaded weights were used.

Classifier manifest: model weights/architecture, tokenizer or byte mapping, chunk coverage/overlap, label map, policy ID, decision threshold, quantization scales, signed range bounds, public/private input layout, proof-system version and verifier-key hash. A change to any field creates a new identity. Proof setup lineage and parameter provenance are mandatory before adoption.

Research identities use SHA-256 over deterministic CBOR. For `commitment(domain, value)`, `tag = ASCII("hallmark/research/1/" + domain)` and the digest input is `u32be(len(tag)) || tag || canonical_cbor(value)`. Types matter: integer 1 is not boolean true. JSON is transport only. Strict input schemas reject duplicate keys, extra fields, nonfinite values and boolean-as-integer labels.

These research encodings are not an interoperable production wire protocol. A circuit-friendly hash or different serialization needs a new domain/version, cross-language golden vectors and explicit migration, not silent substitution.

## 3. Transcript opening

The implemented commitment is:

```
SHA256("hallmark/v0/transcript\0" || salt32
       || u64be(len(system_ref)) || system_ref
       || u64be(len(prompt_utf8)) || prompt_utf8
       || u64be(len(response_utf8)) || response_utf8)
```

`system_ref` is 32 bytes, default all-zero for the fixture; it is a reference, not a verified system-prompt disclosure. Salt is exactly 32 bytes. Enrollment applications must generate it with a CSPRNG, never a text-derived value. Prompt and response are strict UTF-8, with no normalization, trimming or hidden role concatenation. Invalid Unicode is rejected. Length fields prevent field-boundary ambiguity. This function binds bytes under collision resistance; it alone provides no provenance, fresh interaction identity or guaranteed hiding of low-entropy messages.

The production envelope must additionally bind protocol version, audience, request nonce, interaction/session ID, model manifest, all classifier manifests, policy and expiry. They are not fields in the current transcript helper; do not use it as a standalone authenticated receipt. Streaming requires defined finalization and sequence numbers, not unrelated per-chunk hashes.

## 4. Binding modes

| Mode | Verifier knows | Byte-to-token binding | Honest scope |
|---|---|---|---|
| B1, first target | Opened transcript | Verifier independently tokenizes exact bytes and compares proof public inputs | Classifier execution can be checked without trusting the TEE for tokenization |
| B2, future | Commitment only | TEE attests the bytes/tokens link | Classifier arithmetic is proved, text/token binding inherits hardware trust |
| B3, research | Commitment only | Tokenization and commitment opening proved in circuit | Stronger private binding, additional circuit and performance burden |

Do not claim B1 independence in B2 mode. A digest of token IDs does not prove those IDs came from the transcript. The baseline uses raw bytes and contains no tokenizer adapter, proof circuit or combined receipt.

## 5. Executable integer classifier

`hallmark.integer-byte-linear/1` is a deliberately weak, auditable floor baseline, not the planned encoder. It has 256 signed int8 weights, signed int32 bias and threshold, a power-of-two scale in `[1, 2^24]`, a prompt-or-response scope and chunk size in `[1, 4096]` bytes.

Encode the complete selected field as UTF-8. Partition contiguously into nonoverlapping chunks of at most `chunk_bytes`; the empty string has one empty chunk. Count each byte value. For each chunk `j`:

```
s_j = bias + sum(weight[b] * count_j[b] for b in 0..255)
s = max_j s_j
pass = (s < threshold)
```

Equality blocks. No softmax, epsilon or floating comparison enters the decision. Signed mathematical accumulation is normative: artifact admission requires `bias +/- chunk_bytes * max(abs(weight))` to fit int32, so no reachable intermediate sum wraps. The declared scale documents quantization; the runtime does not divide or round again. Full byte coverage is mandatory; decoding at a chunk boundary is unnecessary. Character/word boundary dependence remains a baseline limitation. Overlap and multi-field fusion are new model versions, not runtime options.

Training fits a float64 binary logistic regression only on training records. Quantization chooses a power-of-two weight scale, rounds to nearest with Python's ties-to-even rule and refuses int8 clipping. Bias is rounded under the same scale. Floating coefficients and solver parameters are saved. Calibration runs the resulting integer model, not its floating parent. Training examples longer than one chunk are rejected: per-record labels do not justify treating every chunk as individually positive. A multiple-instance training objective needs its own decision and tests.

## 6. Proposed proof interface and receipt

The first real proof backend should expose `prove(classifier_manifest, private_weights?, text_or_tokens, opening, nonce)` and `verify(enrolled_manifest, public_inputs, proof)`. This is a specification, not an existing Python API.

Public inputs must bind the exact classifier identity, policy/threshold, transcript or token commitment, complete chunk coverage, aggregate decision and interaction identity. The witness contains private weights when hidden, tokens/text as required by binding mode, intermediate activations and openings. Constraints must enforce ranges, signed interpretation, rounding, padding masks, every chunk's inclusion and max aggregation. Hashes inside a field need explicit byte packing and bounds. A proof over a chosen subset is not a proof over the full response.

Proposed receipt contains: version and binding mode; audience/nonce/expiry; transcript commitment; model manifest and attestation evidence reference; each classifier manifest, public inputs and proof; aggregate decision; provenance of setup/key enrollment. No receipt parser or verification stub is shipped, to avoid an apparent success path with no security mechanism.

Composition stages: C0 verifies separate genuine evidence objects; C1 aggregates classifier proofs; C2 verifies attestation policy inside a zkVM if justified; C3 explores private classifiers in a TEE. Start with C0. Aggregation does not repair missing common-input binding or elevate hardware evidence to a cryptographic statement about inference.

## 7. Verifier obligations

Reject unknown versions, identities or modes; untrusted keys/manifests; expired/revoked attestation chains; audience/nonce mismatches; missing classifiers; incorrect policy; transcript opening mismatch; inconsistent common inputs; omitted chunks; malformed or failing proofs; out-of-range values; threshold equality; invalid aggregate decisions. Attestation verification includes vendor collateral, TCB status, freshness and approved measurement policy, not just signature syntax. Retain the exact evidence and verification conditions.

The baseline `audit-run` instead requires a caller-enrolled manifest SHA-256, validates five exact artifact hashes, reloads the dataset by its frozen hash, recomputes integer calibration and predictions, and compares reports type-sensitively. It uses the same reference implementation, so it is not an independently developed verifier or a proof of historical training. Independent arithmetic tests reduce one class of shared-code error only.

## 8. Threat model and release gates

Adversaries include malicious providers choosing inputs/weights, replaying receipts, swapping policies, exploiting serialization or field arithmetic, withholding chunks, downgrading keys and optimizing against a disclosed classifier. Bugs include train/test leakage, threshold tuning on test, Unicode transformation, masking mistakes, numerical drift and proof/host disagreement. Privacy risks include transcript guessing, witness leakage, telemetry, logs and checkpoint licensing.

Before any end-to-end security claim: implement real attestation and proof verification; test independently enrolled inputs; run mutation tests across each receipt field and a second verifier; measure full costs; obtain cryptographic/hardware review; make classifier quality and coverage limits visible. A passing fixture, a hash, a mock receipt or a short demo cannot satisfy these gates.
