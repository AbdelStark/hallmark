# 0093: FlashProve as a pinned external proof backend

Date: 2026-11-03. Status: owner-requested; local verifier and H200 proving accepted.
Merged in [PR #182](https://github.com/AbdelStark/hallmark/pull/182). Numbered 0093
because the Slurm profile decision merged first as 0092.

The owner asked for support of Anthropic's FlashProve prover
([announcement](https://www.anthropic.com/research/provable-inference),
[repository](https://github.com/anthropics/FlashProve)). FlashProve proves that a
committed Mixture-of-Experts transformer, run under greedy decoding on a request
of up to 1,024 tokens, chose each checked token. Its zkSNARK is hash-based. It
hides the weights except for a declared list, and its protocol soundness is
proved in Lean. The C++ verifier and the CUDA prover are tested against that
protocol; neither is itself proved.

**Scope.** Hallmark adds FlashProve the way it added SASH: pinned upstream source
plus command-line adapters, and no copy in the tree. The pin is commit
`9e2bdd8ff5bf9c62f18263d7dac189b0400b260c` (v0.16.0, Apache-2.0), as a
158 MB codeload archive with a fixed SHA-256 and byte count, recorded in
[`source.json`](../../research/probes/flashprove/source.json). No upstream source
file is changed. This adds a backend; it changes no existing contract, model,
threshold, enrollment or identity. FlashProve cannot prove Hallmark's dense
TinyLlama case because it supports MoE models only. The LLM path stays SASH.

**Verifier.** `make verify-flashprove` downloads the archive, builds `cp_verify`
on the host and checks the two stored upstream proofs through upstream's
`integrations/check_proof.py`. Every value comes from the caller: commitment ID,
checked range, next token, configuration and request. A check passes only under
upstream's own three-condition rule (exit 0, `result: outcome=verified` second
to last, matching fields), restricted further to `claim=exact-match` and the
pinned verifier source digest
`93afdaf592393a54ebd17b681d1c03295eb883f0161ff0e6ab872a3b39939595`. On Linux
the build is upstream `verifier/build.sh`, unchanged. On macOS that script
cannot run, because it needs GNU `stat`, `mv -T` and ELF linker flags. Hallmark
then compiles the same unchanged `cp_verify.cpp` with Apple clang, using the
same macros and the same source digest computed the way upstream computes it.
It substitutes libc++ hardening for `_GLIBCXX_ASSERTIONS` and drops the ELF-only
link flags. The compiler and flags differ from upstream's tested build, so the
Mac binary is labelled `apple-clang` in every result.

Acceptance: both stored proofs are accepted, and all 99 altered sets from
upstream's three rejection tables are rejected with the named check. A pass
shows only that the verifier and these synthetic-weight files fit together.

**Prover.** `cp_commit`/`cp_prove` need an sm_90 Hopper GPU, CUDA 13.2 Update 2
and an x86-64 CPU with SHA extensions. HF Jobs offers no H100; its H200 is also
sm_90 (Hopper), and the recorded HF H200 driver (580.178) matches the 580 that
upstream ran under. The owner approved one run on an H200 with a USD 13 ceiling.
The agent-selected controller cap is USD 3.50. At live prices, with HF's 600 s
startup window counted per phase, the worst case is USD 3.27: cpu-xl build
3,600 s, H200 900 s, one attempt each, no retries or top-ups. The owner reported
a USD 31 balance. Only upstream's synthetic small kit (`target_small_f2_roomy`)
is proved. Llama 4 Maverick weights are under Meta's gated licence, which the
run authority excludes (`gated_terms: false`).

`make e2e-flashprove` first runs the free local verifier suite, then two jobs.
The build job runs upstream `verifier/build.sh` and `prover/build.sh` with
upstream's documented pip install of CUDA 13.2.2, as an ordinary account. Its
link stub comes from the pinned `nvidia/cuda` 13.2.1 image, because the build
host has no driver. The prove job runs upstream `run_target_example.sh` with the
retained build. It returns only public files: `config/`, `ivk/`, the request,
the token and the proof. The secret key directory `isk/` never leaves the
worker. The CUDA wheels come from PyPI without hash pins, as upstream's
instructions do; their installed versions are retained.

Caller acceptance for the fresh proof:
- the worker's configuration and request are byte-equal to the pinned kit files;
- the commitment ID is the one `cp_commit` printed, which is valid for a
  commitment the caller made itself;
- the Mac verifier accepts under the same rule as the stored proofs;
- six altered copies are rejected: two proof bits, the next token, a request
  token, a key bit and the commitment ID.

**Not claimed.** No served model, Maverick proof, weight hiding, backend
qualification, security level, or soundness of the C++ verifier or CUDA prover.
The `bits=` figures cp_verify prints are its own accounting, not a security
level. The Lean verifier (`tools/lean-verify`) is not run.

## Results

[Numeric evidence](../../research/evidence/flashprove-2026-11-03.json).

**Local verifier** (Mac, Apple clang build): `make verify-flashprove` took 97.6 s,
including the archive download and a 22 s compile. Both stored proofs were
accepted through `check_proof.py` (small 1.45 s; full size, 1,001 tokens,
7.99 s), and all 99 altered sets were rejected. A later re-timing of raw
`cp_verify` (five calls each, 2026-11-04) gave medians of 0.62 s and 7.88 s,
with a peak of 4.23 GB for the full-size proof
([comparison](../PROVER-COMPARISON.md)).

**Build** (cpu-xl job `6aea16ea0e0338d1bb7f5fb6`): 1,520.5 s, every unit
compiled by nvcc V13.2.86, with a run path to the pip toolkit.

**First prove attempt failed and is retained** (`runs/flashprove-gpu-g9nv07j3`,
job `6aea1d1f0e0338d1bb7f630a`, 80 s). The worker account's `env -i` dropped the
image `PATH`, so `nvidia-smi` (under `/usr/local/nvidia/bin`) was not found, and
the job exited 127 before any commit or proof. Fix: keep the image `PATH` and
`LD_LIBRARY_PATH` for that account, and reuse the retained build after
rechecking its hashes (`--build-run`). One corrected prove job followed.

**Prove** (H200 job `6aea1e650e0338d1bb7f6381`, 74.4 s billed running, driver
580.178.04, Xeon Platinum 8581C with SHA-NI): upstream's commit, prove and
verify example took 22.3 s wall time at 0.9 GB peak RSS. Commitment
`64fbdc19…e81e17`; 48 checked tokens plus next token 284; proof 4,145,980 bytes.
Linux `cp_verify` printed `YES`. The Mac verifier accepted the proof under the
caller rule in 0.97 s. All six altered copies were rejected (`proof-refused` ×3,
`reply-differs`, `key-refused`, `model-statement`). No `isk/` file was
retained.

Spend: the computed upper bounds total USD 0.78 (build 0.44, failed prove 0.17,
prove 0.17), within the USD 3.50 cap and the owner's USD 13. These are not an
invoice. All buckets were deleted after hash-checked retention.
