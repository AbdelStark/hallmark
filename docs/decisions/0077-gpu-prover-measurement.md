# 0077: measure the same LLM relation with a CUDA proof backend

Date: 2026-10-26. Status: implementation experiment, not backend qualification.

The initial resource/build profile below is superseded by
[decision 0078](0078-native-gpu-build-and-window.md). Earlier attempts retain
their original limits and failed outcomes.

The owner requested a GPU prover measurement pipeline using existing authorized
compute credits. The frozen TinyLlama model, quantization, prompt, answer,
calibration, roots and proof parameters stay unchanged. A new experiment identity
separates these measurements from the historical CPU reproduction.

Use the existing HF Jobs transport with a bounded H200 job. One CPU build produces
SIMD and CUDA binaries from the same pinned, unchanged upstream source. Both prove
all 23 segments on the same GPU host, with four Rayon threads and the exact
hash-enrolled public witness archive. Serialized proof/statement/claim inventories
must match byte for byte. The GPU run must report the CUDA backend and sampled
device activity. Full grid verification is mandatory for both runs; a separate
CPU proof-only job then verifies the GPU bundle and runs the existing mutation
suite. The existing native Mac verifier checks the exported GPU bundle as well.

The initial profile is **cuda-host-generation**. Generated constraint kernels are
not installed; witness generation and AIR evaluation remain on the host. All
device-generation path modes are explicitly zero. CUDA still implements the
proof backend. This is a hybrid CPU/GPU baseline, not a claim of full GPU
offloading or the upstream optimized configuration. Generated kernels need a
separate candidate, source inventory and equivalence gates.

Freeze one paired observation, CPU then CUDA, with fresh processes and shared OS
caches. This is not a latency distribution. Retain per-segment internal proving
time, command wall time, verification, sampled host/device memory, GPU activity,
proof size, device/driver data and hashes before publishing conclusions. Reused
preparation and build/transport cost are reported separately from proving; do not
compare the retained-preparation command with a full fresh CPU workflow as a
matched end-to-end speedup. No win is required for a passing measurement.

Initial limits: one job at a time, no retries or top-ups, CPU build/verification
timeouts 1,800 seconds each, H200 timeout 2,100 seconds, worker deadline 1,950
seconds, per-command deadline 600 seconds, sampled RSS stop 200 GiB, at most
4 GiB retained output per phase. The controller checks live provider rates
against a $4 ceiling and a separately checked prepaid balance before launching.
The bound includes the additional 600-second creation/cancellation window per
job because HF also bills the Starting state. At the inspected rates the
worker-timeout component is $2.97 and the complete bound is $3.80; neither is an invoice.
Retain failures, confirm jobs terminal and hash downloads before deleting buckets.

Only the reviewed public archive is eligible for upload. No private inputs,
credentials in workers, hardware-attestation claim or witness-hiding claim is
added. Other GPU hosts can run the portable worker contract later; no provider
abstraction, scheduler or additional provider integration is needed for this
first measurement. A pipeline helper change alters the native verifier's broad
source inventory, so an older signed source enrollment must not be reused.
