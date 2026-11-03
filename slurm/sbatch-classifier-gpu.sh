#!/bin/bash
#SBATCH --job-name=hallmark-classifier-gpu
#SBATCH --partition=__PARTITION__
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=180G
#SBATCH --gres=gpu:1
#SBATCH --time=03:00:00
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err

set -euo pipefail

CONTAINER_IMAGE="${CONTAINER_IMAGE:?CONTAINER_IMAGE must be set}"
WORK_DIR="${WORK_DIR:?WORK_DIR must be set}"
HALLMARK_SOURCE="${HALLMARK_SOURCE:?HALLMARK_SOURCE must be set}"
PREPARED_DIR="${PREPARED_DIR:?PREPARED_DIR must be set}"
NATIVE_PIN="${NATIVE_PIN:?NATIVE_PIN must be set}"
SOURCE_DIR="${SOURCE_DIR:?SOURCE_DIR must be set}"
CPU_BUILD_DIR="${CPU_BUILD_DIR:-}"

OUTPUT_DIR="${WORK_DIR}/classifier-gpu-${SLURM_JOB_ID}"
mkdir -p "${OUTPUT_DIR}"

cd "${OUTPUT_DIR}"

echo "=== Hallmark Classifier GPU Benchmark ==="
echo "Job ID: ${SLURM_JOB_ID}"
echo "Container: ${CONTAINER_IMAGE}"
echo "Work directory: ${WORK_DIR}"
echo "Output directory: ${OUTPUT_DIR}"
echo "Prepared directory: ${PREPARED_DIR}"
echo "Native pin: ${NATIVE_PIN}"
echo "Source directory: ${SOURCE_DIR}"
echo "CPU build directory: ${CPU_BUILD_DIR:-<not provided>}"
echo "Started: $(date -Iseconds)"

START_TIME=$(date +%s)

exec > >(tee -a classifier-gpu.log) 2>&1

nvidia-smi -q > nvidia-smi-start.txt
scontrol show job ${SLURM_JOB_ID} > job-info.txt

CUDA_VERSION=$(nvcc --version | grep -oP 'release \K[0-9.]+' || echo "unknown")
DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)

echo "CUDA version: ${CUDA_VERSION}"
echo "Driver version: ${DRIVER_VERSION}"

BUILD_ARGS=""
if [ -n "${CPU_BUILD_DIR}" ]; then
    BUILD_ARGS="--build-run ${CPU_BUILD_DIR}"
fi

apptainer exec --nv \
    --pwd /work \
    --bind "${HALLMARK_SOURCE}:/work/hallmark:ro" \
    --bind "${PREPARED_DIR}:/work/prepared:ro" \
    --bind "${SOURCE_DIR}:/work/source:ro" \
    --bind "${OUTPUT_DIR}:/work/output" \
    ${CPU_BUILD_DIR:+--bind "${CPU_BUILD_DIR}:/work/cpu-build:ro"} \
    --env RAYON_NUM_THREADS=4 \
    --env OMP_NUM_THREADS=1 \
    --env OPENBLAS_NUM_THREADS=1 \
    --env VECLIB_MAXIMUM_THREADS=1 \
    --env HALLMARK_EXPECTED_GPU=H100 \
    "${CONTAINER_IMAGE}" \
    bash -c "
        set -euo pipefail
        cd /work/hallmark
        
        echo '=== Run Classifier GPU Benchmark ==='
        python3 scripts/run_classifier_gpu.py \
            --prepared /work/prepared \
            --native-preparation-pin '${NATIVE_PIN}' \
            --source /work/source \
            --credit-balance-usd 10.00 \
            --gpu-flavor h200 \
            ${BUILD_ARGS} || { echo 'Classifier GPU benchmark failed'; exit 1; }
        
        echo '=== Classifier GPU Benchmark Complete ==='
        date -Iseconds
    "

EXIT_CODE=$?

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo "Completed: $(date -Iseconds)"
echo "Elapsed time: ${ELAPSED} seconds"
echo "Exit code: ${EXIT_CODE}"

nvidia-smi -q > nvidia-smi-end.txt

{
    echo "{"
    echo "  \"schema_id\": \"hallmark.slurm-classifier-gpu-result/1\","
    echo "  \"job_id\": \"${SLURM_JOB_ID}\","
    echo "  \"exit_code\": ${EXIT_CODE},"
    echo "  \"elapsed_seconds\": ${ELAPSED},"
    echo "  \"cuda_version\": \"${CUDA_VERSION}\","
    echo "  \"driver_version\": \"${DRIVER_VERSION}\","
    echo "  \"completed_at\": \"$(date -Iseconds)\""
    echo "}"
} > run-record.json

exit ${EXIT_CODE}
