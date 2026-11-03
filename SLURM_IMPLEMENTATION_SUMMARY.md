# Slurm + Apptainer Implementation Summary

## Completed Work

This implementation enables Hallmark's GPU workloads to run on generic Slurm + Apptainer GPU clusters, in addition to the existing Hugging Face Jobs path.

## Files Changed

### New Files (12 total)

#### Slurm Infrastructure (7 files)
1. **`slurm/apptainer-cuda13.def`** - CUDA 13.x container definition
   - Base: `nvidia/cuda@sha256:e542739fcaa4f45da5add8c4cf5769783a61628b2518304a5bbe4ace468b8c8f`
   - Compatible with existing HF Jobs evidence
   - Validated with driver 580.x

2. **`slurm/apptainer-cuda12.def`** - CUDA 12.8 container definition
   - Base: `nvidia/cuda@sha256:24c8e3581ea6330038b0d374920721983312627f8adbfcf390bdb4b399d280ed`
   - Enables TDX nodes with driver 570.x
   - New profile, no baseline yet

3. **`slurm/sbatch-cpu-smoke.sh`** - CPU smoke test job template
   - Runs: validate-data, check-conformance, circle-build
   - Resources: 4 CPUs, 32GB RAM, 2h timeout

4. **`slurm/sbatch-classifier-gpu.sh`** - Classifier GPU job template
   - Runs: 9 cases × 2 backends × 3 iterations = 54 proofs
   - Resources: 4 CPUs, 180GB RAM, 1 GPU, 3h timeout

5. **`slurm/sbatch-llm-gpu.sh`** - LLM GPU job template
   - Runs: 23 segments × 2 backends (SIMD/CUDA)
   - Resources: 4 CPUs, 210GB RAM, 1 GPU, 4h timeout

6. **`slurm/hallmark-slurm.sh`** - Launcher script
   - Commands: build-image, submit-cpu, submit-classifier, submit-llm
   - Supports: partition, reservation, nodelist, constraint parameters

7. **`slurm/attest-hook.sh`** - Optional attestation hook
   - Computes manifest hash (inputs + binaries + proofs + nonce)
   - Generates example attestation commands
   - Does NOT execute privileged tools automatically

#### Documentation (2 files)
7. **`docs/SLURM.md`** - Complete Slurm integration guide
   - Building images
   - Submitting jobs
   - Reading results
   - Attestation hooks
   - Troubleshooting

8. **`docs/decisions/0092-slurm-apptainer-cuda12-profile.md`** - Decision record
   - Context and rationale
   - Two CUDA profiles
   - Pass criteria
   - Alternatives considered

#### Updated Files (3 files)
10. **`README.md`** - Added Slurm quickstart section
11. **`AGENTS.md`** - Added note about Slurm support
12. **`CHANGELOG.md`** - Added entry for this feature

## How to Run Each Job

### 1. Build Container Image

```bash
cd slurm

# CUDA 13.1 (for driver 580+, compatible with HF evidence)
./hallmark-slurm.sh build-image --profile cuda13 --output hallmark-cuda13.sif

# CUDA 12.8 (for driver 570+, TDX nodes)
./hallmark-slurm.sh build-image --profile cuda12 --output hallmark-cuda12.sif
```

**Requirements**: Apptainer, network access, ~10GB disk space

### 2. CPU Smoke Test

```bash
./hallmark-slurm.sh submit-cpu \
  --partition cpu \
  --container hallmark-cuda13.sif \
  --work-dir /data/$USER/hallmark \
  --source /path/to/hallmark/repo
```

**Optional**: `--reservation NAME`, `--constraint VALUE`

**Outputs**: 
- `cpu-smoke.log`
- `job-info.txt`
- `target/` directory with built binaries

**Expected runtime**: 30-60 minutes
**Pass criteria**: All three targets build successfully

### 3. Classifier GPU Job

```bash
./hallmark-slurm.sh submit-classifier \
  --partition gpu \
  --container hallmark-cuda13.sif \
  --work-dir /data/$USER/hallmark \
  --prepared /data/$USER/prepared \
  --native-pin <hex-pin> \
  --source-dir /data/$USER/source
```

**Optional**: `--build-dir PATH` (reuse CPU build)

**Outputs**:
- `classifier-gpu.log`
- `run-record.json` (job metadata)
- `nvidia-smi-start.txt`, `nvidia-smi-end.txt`
- 54 proof files (9 cases × 2 backends × 3 iterations)
- Verification logs
- 378 public mutation rejections

**Expected runtime**: 1-2 hours
**Pass criteria**: 
- All 54 proofs verify
- Zero CPU constraint fallback
- All mutations reject

### 4. LLM GPU Job

```bash
./hallmark-slurm.sh submit-llm \
  --partition gpu \
  --container hallmark-cuda13.sif \
  --work-dir /data/$USER/hallmark \
  --llm-run /data/$USER/llm-e2e-xyz \
  --credit-balance 10.00
```

**Optional**: `--build-run PATH` (reuse build), `--max-cost N`

**Outputs**:
- `llm-gpu.log`
- `run-record.json`
- `nvidia-smi-start.txt`, `nvidia-smi-end.txt`
- `binary-hashes.txt` (SHA-256 of provers)
- 23 proof files per backend (46 total)
- Full grid verification logs

**Expected runtime**: 2-3 hours
**Pass criteria**:
- All 23 segments verify
- All 22 links verify
- Zero CPU constraint fallback
- Proof bytes match published proofs (CUDA 13.1 only)

## What Could Be Verified Without GPU

✅ **Completed**:
- Shell script syntax validation (`bash -n` passed)
- Apptainer definition file format
- Documentation completeness
- No hardcoded cluster/organization names
- Generic path structure
- Worker entry point compatibility

## What Could NOT Be Verified Without GPU

❌ **Not Tested**:
- Container image build (requires Apptainer + network)
- CPU smoke test execution
- GPU job execution
- Actual proof generation
- CUDA 12.8 numeric equivalence to CUDA 13.1
- Attestation hook execution
- Run record generation

## CUDA Version Information

### Existing Pinned Image (CUDA 13.x)
- Image: `nvidia/cuda@sha256:e542739fcaa4f45da5add8c4cf5769783a61628b2518304a5bbe4ace468b8c8f`
- CUDA version: **13.x** (per published benchmarks with driver 580.178.04; exact version unconfirmed from image manifest)
- Evidence: Used in published GPU benchmarks with driver 580.178.04
- References: docs/REFERENCE-RUN.md, research/STATE.md, docs/GPU-BENCHMARK.md
- Status: Validated on H200 with published proof bytes

### New Profile (CUDA 12.8)
- Image: `nvidia/cuda@sha256:24c8e3581ea6330038b0d374920721983312627f8adbfcf390bdb4b399d280ed`
- CUDA version: **12.8.1**
- Tag: `nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04`
- Driver requirement: 570.x or later
- Status: **Not yet validated on actual hardware**
- Purpose: Enable TDX nodes with driver 570.211.01

## Key Design Decisions

1. **Two CUDA profiles** instead of one
   - Preserves existing HF evidence (CUDA 13.x, driver 580.x)
   - Enables older drivers including TDX (CUDA 12.8, driver 570.x)

2. **Generic templates** with no hardcoded details
   - All cluster-specific parameters are arguments
   - No organization/company/hostname in code or docs

3. **Same worker entry points** as HF path
   - Reuses `scripts/run_llm_gpu.py` and `scripts/run_classifier_gpu.py`
   - Maintains compatibility with existing evidence

4. **Optional attestation hooks** (off by default)
   - TDX quote generation documented
   - GPU attestation documented
   - No privileged tools executed automatically

5. **Run records** with same shape as HF receipts
   - Commit hash, image digest, CUDA version, driver
   - nvidia-smi output, scontrol job info
   - Binary SHA-256 hashes, timers

## Pull Request

- **URL**: https://github.com/AbdelStark/hallmark/pull/181
- **Branch**: `cursor/slurm-apptainer-support-57f8`
- **Status**: Open, awaiting review
- **Commit**: b772d99

## Next Steps (After PR Merge)

1. **Test on actual Slurm cluster**:
   - Build both container images
   - Run CPU smoke test
   - Run classifier GPU job
   - Run LLM GPU job
   - Validate CUDA 12.8 numeric equivalence

2. **Document actual results**:
   - Record container build times and digests
   - Compare CUDA 12.8 proof bytes with CUDA 13.1
   - Update decision record with test outcomes

3. **Optional: Enable attestation**:
   - Test TDX quote generation on confidential VMs
   - Test GPU attestation with nvattest
   - Document actual attestation workflow

## Limitations and Future Work

### Current Limitations
- CUDA 12.8 profile not validated on hardware
- No multi-node or distributed GPU support
- No automatic driver version detection
- No cluster-specific accounting integration
- Attestation hooks documented but not executed

### Future Enhancements
- Dynamic CUDA profile selection based on driver
- MPI/multi-GPU support for larger models
- Integration with cluster accounting systems
- Automated attestation verification
- Performance comparison across clusters
- Support for additional GPU architectures (sm_80, etc.)

## Security Notes

- Containers run as user (no root required)
- Source mounted read-only
- Work directory is user-owned persistent storage
- No secrets in container images
- Attestation requires explicit opt-in
- No automatic external network calls from jobs
- No hardcoded credentials or tokens

## References

- Decision record: docs/decisions/0092-slurm-apptainer-cuda12-profile.md
- Slurm guide: docs/SLURM.md
- GPU benchmark: docs/GPU-BENCHMARK.md
- Reference run: docs/REFERENCE-RUN.md
- Existing evidence: research/STATE.md
