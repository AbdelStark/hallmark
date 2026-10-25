# 0073: Compose LLM and classifier proofs over one opened request

2026-10-25. Issue #104. New integration experiment; earlier experiments and their
results retain their original identities.

## Statement and baseline

The existing classifier demo uses an authored response. The separate LLM demo
proves a fixed quantized TinyLlama response. Neither entrypoint checks both claims
over one opened request. Compose those existing research relations without changing
their arithmetic, model weights, thresholds, data or proof constraints.

The caller freezes `response-case.json` by SHA-256. Its prompt and response must
exactly equal the classifier transcript opening. The request's model identity is
`H("model", {schema_id:"hallmark/sash-research-model/1", checkpoint:case.model,
quantization:case.spec, calibration_sha256:case.calibration_sha256,
source:case.source})`. This research descriptor is not a v1 `ModelManifest`.
There is no explicit system message (`system_ref` is zero). The separately enrolled
chat template maps that prompt to the LLM token sequence. Fresh nonce, interaction
and transcript salt values distinguish the classifier requests.

The classifier relation retains its complete prompt-only input scope. Its context
binds the exact response and model identity, but it does not classify the response.
The caller checks equality with the proved LLM case and verifies both proof sets.
This is caller composition, not a recursive proof, authentic context capture,
fresh generation attestation or a protected release mechanism. Reusing a valid
deterministic LLM proof establishes the same computation, not when it occurred.

## Workflow

`make e2e-composed` prepares the existing LLM and classifier demonstrations, freshly
verifies the LLM proof bundle on the Mac, then generates three new classifier setups
and proofs for the exact LLM request. The existing classifier demonstration remains
a control and retains its own result. Supplying caller-owned `LLM_RUN` and
`CLASSIFIER_RUN` paths reuses preparation, never a saved proof-success verdict.
The retained classifier binary and both selected quantizations have fixed hashes.
The separate pairing verifier environment is caller-owned, as in the existing demo.

Fresh LLM verification remains mandatory, including its two honest checks and
36 mutations. Each new classifier proof is checked with the separate pairing
implementation. Its existing negative roster checks all 100 public fields,
keys, encodings, groups and proof components. Additional caller tests change the
prompt, response, system reference, model, nonce, interaction, policy and salt,
and corrupt each classifier artifact. Missing or failed stages preserve failure
evidence and cannot publish a successful combined result.

## Bounded acceptance

Mutable paths are the composition helpers, trained classifier controller,
Make task, focused tests and documentation. Existing model exports, data, splits,
thresholds, circuits, LLM case and proof verifiers are frozen. First run the small
binding fixture; then run two fresh local campaigns. Each must freshly verify all
23 LLM proofs, create and separately verify three classifier proofs, reject all
11 composition mutations and match all 399 classifier arithmetic outcomes.
Record the actual classifier verdicts; an unexpected verdict is not permission
to retrain or change a threshold.

The integration campaigns use retained public-model proof bytes and frozen
synthetic classifier exports. No prior acceptance report substitutes for a fresh
check. No new cloud job, checkpoint download, private input or external inference
is needed. Each campaign has a two-hour limit and four worker threads; classifier
workers retain the existing 8 GiB sampled RSS/output limits. The study permits at
most 16 GiB additional retained outputs in total, preserving prior failures.

The initial storage observation found 280,712,892 KiB of retained runs, already
above the older 256 GiB agent-selected ceiling. Under the owner's standing storage
and bounded-research approval, this study records a new 300 GiB checkout ceiling
and a 32 GiB free-space floor. These are agent-selected limits, not quotations
from the owner. Historical budgets and raw artifacts are unchanged.

No operational backend, setup custody, policy quality, independent security review,
zero-knowledge hiding or hardware evidence is admitted by this experiment.
