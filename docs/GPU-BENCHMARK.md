# Measure the LLM prover on GPU

`make benchmark-llm-gpu` measures the existing fixed TinyLlama response with
SIMD and CUDA on the **same H200 host**. It reuses the reviewed public witness
archive from a completed LLM run. Model, quantization, tokens, calibration,
roots and proof parameters remain fixed.

The first **experimental** profile passes the complete proof and verification
gates below. Its one paired observation is slower with CUDA and uses less host
memory. See the [numeric evidence](../research/evidence/llm-gpu-benchmark-2026-10-26.json),
[decision 0077](decisions/0077-gpu-prover-measurement.md) and the native CUDA
build/resource follow-up in [decision 0078](decisions/0078-native-gpu-build-and-window.md).

## Recorded same-host result

One CPU-then-CUDA pair on an HF H200, four Rayon threads, 2026-10-26:

Measured source: [`a81c10a`](https://github.com/AbdelStark/hallmark/commit/a81c10a324fe7e849a40cf1f0caa9338e1a0cc3d).
The later controller prerequisite check rejects unsupported hosts or missing Rust
before paid work; it changes no prover, evaluator, input or recorded measurement.

| Measurement | SIMD | CUDA, host generation |
|---|---:|---:|
| Summed proving stages, 23 segments | 537.20 s | 583.87 s |
| Complete segment commands | 669.25 s | 687.34 s |
| Separate SIMD grid verification on the H200 host | 88.59 s | 85.07 s |
| Sampled peak prover host RSS, decimal GB | 104.69 GB | 11.78 GB |
| Sampled peak device memory | 0 | 68,685 MiB (67.08 GiB) |
| Maximum sampled GPU utilization | 0% | 89% |
| Serialized proof bytes | 737,858,641 | 737,858,641 |

All **69 proof/statement/claim files match byte for byte**. Both grids accept all
23 segments, 22 residual links and seven generated-input links. A fresh CPU-only
worker accepts two honest checks in 81.02/80.94 seconds and rejects all 14
mutations, with 14.35 GB peak child RSS. The native Mac verifier accepts two
honest checks in 3.53/3.39 seconds and rejects all 36 mutations. These verifier
implementations have different shape-root preprocessing, as explained below.

CUDA is **8.7% slower in summed proving and 2.7% slower in complete commands** in
this pair. Its profiler records 1,710 CPU constraint-evaluation fallback calls,
taking 532.75 seconds. SIMD constraint evaluation takes 23.99 seconds. Reported
Merkle and FRI stages accelerate substantially, but the complete CUDA path remains
slower. The next performance candidate is generated CUDA constraint kernels,
with a new source inventory and the same equivalence/verification gates.
Nested profiler timers overlap; do not add them to reconstruct wall time.

The fresh benchmark command takes **3,372.34 seconds (56 min 12 s)** with reused
preparation, fresh SIMD/CUDA builds, both full proving runs and CPU/Mac checks.
Its running-compute estimate is **$2.52**, under the $5 run ceiling; all four
attempts including failures total **$5.37** by that measure. These are not
invoices. All six jobs are terminal and all temporary buckets were deleted after
hash-checked retention. Raw source/input/binary hashes, per-segment metrics,
profiler counters, mutation outcomes and failed attempts are in the linked JSON.

## Run it

Use the Apple Silicon Mac, uv and native Rust prerequisites from the
[LLM guide](LLM-PROOF.md). Allow at least 16 GiB free local storage. Set `HF_TOKEN`
in the environment or ignored `.env`. Check the live prepaid balance in your
HF billing dashboard, then run:

```sh
make benchmark-llm-gpu \
  LLM_RUN=/path/to/completed/llm-e2e-run \
  GPU_CREDIT_BALANCE_USD=YOUR_CHECKED_BALANCE
```

The balance argument is an independently checked input, not a balance fetched
by this command. The controller compares it with live hardware rates and the
job plan before launching. No top-up or recharge change occurs. Only the exact
hash-enrolled public archive is eligible; edited or unrelated preparations
reject before upload. No checkpoint is downloaded or model retrained.

To reuse a completed build from a **caller-owned** earlier GPU measurement run,
also supply `GPU_BUILD_RUN=/path/to/llm-gpu-run`. The controller checks its case,
build-script and binary hashes plus complete retention/cleanup receipts before
enrolling those binaries. This skips the CPU build job and explicitly reports
reused build cost separately; a prover-supplied executable directory is not a
trusted build cache.

This starts paid HF jobs under a **$5 single-run ceiling**, with one job at a time
and no retries. Build and CPU verification each have a 30-minute timeout; the
H200 job has 45 minutes, with a 42.5-minute worker deadline and memory stop. The plan
also reserves the full additional ten-minute creation/cancellation window per job in
the price guard because HF bills startup time. At the inspected rates the
complete bound is $4.64 with a fresh build, or $4.62 with a retained build.
These are conservative bounds, not invoices. Jobs
and buckets are retained on uncertain failure; successful outputs are downloaded
and hashed before temporary buckets are deleted.

Ordinary CI runs offline admission/orchestration tests. Paid GPU execution starts
only through this explicit command; merging code does not schedule GPU jobs.

## What runs

```text
Reviewed public witness archive
  → CPU build: pinned source → SIMD and CUDA binaries
  → H200: small real CUDA fixture → complete SIMD run → complete CUDA run
  → separate CPU worker: GPU proof bundle only, two honest checks + 14 mutations
  → Mac: existing native verifier, two honest checks + 36 mutations
```

Both complete runs prove all 22 transformer layers and the final-norm head,
then check the full grid and token links. All 69 proof/statement/claim files must
match byte for byte between SIMD and CUDA. The fresh CPU worker receives no
model weights or full witness. Source/binary/input hashes and caller-enrolled
roots bind every phase. A reported GPU name alone is insufficient: the prover
must report the CUDA backend and the full CUDA run must show sampled device
activity.

This one-block case checks seven generated-input/previous-output equalities
inside the 32-position block. Its zero expected interblock token links do not
skip those seven autoregressive checks; see the [LLM statement](LLM-PROOF.md).

The fresh verifier processes share SASH's cryptographic implementation. They
provide process/input separation, not an independently implemented verifier.

## Which work is accelerated?

The **cuda-native-sm90-host-generation** profile runs the SASH CUDA proof backend
while keeping witness generation and AIR constraint evaluation on the CPU.
Generated constraint/witness kernels are not installed. Relevant path modes are
explicitly zero and retained in every prover report. This is a CPU/GPU baseline,
not the upstream optimized configuration or a claim that every operation is on
GPU. No proof constraints, bindings or verifier checks are disabled.

This avoids silently measuring a missing-kernel fallback as full GPU offloading.
Generated-kernel optimization needs a new source inventory and equivalence gates.
The CPU and CUDA binaries currently build from unchanged pinned upstream source.
The CUDA build uses an isolated target directory. Retained `cuobjdump` inventories
must show native sm_90 code and no sm_89 code before the binary is admitted.

## Read the measurements

Every invocation prints a fresh `runs/llm-gpu-*` directory. Retained outputs include:

Top-level `result.json` is written only after CPU and Mac verification pass.
`prove/retained/output/result.json` covers the H200 pair alone; its proof-only
worker verification field describes a later phase that has not run at that point.

| Measurement | Meaning |
|---|---|
| `prove_seconds` | Sum of internal prove-stage timers for all 23 segments |
| `commands_seconds` | Complete segment commands, including generation, internal verification and serialization |
| `verify_seconds` | Separate SIMD grid-verifier process on the same H200 host |
| `sampled_peak_rss_bytes` | Linux process high-water RSS observed every 250 ms; not total host memory |
| `gpu_peak_memory_mib` | Device memory sampled every 500 ms; includes device/runtime overhead |
| `gpu_peak_utilization` | Maximum sampled utilization; not average occupancy or attribution of every operation |
| `serialized_proof_bytes` | Serialized proof files; statements/claims have a separate retained inventory |
| Phase receipts | Build/transport/job wall time, bounded compute estimate and cleanup status; not invoices |

Raw per-segment JSON retains additional internal phases and path modes. The
separate CPU proof-only and native Mac directories retain their own verification
times and mutation outcomes. The native verifier uses compiled enrolled shape
roots; its time is not a like-for-like comparison with Linux runtime derivation.

The first run supplies **one pair**, CPU then CUDA, with fresh processes and
shared OS caches. It is not a latency distribution. A speed ratio from that pair
is one observation, not a general speedup claim. The command reuses preparation;
its total wall time cannot be compared with the README's fully fresh CPU workflow
as a matched end-to-end speedup. Preserve failures and start a new directory for
each repeat.

The small fixture runs first and warms the CUDA driver/kernel cache. Its own
time is retained; the full model measurement is not a cold-start GPU latency.
Earlier attempts remain failed records: a fixture enrollment mismatch, then a
deadline after all 22 CUDA layers but before the head. Neither is a full GPU proof.

## Other infrastructure

HF Jobs is the first supported transport. The worker consumes files under
`/persist`, uses `/work` for scratch, and writes results back under `/persist`.
The same worker contract can move to another suitable H200 host. Other cards
need a separately frozen architecture/build and resource profile. Modal/Vast
adapters, ongoing schedulers and additional infrastructure are not implemented.

Changing the shared controller helper changes the native verifier's source
identity. An earlier signed source enrollment must be replaced after reviewing
the new inventory; the command does not manufacture operational authorization.
No hardware-attestation, hiding or production-qualification claim is added.
