# 0092: Slurm + Apptainer Support with CUDA 12.8 Profile

**Status**: Proposed  
**Date**: 2026-11-03  
**Deciders**: Owner review required

## Context

Hallmark's existing GPU workloads (TinyLlama LLM prover via SASH and classifier proofs via STWO) currently run exclusively on Hugging Face Jobs using a pinned CUDA 13.1 container (`nvidia/cuda@sha256:e542739fcaa4f45da5add8c4cf5769783a61628b2518304a5bbe4ace468b8c8f` with driver 580.178.04).

Target deployment includes generic Slurm + Apptainer GPU clusters with:
- H100 NVL nodes inside Intel TDX confidential VMs
- NVIDIA driver 570.211.01 (supports CUDA up to 12.8)
- H100 SXM nodes (sm_90) with newer drivers
- No sudo access, per-user storage
- Optional confidential computing attestation

The existing pinned CUDA 13.1 image requires driver 580.x or later and will not run on driver 570.x nodes.

## Decision

Add a **second, explicitly versioned CUDA 12.8 build profile** alongside the existing CUDA 13.1 profile:

### CUDA 12.8 Profile

- **Base image**: `nvidia/cuda@sha256:24c8e3581ea6330038b0d374920721983312627f8adbfcf390bdb4b399d280ed` (12.8.1-cudnn-devel-ubuntu24.04)
- **CUDA version**: 12.8.1
- **Driver requirement**: 570.x or later
- **Target architecture**: sm_90 (H100)
- **Build identity**: Separate from existing CUDA 13.1 builds

### CUDA 13.1 Profile (Unchanged)

- **Base image**: `nvidia/cuda@sha256:e542739fcaa4f45da5add8c4cf5769783a61628b2518304a5bbe4ace468b8c8f` (existing)
- **CUDA version**: 13.1
- **Driver requirement**: 580.x or later
- **Target architecture**: sm_90 (H100)
- **Build identity**: Unchanged, preserves existing evidence

Both profiles include:
- Rust nightly-2025-07-14 with rustup 1.29.1
- uv 0.9.18
- CPython 3.12
- CUDA toolkit and development libraries
- Identical toolchain sources (same download URLs and hashes)

### Slurm Integration

1. **Apptainer definition files** (`slurm/apptainer-cuda12.def`, `slurm/apptainer-cuda13.def`)
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

5. **Optional attestation hooks** (off by default):
   - Manifest hash computation (inputs + binaries + proofs + verifier nonce)
   - Documented hook points for TDX quote (`tdx-attest --report-data`) and GPU attestation (`nvattest --nonce`)
   - No privileged tool calls in default workflow

### Pass Criteria

Same as existing GPU benchmarks:
- All segments and links verify
- Zero CPU constraint fallback
- Proof bytes match published proofs (for CUDA 13.1 profile)
- Fresh proof-only verification passes

## Consequences

### Accepted

- Two build profiles with explicit CUDA version and driver compatibility
- Slurm users can select profile based on available driver version
- CUDA 12.8 profile enables deployment on TDX nodes with driver 570.x
- Existing CUDA 13.1 profile and evidence remain unchanged
- Same worker entry points (`scripts/run_llm_gpu.py`, `scripts/run_classifier_gpu.py`)
- Generic Slurm templates with no hardcoded cluster details

### Deferred

- Automatic profile selection based on detected driver version
- Multi-node or distributed GPU proving
- Dynamic resource allocation
- Integration with cluster-specific accounting systems
- Actual TDX quote generation (hook documented but not executed)
- GPU attestation verification (hook documented but not executed)

### Risks

- Two profiles increase maintenance surface
- CUDA 12.8 profile has not been validated on H100 hardware (no baseline)
- Apptainer build requires network access and disk space
- Container digest must be tracked separately per profile
- No guarantee that CUDA 12.8 numerics exactly match CUDA 13.1 proofs

## Alternatives Considered

### Alternative 1: Single CUDA 13.1 Profile Only

**Rejected**: Requires driver 580.x, excludes TDX nodes with driver 570.x

### Alternative 2: Conditional CUDA Toolkit Build

**Rejected**: Requires building CUDA toolkit from source, increases build complexity and reproducibility risk

### Alternative 3: Driver Upgrade on Target Nodes

**Rejected**: Requires privileged access (sudo), cluster-wide coordination, may break other workloads

### Alternative 4: Use Oldest Compatible CUDA Only

**Rejected**: Abandons existing CUDA 13.1 evidence and invalidates published proofs

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
- [ ] Apptainer definitions frozen with pinned base digests
- [ ] Documentation complete (SLURM.md, README, AGENTS.md)
- [ ] CHANGELOG entry
- [ ] Version bump if required by project convention

## Related

- [0079: Generated CUDA Constraints](0079-generated-cuda-constraints.md)
- [0077: GPU Prover Measurement](0077-gpu-prover-measurement.md)
- [0089: Classifier A100 Capacity Fallback](0089-classifier-a100-capacity-fallback.md)
- [GPU Benchmark Guide](../GPU-BENCHMARK.md)
- [Slurm Integration Guide](../SLURM.md)

## References

- NVIDIA CUDA Compatibility: https://docs.nvidia.com/deploy/cuda-compatibility/
- Driver 570.211.01 supports CUDA 12.8.x
- Driver 580.178.04 supports CUDA 13.1.x
- Existing CUDA 13.1 image: `nvidia/cuda@sha256:e542739fcaa4f45da5add8c4cf5769783a61628b2518304a5bbe4ace468b8c8f`
- New CUDA 12.8 profile: `nvidia/cuda@sha256:24c8e3581ea6330038b0d374920721983312627f8adbfcf390bdb4b399d280ed`
