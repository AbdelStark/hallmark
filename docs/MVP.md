# LLM integrity MVP

The owner-selected **fixed-case LLM integrity MVP is complete**. It proves a short
response from a real pretrained, disclosed quantized model and verifies the
proofs without requiring hardware attestation or witness hiding.
[Decision 0076](decisions/0076-integrity-mvp-scope.md) records that scope;
[the numeric acceptance audit](../research/evidence/integrity-mvp-completion-2026-10-25.json)
links the inspected sources, artifacts, results and future issues.

For command selection, end-to-end diagrams and the division between circuit
checks and caller checks, read [architecture and proof flows](ARCHITECTURE.md).
Circle STARK now defaults for both LLM inference and classifiers, through SASH
and direct STWO respectively. Gnark remains an explicit comparison backend.
[Decision 0085](decisions/0085-circle-default.md) records this later default change;
the original MVP acceptance below retains its historical measurements.

```text
Model:    TinyLlama-1.1B-Chat-v1.0, pinned y-attnout-w12 quantization
Prompt:   Name the capital of France in one short sentence.
Response: The capital of France is Paris.
```

The proof covers the embedding, 22 transformer layers, final normalization and
output projection/greedy argmax: **23 proof segments, 22 residual links and eight
answer tokens through EOS**. Caller checks bind the expected prompt/answer tokens,
model/shape/calibration roots and complete coverage. Tokenization and parameter
provisioning remain caller responsibilities. Read the [exact LLM statement and
trust boundary](LLM-PROOF.md#the-statement).

## Run it

Use an Apple Silicon Mac with the [documented prerequisites](LLM-PROOF.md#run-it),
uv 0.9.18, 16 GiB free storage, 32 GB RAM, and an HF account with Jobs access and
prepaid credits. Put `HF_TOKEN` in the environment or ignored `.env` file:

```sh
make e2e-llm
```

Preparation runs locally. Three sequential HF CPU jobs build, prove and verify
under a **$2.10 timeout-based ceiling**, without adding funds. The recorded fresh
LLM phase took 32 min 44 s; its compute bound was $0.31, not an invoice. These
are case observations with populated caches, not a latency distribution.

To verify retained proofs locally, without weights or an HF credential:

```sh
make verify-llm LLM_RUN=/path/to/llm-e2e-run
```

The native verifier rebuilds and requires two honest checks plus all 36 mutation
rejections. Recorded honest checks take 3.33–4.00 s after compilation. It compiles
caller-enrolled shape roots; the original Linux verifier derives them at runtime.
[Signed parameter authorization](LLM-PROOF.md#verify-a-signed-parameter-enrollment)
is optional and requires a public key obtained through the caller's own channel.

For the [full LLM/classifier composition](COMPOSED-DEMO.md), run
`make e2e-composed`. The complete fresh workflow is recorded at 66 min 50 s.
For the local synthetic classifier pipeline alone, run `make e2e`; it needs no
cloud account. Each invocation gets a new evidence directory and preserves
failures. Raw checkpoints, keys and run directories stay out of Git.

## Acceptance and evidence

| Requirement | Verified result | Evidence |
|---|---|---|
| Real pretrained LLM and disclosed quantization | Pinned Apache-2.0 TinyLlama checkpoint; all eight model files rehashed; `y-attnout-w12` | [Case](../research/probes/sash/response-case.json), [audit](../research/evidence/integrity-mvp-completion-2026-10-25.json) |
| Complete short response | Eight answer tokens through EOS, 23 real proof segments and 22 links | [LLM result and failure history](../research/evidence/llm-response-composition-2026-10-23.json) |
| Specialized integrity proof | SASH Circle STARK/GKR inference relation; no general-purpose zkVM | [Proof statement](LLM-PROOF.md#the-statement) |
| Caller-owned expectations and negative checks | Original verifier: two honest checks and 14 rejections; native: two and 36 | [Fresh run](../research/evidence/fresh-composed-2026-10-25.json), [native boundary tests](../research/evidence/native-proof-boundaries-2026-10-23.json) |
| Reproducible end-to-end workflow | Fresh witnesses/proofs, training/exports, nine classifier control proofs and three composed proofs | [Fresh Make run](COMPOSED-DEMO.md#historical-gnark-composition-fresh-preparation) |
| Multiple classifier architectures | Rule, trained MLP and trained CNN; 18 control substitutions reject; 405 control and 399 composed arithmetic outcomes match | [Classifier proof explanation](PROOFS.md), [composed workflow](COMPOSED-DEMO.md) |
| Explicit parameter authority | Same signed case/source/key authorization checked five times through the final join; invalid authorization fails before preparation | [Signed composition](COMPOSED-DEMO.md#signed-llm-parameters) |
| Public, reusable source | MIT project source, public repository, locked environments and passing source/install CI | [Licence](../LICENSE.md), [packaging](PACKAGING.md), [acceptance audit](../research/evidence/integrity-mvp-completion-2026-10-25.json) |

The audit confirms the current code matches the executed proving and verification
sources. It preserves historical source identities rather than relabeling old
runs. Local repository, required-training and installed-package gates remain
separate from cryptographic proof evidence. The 32 unavailable full-hybrid
conformance cases are future v1 obligations, not passing MVP checks.

## Limits and future work

This is one fixed prompt, model, quantization and greedy answer. Another case
needs its own preparation, enrollment and evidence. It is not an arbitrary-model
or interactive generation API, or a proof of floating-point Transformers output.
No witness-hiding, hardware provenance or independent security qualification is
claimed. Native compiled roots require trusted parameter provisioning.

The classifiers evaluate the prompt only. Their data is authored synthetic text;
the CNN blocks this ordinary prompt. `policy_release: false` can accompany valid
proofs. No safety, factuality, model-quality or protected-release claim follows.

The [original v1 roadmap](roadmap/IMPLEMENTATION.md) is preserved as future work:

| Future scope | Open original issues |
|---|---|
| Genuine hardware, measured loading and release | #23, #24, #25, #28, #36, #47 |
| Qualified operational classifier/model/backend interfaces | #13, #17, #19, #20, #21, #22, #29, #30, #44, #45, #46 |
| Private receipt lifecycle, full cost accounting and release packet | #26, #27, #33, #40, #48, #49, #51 |
| Independent full-system verification/reviewer reproduction | #35, #41, #50 |
| Full-v1 wire/registry review dashboards | #42, #43 |

These issues stay open with their original acceptance criteria and a `post-mvp`
label. Some research counterparts and child implementations already work;
this scope decision does not close unfinished operational requirements.
