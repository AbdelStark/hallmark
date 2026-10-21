# 0036 — Sample live proof-worker memory

Date: 2026-10-21. Scope: W18 / issue #19, worker resource enforcement.

Hypothesis: sampling the existing single child permits stopping a growing proof
worker before the approved 16 GiB ceiling. Baseline: commit `2ac8fe5` checked RSS
only after exit; the maximum-input compile exceeded that ceiling by 2,048,000
bytes. Mutable paths are the shared Python worker, its failure tests, resource
documentation and new evidence. Circuits, datasets, proof/evaluation relations,
thresholds and historical results remain frozen. This does not reuse an old
qualification result under a changed controller identity.

Use the macOS arm64 system `proc_pidinfo(PROC_PIDTASKINFO)` ABI through Python's
standard-library `ctypes`. The installed SDK declares a 96-byte `proc_taskinfo`
with resident bytes at offset 8. Reject incomplete reads. No dependency, process
per sample, credential inheritance or external service is added. Inspecting
Apple's system interface and [signal implementation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_sig.c)
does not make its source part of the distribution. The SDK identity is retained
with the run.

Poll at the existing 10 ms interval and request termination at seven eighths of
the RSS ceiling: 14 GiB for the approved 16 GiB ceiling. A failed sample allows
one 10 ms exit-race grace and checks whether the child has exited. Otherwise it
stops the child and rejects the attempt. On group-signal `EPERM`, signal only the
still-unreaped child PID; real permission errors propagate. Record actual exit
status, cutoff/monitor flags, sampled peak and `wait4` peak before rejecting a
budget failure. Preserve the existing post-exit peak, CPU, storage and deadline
checks. Both standalone and staged callers use this worker.

This is a sampled cutoff, not an OS memory quota. Scheduling, fast allocations
and signal latency can overshoot it. Fork remains denied by the existing sandbox.
A cutoff event rejects even when the child naturally finishes before the signal;
an ordinary nonzero exit is not evidence that the monitor killed it.

Before new runs, reconcile completed outer command/roster receipts with their
nested timings. Retain failed runs, do not refund concurrent wall time, and keep
the original unattributed 1,800-second allowance. Selected measurements total
3,429.129 seconds; allowances total 2,110 seconds. Round up to 5,540 charged
seconds of the existing 7,200-second proving allocation. Reserve 300 seconds for
this increment, leaving 1,360 unreserved. Full local study and 40 GiB retained
storage limits still apply; no paid compute or token access is involved.

Pass criterion: injected cutoff, missing sample, exit/signal races and peak-only
violations reject correctly; a native small compile passes; two identical native
cutoff attempts stop below their declared ceiling; local and package gates pass.
The first native attempt lost its cost receipt on a signal race. A subsequent
256-byte compile finished below its test cutoff, so it did not exercise stopping.
Both failures are retained. The final confirmation uses the unchanged maximum
capacity circuit twice with a deliberately lower 2 GiB ceiling and a 30-second
limit per attempt. No maximum-input proof or backend qualification follows.
