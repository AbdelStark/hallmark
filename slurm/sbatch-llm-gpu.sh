#!/bin/bash
#SBATCH --job-name=hallmark-llm-gpu
#SBATCH --partition=__PARTITION__
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=210G
#SBATCH --gres=gpu:1
#SBATCH --time=04:00:00
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err

set -euo pipefail

CONTAINER_IMAGE="${CONTAINER_IMAGE:?CONTAINER_IMAGE must be set}"
WORK_DIR="${WORK_DIR:?WORK_DIR must be set}"
HALLMARK_SOURCE="${HALLMARK_SOURCE:?HALLMARK_SOURCE must be set}"
LLM_RUN="${LLM_RUN:?LLM_RUN must be set}"
CREDIT_BALANCE="${CREDIT_BALANCE:?CREDIT_BALANCE must be set}"
MAX_COST="${MAX_COST:-5.00}"
BUILD_RUN="${BUILD_RUN:-}"

OUTPUT_DIR="${WORK_DIR}/llm-gpu-${SLURM_JOB_ID}"
mkdir -p "${OUTPUT_DIR}"

cd "${OUTPUT_DIR}"

echo "=== Hallmark LLM GPU Benchmark ==="
echo "Job ID: ${SLURM_JOB_ID}"
echo "Container: ${CONTAINER_IMAGE}"
echo "Work directory: ${WORK_DIR}"
echo "Output directory: ${OUTPUT_DIR}"
echo "LLM run: ${LLM_RUN}"
echo "Credit balance: ${CREDIT_BALANCE}"
echo "Max cost: ${MAX_COST}"
echo "Build run: ${BUILD_RUN:-<not provided>}"
echo "Started: $(date -Iseconds)"

START_TIME=$(date +%s)

exec > >(tee -a llm-gpu.log) 2>&1

nvidia-smi -q > nvidia-smi-start.txt
scontrol show job ${SLURM_JOB_ID} > job-info.txt

CUDA_VERSION=$(nvcc --version | grep -oP 'release \K[0-9.]+' || echo "unknown")
DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)

echo "CUDA version: ${CUDA_VERSION}"
echo "Driver version: ${DRIVER_VERSION}"
echo "GPU: ${GPU_NAME}"

BUILD_ARGS=""
if [ -n "${BUILD_RUN}" ]; then
    BUILD_ARGS="--build-run ${BUILD_RUN}"
fi

apptainer exec --nv \
    --pwd /work \
    --bind "${HALLMARK_SOURCE}:/work/hallmark:ro" \
    --bind "${LLM_RUN}:/work/llm-run:ro" \
    --bind "${OUTPUT_DIR}:/work/output" \
    ${BUILD_RUN:+--bind "${BUILD_RUN}:/work/build-run:ro"} \
    --env RAYON_NUM_THREADS=4 \
    --env OMP_NUM_THREADS=1 \
    --env OPENBLAS_NUM_THREADS=1 \
    --env VECLIB_MAXIMUM_THREADS=1 \
    "${CONTAINER_IMAGE}" \
    bash -c "
        set -euo pipefail
        cd /work/hallmark
        
        echo '=== Run LLM GPU Benchmark ==='
        python3 scripts/run_llm_gpu.py \
            --llm-run /work/llm-run \
            --credit-balance-usd '${CREDIT_BALANCE}' \
            --max-cost-usd '${MAX_COST}' \
            ${BUILD_ARGS} || { echo 'LLM GPU benchmark failed'; exit 1; }
        
        echo '=== LLM GPU Benchmark Complete ==='
        date -Iseconds
    "

EXIT_CODE=$?

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo "Completed: $(date -Iseconds)"
echo "Elapsed time: ${ELAPSED} seconds"
echo "Exit code: ${EXIT_CODE}"

nvidia-smi -q > nvidia-smi-end.txt

for binary in /work/output/build/retained/zk-prover-simd /work/output/build/retained/zk-prover-cuda; do
    if [ -f "$binary" ]; then
        sha256sum "$binary" >> binary-hashes.txt
    fi
done

{
    echo "{"
    echo "  \"schema_id\": \"hallmark.slurm-llm-gpu-result/1\","
    echo "  \"job_id\": \"${SLURM_JOB_ID}\","
    echo "  \"exit_code\": ${EXIT_CODE},"
    echo "  \"elapsed_seconds\": ${ELAPSED},"
    echo "  \"cuda_version\": \"${CUDA_VERSION}\","
    echo "  \"driver_version\": \"${DRIVER_VERSION}\","
    echo "  \"gpu_name\": \"${GPU_NAME}\","
    echo "  \"completed_at\": \"$(date -Iseconds)\""
    echo "}"
} > run-record.json

exit ${EXIT_CODE}
