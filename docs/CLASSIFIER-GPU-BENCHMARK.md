# Circle classifier GPU benchmark

Recorded 2026-10-28, under [decision 0089](decisions/0089-classifier-a100-capacity-fallback.md).
The unchanged C1 rule, integer MLP and CNN prove on CUDA and pass the stock
STWO 2.2.0 verifier. Median summed prover-command time for nine proofs is
**92.41 seconds CPU / 22.22 seconds CUDA**, a **4.16× ratio of medians**.
This measures three fixed-case pairs on one A100 host, with four host threads.
It excludes training, Python witness preparation and verification.

[Numeric evidence](../research/evidence/classifier-gpu-benchmark-2026-10-28.json)
contains all 54 measurements, individual stages, seven rejection timings per
proof, machine/source/input/binary pins and retained-file audit counts. Serialized
proofs and complete logs remain in the named local run directories; the evidence
JSON is not a public download of those proof files.

## Measurements and boundaries

HF `a100-large`: one NVIDIA A100-SXM4-80GB, driver 580.178.04, native `sm_80`;
Intel Xeon Platinum 8275CL. Provider allocation is 12 vCPUs / 142 GB RAM. The
guest exposes 96 logical CPUs, but its CPU quota is 12 CPUs and memory cgroup
limit is 152,999,997,440 bytes. Rust uses four Rayon threads. Linux Python is
3.12.3. No exclusive physical-host allocation is claimed.

| Nine-proof suite | CPU SIMD | CUDA |
|---|---:|---:|
| Complete prover commands, repetition 1 | 92.406 s | 22.241 s |
| Complete prover commands, repetition 2 | 92.517 s | 22.142 s |
| Complete prover commands, repetition 3 | 92.317 s | 22.216 s |
| Median complete commands | **92.406 s** | **22.216 s** |
| Median summed final STWO proving calls | 44.310 s | 7.550 s |
| Maximum sampled prover RSS | 19.456 GB | 0.624 GB |
| Peak sampled device memory | — | 18.25 GiB |
| Proof JSON for one nine-case suite | 18,063,779 bytes | 18,063,779 bytes |

Final STWO calls are inside complete commands; do not add them. Their ratio of
medians is 5.87×. Commands include parse/load, twiddles, preprocessing/model
commitment, host base/interaction generation, trace commitments, final proving
and serialization. CUDA accelerates the proving machinery and the specialized
gate AIR; witness/base/interaction generation remains host work. Device transfers
are charged to their enclosing stages, not isolated transfer measurements.

| Classifier | Median CPU command | Median CUDA command | CPU final STWO call | CUDA final STWO call |
|---|---:|---:|---:|---:|
| Rule | 7.659 s | 2.049 s | 3.727 s | 0.795 s |
| MLP | 7.660 s | 2.109 s | 3.713 s | 0.805 s |
| CNN | 15.567 s | 3.205 s | 7.288 s | 0.916 s |

Each classifier row pools its three fixed requests across three repetitions.
The suite table instead sums each repetition before taking a median. Pair order
is CPU/CUDA, CUDA/CPU, CPU/CUDA. The arithmetic fixture warms the driver; OS
caches are shared. Three suite samples are descriptive, not a reliable latency
distribution. These measurements are separate from the published Mac C1
controller and the older HF Circle/gnark workflow comparison.

## Proof acceptance and retained resources

All **54** honest Linux checks and **54** fresh stock Mac checks pass against
caller-reconstructed public vectors and the original enrollment. All **378**
public-input mutations reject. Each of the 27 CUDA classifier proofs records one
device AIR call and zero CPU AIR fallback. Both arithmetic backends pass honest
proof checks and reject the changed internal witness before the full campaign.
All 54 proof byte strings also match their nine published C1 controls. Byte
equality is an observed result, not a general requirement that proofs be unique.

The audit rehashes **1,612 retained files / 133,042,187 bytes**, including failed
attempt outputs and both native builds. All five temporary buckets are deleted.
Fresh Mac proof-only verifier processes total 1.439 seconds for all 54 proofs;
Linux positive verifier processes total 1.417 seconds. These are separate from
prover timings. The corrected controller takes 546.35 seconds including reused
input reconstruction (74.60 seconds), transfers, device job and Mac checks.
Training and the completed native build are reused.

The rounded running-compute bound across these classifier attempts is **USD 0.37**,
not an invoice or a complete storage bill; the combined admission ceiling is
USD 5. The H200 build completes, but its GPU allocation never starts and is
canceled while queued. The first A100 worker fails before proving because object
storage drops executable mode. The corrected worker copies admitted binaries to
local storage, rechecks hashes and sets executable mode. It reuses the completed
A100 build only after source-content/native-target and binary receipt admission.
Failures remain separate and do not enter timing statistics. The separate prior
LLM repeat build timed out; this report establishes no fresh LLM GPU measurement.

## Commands and scope

With the pinned toolchain and a caller-owned C1 preparation whose manifest hash
matches decision 0088, prepare a new source directory and run:

```bash
uv run --locked --extra llm python scripts/prepare_classifier_gpu.py --out runs/<new-source>
uv run --locked --extra train --extra llm python scripts/run_classifier_gpu.py \
  --prepared runs/<caller-C1-preparation> \
  --native-preparation-pin 3eab49c2a4a97a3e7d4daaefbbdc4c68a09ae7ba2d9a0d438c803cc7efcb13cd \
  --source runs/<new-source> --gpu-flavor a100-large \
  --credit-balance-usd <independently-checked-balance>
```

`--build-run runs/<prior-campaign>` admits a matching retained native build.
The recorded corrected campaign uses `runs/classifier-gpu-399bl9ec` as its build
and writes `runs/classifier-gpu-sm11ii3z`. The owner explicitly approved the
recorded credit-check exception; its balance remains null. Normal reproduction
uses the checked balance above and its own provider authority.

Stock classifier/core/verifier sources, models, thresholds, SHA-256 commitment,
proof parameters and C1 enrollment remain unchanged. The optional CUDA crate
uses the reviewed Apache-2.0 Nitroo operations and the pinned STWO overlay; the
Mac default stays stock. This establishes fixed-case cryptographic execution
and a measured implementation speedup, not hiding, hardware attestation,
independent security review, useful policy quality or backend qualification.
