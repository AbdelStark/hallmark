# 0088: unchanged classifier relations with a CUDA prover

Date: 2026-10-28. Status: H200 attempt preserved; accepted A100 experiment in decision 0089.

The owner explicitly requests GPU classifier proving in addition to an LLM GPU
repeat, retaining the local Mac measurements. Hypothesis: an optional CUDA
backend can prove all nine C1 classifier statements under their unchanged
enrollments and STWO 2.2.0 verifier, with measured device AIR execution. Speed
is an outcome, not an acceptance requirement. Historical C1 remains unchanged.

The stock Apache-2.0 Nitroo backend at 41c2a05 uses an older PCS/proof format;
an attempted direct dependency fails compilation against our unmodified adapter.
Preserve that attempt. VortexSTARK's current Business Source licence is excluded
from the dependency path. Instead, copy Nitroo's pinned Apache-2.0 CUDA
operations/buffers into a generated, optional-feature STWO 2.2.0 tree. The
registry archive checksum is independently pinned by our existing Cargo.lock.
The overlay adapts API signatures, subdomain quotient evaluation, twiddle
extraction, FRI folding and four-way packed leaves. A specialized nine-constraint
CUDA kernel evaluates the existing gate AIR. No stock core/verifier, PCS driver,
model, quantization, arithmetic, threshold, request or proof parameter changes.
Host witness/base/interaction generation remains CPU work and is labelled.

Preparation must verify upstream archive hashes, regular-file bounds, the
closed source inventory, unchanged stock verifier/core bytes and exact overlays.
The Mac default crate is unchanged; CUDA is built in an isolated generated
crate. Keep original licences with the source tree. Do not treat compilation
as proof correctness or device execution. Local CPU fixture tests, a
byte-identical C1 rule proof and a CUDA-feature Rust compile check precede
paid work. Device acceptance starts with an honest tiny arithmetic proof and
a changed internal witness, checked by an independently built stock verifier.
Failure there stops the full campaign.

Freeze the published C1 preparation at native manifest
3eab49c2a4a97a3e7d4daaefbbdc4c68a09ae7ba2d9a0d438c803cc7efcb13cd.
Reconstruct all nine programs, witnesses and public vectors using the unchanged
native/compiler code and compare retained bytes before upload. Keep caller
enrollment pin 56c29c74a4efa0443bff84cc516349b0369360e2feaf347b871b860b06cd635e.
Only public synthetic fixtures and public-model derived witnesses are uploaded;
no private source, checkpoint or token enters the worker.

Measure three complete nine-proof pairs on one HF H200, order CPU/CUDA,
CUDA/CPU, CPU/CUDA, with four Rayon threads and a warmed fixture/driver. CPU
uses the stock crate, compiled for x86-64-v3; CUDA uses the same target feature.
Record every proof, complete command, internal stage, fresh stock verification,
proof bytes, process RSS and 100-ms GPU samples. Require 54 fresh honest Linux
checks, 378 public-input mutation rejections and 54 fresh stock Mac checks
against the pre-upload caller inputs. Report byte equality separately: a valid
proof need not have unique bytes. Missing/failed cases do not enter averages.
This excludes fresh training and Python witness preparation from prover latency.
Report those costs separately and do not compare it as a full-workflow speedup
over the Mac C1 controller. Three observations give descriptive medians, not
a reliable tail-latency distribution or an equal-security backend ranking.

Select a separate USD 5 cap under standing owner provider approval: CPU Upgrade
build 1,800 s, H200 1,800 s, each with 600 s startup/cancellation allowance,
one concurrent Job, no retries/top-ups/schedulers. Current rates give a USD 3.37
timeout/startup/storage bound. Check available credit again before launch, and
wait until the LLM repeat is terminal. Use the existing foreground transport,
pinned CUDA image, hash-checked retention and bucket cleanup. Per Rust process:
180-GiB sampled RSS stop, 300-s command deadline,
2-GiB file cap; worker 1,600-s experiment deadline. Preserve failed attempts.
CUDA's large virtual reservations preclude RLIMIT_AS; the generic transport's
210-GiB memory-envelope field is not an enforced address-space cap here.
Publication excludes witness inputs and executable binaries; actual proofs,
public inputs, logs, source/parameter pins and machine records may be published.
No hiding, hardware provenance or backend qualification is claimed.

Fresh-clone continuation: after being told numeric billing access was unavailable,
the owner explicitly said "go ahead and finish, you have my approval" on
2026-10-28. This authorizes proceeding with the existing USD 5 cap without the
numeric credit check. Record the balance as null and this exception explicitly;
do not invent a balance or top up. Live prices, no active jobs, all other limits,
source/input admission and smallest-device-proof gates remain required.
