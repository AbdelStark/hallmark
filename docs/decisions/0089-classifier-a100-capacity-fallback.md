# 0089: A100 classifier capacity fallback

Date: 2026-10-28. Status: accepted fixed-case A100 experiment; see numeric evidence and report.

The owner requests finishing PR #135 and approves proceeding after the unavailable
numeric credit check was explained. Preserve decision 0088's H200 attempt:
build `6ae1fb193fb22a235dd40305` completed, while device job
`6ae1fccd3fb22a235dd4049f` remained scheduling with no start time. It was canceled
before using a GPU; both buckets are deleted after hash-checked retention.
No device result or H200 measurement follows from that attempt.

Use a new experiment directory and a separately recorded A100-large profile.
Hypothesis and proof acceptance remain those of 0088: unchanged C1 inputs,
enrollment, arithmetic, AIR, proof parameters, stock verifier and 54-proof roster;
three matched CPU/CUDA pairs in CPU/CUDA, CUDA/CPU, CPU/CUDA order. This changes
the measurement host and native compilation target, not the proof relation or
evaluator. Do not combine host measurements or relabel A100 results as H200.
No prior device result exists to reuse.

Live HF inventory gives A100-large: one 80-GB A100, 12 vCPUs, 142-GB host RAM,
USD 0.041667/minute. Build native `sm_80` instead of `sm_90`; keep the gate kernel,
engine overlay and stock verifier source unchanged. The worker must see one
A100 and retain its full machine record. Lower sampled host RSS stop from
180 to 120 GiB. Keep four host threads, 300-second commands, 1,600-second worker
deadline and 2-GiB file cap. Smallest real positive/negative proofs still gate
the full campaign. Compile success alone is insufficient.

Retain the USD 5 combined classifier ceiling. Prior observed running-compute
bound is USD 0.01, not an invoice. New CPU Upgrade build and A100 phase each
allow 1,800 seconds plus 600 seconds creation/cancellation allowance; at the
live rates their combined startup/storage bound is below USD 1.70. Recheck it
programmatically and require no other live job before launch. One job at a time,
no automatic retry, top-up, scheduler or private input. Preserve every failure.
The explicit credit-check exception records a null balance, not fabricated funds.

Mutable candidate paths are only the GPU controller, worker machine/RSS guard,
native architecture selection and supporting evidence/docs/tests. Recreate source
admission because the overlay inventory includes worker/build scripts. Stock
classifier, LLM and verifier source identities remain unchanged.

The first A100 device job reaches its worker but fails before proof generation:
object storage drops executable mode on the binaries. Preserve that failed run.
Stage each hash-checked binary into local worker storage, recheck its bytes and
set mode 0755 there. A real local regression executes a mode-0644 bucket fixture
after staging. This changes transport only. Reuse the completed A100 build only
when its complete source-content inventory, native target, retained binary
inventory and all three binary hashes match; prepare a new worker/source receipt.
One manually corrected device attempt keeps the same three-pair protocol and
USD 5 combined ceiling. No proof result is accepted from the failed attempt.
