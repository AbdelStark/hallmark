#!/bin/bash
#SBATCH --job-name=hallmark-cpu-smoke
#SBATCH --partition=__PARTITION__
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err

set -euo pipefail

CONTAINER_IMAGE="${CONTAINER_IMAGE:?CONTAINER_IMAGE must be set}"
WORK_DIR="${WORK_DIR:?WORK_DIR must be set}"
HALLMARK_SOURCE="${HALLMARK_SOURCE:?HALLMARK_SOURCE must be set}"

OUTPUT_DIR="${WORK_DIR}/cpu-smoke-${SLURM_JOB_ID}"
mkdir -p "${OUTPUT_DIR}"

cd "${OUTPUT_DIR}"

echo "=== Hallmark CPU Smoke Test ==="
echo "Job ID: ${SLURM_JOB_ID}"
echo "Container: ${CONTAINER_IMAGE}"
echo "Work directory: ${WORK_DIR}"
echo "Output directory: ${OUTPUT_DIR}"
echo "Started: $(date -Iseconds)"

exec > >(tee -a cpu-smoke.log) 2>&1

apptainer exec \
    --pwd /work \
    --bind "${HALLMARK_SOURCE}:/work/hallmark:ro" \
    --bind "${OUTPUT_DIR}:/work/output" \
    --env RAYON_NUM_THREADS=4 \
    --env CARGO_BUILD_JOBS=4 \
    "${CONTAINER_IMAGE}" \
    bash -c '
        set -euo pipefail
        cd /work/hallmark
        
        echo "=== Validate Data ==="
        make validate-data || { echo "validate-data failed"; exit 1; }
        
        echo "=== Check Conformance ==="
        make check-conformance || { echo "check-conformance failed"; exit 1; }
        
        echo "=== Circle Build (CPU) ==="
        make circle-build || { echo "circle-build failed"; exit 1; }
        
        cp -r research/probes/circle/target /work/output/
        
        echo "=== CPU Smoke Test Complete ==="
        date -Iseconds
    '

EXIT_CODE=$?

echo "Completed: $(date -Iseconds)"
echo "Exit code: ${EXIT_CODE}"

nvidia-smi -q > "${OUTPUT_DIR}/nvidia-smi.txt" 2>&1 || echo "No GPU available (expected for CPU job)"
scontrol show job ${SLURM_JOB_ID} > "${OUTPUT_DIR}/job-info.txt"

exit ${EXIT_CODE}
