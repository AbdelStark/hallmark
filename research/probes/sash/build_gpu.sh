set -euo pipefail
# SIMD stays pristine; CUDA installs generated constraints and forbids fallback.
bash /persist/build_cpu.sh
python3 - <<'PY'
import hashlib, json
from pathlib import Path
root = Path('/persist')
for name, pin in json.loads((root / 'protocol.json').read_text())['inputs'].items():
    with (root / name).open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == pin
PY
exec > >(tee -a /persist/worker.log) 2>&1
trap 'rc=$?; printf "{\"exit_code\":%s}\n" "$rc" > /persist/exit.json' EXIT
cd /work/source
export PATH=/root/.cargo/bin:$PATH
export CARGO_BUILD_JOBS=4 CUDAHOSTCXX=/usr/bin/g++
python3 /persist/generate_kernels.py
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
python3 - <<'PY'
import hashlib, json
from pathlib import Path
root = Path('/persist')
p = root / 'kernel-build.json'
report = json.loads(p.read_text())
report['binaries'] = {}
for name in ('zk-prover-simd', 'zk-prover-cuda'):
    with (root / name).open('rb') as stream:
        report['binaries'][name] = hashlib.file_digest(stream, 'sha256').hexdigest()
p.write_text(json.dumps(report, indent=2) + '\n')
PY
printf 'Verified native sm_90 generated-constraint binary; CPU fallback is forbidden.\n'
