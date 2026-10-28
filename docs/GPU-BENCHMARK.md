# Measure the LLM prover on GPU

[Actual L1 proof files, raw logs, machine/job records and verification commands](REFERENCE-RUN.md#l1-complete-tinyllama-response)
are now published in the reference collection. The numbers below retain their
original run identity; no new GPU run is implied.


`make benchmark-llm-gpu` measures the existing fixed TinyLlama response with
SIMD and CUDA on the **same H200 host**. It reuses the reviewed public witness
archive from a completed LLM run. Model, quantization, tokens, calibration,
roots and proof parameters remain fixed.

The current profile generates CUDA constraint kernels and forbids CPU
constraint fallback. Its complete real-device measurement passes under
[decision 0079](decisions/0079-generated-cuda-constraints.md). The earlier
**fallback baseline** below passes complete proof verification but is slower
with CUDA. See its [numeric evidence](../research/evidence/llm-gpu-benchmark-2026-10-26.json),
[decision 0077](decisions/0077-gpu-prover-measurement.md) and the native CUDA
build/resource follow-up in [decision 0078](decisions/0078-native-gpu-build-and-window.md).

## Generated-constraint result

The clean H200 pair and fresh CPU/Mac mutation suites pass. See the
[audited numeric evidence](../research/evidence/llm-gpu-generated-constraints-2026-10-26.json).
Measured source is `ef09216eabee044c24209f555df39e277ee6dfaa`; the admitted
generated build was produced at `74bc2db33df5cf4d1e5a5b101b30fecba122960f`.

![TinyLlama proving on one H200: CUDA cuts the proving session from 547.75 s to 53.94 s (10.15×); complete segment commands go from 679.49 s to 155.89 s (4.36×); trace generation is unchanged.](assets/figures/perf-llm-gpu.svg)

![Dumbbell chart, log scale: proving-session seconds per segment on CPU and GPU. Ratios range from 3.2× to 28.7×; segments L0 to L2 are much slower on CPU.](assets/figures/perf-llm-segments.svg)

| Measurement | SIMD | Generated-constraint CUDA |
|---|---:|---:|
| Summed proving stages, 23 segments | 547.75 s | **53.94 s** |
| Complete segment commands | 679.49 s | **155.89 s** |
| Separate SIMD grid verification on the H200 host | 85.35 s | 84.32 s |
| Sampled peak prover host RSS, decimal GB | 103.75 GB | 8.07 GB |
| Sampled peak device memory | 0 | 69,293 MiB (67.67 GiB) |
| Maximum sampled GPU utilization | 0% | 100% |
| Constraint-evaluation time | 24.29 s | 0.47 s |
| CPU constraint fallback calls | 0 | **0** |
| Serialized proof bytes | 737,858,641 | 737,858,641 |

This pair observes **10.15× faster summed proving** and **4.36× faster complete
segment commands** with CUDA. All 23 segments and both grids pass, and all 69
proof/statement/claim files match. CUDA reports 1,710 actual device constraint
evaluations. Witness/interaction generation remains on the CPU; this is not a
claim that every operation runs on GPU. The cache/order/sample-count limits
below still apply. The separate CPU suite accepts two honest checks in
77.61/77.40 seconds and rejects all 14 mutations; its peak child RSS is 14.34 GB.
The Mac suite accepts two in 3.53/3.40 seconds after compilation and rejects all
36 mutations. All 69 artifact entries also match the historical complete CPU case.

The first generated-kernel attempt produced all 23 individually valid CUDA
proofs and matching files, then failed on a concurrently written partial
telemetry record. That failed record is preserved. The correction frames complete
CSV records without weakening proof checks. The clean pair reuses the same
generated binaries, avoiding another 30-minute build.

The successful command takes **2,086.78 seconds (34 min 47 s)** with preparation
and generated binaries reused. That command includes the fresh SIMD reference,
CUDA proving, both grid checks, transfers and CPU/Mac verification; it is not a
single GPU proof latency. The original build takes **1,815.94 seconds** and
installs **77 kernel shapes across 16 families**. A full fresh-build command was
not measured uninterrupted; keep these costs separate. Use `GPU_BUILD_RUN` below
to reuse a caller-owned admitted build.

The successful rerun has a **$1.76 running-compute estimate**. Including the
original build and retained telemetry-failure attempt, this kernel campaign
totals **$3.37**, not invoices. All four campaign jobs are terminal and all
temporary buckets were deleted after hash-checked retention. The source, build,
generated/modified files, profiler counters and failure are pinned in the JSON.

## Historical fallback baseline

<a id="recorded-same-host-result"></a>

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
slower. The generated-constraint candidate addresses this measured bottleneck
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
The completed run must also contain the enrolled proof archive/inventory: the
builder extracts and hash-checks all 23 public statements to generate kernels.

To reuse a completed build from a **caller-owned** earlier GPU measurement run,
also supply `GPU_BUILD_RUN=/path/to/llm-gpu-run`. The controller checks its case,
build-script and binary hashes plus complete retention/cleanup receipts before
enrolling those binaries. This skips the CPU build job and explicitly reports
reused build cost separately; a prover-supplied executable directory is not a
trusted build cache.
Only a matching generated-constraint build is eligible; the historical
fallback-only binary cache is rejected.

This starts paid HF jobs under a **$5 single-run ceiling**, with one job at a time
and no retries. Build has a 60-minute timeout and CPU verification 30 minutes; the
H200 job has 45 minutes, with a 42.5-minute worker deadline and memory stop. The plan
also reserves the full additional ten-minute creation/cancellation window per job in
the price guard because HF bills startup time. At the inspected rates the
complete bound is $4.66 with a fresh build, or $4.62 with a retained build.
These are conservative bounds, not invoices. Jobs
and buckets are retained on uncertain failure; successful outputs are downloaded
and hashed before temporary buckets are deleted.

Ordinary CI runs offline admission/orchestration tests. Paid GPU execution starts
only through this explicit command; merging code does not schedule GPU jobs.

## What runs

```text
Reviewed public witness archive
  + enrolled statements → CPU: pristine SIMD build → cudaemit shape union
  → upstream installer + strict fallback guard → native sm_90 CUDA build
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

The **cuda-native-sm90-generated-constraints** candidate installs upstream-generated
AIR constraint kernels for the union of all 23 statement shapes and the small
fixture. Witness and interaction generation remain on the host, with their path
modes explicitly zero. Generated witness kernels are not installed. No proof
constraint, binding or verifier check is disabled.

SIMD uses pristine pinned source. CUDA truthfully reports a dirty build: generated
sources/dispatch/table, a guard that aborts both CPU constraint fallback branches,
and a build-only cap of two CUDA compile jobs. `kernel-build.json` retains exact
generated/modified-source inventories, patch hash and binary hashes. Every CUDA
proof must also report zero fallback counters and positive GPU constraint time.
The CUDA build uses an isolated target directory. Retained `cuobjdump` inventories
must show native sm_90 code and no sm_89 code before the binary is admitted.

## Read the measurements

Every invocation prints a fresh `runs/llm-gpu-*` directory. Retained outputs include:

Top-level `result.json` is written only after CPU and Mac verification pass.
`prove/retained/output/result.json` covers the H200 pair alone; its proof-only
worker verification field describes a later phase that has not run at that point.

| Measurement | Meaning |
|---|---|
| `prove_seconds` | Sum of SASH proving-session timers for all 23 segments, from session creation through proof generation; includes commitments and interaction work |
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
