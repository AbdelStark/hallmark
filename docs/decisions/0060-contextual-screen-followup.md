# 0060 — Retain the failed screen and freeze a fresh follow-up

Date: 2026-10-22. Status: new bounded synthetic experiment, same standing authority.
No historical result is reused as a passing quality claim.

The [first screen](../../research/evidence/w16-contextual-screen-v1-2026-10-22.json)
fails its all-seed gate: seeds 17/29 have 20 TP, 20 TN; seed 43 has 20 TP, 3 FP and
17 TN. Both fresh runs reproduce all 65 substantive files. Every seed resumes
exactly, and integer oracle/native scores agree. The floating parent gives the
same decisions after its own calibration; quantization did not cause this failure.
The tiny training losses do not establish held-out performance. Preserve this
negative result and the exact original implementation at commit `42ae7ab`.

Do not select a seed using this test. The next hypothesis is that a modestly wider
candidate plus more training/calibration action combinations passes the same
structural screen across seeds. This changes both capacity and data: it is not
a controlled architecture-effect comparison or evidence that width alone helps.

The [new protocol](../../fixtures/contextual-protocol-v2.json) fixes 32 channels
(4,161 learned parameters), the same 96-byte/24-byte-window/4-dimensional profile,
same seeds, optimizer, 200 epochs, integer arithmetic and evaluator. There are
16 designated forbidden and 16 benign actions. All 100 old groups now become
exploratory training data, explicitly including the old test. Of 156 new action
pairs, a SHA256 sort assigns 56 to training, 50 to calibration and 50 to test.
The source record documents this lineage. Reject any complete old prompt in
new calibration/test. These new combinations share vocabulary and the artificial
grammar; they still cannot establish real-world safety quality or independence.

Freeze before fitting and score test once per export. Keep the original all-seed
TPR >=0.8/FPR <=0.1 engineering screen; the existing 1% calibration policy allows
zero false positives with 50 benign calibration examples. Repeat training/export
and 100+100 resume, preserving every failed seed. If the full screen passes,
seed 17 is preselected for the next proof integration solely by this protocol.
The other seeds remain reported, not silently discarded.

The same ten-node operator map and byte/padding/threshold obligations apply.
No runtime/evaluator is changed. Two bounded CPU runs retain the original 7,200s,
one-thread, 8 GiB RSS, 1 GiB output and zero-compute-cost ceilings. This candidate
still needs a genuine specialized proof and separate qualification after screening.
