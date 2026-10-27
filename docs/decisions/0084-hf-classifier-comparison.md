# 0084: Isolated HF CPU fallback for the classifier comparison

Date: 2026-10-27. Status: prepared; no job started at this decision's creation.

The Mac passes the complete classifier proof and adversarial gates, but its
available data-volume storage falls below decision 0083's 8 GiB stop boundary.
The measurement smoke stops at admission, before any compiler/prover starts.
Verified APFS deduplication preserves artifact bytes; the busy download cache is
cleared after an idle demo-server restart. Storage still lacks campaign headroom.
Do not reduce the frozen boundary or delete models/proofs/failures to force a run.

Use the standing approved HF Jobs fallback for a separate experiment,
`circle-classifiers-matched-hf-v1`. The live hardware API reports `cpu-upgrade`:
8 vCPU, 32 GB RAM, 50 GB ephemeral storage, 500 micro-USD per minute. No existing
HF job is active at admission. Recheck that quote before launch and stop if the
bounded startup-inclusive estimate exceeds **$0.30**. The owner has reported
sufficient prepaid balance; no new credit or top-up is requested.

The [HF profile](../../configs/circle-classifiers/hf-plan.json) preserves all
three models, thresholds, exact arithmetic/SHA-256 relations, request openings,
three-fresh/five-warm repetitions, order, raw schema and statistical definitions.
Both backends run in the same Linux x86-64 job with four proving threads, a 28 GiB
process-tree stop and the original 16 GiB raw-output allowance. Installed tools
and downloaded sources are reused; every fresh workflow starts an empty compiler
object cache. There is no matched Mac/Linux speedup claim.

Reuse the existing bounded Linux worker and seccomp filter. A small input adapter
installs caller-pinned files, records copy time and execs the pinned proof-only
tool in the same process. Proof workers receive no provider credential. The
Linux controller restricts networking and resources; it does not provide the Mac
filesystem sandbox. The verifier still receives only enrollment/expected public
inputs and proof bytes, without a witness/checkpoint or native fallback.

Keep one canonical preparation per fresh workflow. After a successful worker,
record exact source hashes/references before removing duplicate input copies;
retain every failed worker intact. Preserve source, binaries, keys, statements,
proofs, all numeric samples and logs. Compiler object caches may be removed only
after successful builds with their byte counts and binaries retained.

Run the single-rule measurement fixture first. Its report cannot satisfy the
matched campaign. Then execute the full fixed matrix in one job. Allow at most
one hour for the fixture and seven hours ten minutes for preparation, campaign
and archival; reserve ten extra startup minutes per job plus the existing
one-cent storage reserve. At the observed price the rounded estimate is within
the $0.30 cap. Use one attempt per job, cancel on controller deadline, retain
failures, download and verify outputs, confirm terminal jobs and delete owned
temporary buckets. No scheduler, automatic paid retry or private asset upload.

Upload only reviewed public source, the already-published frozen quantizations,
public verification keys and synthetic caller fixtures. Exclude credentials,
business context, raw private transcripts and unrelated local files. Use a pinned
Python image with existing build tools and user-local Rust/Go/uv installations;
do not install system packages.

This changes the experiment host/resource envelope, not the classifier relation.
Prior acceptance trials remain under their original identities and are not
reused as matched timings. Independent security review, witness hiding, hardware
provenance, setup ceremony and default-backend adoption remain outside this work.

The first fixture (job `6ae0f7b441e90535df76716c`, source `084c692`) fails
before compiler/prover startup: the extracted source has no ignored `runs/`
parent. Its 59.64 s running time, output archive and logs are retained; the
terminal bucket is deleted. Correct directory creation and freeze candidate
`circle-classifiers-matched-hf-v2` before the next manual attempt. This is a
new candidate identity, not an automatic retry or an omitted benchmark sample.
Reserve one additional cent for the failed attempt: the new campaign estimate
is $0.28, still under $0.30. The successful fixture must precede the matrix.
The separate composed request is frozen by the caller before upload, including
its Circle enrollment and all 300 expected public fields. Its three new proofs
are outside the 144-proof measurement matrix and receive fresh local proof-only
verification with the retained LLM proof bundle.

The second fixture (`6ae0f89041e90535df7672d0`, source `940f004`) reaches the
isolated Go compiler and fails because the source-copy inventory omits
`encoder-graph.json`, a `go:embed` input. Retain its compiler source/cache/logs
and 43.616 s running-time receipt; its bucket is deleted. Candidate HF v3
shares one source inventory for capture and copy, including embedded JSON,
with a regression check for every `go:embed` path. Reserve a second extra cent;
the new startup-inclusive estimate is $0.29 within the unchanged $0.30 cap.
No failed fixture or partial timing is a matched sample.

The third fixture (`6ae0f91941e90535df767391`, source `d7b6f98`) compiles
gnark, matches the frozen R1CS and generates a real proof. Its isolated pairing
entry point then fails to import an unnecessary CBOR dependency. The entry point
now uses stdlib JSON after checking the caller's exact job hash, like the existing
three-proof entry point. A fresh isolated local process verifies the retained
proof before launching HF v4. Retain all failed bytes; its bucket is deleted
and running time is 300.002 s. Three reserved extra cents bring the bounded
estimate to $0.30; no automatic retries are enabled.

Before the full matrix, enlarge the retained archive allowance from 2 to 3 GiB.
Three fresh gnark setups alone retain 1,620,318,315 key bytes; the three retained
encodings of 72 Circle proofs project another 433,506,168 bytes before sources,
circuits and witnesses. Do not rely on compression to force this through 2 GiB.
The raw-output allowance stays 16 GiB and the compute/storage dollar cap is
unchanged. Local receipt retrieval still requires at least 4 GiB free.
