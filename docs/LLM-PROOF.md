# A proved TinyLlama response

```text
Prompt:   Name the capital of France in one short sentence.
Response: The capital of France is Paris.
```

Hallmark proves that a **pretrained, quantized TinyLlama-1.1B-Chat-v1.0**
computes this response, greedily and token by token, through end-of-sequence.
The proof is a bundle of **23 SASH Circle STARK segments**, one per transformer
layer plus one for the final norm and output head, joined by **22 residual
links**. A verifier checks all of them against model, shape and calibration
roots the caller enrolled before proving. No general-purpose zkVM or hardware
attestation is involved.

![What the TinyLlama proof covers: a 32-position input block, 23 segment proofs stacked as layers, the output head's argmax at positions 24 to 31, and seven links feeding each output back as the next input.](assets/figures/llm-statement.svg)

| Read | For |
|---|---|
| [The statement](#the-statement) | Exactly what the proof establishes, token by token |
| [What the caller checks](#what-the-caller-checks) | The bindings outside the circuit |
| [Run it](#run-it) | `make e2e-llm`: fresh witnesses and proofs, three paid CPU jobs |
| [Verify on your Mac](#verify-retained-proofs-on-your-mac) | `make verify-llm`: offline, no weights |
| [Measured results](#measured-results) | Fresh CPU workflow and the earlier composition |
| [GPU benchmark](GPU-BENCHMARK.md) | 547.75 s SIMD / 53.94 s CUDA proving session on one H200 |
| [Composed demo](COMPOSED-DEMO.md) | The same request, plus three classifier proofs |

Hallmark downloads pinned upstream SASH source and drives its real Rust prover
and verifier through CLI adapters. The Linux CPU binary is built without source
changes; local witness preparation and the optional native Mac verifier carry
separate, explicit patches ([how SASH is integrated](ARCHITECTURE.md#how-sash-is-integrated)).
A fresh SASH process is not an independently implemented verifier.
[Raw results and hashes](../research/evidence/llm-response-composition-2026-10-23.json)
keep the failed first composition as well as the corrected one.

## Run it

![The TinyLlama workflow: prepare on a Mac, then three Hugging Face CPU jobs build the prover, prove 23 segments and verify them; an optional native verifier rechecks on the Mac.](assets/figures/llm-pipeline.svg)

You need an **Apple Silicon Mac**, Git, Make, **uv 0.9.18**, at least **16 GiB free
storage**, and a Hugging Face account with Jobs access and enough prepaid credits.
Allow 32 GB RAM for local preparation; the recorded preparation process peaked at
13.27 GB. The command downloads the public 2.2 GB Apache-2.0 checkpoint and creates
an isolated, locked witness environment. You do not need a local GPU or CUDA.

Put `HF_TOKEN` in the environment or in an ignored `.env` file at the checkout
root, then run:

```sh
make e2e-llm
```

This starts paid jobs. The command refuses current provider rates whose fixed
timeouts exceed **$2.10**, including a storage reserve. It allows 30 minutes each
for build and verification on CPU Upgrade, and 60 minutes for proving on CPU
Performance. Jobs run sequentially, with one attempt each. It does not add credits
or configure recharge. Check your available credits before starting.

The command checks all checkpoint hashes, reproduces calibration and the exact
answer, then derives model roots and compares them with the caller's frozen
enrollment before proving. It rebuilds the original Rust prover, generates **23
new proofs**, verifies them in **two fresh processes** and rejects **14 mutations**.
Credentials remain in the local controller; workers receive only the reviewed
public case and its derived artifacts.

Each invocation prints a fresh `runs/llm-e2e-*` directory. On success, its
`result.json` reports:

```json
{
  "passed": true,
  "response": "The capital of France is Paris.",
  "proofs": 23,
  "residual_links": 22,
  "fresh_verifications": 2,
  "mutations_rejected": 14,
  "qualified_backend": false,
  "hardware_claim": "not-accepted",
  "hiding_claim": false
}
```

The run directory keeps source/input hashes, command logs, all proofs and claims,
verification results and resource receipts. Temporary buckets are deleted only
after their outputs are downloaded and hashed. Failures return nonzero and keep
their evidence. If job creation or retention is uncertain, the recorded bucket
is kept: inspect the job URL or bucket record before starting another run. The
controller refuses to start while another HF job is active.

This command supports the pinned prompt and model. Another prompt, response
length, model or arithmetic profile needs a new case and caller enrollment;
editing expected tokens alone does not establish a new proved response.

## Verify retained proofs on your Mac

After a successful `make e2e-llm` run, use its printed directory:

```sh
# One-time prerequisite, using an existing Rust installation:
rustup toolchain install nightly-2025-07-14 --profile minimal
make verify-llm LLM_RUN=runs/llm-e2e-...
```

This builds a native Apple Silicon verifier and checks all 23 proofs twice, then
runs 38 rejection checks: the 14 original mutations, two enrollment mutations, two
statement mutations and 20 direct native checks for field aliases, malformed shapes
and configuration drift. The statement mutations hand the native verifier a changed
prompt and a changed model root while skipping the Python caller guard, so the
verifier's own `--prompt` and `--expect-model-roots` comparisons must reject them.
On the published reference proofs, both were rejected by the native verifier itself,
with all 23 proofs still accepted ([evidence](../research/evidence/llm-native-mutations-2026-10-29.json)).
It needs 8 GiB free storage, the pinned Rust toolchain and the same Python setup.
Building can download locked Rust dependencies. Verification is sandboxed and
offline; it uses no model weights, witness, HF token or paid compute. Results and
failures go to a fresh `runs/llm-verify-*` directory.

The native verifier is specialized to this public case. It compiles the caller's
23 shape roots and exact parameter/calibration digests into the executable;
unknown shapes reject. It checks the same STARK/GKR proofs and layer/token links,
but does **not** reconstruct the preprocessed shape trees. Its source is explicitly
marked modified. The [design and trust boundary](decisions/0070-native-enrolled-llm-verifier.md)
and [measurements](../research/evidence/native-llm-verification-2026-10-23.json)
are separate from the Linux verifier, which still derives those roots at runtime.
This is research enrollment, not authenticated operational enrollment or an
independently reviewed verifier.

Two fresh native workflows completed in **214.45 and 203.98 seconds**, including
rebuilding the verifier and running the expanded suite. Their four honest checks
took **4.00, 3.57, 3.50 and 3.33 seconds**. Each run rejected all 36 mutations. Peak
sampled process-group RSS was **2.47 GB while building** and **1.19 GB for the
verification suite**. Both runs passed the sandbox fork, network-denial and
outside-file-denial controls. No cloud job was started.
These fixed-case observations use different preprocessing and hardware from the
Linux measurements below; they are not a matched speedup benchmark.

The expanded boundary probe found a native output-token alias and four malformed
shapes that crashed the process. The caller already rejected the alias. The native
verifier now checks vocabulary ranges and proof dimensions before using them;
the regression suite requires structured rejection rather than a crash. See
[decision 0071](decisions/0071-native-proof-input-boundaries.md) and
[its evidence](../research/evidence/native-proof-boundaries-2026-10-23.json) for
the exact counterexample, baseline failures and corrected runs.

### Verify a signed parameter enrollment

For parameters authorized by a separate signer, obtain the signer's Ed25519
public key through your own authenticated channel. Supply its 64 lowercase hex
characters separately from the enrollment and submitted proofs:

```sh
LLM_ENROLLMENT=/path/to/enrollment.cbor \
LLM_TRUST_KEY="$SIGNER_PUBLIC_KEY_HEX" \
make verify-llm LLM_RUN=runs/llm-e2e-...
```

The equivalent script flags are `--enrollment FILE --trusted-key HEX`. The signed
record authorizes the exact case bytes, verifier source inventory and validity
interval. The controller checks it before compilation, before starting the proof
worker and after verification. A wrong key, altered record, mismatched case/code
or expired interval fails; it cannot fall back to unsigned verification.

Set `SIGNER_PUBLIC_KEY_HEX` from that authenticated channel. Successful results
report `parameter_authority.kind: "ed25519"`, SHA-256 fingerprints of the CBOR
enrollment and raw 32-byte public key, and the final check time. Without these arguments,
the existing command reports `parameter_authority.kind: "checkout-case"` and
uses the repository case. The public key is never taken from the signed record.
The result schema is `hallmark.native-llm-result/1`; the three retained authority
checks use `hallmark.llm-parameter-authority/1`.

The parameter owner can authorize a reviewed checkout using the Python API.
This example assumes a caller-owned `Ed25519PrivateKey` object named `key`; key
custody and provisioning stay outside the proof workflow:

```python
import hashlib
import sys
import time
from pathlib import Path

sys.path.insert(0, "scripts")  # Run from the reviewed source checkout.
from verify_llm import PROBE, source_inventory, verifier_identity
from hallmark.llm_enrollment import LIMITS, LlmEnrollment, sign_llm_enrollment

now = int(time.time())
body = LlmEnrollment(
    schema_id="hallmark/llm-enrollment/1",
    case_sha256=hashlib.sha256((PROBE / "response-case.json").read_bytes()).digest(),
    verifier=verifier_identity(source_inventory()),
    not_before=now,
    expires_at=now + 86400,  # Choose and review the intended validity interval.
)
signed = sign_llm_enrollment(body, key)
with Path("enrollment.cbor").open("xb") as output:
    output.write(signed.encode(limits=LIMITS))
```

Review the actual source inventory and independently derived parameters before
signing. Do not authorize an inventory supplied only by the prover. Any bound
source or case change requires a new enrollment. The API generates no keys and
the verifier never receives a private key.

This authorization uses the caller's trusted clock. It has no revocation service
or persistent rollback protection and does not replace the separate v1 registry.
A valid signature authenticates the signer's decision; model quality and
independent security qualification remain separate. [Decision 0072](decisions/0072-signed-llm-parameter-enrollment.md)
defines the format and scope.

## The statement

For the enrolled quantized model and exact input token sequence, the answer tokens
are the greedy continuation computed by the pinned SASH relation. The proof
covers the model's embedding, 22 transformer layers, final normalization and
output projection/argmax. The caller pins the model, arithmetic parameters,
calibration, shapes and exact prompt/answer IDs.

The pinned chat template turns the prompt into **25 tokens**. A causal block of
32 positions contains those tokens plus the first seven answer tokens. Output
positions 24–31 produce the eight answer tokens, including EOS. Checking that the
first seven outputs equal the appended inputs closes the generation loop; the
caller separately checks the final EOS output. This is why the grid reports
seven generated input positions while proving eight output tokens.

```text
25 prompt IDs + first 7 answer IDs
  → embedding → layers 0…21 → final norm → output head
  → 8 expected answer IDs at positions 24…31, ending in EOS
```

This is the disclosed `y-attnout-w12` integer/quantized relation. It is not a proof
that every floating-point Transformers execution returns the same text. The
original fixed-length generation continued for 16 steps; this experiment proves
the complete first answer through EOS and discloses that selection. It does not
claim stochastic sampling or a held-out language-quality evaluation.

## What the caller checks

| Binding | Check |
|---|---|
| Text and tokens | Apply the pinned tokenizer/chat template locally; compare exact prompt and answer IDs |
| Model and arithmetic | Supply previously enrolled model/preprocessed roots, calibration and shape digests |
| Coverage | Require exactly 22 transformer segments and one final-norm head, with 32 positions each |
| Generation | Check all prompt IDs, seven generated input links and all eight answer IDs |
| Layer connections | Verify all 22 residual commitment links |
| Proofs | Run the real SASH verifier on every segment; reject any failure |

The [caller guard](../research/probes/sash/check_response.py) checks the statement,
including a digest of the complete parameter object. It rejects the delayed-value
profile and requires the head's final normalization. **Passing this Python guard
is not proof verification**: SASH's `boundary-grid --verify` must also accept the
entire bundle. The caller's expected roots must come from its own enrollment;
roots supplied only by the prover are insufficient.

The tokenizer, checkpoint-to-quantized-model preparation and enrollment are host
software responsibilities. The verifier implementation is the same pinned SASH
implementation used by the prover; a fresh process is not an independently
developed verifier or security audit. No trace blinding or witness-hiding claim
is made.

## Measured results

The [performance guide](PERFORMANCE.md) puts these numbers next to the H200
measurements and explains each timer boundary.

The [fresh one-command reproduction](../research/evidence/llm-e2e-reproduction-2026-10-23.json)
completed in **31 minutes 15 seconds**, including downloads, local preparation,
a new prover build, new proofs, transfers and verification. Its compute bound was
**$0.31**, not an invoice; the controller separately reserves $0.01 for storage.
Every one of the 69 proof, statement and claim files matches the earlier accepted
bundle byte for byte. The rebuilt binary has its own recorded hash; byte-identical
binary builds are not claimed.

| Fresh workflow stage | Recorded result |
|---|---:|
| Native preparation, excluding downloads and packing | 32.22 seconds |
| Build job, including six upstream tests | 560.40 seconds |
| Proving job, including root derivation and serialization | 533.64 seconds |
| Summed proving-only time across 23 segments | 328.46 seconds |
| Fresh proof-only verification, two processes | 80.11 / 78.45 seconds |
| Changed claims rejected | 14 / 14 |
| Peak prover / verifier process RSS | 116.20 / 14.35 GB |

All temporary buckets were deleted after local retention and hashing. Jobs ran
sequentially: the build and verifier on 8-vCPU / 32-GB CPU Upgrade workers, proving
on a 32-vCPU / 256-GB CPU Performance worker. CPU time, process RSS and end-to-end
wall time measure different costs. CI runs offline controller/statement fixtures;
it does not run the paid model workflow.

The earlier composition, which reused 22 transformer proofs while correcting the
head, remains recorded separately:

| Measure | Recorded result |
|---|---:|
| Accepted proof segments | 23 / 23 |
| Residual links | 22 / 22 |
| Enrolled shape roots | 23 / 23 |
| Answer tokens, including EOS | 8 |
| Serialized proofs | 737,858,641 bytes |
| Proofs plus statements and claims | 761,015,496 bytes |
| Fresh proof-only verification, two processes | 83.99 / 79.16 seconds |
| Changed claims rejected | 14 / 14 |
| Peak verifier process RSS | 14.35 GB |

Verification used an HF CPU Upgrade worker with 8 vCPUs, 32 GB RAM and four Rayon
threads. The 22 transformer proofs took 307.00 seconds of summed prove-stage time
on a different, larger CPU worker; the corrected head took 21.90 seconds on the
smaller worker. These are separate measurements, not one end-to-end wall-time
benchmark. The original proving run reached 113.44 GB peak RSS. No GPU was used
for these proofs; the build still required CUDA libraries for linking.

The caller guard rejected 11 mutations: changed prompt, answer, model root,
calibration, missing layer, wrong coordinate, final output, token alias, Boolean
token, open-scale profile and weaker security parameters. The cryptographic
verifier rejected altered proof commitments, a residual boundary and an output
claim. The original proof files were rehashed afterward and remained unchanged.

For the separately frozen SIMD/CUDA experiment on one H200, see the
[GPU measurement pipeline](GPU-BENCHMARK.md). It reuses this response's reviewed
witnesses and keeps the same inference relation and verifier checks.

## Failures that changed the implementation

1. An exact integer witness accumulator was rounded through float32. A
   [one-line Python fix](../research/probes/sash/exact-gemm.patch) preserves it;
   regression tests compare the helper with an int64 oracle.
2. The delayed-value profile left an activation-scale equality unchecked. Its
   proof cannot qualify for complete inference, even when its broad binding
   summary says all edges are bound. The experiment uses the existing non-delayed
   profile; the Rust prover and verifier remain unmodified.
3. Combining `--head` and `--residual-stream` selected the wrong proof family for
   the output head. All individual proofs passed, but the last layer connection
   failed. Extracting only the final-norm head repaired that connection without
   changing the other 22 proofs. [Decision 0068](decisions/0068-prove-the-output-head-final-norm.md).
4. The first one-command run found that Git had silently skipped the witness patch
   inside an enclosing checkout. The exact-GEMM regression stopped it before any
   cloud job. Patch application now stops Git's parent-directory search; a focused
   regression covers that layout. [Decision 0069](decisions/0069-reproduce-the-llm-response-workflow.md).

The result establishes one bounded computation under the enrolled relation. It
does not establish model quality, safety-policy quality, authentic capture of a
real interaction, hardware provenance, hiding or independently reviewed
cryptographic security. See the [source review](../research/real-llm-proof-plan.md)
for the pinned model/source revisions and remaining qualification work.
