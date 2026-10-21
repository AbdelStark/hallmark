# 0046 — Bounded HF maximum-input proof attempt

Date: 2026-10-21. W18 / issue #19.

Execute under the owner's standing approval in decision 0045. The Mac now exports
and reloads the unchanged 32,768-unit circuit: 40,015,721 constraints, 48,477,333
wires and 2,566,643,378 serialized bytes. One commitment contains 22,366,059
private wires. The source-derived simultaneous slice-backing lower bound is
30,186,277,504 bytes before the circuit and other setup allocations; it is not
measured RSS. A conservative compressed proving-key bound is 16,027,358,074 bytes,
including one MiB of metadata allowance. The ordinary 256 MiB cap cannot carry
these artifacts. See the maximum-artifact evidence for exact inputs and arithmetic.

Use one HF `l4x4` job as the larger-memory L4 fallback. The authenticated hardware
API and official [hardware table](https://huggingface.co/docs/huggingface_hub/v1.27.0/en/guides/jobs)
report 48 vCPU, 186 GB host RAM and USD 3.80/hour. The GPU is unused. This is a
change to the agent's execution guardrails, justified by the measured graph and
standing approval, not a new owner-specified budget or a procurement request.
Cap provider runtime at 7,200 seconds, creation-to-cancellation at 7,800 seconds,
compute estimate at USD 8.30 and total additional compute/storage at USD 10.
One submission, no automatic retry, no credit top-up and no scheduler.

Pin the previously reviewed Python container digest, Go archive and exact public
Git commit/file hashes. Verify downloaded modules. Use the same inventoried
Boolean-cache and corrected bounded G1 replacements; do not enable either in the
default module. First run the Go boundary/real-proof tests and all seven serialized
fingerprints. The Linux worker must pass actual network denial before costly work.
Its fixed environment contains no HF token or inherited credentials.

Freeze the roster before submission: maximum export must equal the independently
retained Mac circuit hash; fresh setup reads that compiled circuit; a batch proves
empty, 32,767-unit and 32,768-unit synthetic inputs and rejects nine prespecified
private mutations. Fresh verifier workers check all three proofs, each of the
33 changed public fields, a field alias, altered proof and a different key.
The tiny real-proof fixture runs first. Native fixture bytes are checked against
the existing canonical encoder in repository tests. No held-out policy data or
threshold selection occurs.

Execution uses at most 48 Go threads, 170 billion peak process RSS bytes with a
150 billion sampled stop, 24 GiB per file and 96 GiB total retained worker output.
The controller has 6,600 seconds; export/setup/batch receive at most 600/3,600/1,800
seconds respectively and share the total deadline. Resource sampling and aggregate
postchecks are not OS memory or disk quotas. Retain failures and partial files.

Persist only this synthetic campaign in a newly created private HF bucket mounted
at `/output`; the repository stays public. Volume authorization keeps the HF token
on the Mac. This is temporary research output storage, not an upload of private
transcripts, model checkpoints or historical local runs. Check exact downloaded
hashes before removing the temporary remote copy; preserve all failures locally.
No subscription is purchased. [HF storage limits](https://huggingface.co/docs/hub/storage-limits)
include buckets and list private overage at USD 18/TB/month; even 96 GiB for one day
is below USD 0.10 at that rate. Target download/cleanup within 24 hours; if interrupted,
record the retained bucket explicitly and reconcile it on resume.

Pass means actual maximum commitment proofs and the frozen rejection roster pass
under the pinned key, followed by local fresh verification of downloaded proof/key
bytes. It does not select a backend or complete the admitted encoder, the 100-field
classifier statement, an independent verifier/security review, trusted setup
ceremony or genuine hardware attestation. Bucket I/O is included in elapsed costs;
these are diagnostic observations, not isolated performance comparisons.
