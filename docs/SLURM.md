# Running Hallmark on Slurm with Apptainer

This guide explains how to run Hallmark's GPU workloads (TinyLlama LLM prover via SASH and classifier proofs via STWO) on a generic Slurm cluster with Apptainer containers.

## Requirements

### Cluster Environment

- Slurm workload manager
- Apptainer (formerly Singularity) on compute nodes
- NVIDIA GPUs with CUDA support on GPU nodes
- No sudo/root access required
- Per-user storage (e.g., `/data/$USER`)

### Target Hardware

- **CPU nodes**: For smoke tests, validation, and kernel builds
- **GPU nodes**: For CUDA proving workloads
  - H100 NVL or H100 SXM recommended (sm_90)
  - NVIDIA driver 570.x or later (supports CUDA 12.8+)
  - Driver 580.x or later (supports CUDA 13.1)

### Tested Configurations

This implementation has been tested with:
- H100 NVL with Intel TDX confidential VM
  - NVIDIA driver 570.211.01 (CUDA 12.8 compatible)
  - CUDA 12.8.1 container profile
- H100 SXM (sm_90)
  - NVIDIA driver 580.x
  - CUDA 13.1 container profile (existing HF path)

## Container Profiles

Two Apptainer definition files are provided:

### CUDA 13.1 Profile (cuda13)

- Based on `nvidia/cuda@sha256:e542739fcaa4f45da5add8c4cf5769783a61628b2518304a5bbe4ace468b8c8f`
- CUDA version: 13.1
- Requires driver 580.x or later
- Compatible with existing HF Jobs workflow
- Located at: `slurm/apptainer-cuda13.def`

### CUDA 12.8 Profile (cuda12)

- Based on `nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04`
- CUDA version: 12.8.1
- Requires driver 570.x or later
- Compatible with older drivers including TDX nodes
- Located at: `slurm/apptainer-cuda12.def`

Both profiles include:
- Rust nightly-2025-07-14 with rustup 1.29.1
- uv 0.9.18
- CPython 3.12
- CUDA toolkit and development libraries
- Build tools (gcc, cmake, git, etc.)

## Building Container Images

### Build Command

```bash
cd slurm

# Build CUDA 13.1 image (default)
./hallmark-slurm.sh build-image --profile cuda13 --output hallmark-cuda13.sif

# Build CUDA 12.8 image (for older drivers)
./hallmark-slurm.sh build-image --profile cuda12 --output hallmark-cuda12.sif
```

The build process:
1. Downloads the base CUDA image from Docker Hub
2. Installs Rust toolchain and uv
3. Creates an Apptainer SIF image
4. Outputs the image digest (SHA-256)

### Build Location

Build the image on a node with:
- Internet access (to download base image and tools)
- Sufficient disk space (~10 GB)
- Apptainer build permissions

Note: Some clusters require building images on login nodes or dedicated build nodes, not compute nodes.

## Job Workflows

### 1. CPU Smoke Test

Validates data, checks conformance, and builds the Circle prover (CPU only). This must complete successfully before running GPU jobs.

```bash
./hallmark-slurm.sh submit-cpu \
  --partition cpu \
  --container hallmark-cuda13.sif \
  --work-dir /data/$USER/hallmark \
  --source /path/to/hallmark/repo
```

Optional parameters:
- `--reservation NAME`: Use a specific Slurm reservation
- `--constraint VALUE`: Add node constraint (e.g., `--constraint tdx`)

This job:
- Runs `make validate-data`
- Runs `make check-conformance`
- Runs `make circle-build` (CPU prover)
- Copies built binaries to output directory
- Generates: `cpu-smoke.log`, `job-info.txt`, target directory

Expected runtime: ~30-60 minutes
Expected memory: ~32 GB

### 2. Classifier GPU Job

Runs the classifier proof campaign with CPU and CUDA backends.

```bash
./hallmark-slurm.sh submit-classifier \
  --partition gpu \
  --container hallmark-cuda13.sif \
  --work-dir /data/$USER/hallmark \
  --prepared /data/$USER/prepared \
  --native-pin abc123def456 \
  --source-dir /data/$USER/source \
  --build-dir /data/$USER/cpu-build
```

Required parameters:
- `--prepared PATH`: Directory with prepared classifier inputs
- `--native-pin PIN`: Native preparation pin (hex string)
- `--source-dir PATH`: Source directory for classifier

Optional parameters:
- `--build-dir PATH`: Reuse CPU build from previous job
- `--reservation NAME`: Slurm reservation
- `--constraint VALUE`: Node constraint

This job:
- Reconstructs native witnesses
- Builds or reuses CPU/CUDA provers
- Runs 3 iterations × 9 cases × 2 backends = 54 proofs
- Verifies all proofs and rejects mutations
- Zero CPU constraint fallbacks required

Generates:
- `classifier-gpu.log`
- `run-record.json` (job metadata)
- `nvidia-smi-start.txt`, `nvidia-smi-end.txt`
- `job-info.txt` (Slurm job details)
- Per-case proof files and verification logs

Expected runtime: ~1-2 hours
Expected memory: ~180 GB
Expected GPU memory: ~18 GB

### 3. LLM GPU Job

Runs the TinyLlama proving workflow with SIMD and CUDA backends.

```bash
./hallmark-slurm.sh submit-llm \
  --partition gpu \
  --container hallmark-cuda13.sif \
  --work-dir /data/$USER/hallmark \
  --llm-run /data/$USER/llm-e2e-xyz \
  --credit-balance 10.00 \
  --max-cost 5.00 \
  --build-run /data/$USER/llm-gpu-build
```

Required parameters:
- `--llm-run PATH`: Completed LLM e2e run directory
- `--credit-balance N`: Credit balance in USD (for compatibility)

Optional parameters:
- `--max-cost N`: Maximum cost in USD (default: 5.00)
- `--build-run PATH`: Reuse build from previous run
- `--reservation NAME`: Slurm reservation
- `--constraint VALUE`: Node constraint

This job:
- Validates enrolled witness archive
- Builds or reuses SIMD/CUDA provers with generated kernels
- Proves all 23 TinyLlama segments on both backends
- Verifies grid and rejects mutations
- Zero CPU constraint fallback required

Generates:
- `llm-gpu.log`
- `run-record.json`
- `nvidia-smi-start.txt`, `nvidia-smi-end.txt`
- `job-info.txt`
- `binary-hashes.txt` (SHA-256 of provers)
- 23 proof files per backend
- Full grid verification logs

Expected runtime: ~2-3 hours
Expected memory: ~210 GB
Expected GPU memory: ~68 GB

## Reading Results

### Job Output Files

Each job produces:
- `<jobname>_<jobid>.out`: Stdout log
- `<jobname>_<jobid>.err`: Stderr log
- `<workdir>/<jobtype>-<jobid>/`: Output directory with:
  - `*.log`: Main job log with timestamps
  - `run-record.json`: Job metadata and results
  - `job-info.txt`: Slurm job details (`scontrol show job`)
  - `nvidia-smi*.txt`: GPU state snapshots
  - Proof files, verification logs, and binary hashes

### Run Record Schema

The `run-record.json` file contains:

```json
{
  "schema_id": "hallmark.slurm-*-result/1",
  "job_id": "12345",
  "exit_code": 0,
  "elapsed_seconds": 7200,
  "cuda_version": "12.8",
  "driver_version": "570.211.01",
  "gpu_name": "NVIDIA H100",
  "completed_at": "2026-11-03T12:00:00+00:00"
}
```

### Verification Commands

After a successful GPU job, verify proofs independently:

```bash
# Classifier proofs (example for one case)
research/probes/circle/target/release/circle-verify \
  <enrollment.json> <enrollment-sha256> \
  <public.json> <proof.json>

# LLM proofs (grid verification)
<output-dir>/build/retained/zk-prover-simd boundary-grid \
  --dir <proofs-dir> \
  --tags <comma-separated-tags> \
  --verify \
  --prompt <prompt_ids.json> \
  --verify-calibration <roots.json> \
  --expect-model-roots <roots.json> \
  --expect-pre-roots <roots.json> \
  --expect-layer-links 22 \
  --expect-token-links 0
```

### Monitoring Jobs

```bash
# Check job status
squeue -u $USER

# View job details
scontrol show job <jobid>

# View job output in real-time
tail -f <jobname>_<jobid>.out

# Cancel a job
scancel <jobid>
```

## Confidential Computing Support

For confidential computing nodes (e.g., Intel TDX), optional attestation hooks are available.

### Attestation Hook Points

The run record generation includes documented hook points for:

1. **TDX Quote with Report Data**
   - Compute manifest hash of inputs, binaries, proofs, and verifier nonce
   - Pass as report data to TDX quote generation tool
   - Example: `tdx-attest --report-data <manifest-hash>`

2. **NVIDIA GPU Attestation**
   - Use manifest hash as nonce for GPU attestation
   - Example: `nvattest --nonce <manifest-hash>`

### Enabling Attestation (Optional)

Attestation is **off by default** and requires:
1. Access to privileged attestation tools (`tdx-attest`, `nvattest`)
2. Appropriate node permissions
3. Manual integration into job scripts

To enable:
1. Modify the sbatch script to compute the manifest hash
2. Call attestation tools after proof generation
3. Append attestation results to `run-record.json`

Example manifest computation:

```bash
# Compute run manifest hash
manifest_hash=$(cat \
  <inputs-hash> \
  <binary-hashes> \
  <proof-hashes> \
  <verifier-nonce> \
  | sha256sum | cut -d' ' -f1)

# (Optional) Call TDX attestation
tdx-attest --report-data "$manifest_hash" > tdx-quote.bin

# (Optional) Call GPU attestation
nvattest --nonce "$manifest_hash" > gpu-attestation.json
```

**Important**: Do not call privileged tools without explicit authorization and proper security review.

## Troubleshooting

### Container Build Fails

- Check internet connectivity
- Verify Apptainer version supports Docker bootstrap
- Ensure sufficient disk space for build cache

### Job Fails with "CUDA driver version"

- Check `nvidia-smi` output on target nodes
- Use `cuda12` profile for driver 570.x
- Use `cuda13` profile for driver 580.x or later

### Job Fails with "CPU constraint fallback"

- GPU is not being used properly
- Check `--nv` flag is in `apptainer exec` command
- Verify `nvidia-smi` works inside container
- Check CUDA architecture matches GPU (sm_90 for H100)

### Memory Errors

- Increase `--mem` in sbatch script
- Check actual memory usage in `job-info.txt`
- Verify no memory leaks in profiler output

### Proof Verification Fails

- Compare binary hashes with published proofs
- Check for bit flips or memory corruption
- Verify input archive hash matches enrolled case
- Ensure no modifications to witness or enrollment

### Job Timeout

- Increase `--time` in sbatch script
- Check if build is included (use `--build-dir` to skip)
- Monitor actual runtime in previous jobs

## Differences from HF Jobs Path

| Aspect | HF Jobs | Slurm + Apptainer |
|--------|---------|-------------------|
| Scheduler | Hugging Face managed | Slurm |
| Container | Docker (nvidia/cuda) | Apptainer SIF |
| GPU allocation | HF flavor (h200, a100-large) | `--gres=gpu:1` |
| Storage | Temporary HF bucket | User-owned persistent storage |
| Networking | Outbound allowed | Cluster policy dependent |
| Attestation | Not supported | Optional TDX/GPU hooks |
| Cost tracking | HF billing | Cluster accounting |

The worker entry points (`scripts/run_llm_gpu.py`, `scripts/run_classifier_gpu.py`) remain the same. The Slurm path wraps them in sbatch templates with equivalent resource parameters.

## Version Information

- Rust toolchain: nightly-2025-07-14
- rustup: 1.29.1
- uv: 0.9.18
- Python: 3.12
- CUDA 13.1 profile: Based on published HF image digest
- CUDA 12.8 profile: nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04

## Security Notes

- Container runs as user (no root required)
- Source mounted read-only
- Work directory is user-owned persistent storage
- No secrets or credentials stored in container
- Attestation hooks require explicit opt-in
- No automatic external network calls

## See Also

- [GPU Benchmark Guide](GPU-BENCHMARK.md)
- [Reference Run Details](REFERENCE-RUN.md)
- [Classifier GPU Benchmark](CLASSIFIER-GPU-BENCHMARK.md)
- [Research State](../research/STATE.md)
