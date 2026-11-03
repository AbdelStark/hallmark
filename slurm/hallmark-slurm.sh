#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HALLMARK_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

show_usage() {
    cat <<EOF
Usage: $0 <command> [options]

Commands:
  build-image       Build the Apptainer image
  submit-cpu        Submit CPU smoke test job
  submit-classifier Submit classifier GPU job
  submit-llm        Submit LLM GPU job

Build image options:
  --profile PROFILE   Image profile: cuda12.9 or cuda12.8 (default: cuda12.9)
  --output PATH       Output image path (default: ./hallmark-PROFILE.sif)

Submit CPU options:
  --partition NAME    Slurm partition (required)
  --container PATH    Path to container image (required)
  --work-dir PATH     Work directory (default: /data/\$USER/hallmark)
  --source PATH       Path to Hallmark source (default: current directory)
  --reservation NAME  Slurm reservation (optional)
  --constraint VALUE  Slurm constraint (optional)

Submit classifier options:
  (same as CPU, plus:)
  --prepared PATH     Path to prepared directory (required)
  --native-pin PIN    Native preparation pin (required)
  --source-dir PATH   Path to source directory (required)
  --build-dir PATH    Path to CPU build directory (optional)

Submit LLM options:
  (same as CPU, plus:)
  --llm-run PATH      Path to LLM run directory (required)
  --credit-balance N  Credit balance in USD (required)
  --max-cost N        Maximum cost in USD (default: 5.00)
  --build-run PATH    Path to build run directory (optional)

Examples:
  # Build CUDA 12.8 image
  $0 build-image --profile cuda12.8 --output hallmark-cuda12.8.sif

  # Submit CPU smoke test
  $0 submit-cpu --partition cpu --container hallmark-cuda12.9.sif

  # Submit classifier GPU job
  $0 submit-classifier --partition gpu --container hallmark-cuda12.9.sif \\
      --prepared /data/user/prepared --native-pin abc123 \\
      --source-dir /data/user/source

  # Submit LLM GPU job
  $0 submit-llm --partition gpu --container hallmark-cuda12.9.sif \\
      --llm-run /data/user/llm-e2e-xyz --credit-balance 10.00
EOF
}

build_image() {
    local profile="cuda12.9"
    local output=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --profile)
                profile="$2"
                shift 2
                ;;
            --output)
                output="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1" >&2
                exit 1
                ;;
        esac
    done
    
    if [[ ! "$profile" =~ ^(cuda12\.8|cuda12\.9)$ ]]; then
        echo "Error: Invalid profile. Must be cuda12.8 or cuda12.9" >&2
        exit 1
    fi
    
    if [ -z "$output" ]; then
        output="hallmark-${profile}.sif"
    fi
    
    local def_file="${SCRIPT_DIR}/apptainer-${profile}.def"
    
    if [ ! -f "$def_file" ]; then
        echo "Error: Definition file not found: $def_file" >&2
        exit 1
    fi
    
    echo "Building Apptainer image: $output"
    echo "Profile: $profile"
    echo "Definition: $def_file"
    
    apptainer build "$output" "$def_file"
    
    echo "Image built successfully: $output"
    echo "Image digest:"
    sha256sum "$output"
}

submit_cpu() {
    local partition=""
    local container=""
    local work_dir="/data/${USER}/hallmark"
    local source="${HALLMARK_ROOT}"
    local reservation=""
    local constraint=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --partition) partition="$2"; shift 2 ;;
            --container) container="$2"; shift 2 ;;
            --work-dir) work_dir="$2"; shift 2 ;;
            --source) source="$2"; shift 2 ;;
            --reservation) reservation="$2"; shift 2 ;;
            --constraint) constraint="$2"; shift 2 ;;
            *) echo "Unknown option: $1" >&2; exit 1 ;;
        esac
    done
    
    if [ -z "$partition" ] || [ -z "$container" ]; then
        echo "Error: --partition and --container are required" >&2
        exit 1
    fi
    
    local sbatch_file=$(mktemp)
    sed "s|__PARTITION__|${partition}|g" "${SCRIPT_DIR}/sbatch-cpu-smoke.sh" > "$sbatch_file"
    
    local sbatch_args=()
    [ -n "$reservation" ] && sbatch_args+=(--reservation="$reservation")
    [ -n "$constraint" ] && sbatch_args+=(--constraint="$constraint")
    
    CONTAINER_IMAGE="$container" \
    WORK_DIR="$work_dir" \
    HALLMARK_SOURCE="$source" \
    sbatch "${sbatch_args[@]}" "$sbatch_file"
    
    rm "$sbatch_file"
}

submit_classifier() {
    local partition=""
    local container=""
    local work_dir="/data/${USER}/hallmark"
    local source="${HALLMARK_ROOT}"
    local prepared=""
    local native_pin=""
    local source_dir=""
    local build_dir=""
    local reservation=""
    local constraint=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --partition) partition="$2"; shift 2 ;;
            --container) container="$2"; shift 2 ;;
            --work-dir) work_dir="$2"; shift 2 ;;
            --source) source="$2"; shift 2 ;;
            --prepared) prepared="$2"; shift 2 ;;
            --native-pin) native_pin="$2"; shift 2 ;;
            --source-dir) source_dir="$2"; shift 2 ;;
            --build-dir) build_dir="$2"; shift 2 ;;
            --reservation) reservation="$2"; shift 2 ;;
            --constraint) constraint="$2"; shift 2 ;;
            *) echo "Unknown option: $1" >&2; exit 1 ;;
        esac
    done
    
    if [ -z "$partition" ] || [ -z "$container" ] || [ -z "$prepared" ] || \
       [ -z "$native_pin" ] || [ -z "$source_dir" ]; then
        echo "Error: --partition, --container, --prepared, --native-pin, and --source-dir are required" >&2
        exit 1
    fi
    
    local sbatch_file=$(mktemp)
    sed "s|__PARTITION__|${partition}|g" "${SCRIPT_DIR}/sbatch-classifier-gpu.sh" > "$sbatch_file"
    
    local sbatch_args=()
    [ -n "$reservation" ] && sbatch_args+=(--reservation="$reservation")
    [ -n "$constraint" ] && sbatch_args+=(--constraint="$constraint")
    
    CONTAINER_IMAGE="$container" \
    WORK_DIR="$work_dir" \
    HALLMARK_SOURCE="$source" \
    PREPARED_DIR="$prepared" \
    NATIVE_PIN="$native_pin" \
    SOURCE_DIR="$source_dir" \
    CPU_BUILD_DIR="$build_dir" \
    sbatch "${sbatch_args[@]}" "$sbatch_file"
    
    rm "$sbatch_file"
}

submit_llm() {
    local partition=""
    local container=""
    local work_dir="/data/${USER}/hallmark"
    local source="${HALLMARK_ROOT}"
    local llm_run=""
    local credit_balance=""
    local max_cost="5.00"
    local build_run=""
    local reservation=""
    local constraint=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --partition) partition="$2"; shift 2 ;;
            --container) container="$2"; shift 2 ;;
            --work-dir) work_dir="$2"; shift 2 ;;
            --source) source="$2"; shift 2 ;;
            --llm-run) llm_run="$2"; shift 2 ;;
            --credit-balance) credit_balance="$2"; shift 2 ;;
            --max-cost) max_cost="$2"; shift 2 ;;
            --build-run) build_run="$2"; shift 2 ;;
            --reservation) reservation="$2"; shift 2 ;;
            --constraint) constraint="$2"; shift 2 ;;
            *) echo "Unknown option: $1" >&2; exit 1 ;;
        esac
    done
    
    if [ -z "$partition" ] || [ -z "$container" ] || [ -z "$llm_run" ] || \
       [ -z "$credit_balance" ]; then
        echo "Error: --partition, --container, --llm-run, and --credit-balance are required" >&2
        exit 1
    fi
    
    local sbatch_file=$(mktemp)
    sed "s|__PARTITION__|${partition}|g" "${SCRIPT_DIR}/sbatch-llm-gpu.sh" > "$sbatch_file"
    
    local sbatch_args=()
    [ -n "$reservation" ] && sbatch_args+=(--reservation="$reservation")
    [ -n "$constraint" ] && sbatch_args+=(--constraint="$constraint")
    
    CONTAINER_IMAGE="$container" \
    WORK_DIR="$work_dir" \
    HALLMARK_SOURCE="$source" \
    LLM_RUN="$llm_run" \
    CREDIT_BALANCE="$credit_balance" \
    MAX_COST="$max_cost" \
    BUILD_RUN="$build_run" \
    sbatch "${sbatch_args[@]}" "$sbatch_file"
    
    rm "$sbatch_file"
}

if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

COMMAND=$1
shift

case $COMMAND in
    build-image)
        build_image "$@"
        ;;
    submit-cpu)
        submit_cpu "$@"
        ;;
    submit-classifier)
        submit_classifier "$@"
        ;;
    submit-llm)
        submit_llm "$@"
        ;;
    help|-h|--help)
        show_usage
        ;;
    *)
        echo "Unknown command: $COMMAND" >&2
        show_usage
        exit 1
        ;;
esac
