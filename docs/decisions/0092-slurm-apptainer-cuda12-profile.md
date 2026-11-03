# 0092: Slurm + Apptainer Support with CUDA 12.8 Profile

**Status**: Proposed  
**Date**: 2026-11-03  
**Deciders**: Owner review required

## Context

Hallmark's existing GPU workloads (TinyLlama LLM prover via SASH and classifier proofs via STWO) currently run exclusively on Hugging Face Jobs using a pinned CUDA 12.9.1 container (`nvidia/cuda@sha256:e542739fcaa4f45da5add8c4cf5769783a61628b2518304a5bbe4ace468b8c8f`). Per the image config, `CUDA_VERSION=12.9.1`, `NV_CUDA_CUDART_VERSION=12.9.79-1`, and `NVIDIA_REQUIRE_CUDA=cuda>=12.9` with datacenter (brand=tesla) driver branches 535, 550, 560, 565, and 570 listed. This image requires driver 535+ and can run on driver 570.x only through CUDA forward compatibility (cuda-compat libraries), not natively.

Target deployment includes generic Slurm + Apptainer GPU clusters with:
- H100 NVL nodes inside Intel TDX confidential VMs
- NVIDIA driver 570.x (supports CUDA up to 12.8 natively)
- H100 SXM nodes (sm_90) with driver 535+
- No sudo access, per-user storage
- Optional confidential computing attestation

On clusters with driver 570.x, users can either:
1. Use the existing CUDA 12.9.1 image via forward compatibility (preserves HF build identity, requires cuda-compat setup, unverified in TDX)
2. Use a new CUDA 12.8.1 image natively (new build identity, simpler deployment, verified for TDX)

## Decision

Add a **second, explicitly versioned CUDA 12.8 build profile** alongside the existing CUDA 12.9.1 profile:

### CUDA 12.8.1 Profile (cuda12.8) — New, Recommended for Driver 570.x

- **Base image**: `nvidia/cuda@sha256:24c8e3581ea6330038b0d374920721983312627f8adbfcf390bdb4b399d280ed` (12.8.1-cudnn-devel-ubuntu24.04)
- **CUDA version**: 12.8.1
- **Driver requirement**: 570.x or later (native support)
- **Target architecture**: sm_90 (H100)
- **Build identity**: New (does not match HF evidence)
- **Recommended for**: Clusters with driver 570.x, including TDX confidential VMs

### CUDA 12.9.1 Profile (cuda12.9) — Existing HF Baseline

- **Base image**: `nvidia/cuda@sha256:e542739fcaa4f45da5add8c4cf5769783a61628b2518304a5bbe4ace468b8c8f` (existing)
- **CUDA version**: 12.9.1 (per image config: `CUDA_VERSION=12.9.1`, `NV_CUDA_CUDART_VERSION=12.9.79-1`)
- **Driver requirement**: `NVIDIA_REQUIRE_CUDA=cuda>=12.9` with datacenter branches 535, 550, 560, 565, 570
- **Validated with**: Driver 580.178.04 on HF Jobs
- **Target architecture**: sm_90 (H100)
- **Build identity**: Unchanged, preserves existing HF evidence
- **On driver 570.x**: Runs via CUDA forward compatibility (cuda-compat on LD_LIBRARY_PATH), not natively
- **Caveat**: Forward compatibility unverified inside TDX confidential VMs

Both profiles include:
- Rust nightly-2025-07-14 with rustup 1.29.1
- uv 0.9.18
- CPython 3.12
- CUDA toolkit and development libraries
- Identical toolchain sources (same download URLs and hashes)

### Slurm Integration

1. **Apptainer definition files** (`slurm/apptainer-cuda12.8.def`, `slurm/apptainer-cuda12.9.def`)
   - Bootstrap from Docker images
   - Install frozen toolchain
   - Generate SIF container images

2. **Sbatch templates**:
   - `slurm/sbatch-cpu-smoke.sh`: CPU smoke test (validate-data, check-conformance, circle-build)
   - `slurm/sbatch-classifier-gpu.sh`: Classifier GPU proofs (9 cases × 2 backends × 3 iterations)
   - `slurm/sbatch-llm-gpu.sh`: LLM GPU proofs (23 segments × 2 backends)

3. **Launcher script** (`slurm/hallmark-slurm.sh`):
   - Build images with profile selection
   - Submit jobs with parameterized partition, reservation, nodelist, constraint
   - No hardcoded cluster names or paths

4. **Run records**:
   - Schema: `hallmark.slurm-{classifier,llm}-gpu-result/1`
   - Contains: commit, image digest, CUDA version, driver version, `nvidia-smi -q`, `scontrol show job`, binary SHA-256s, timers
   - Same evidence shape as existing HF receipts

5. **Optional attestation hook** (off by default):
   - Script `slurm/attest-hook.sh` computes manifest hash (inputs + binaries + proofs + verifier nonce)
   - Generates example commands for TDX quote (`tdx-quote <manifest-hash>`) and GPU attestation (`nvattest attest --device gpu --verifier local`)
   - TDX quote requires sudo, runs as separate CPU-only job step
   - GPU attestation nonce option syntax depends on nvattest version (must be checked against installed version)
   - No privileged tool calls executed automatically

### Pass Criteria

Same as existing GPU benchmarks:
- All segments and links verify
- Zero CPU constraint fallback
- Proof bytes match published proofs (for CUDA 12.9.1 profile)
- Fresh proof-only verification passes

## Consequences

### Accepted

- Two build profiles with explicit CUDA version and driver compatibility
- Slurm users can select profile based on available driver version
- CUDA 12.8 profile enables deployment on TDX nodes with driver 570.x
- Existing CUDA 12.9.1 profile and evidence remain unchanged
- Same worker entry points (`scripts/run_llm_gpu.py`, `scripts/run_classifier_gpu.py`)
- Generic Slurm templates with no hardcoded cluster details

### Deferred

- Automatic profile selection based on detected driver version
- Multi-node or distributed GPU proving
- Dynamic resource allocation
- Integration with cluster-specific accounting systems
- Actual TDX quote generation (hook script provided but not executed automatically)
- GPU attestation execution (hook script provided but not executed automatically)
- Verification of nvattest nonce option availability (depends on installed version)

### Risks

- Two profiles increase maintenance surface
- CUDA 12.8 profile has not been validated on H100 hardware (no baseline)
- Apptainer build requires network access and disk space
- Container digest must be tracked separately per profile
- No guarantee that CUDA 12.8 numerics exactly match CUDA 12.9.1 proofs
- CUDA 12.9.1 forward compatibility on driver 570.x unverified in TDX VMs

## Alternatives Considered

### Alternative 1: Single CUDA 12.9.1 Profile Only

**Rejected**: Requires forward compatibility on driver 570.x; TDX support unverified

### Alternative 2: Conditional CUDA Toolkit Build

**Rejected**: Requires building CUDA toolkit from source, increases build complexity and reproducibility risk

### Alternative 3: Driver Upgrade on Target Nodes

**Rejected**: Requires privileged access (sudo), cluster-wide coordination, may break other workloads

### Alternative 4: Use Oldest Compatible CUDA Only

**Rejected**: Abandons existing CUDA 12.9.1 evidence and invalidates published proofs

## Implementation Notes

1. Pin CUDA 12.8.1 base image by digest after manifest inspection
2. Build both SIF images and record their digests
3. Test CPU smoke job on non-GPU partition
4. Test GPU jobs on both driver versions if available
5. Document actual driver versions tested
6. Update README and AGENTS.md with Slurm path
7. Add to CI documentation (tests cannot run without GPU cluster access)

## Acceptance

- [ ] Owner approval of CUDA 12.8 profile introduction
- [ ] Decision record merged
- [x] Apptainer definitions frozen with pinned base digests
- [x] Documentation complete (SLURM.md, README, AGENTS.md)
- [x] CHANGELOG entry
- [x] Version bump: Not required. Python package version (0.1.0) and Rust crate version (0.1.0) remain unchanged. This adds an optional deployment path without modifying the core proof relation, protocol, or existing evidence. Version bumps in this repository track protocol/evidence changes (per decisions 0088, 0089), not deployment infrastructure additions. New container profiles are tracked by their base image digests and documented in CHANGELOG.

## Related

- [0079: Generated CUDA Constraints](0079-generated-cuda-constraints.md)
- [0077: GPU Prover Measurement](0077-gpu-prover-measurement.md)
- [0089: Classifier A100 Capacity Fallback](0089-classifier-a100-capacity-fallback.md)
- [GPU Benchmark Guide](../GPU-BENCHMARK.md)
- [Slurm Integration Guide](../SLURM.md)

## References

- NVIDIA CUDA Compatibility: https://docs.nvidia.com/deploy/cuda-compatibility/
- 570-branch drivers support CUDA 12.8 natively; CUDA 12.9 requires forward compatibility
- 580-branch drivers support CUDA 12.9 natively
- Existing CUDA 12.9.1 image: `nvidia/cuda@sha256:e542739fcaa4f45da5add8c4cf5769783a61628b2518304a5bbe4ace468b8c8f`
  - Image config: `CUDA_VERSION=12.9.1`, `NV_CUDA_CUDART_VERSION=12.9.79-1`
  - Validated with driver 580.178.04 on HF Jobs
- New CUDA 12.8.1 profile: `nvidia/cuda@sha256:24c8e3581ea6330038b0d374920721983312627f8adbfcf390bdb4b399d280ed`
