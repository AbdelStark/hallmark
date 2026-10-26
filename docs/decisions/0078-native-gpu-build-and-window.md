# 0078: native CUDA build and a complete measurement window

Date: 2026-10-26. Status: bounded follow-up experiment; no backend adoption.

The initial [GPU measurement](0077-gpu-prover-measurement.md) verified both small
fixture digests, the complete SIMD case and 22 CUDA transformer segments. Its
1,950-second worker deadline killed the output-head command before it produced
any head proof. Preserve that run as failed/incomplete, not a complete LLM proof
or an accepted full-case speedup. No verifier/evaluator change follows from it.

The first CUDA fixture took 218.745 seconds. Binary inspection found sm_89 PTX
despite a requested sm_90 target; this observation alone does not identify all
native cubins. The corrected builder uses an isolated Cargo target directory,
a plain CMake architecture setting, and records cuobjdump ELF/PTX inventories.
It requires native sm_90 and rejects sm_89 before admitting the new CUDA binary.
This separates it from the SIMD build's cached CUDA library.

Archive compression uses level one: raw proof/statement/claim bytes must remain
identical, while compression time and archive size may change. This changes
packaging, not the inference relation or proof configuration. Preserve the old
level-nine archives and timings. Explicitly retain the initial fixture-only
shape-admission failure as well; the corrected fixture check never relaxes the
complete LLM enrollment check.

Freeze a new run: one same-host pair, unchanged inputs/model/proof parameters,
four Rayon threads, H200 provider timeout 2,700 seconds, worker deadline 2,550
seconds, per-command deadline 600 seconds and sampled RSS stop 200 GiB. CPU build
and proof-only verification remain at 1,800 seconds each. The new agent-selected
single-run ceiling is $5 under the existing standing provider/credit authority;
the earlier $4-capped attempts remain separate immutable records. No top-up or
automatic retry is permitted. Recheck prepaid credits/rates before launching.
The inspected full timeout/startup/storage bound is $4.64 with a fresh build.

The profile is `cuda-native-sm90-host-generation`. Generation/AIR evaluation
remain on the host, with no generated-kernel install. Acceptance still requires
all 23 segments, full grid/token verification, byte-identical CPU/CUDA artifacts,
fresh CPU proof-only mutations and the existing native Mac verifier. No partial
proof or failed job counts as a passing full measurement.
