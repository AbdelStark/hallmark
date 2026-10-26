# 0079: generated CUDA constraints with no CPU fallback

Date: 2026-10-26. Status: owner-requested bounded implementation experiment.

The owner requests completing generated constraint kernels after the initial
[H200 baseline](0078-native-gpu-build-and-window.md) spent 532.75 seconds in
1,710 scalar CPU fallback calls. Preserve that result and all failed attempts.
The new hypothesis is that generated CUDA constraints remove this bottleneck
while producing exactly the same complete TinyLlama proof artifacts.

Use pinned upstream `cudaemit --params` on all 23 previously verified public
statements plus the smallest aligned synthetic fixture. Admit statements by the
existing 69-file proof inventory and hash every extracted statement. Build the
union with the upstream installer and its default 3,000-instruction segmentation.
Keep witness generation on the host; witness kernels are outside this candidate.

The original SIMD binary stays pristine. CUDA truthfully reports a dirty build:
generated constraint sources/dispatch/table are installed, a reviewed patch
forbids both CPU fallback branches, and CMake compile parallelism is limited to
two jobs to fit the 32-GB build host. Retain exact generated and modified-source
inventories, patch hash, native sm_90 inventory and binary hashes. No inference
constraint, proof parameter, model, quantization, calibration or input changes.

Run the smallest real CUDA proof first. Reject any explicit/automatic fallback,
require zero fallback counters and positive GPU constraint execution, then prove
all 23 segments on SIMD/CUDA with identical inputs and four Rayon threads on one
H200. Require full grid/token checks, all 69 files byte-identical and fresh CPU
and Mac proof-only mutation suites. The original cryptographic evaluators and
caller expectations remain frozen. A failed kernel or missing shape fails the
experiment; no fallback or weaker verifier repairs it.

Freeze one pair, CPU then CUDA, with shared OS caches and a fixture-warmed driver.
Report proving/command/verification times, host/device memory, profiler counters,
proof bytes, failures and costs before conclusions. No speedup is assumed.

Under standing owner credit/provider approval, select a $5 single-run ceiling:
CPU Upgrade build 3,600 seconds, H200 2,700 seconds, CPU Upgrade verification
1,800 seconds, plus 600 seconds creation/cancellation allowance per phase.
The inspected full price/storage bound is $4.66. Preserve live rate/balance
checks, 200-GiB sampled RSS stop, concurrency one, no automatic retries/top-ups,
no private uploads and no scheduler. The Mac coordinates and verifies locally.

[Issue #122](https://github.com/AbdelStark/hallmark/issues/122) tracks delivery.
This does not adopt a qualified backend, hiding or hardware provenance.

The first device run produced all 23 individually accepted CUDA proofs with zero
fallback and 69 files identical to SIMD, but failed while parsing a telemetry
record written concurrently at the head command. No complete run is accepted
from that attempt. Preserve its raw results and failed status. The parser now
frames complete newline-terminated CSV records, discarding only first/last
partial records; malformed complete records still reject. A regression covers
both partial boundaries. This changes measurement I/O only. Start a new frozen
run with the same admitted generated binaries, inputs, evaluator and limits;
its remaining timeout/startup/storage bound is $4.62 under the $5 run ceiling.
