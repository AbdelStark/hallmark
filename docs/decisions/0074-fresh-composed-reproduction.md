# 0074: Reproduce the complete fresh composed workflow

2026-10-25. Issue #106. The retained-preparation composition in decision 0073
passed twice. **Outcome:** the complete fresh default command passes in 4,010.05
seconds after the descriptor and assembly-path fixes. The numeric record
preserves three failed full runs, one deliberately interrupted run and one full success.
The original hypotheses and rejected candidates below remain part of the record.

## Frozen hypothesis

Run the actual `make e2e-composed` command with neither `LLM_RUN` nor
`CLASSIFIER_RUN`. It must prepare the pinned public TinyLlama checkpoint, regenerate
calibration/witnesses and all 23 LLM proofs, freshly verify them, retrain/export the
frozen synthetic classifiers and complete both classifier proof campaigns.
The response, model exports, circuits and substantive proof inventory must match
the existing cases. The synthetic CNN's block remains expected; no retuning follows.

The baseline is `68010b345849486359a19ac36ab54f0365d23994`. Runtime sources,
Make recipes, model/case, datasets/splits, seeds, thresholds, evaluator and proof
constraints stay unchanged. Mutable paths are documentation, research authority,
STATE, LEDGER and numeric evidence. Two prospectively planned fresh campaigns
test repetition; neither is an automatic retry of a failed job. A failure is
retained and diagnosed before any amended protocol or candidate is run.

## Resources and authority

Standing owner approval permits bounded foreground research using the Mac and
existing HF credits. Before each run, verify available prepaid credit, no active
Jobs and current provider rates. Keep account details and credentials local.
Each campaign permits the existing three sequential CPU jobs: build and verify
on CPU Upgrade for at most 1,800 seconds each, proving on CPU Performance for at
most 3,600 seconds. Its maximum compute/storage ceiling is $2.10; both campaigns
together are capped at $4.20, with no recharge, retry, scheduler or private inputs.
Credentials remain in the local controller. No host system packages are installed.
The existing disposable worker provisioning is unchanged; its image is pinned,
and build OS-package inventories are retained. These workers are not a claim of
fully hermetic OS-package resolution.

The local supervisor caps each entire campaign at 7,200 seconds, samples its
descendant RSS with a 28 GiB stop, and permits at most 24 GiB additional allocated
study storage per campaign. Host physical memory is 48 GiB. Worker-specific
limits remain tighter where already specified. Preserve failures and earlier runs.
The study extends the agent-selected checkout ceiling to 336 GiB and reserves
48 GiB for two campaigns, with a 32 GiB free-space floor. These are agent-selected
limits under standing storage approval, not numeric quotations from the owner.

## Acceptance

Each run must pass the original LLM proving/verification and 14 mutations, the
38-case native suite, the nine-proof classifier control campaign with 18
cross-request rejections and 405 arithmetic outcomes, then three fresh composed
classifier proofs with eleven binding rejections and 399 arithmetic outcomes.
Every job must be terminal and every temporary bucket deleted after verified
output retention. Record source/environment/input hashes and raw costs before prose.

Compare exact model/circuit identities and the 69 LLM proof/statement/claim files
with the existing baseline and between campaigns. Classifier setup keys, request
IDs and proofs can differ. Report measured differences and all missing or failed
results; do not reinterpret a failure as successful reproduction.

The result remains a non-attested research demo. It does not supply independent
security review, operational setup/key custody, policy quality or private-witness
hiding qualification.

## Retained failure and startup-budget amendment

Campaign 01 passed fresh LLM preparation, all 23 proofs, both original honest
checks and all 14 mutations. Its 69 proof/statement/claim files and deterministic
archive match the earlier baseline exactly. All three jobs completed and their
buckets were deleted. The complete Make command nevertheless failed: the native
sandbox control exceeded its 20-second process-group allowance, before native
proof verification or classifier preparation. The failed directory remains retained.

Three local controls then passed in 0.90, 0.42 and 0.40 seconds: an instrumented
replay, an exact replay and execution of a byte-identical fresh binary copy. Their
fork, outside-file denial and networking denial checks all passed. The transient
OS-level stall's cause remains unresolved; these probes do not establish a
specific macOS cause.

The amended candidate changes only `scripts/verify_llm.py`: declare and allow
120 seconds for startup/control. Its fail-closed assertions, filesystem/network
restrictions, 4 GiB RSS stop and proof relation remain unchanged. An artificial
25-second startup delay must pass the real control; a fresh native build and all
38 cases on the first fresh proof bundle must pass before further paid work.
The original proof/evaluator sources, model, data and thresholds remain frozen.
The controller source identity changes; a signed enrollment must authorize the
new source inventory through its existing issuer.

Campaign 02 uses the actual default Make command and the amended candidate.
Acceptance now requires one complete fresh success, reported alongside the
initial failure. It does not claim two successful full campaigns. The original
six-job, $4.20, time and storage envelopes remain unchanged. The remaining three
jobs serve campaign 02; no third campaign or automatic job retry is scheduled.
Local diagnosis and the native preflight start no cloud jobs. Both original and amended protocols have distinct hashes.

## Rejected timeout candidate and descriptor-bound candidate

Campaign 02 also failed at the native control, after 120 seconds. Fresh LLM
proving and original verification passed again in 1,740.37 seconds, with a $0.31
compute bound and every temporary bucket deleted. Increasing the timeout is
rejected; the final candidate restores the original 20-second control allowance.

The minimized reproduction identifies the cause: importing `hf_xet` 1.7.0 changes
`RLIMIT_NOFILE` from `(4096, 2^63-1)` to `(2^63-1, 2^63-1)`. A sandboxed Python
worker then stalls before executing its nested child. A captured sample shows
`child_exec -> _Py_closerange -> close`; its parent waits on the exec-error pipe.
Imports without the checkpoint client and standalone native builds pass because
they retain the ordinary descriptor limit. This replaces the earlier unresolved
startup-delay hypothesis with a reproducible resource-inheritance failure.

The final candidate caps worker child soft/hard descriptor limits at 4,096,
preserving stricter inherited limits. The shared proof-worker limiter and native
bounded launcher apply the same helper before execution. Their plans record the
cap. The parent retains its original limits. No sandbox permission is widened.

A real Mac sandbox regression first fails in 5.18 seconds, then starts its nested
child in under one second. It also requires outside-file and network denial and
unchanged parent limits. Three unit cases cover ordinary, stricter and unlimited
limits. All 138 focused tests pass. A fresh native build and all 38 proof cases
must additionally pass after importing the real checkpoint client, before further
paid work. The candidate changes only the two worker-launch modules; model,
data, thresholds, proof relations and evaluators remain frozen.

The third full campaign is a new descriptor-bound candidate. It must run the
actual default Make command with neither retained argument and satisfy every
original proof/control/classifier criterion. The first two full campaigns remain
failures. Their conservative compute bounds total $0.62; reserve another $0.02
for their temporary storage. At most three further jobs and $2.10 are allowed,
within the original $4.20 total envelope. The total job ceiling becomes nine;
existing time, storage and memory limits remain unchanged. No automatic job retry,
recharge or ongoing scheduler is introduced. This is one prospective full success
criterion after diagnosis, not a claim of two successful full reproductions.

## Classifier build identity and canonical-build candidate

Campaign 03 passes fresh LLM proving, both verifier suites and the complete fresh
classifier control: nine proofs, 18 cross-request rejections and all 405 arithmetic
outcomes. It then fails at the composed controller's binary admission. The fresh
classifier binary hashes to `df190be27e588c893fc30ea15015aa6916729b0b1d9cd79fb783fd628d30c412`,
while the admitted historical build hashes to `376c9aea1c28e5656099b8248d449323268670d77a67196f501301ab8d80a377`.
Go sources, dependency versions, compiler version and recorded build settings match;
the embedded build IDs differ. The default path must not assume that an old
unnormalized build ID gives a portable binary pin.

The canonical candidate adds `-ldflags=-buildid=` to the existing trimmed,
VCS-independent Go build. Three builds with different source checkout, toolchain
and cache locations are byte-identical:
`681a23f34a3f11e6057b1bba36cc2376e70ed5d78d15ae748e3628aa68d7433f`.
A real fresh setup/prove/verify installation probe passes with that binary.
Admission keeps this explicit canonical pin and the original historical pin;
unknown builds still reject. The downstream worker receives the actual admitted
hash. Tests exercise both admitted identities and reject changed bytes. No
prover-selected checksum or saved result supplies authority.

All 140 focused tests pass. `make check` passes 2,395 tests with 50 skips, and
all 77 required training tests pass. The model, data, thresholds, Go circuit sources
and proof/evaluation semantics remain frozen. The fourth full campaign uses the
actual default Make command and is the prospective success test for this candidate.
The earlier three full commands remain failed records, including campaign 03's
successful component results.

Observed conservative compute bounds total $0.93; reserve $0.03 for their temporary
storage. At most three further jobs and $2.10 are permitted under the original
$4.20 study ceiling. The total job ceiling becomes twelve. The fourth campaign's
additional allocation stop tightens to 14 GiB, based on campaign 03's 11.92 GB
prefix and the earlier composed stage's 1.29 GB. The original 48 GiB study,
336 GiB checkout, 32 GiB free-space, 7,200-second and 28 GiB sampled-RSS bounds
remain unchanged. Live credit, rates, idle jobs and allocated storage are checked
before launch; no automatic job retry, recharge, private input or scheduler follows.

## Included assembly paths and complete build normalization

Campaign 04 passes fresh LLM proving and both verifier suites. Before spending
more local time on its classifier control, an early hash check finds another
unadmitted build: `230a5859afee5c9518c13e20b9b7844c6d0d39f68881ae08848c20afd63eb2ff`.
The foreground supervisor is deliberately interrupted. This is an interrupted
full campaign, not a completed composed result. Every cloud job was already
terminal and its bucket deleted.

The build-ID-only candidate was insufficient. Its first three rebuilds varied
source, toolchain and Go build-cache locations but shared one module cache.
A fresh module cache exposes four absolute included-assembly filenames in the
runtime PC table. Removing debug symbols alone cannot address that runtime table.

The final build uses Go's `-toolexec` interface to extend the assembler's existing
path map for included files outside their Go package. The helper forwards other
tools unchanged and incorporates its source hash into the assembler version query,
so cached objects cannot bypass a changed normalization rule. The mapping is not
placed in recorded build flags, where absolute paths would re-enter the binary.
Go code, dependencies, instructions and circuit definitions are unmodified inputs.

Two builds using genuinely separate module caches, source trees, toolchains and
Go build caches match. The actual fresh standalone builder, stopped immediately
after compilation, produces the same binary from another new module cache in
31.56 seconds. All three hash to
`ad40c57319d370d16e9f75b19f98291ae748d661b7c509375e7f7997a597e43a`,
with no absolute machine paths found. A fresh real setup/prove/verify smoke test
passes. Admission includes only this final pin and the original historical pin;
the rejected build-ID-only pin is not admitted.

The fifth full command is the prospective end-to-end test. Four completed LLM
stages have a combined $1.24 conservative compute bound; reserve $0.04 for their
short-lived storage. Three further jobs and at most $2.10 remain below the original
$4.20 total ceiling. The total job ceiling becomes fifteen. Preserving all failed
runs and local build diagnostics extends the agent-selected storage ceilings to
64 GiB for the study and 384 GiB for the checkout under standing storage approval.
The per-campaign additional stop remains 14 GiB; the 32 GiB free-space, 7,200-second,
28 GiB sampled-RSS and one-campaign-at-a-time limits remain unchanged. No recharge,
private upload, automatic job retry or scheduler is authorized by this amendment.

## Completed acceptance

Campaign 05 exits zero with no retained-run arguments. It passes all 23 fresh LLM
proofs, 22 residual links and eight answer tokens through EOS; the original
16-case suite and native 38-case suite; nine classifier control proofs, 18
cross-request rejections and 405 arithmetic outcomes; then three new classifier
proofs for the LLM request, eleven binding rejections and 399 arithmetic outcomes.
The expected `[1, 1, 0]` verdict and blocked synthetic policy reproduce.

All 69 LLM files match all earlier fresh campaigns and the accepted baseline.
Model/circuit identities match, new setup keys differ, and the final opening
matches the actual pairing-verifier jobs. All fifteen jobs are terminal and all
fifteen buckets independently return not-found after verified output retention.
The successful command takes 4,010.05 seconds, adds 13,222,207,488 allocated bytes
and peaks at 14,519,255,040 sampled local descendant RSS bytes. Its compute bound
is $0.31; the five-campaign study totals $1.55, not an invoice. No cryptographic,
policy-quality, hardware or operational qualification flag is promoted.
