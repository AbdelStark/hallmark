# 0040 — Bounded Linux compilation on the approved HF fallback

Date: 2026-10-21. Scope: W18 / issue #19, compile feasibility only.

The Mac's maximum-input compile repeatedly stops within its resource envelope.
The latest snapshot places it in deferred range checking, with substantial live
instruction/hint storage. Hypothesis: the approved L4 host's additional RAM can
finish the same circuit. Do not infer GPU acceleration: this gnark build uses CPU.
Keep circuit, codec, compiler-cache patch, small fingerprints and all historical
proof/evaluator identities unchanged. Platform/build/resource changes have a new
experiment identity; compilation cannot qualify a proof backend.

Recheck the late-diagnosis receipts and retain its entire ancillary allowance.
The prior 6,660 seconds plus 200.412 round conservatively to 6,870. Reserve 300
local seconds initially, including software gates. After correcting and rechecking
bootstrap timeout-log retention, reserve the remaining 30 seconds for local
control-plane receipts: 330 total, zero unreserved, within the unchanged
7,200-second allocation. Cloud execution has the separate existing
one-job, one-hour, two-dollar ceiling. No retry, top-up, scheduler or private upload.

Use a digest-pinned official Python Linux/amd64 image and the reviewed Go 1.26.8
toolchain with its Linux archive hash. Record exact public source/module/build
identities before execution. Credentials authenticate only the local control
plane; never inject the token into the worker. Download public pinned assets in
the bootstrap, then build offline. Do not install system packages or model code.

The separate Linux compile controller reuses file, hash and termination helpers;
the admitted Mac worker stays unchanged. Children receive a fixed environment,
closed inherited file descriptors, CPU/file limits and a seccomp filter denying
socket creation, io_uring creation and cross-process descriptor/ptrace acquisition.
Reject other syscall ABIs, and require a real network-denial smoke before compiling.
This is a network restriction, not a general filesystem or hostile-code sandbox.

Sample child RSS from procfs, retain kernel peak RSS in bytes, stop at 26 billion
sampled bytes and reject a peak above 28 billion. Four Go threads and the existing
1 GiB soft heap limit remain. Missing or malformed live samples fail closed;
record timeout, signal, memory and monitor failures. Sampling is not a hard quota.
The job must have enough actual container RAM before the maximum attempt.

First run the six Go tests and compare seven small serialized circuit fingerprints.
Then compile capacity eight and require 205,547 constraints. Bound each maximum
compile at 300 seconds. Only if it succeeds within limits, repeat in a fresh
process and require the same positive constraint count. A failed prerequisite
skips later cases. The controller roster is bounded at 640 seconds; the job
manifest must bound bootstrap plus execution below the provider/authority timeout.
Retain logs, raw numeric results, all failures and local control-plane receipts.
Full-input proving, encoder/layer-normalization execution, operational enrollment,
independent verification/security/hiding/setup and genuine hardware remain open.

Kernel behavior follows the [Linux seccomp documentation](https://docs.kernel.org/userspace-api/seccomp_filter.html).
HF hardware, prices and timeouts must be refreshed from its
[Jobs documentation](https://huggingface.co/docs/hub/jobs-pricing) and public API
when preparing the exact manifest. This decision alone does not prove a job ran.
