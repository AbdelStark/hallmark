# 0075: Preserve LLM parameter authorization through composition

2026-10-25. Issue #108, progressing #19. Baseline:
`baeee45f9564f67cfcb03ed35217684e2255c3a9`.

## Hypothesis and scope

The composed workflow can preserve the existing signed LLM parameter enrollment,
reject invalid authorization before paid preparation, and check validity at the
final join. No new registry or signing format is needed. The standalone verifier's
authorization checks become shared script helpers; its exact case, source identity,
three verification-time checks and signature semantics remain unchanged.

Mutable paths are the two controllers, composition tests, documentation and
numeric evidence. The model, quantization, prompt/answer, arithmetic, proof
relations, classifier data/splits/thresholds and separate verifiers stay frozen.
The new source inventory needs its own authorization; old signatures are not
reused to authorize changed controller bytes.

## Boundary

`run_composed.py` accepts the same `--enrollment` / `--trusted-key` arguments and
`LLM_ENROLLMENT` / `LLM_TRUST_KEY` environment variables as the native verifier.
Either input requires the other. The caller independently supplies the public
key; no key is obtained from the signed record or proof bundle.

Before any fresh LLM or classifier preparation, validate the signature, exact
case/source pins and validity interval. Snapshot the signed bytes into the new
run directory and pass that copy to native verification. Require its reported
authority to match the caller's authorization, excluding check time/stage only.
After classifier proving and source checks, validate the same authorization again.
Expiry at that final join leaves a failure, never a composed success. Results
report `parameter_authority`; unsigned research runs report `checkout-case`.

The signature authorizes the LLM case and verifier source inventory. It does not
authorize classifier policy, setup keys or operational release. This extension
provides no persistent revocation/rollback mechanism, key custody, independent
security/hiding qualification or hardware provenance. The v1 registry remains
separate and its entry meanings are unchanged.

## Acceptance and bounded experiment

First reproduce missing enrollment support, then require invalid/partial records,
wrong keys, changed parameters and expiry to reject before preparation. Fixture
tests must also reject changed native authority and expiry during classifier
proving, and preserve unsigned behavior and a frozen caller snapshot.

Run one actual signed `make e2e-composed` campaign using the already retained
LLM/classifier preparation from decision 0074. Rebuild and freshly verify all
23 LLM segments, requiring two honest checks and all 36 mutations. Create three
new classifier setups/proofs over the same opened request, require all eleven
binding rejections and 399 arithmetic outcomes, and retain the synthetic CNN's
block. Compare all model/circuit and LLM proof identities to the frozen baseline.

Standing local-research/storage authority permits this foreground experiment:
one campaign, 7,200 seconds, four worker threads, 8 GiB sampled descendant RSS
stop, 12 GiB new allocated storage and a 32 GiB free-space floor. Native workers
retain their tighter 4 GiB stop. New cloud jobs/spend are zero. Dependency caches
remain populated; locked builds may fetch software dependencies. A disposable
issuer key stays only in the local issuer process; only the public key, signed
record and public test evidence are retained. No contact, private input or key
provisioning occurs. Preserve failures in new run directories.

Local repository, required-training and installed core/training package gates
remain required, followed by exact-head and exact-merge hosted checks.

## Outcome

The actual signed Make command passes in 866.49 seconds. Fresh native verification
takes 211.64 seconds, accepting two honest checks and rejecting all 36 mutations.
Three new classifier setups/proofs and their checks take 653.43 seconds; all
eleven binding mutations and 399 separate-arithmetic outcomes pass. The final
authorization check succeeds after those stages. All five checks bind the same
record/public key, and all 69 original LLM files, both model identities and all
three circuits match the baseline. All new setup keys differ from the prior run.

Allocated growth is 3,345,911,808 bytes; sampled summed descendant RSS peaks at
2,490,826,752 bytes. The sample interval is one second. These are one diagnostic
observation with other host activity uncontrolled, not latency distributions.
New cloud jobs/spend are zero. Ten real CLI preflight cases reject; the first
harness incorrectly expected WireError rather than the correct SIGNATURE_INVALID
HallmarkError for a tampered signature. Its failed harness, inputs and logs remain
retained; no full campaign had started. Source behavior was not changed to pass it.

[Numeric evidence](../../research/evidence/signed-composed-2026-10-25.json)
precedes this interpretation. The signer remains a disposable integration key.
No operational custody, revocation/rollback, classifier-policy adoption, independent
security/hiding review or hardware claim follows.
