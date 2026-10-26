set -euo pipefail
# Build both backends from the same unchanged source; no generated-kernel install.
bash /persist/build_cpu.sh
exec > >(tee -a /persist/worker.log) 2>&1
trap 'rc=$?; printf "{\"exit_code\":%s}\n" "$rc" > /persist/exit.json' EXIT
cd /work/source
export PATH=/root/.cargo/bin:$PATH
export CARGO_BUILD_JOBS=4 CUDAHOSTCXX=/usr/bin/g++
printf 'set(CMAKE_CUDA_ARCHITECTURES "90")\n' > /work/gpu-architecture.cmake
export CMAKE_TOOLCHAIN_FILE=/work/gpu-architecture.cmake
# Isolate CUDA's native target from the SIMD build's cached sm_89 library.
/usr/bin/time -v cargo build --release --locked -j 4 -p zk-prover --features cuda --target-dir /work/cuda-target
cp /work/cuda-target/release/zk-prover /persist/zk-prover-cuda
sha256sum /persist/zk-prover-cuda > /persist/cuda.sha256
cuobjdump --list-elf /persist/zk-prover-cuda > /persist/cuda-elf.txt
cuobjdump --list-ptx /persist/zk-prover-cuda > /persist/cuda-ptx.txt
python3 - <<'PY'
from pathlib import Path
native = Path('/persist/cuda-elf.txt').read_text()
assert 'sm_90' in native and 'sm_89' not in native, 'unexpected native CUDA target'
PY
cp prover/src/cudakernels.rs prover/src/gencudakernels.rs /persist/
printf 'Verified native sm_90 CUDA binary; witness/AIR generation stays on the host.\n'
