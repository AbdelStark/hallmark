# Compute and independent review options

Prepared 2026-10-20. Public documentation and pricing observations, not capacity
reservations or evidence of working attestation. The [metadata record](../../evidence/w13-compute-options-2026-10-20.json)
preserves retrieved bytes' hashes and the public HF hardware inventory. Direct
HTTP retrieval of the reviewer pages failed; the browser search reader supplied
those pages. No authenticated API call, job, upload or reviewer contact occurred.

## Ordinary research compute

Start on the owner's Mac: observed arm64, 48 GiB physical memory, 16 logical
CPUs and about 610 GiB free disk. Use the approved four-thread/16-GiB/20-GiB
envelope, two hours per job, six hours total. This is the selected execution
route; it supplies no confidential-computing attestation.

| Fallback | Published hourly compute price | Fit |
|---|---:|---|
| HF T4 small, 16 GB VRAM | $0.40 | Lowest-cost CUDA smoke or small training job; 15 GB host RAM may constrain import. |
| HF L4, 24 GB VRAM | $0.80 | Preferred fallback if a measured local bottleneck requires CUDA or more accelerator memory. |

Prices come from [HF Jobs pricing](https://huggingface.co/docs/hub/jobs-pricing);
the API bills by the minute, with rounded minute rates. Starting and running time
are billable. Jobs need a positive credit balance. Use one L4 job, a one-hour
provider timeout and a $2 total execution ceiling; no automatic retry, ports,
scheduler, top-up or larger instance. This is an agent-imposed limit under the
owner's HF Jobs authorization. Refresh the price and include starting time in the
preflight estimate. Abort if the ceiling cannot be enforced.

Before launch, record the local bottleneck, source/data hashes, reviewed pinned
container and locked environment, output location and cancellation procedure.
Send only reviewed public inputs and source, with no private transcript,
checkpoint or account secret in the command/log. Use the token for control-plane
authentication; do not inject it into the worker unless a specifically reviewed
input requires it. An ordinary HF GPU job supplies no evidence of a TEE.

## Genuine confidential-computing hosts

| Option | Published capability | Decision and missing evidence |
|---|---|---|
| Azure NCCadsH100v5 | AMD SEV-SNP CPU with NVIDIA H100 confidential GPU. | First candidate for a fixed, short qualification session. Region, quota, capacity, supported image and all-in quote still need account-specific checks. |
| Google Cloud A3 High `a3-highgpu-1g` | Intel TDX with H100; Spot or Flex-start provisioning. | Alternative hardware stack; interruption/queue behavior complicates reproducibility. Region/quota and all-in price are unconfirmed. |
| Google Cloud G4 `g4-standard-48` | AMD SEV with RTX PRO 6000; standard, Spot or Flex-start. | On-demand alternative; includes an additional confidential-computing software licence charge. Review exact CPU threat coverage before choosing it. |

These capabilities are described by [Azure](https://learn.microsoft.com/en-us/azure/confidential-computing/gpu-options)
and [Google Cloud](https://docs.cloud.google.com/confidential-computing/confidential-vm/docs/create-a-confidential-vm-instance-with-gpu).
The Azure preference is an engineering recommendation, not a benchmark result.
No cloud account, availability or price is assumed. Obtain an hourly quote plus
storage/network charges for a two-hour qualification window before requesting a
specific purchase. The owner asked for options, so no host is provisioned.

The qualification packet must include a fresh verifier challenge, validated CPU
and GPU evidence and certificate/revocation state, pinned guest/model/runtime
identities, a binding between that workload and both evidence paths, explicit
debug-mode rejection, and tamper/expiry/replay negatives. Two successful isolated
quotes do not demonstrate a bound end-to-end execution. Run this packet on
harmless inputs before admitting any confidential workload.

## Independent reviewer

| Option | Suitable scope | Cost/availability |
|---|---|---|
| Owner-nominated independent researcher or engineer | Reproduce the pinned run on a fresh machine, audit labels/splits and challenge the verifier against the negative corpus. | Unknown until a person is nominated and agrees. Independence and relevant expertise must be recorded. |
| Trail of Bits professional assessment | Candidate for a scoped security design and implementation review spanning trust enrollment, confidential execution and proof integration. | Quote required; no fee or availability is assumed. |

[Trail of Bits' application-security service](https://trailofbits.com/services/application-security/)
describes design and implementation assessment; its [public reports](https://trailofbits.com/reports/)
provide examples of prior work. These references establish a candidate to assess,
not an endorsement of this repository or confirmation of suitable staffing.

Prepare one review packet after the relevant implementation exists: frozen
commit and dependencies, claims/limits, trust enrollment and threat model,
data licence/lineage and label-audit records, reproducible commands, raw results,
failure corpus and unresolved risks. Ask for an independently produced result
with exact inputs, findings and remaining limitations. The authoring agent's
self-check is not the independent review.

Recommendation: use the Mac now, HF only for a demonstrated bottleneck, qualify
Azure's CPU/GPU evidence path when the local verifier is ready, and seek an
independent reproduction before commissioning a broader paid assessment.
Reviewer nomination and a concrete confidential-host budget are later owner
choices; neither blocks current local implementation.
