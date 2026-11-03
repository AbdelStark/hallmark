#!/bin/bash
# FlashProve worker for one HF job. Phase "build" (CPU host): upstream verifier/build.sh and
# prover/build.sh. Phase "prove" (sm_90 GPU host): upstream run_target_example.sh on the small
# synthetic-weight kit with the retained build. Upstream sources are unchanged; every upstream
# command runs as an ordinary account, as FlashProve's AGENTS.md requires.
set -euo pipefail
pin() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' /home/fp/in/source.json "$1"; }

if [ "${1:-}" = user ]; then
  cd /home/fp
  curl -fsSL --max-time 300 -o src.tar.gz "$(pin url)"
  echo "$(pin sha256)  src.tar.gz" | sha256sum -c -
  mkdir src && tar -xzf src.tar.gz -C src --strip-components=1 --no-same-owner && rm src.tar.gz
  # Upstream's documented compiler install (prover/docs/build.md#install-the-compiler).
  cuda=$HOME/cuda-13.2.86
  mkdir "$cuda"
  extras=$(pin cuda_toolkit)
  [ "$PHASE" = prove ] && extras='cuda-toolkit[cublas,cudart]==13.2.2' # runtime libraries only
  PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install -q --no-cache-dir --target "$cuda" "$extras"
  PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip list --path "$cuda" --format json > out/cuda-packages.json
  lib=$cuda/nvidia/cu13/lib
  if [ "$PHASE" = build ]; then
    for n in cublasLt cublas cudart; do ln -s "lib$n.so.13" "$lib/lib$n.so"; done
    mkdir "$lib/stubs"
    # The build host has no driver; the image's link stub stands in for libcuda.so at link time only.
    ln -s /usr/local/cuda/lib64/stubs/libcuda.so "$lib/stubs/libcuda.so"
    chmod -R go-w "$cuda"
    export PATH=$cuda/nvidia/cu13/bin:$PATH
    nvcc --version | tee out/nvcc.txt
    grep -q "$(pin nvcc_release)" out/nvcc.txt
    cd src
    /usr/bin/time -v verifier/build.sh > ../out/verifier-build.log 2>&1
    (cd prover && /usr/bin/time -v ./build.sh) > ../out/prover-build.log 2>&1
    tail -n 3 ../out/prover-build.log
    tar -C prover/build -czf ../out/hc.tar.gz hc
  else
    chmod -R go-w "$cuda"
    mkdir -p src/prover/build
    tar -xzf in/hc.tar.gz -C src/prover/build --no-same-owner
    (cd src/prover/build/hc && sha256sum cp_commit cp_prove cp_verify) > out/binaries.sha256
    grep -m1 -ow sha_ni /proc/cpuinfo > out/sha_ni.txt
    nvidia-smi --query-gpu=name,compute_cap,driver_version,memory.used,memory.total --format=csv,noheader > out/gpu.txt
    mkdir -m 700 work
    cd src
    status=0
    /usr/bin/time -v prover/examples/run_target_example.sh "$KIT" /home/fp/work/example > ../out/example.log 2>&1 || status=$?
    echo "$status" > ../out/example-status.txt
    w=/home/fp/work/example
    # Public files only: the secret key directory isk/, home/ and tmp/ stay on the worker.
    mkdir -p ../out/case/config ../out/case/ivk/leaf
    cp "$w"/config/* ../out/case/config/ || true
    cp "$w"/ivk/key.bin ../out/case/ivk/ || true
    cp "$w"/ivk/leaf/*.bin ../out/case/ivk/leaf/ || true
    cp "$w"/in/example.req "$w"/out/example.y "$w"/out/example.proof ../out/case/ || true
    cp "$w"/cp_commit.log "$w"/cp_prove.log "$w"/cp_verify.log ../out/ || true
    exit "$status"
  fi
  exit 0
fi

exec > >(tee /persist/worker.log) 2>&1
trap 'rc=$?; printf "{\"exit_code\":%s,\"seconds\":%s}\n" "$rc" "$SECONDS" > /persist/exit.json' EXIT
[ "$HALLMARK_FLASHPROVE_PHASE" = build ] || [ "$HALLMARK_FLASHPROVE_PHASE" = prove ]
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends python3 python3-pip curl ca-certificates make time util-linux >/dev/null
python3 - <<'PY'
import hashlib, json
from pathlib import Path
root = Path("/persist")
for name, pin in json.loads((root / "protocol.json").read_text())["inputs"].items():
    with (root / name).open("rb") as f:
        assert hashlib.file_digest(f, "sha256").hexdigest() == pin, name
PY
lscpu > /persist/lscpu.txt
free -b > /persist/memory.txt
useradd -m -s /bin/bash fp
install -d -o fp -g fp -m 700 /home/fp/in /home/fp/out
install -o fp -g fp -m 400 /persist/source.json /home/fp/in/
[ ! -e /persist/hc.tar.gz ] || install -o fp -g fp -m 400 /persist/hc.tar.gz /home/fp/in/
install -o fp -g fp -m 500 /persist/build_prover.sh /home/fp/job.sh
status=0
runuser -u fp -- env -i HOME=/home/fp PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  PHASE="$HALLMARK_FLASHPROVE_PHASE" KIT="${HALLMARK_FLASHPROVE_KIT:-}" bash /home/fp/job.sh user || status=$?
cp -R /home/fp/out/. /persist/
exit "$status"
