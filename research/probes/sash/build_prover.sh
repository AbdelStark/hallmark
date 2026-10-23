set -euo pipefail
mkdir -p /work /persist
exec > >(tee /persist/worker.log) 2>&1
trap 'rc=$?; printf "{\"exit_code\":%s,\"finished_unix\":%s}\n" "$rc" "$(date +%s)" > /persist/exit.json' EXIT
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends build-essential cmake curl ca-certificates git pkg-config python3 time
cd /work
curl -fLsS --max-time 120 "$SOURCE_URL" -o source.tar.gz
printf '%s  source.tar.gz\n' "$SOURCE_SHA256" | sha256sum -c -
mkdir source
tar -xzf source.tar.gz -C source --strip-components=1
cd source
printf '%s\n' "$SOURCE_COMMIT" > .source-commit
curl -fLsS --max-time 120 https://static.rust-lang.org/rustup/archive/1.29.1/x86_64-unknown-linux-gnu/rustup-init -o /work/rustup-init
curl -fLsS --max-time 120 https://static.rust-lang.org/rustup/archive/1.29.1/x86_64-unknown-linux-gnu/rustup-init.sha256 -o /work/rustup-init.sha256
(cd /work && sha256sum -c rustup-init.sha256)
chmod +x /work/rustup-init
/work/rustup-init -y --profile minimal --default-toolchain nightly-2025-07-14 --no-modify-path
export PATH=/root/.cargo/bin:$PATH
export CARGO_BUILD_JOBS=4 RAYON_NUM_THREADS=4 CUDAHOSTCXX=/usr/bin/g++
printf 'set(CMAKE_CUDA_ARCHITECTURES "89")\n' > /work/cuda-architecture.cmake
export CMAKE_TOOLCHAIN_FILE=/work/cuda-architecture.cmake
rustc --version
cargo --version
cmake --version
nvcc --version
dpkg-query -W > /persist/os-packages.txt
sha256sum Cargo.lock rust-toolchain.toml > /persist/input-hashes.txt
/usr/bin/time -v cargo build --release --locked -j 4
cp target/release/zk-prover /persist/zk-prover-simd
sha256sum /persist/zk-prover-simd > /persist/binary.sha256
/usr/bin/time -v target/release/zk-prover compose --round away --variants intsplit6 --table-bits 16 --s 32 --ctx 128 --hd 32 --head-groups 2,2 --nin 128 --nout 128 --residual-stream-a 32 --kmax 16 --synth-residual-stream --diagonal-block --ser-dir /persist/aligned-proof --ser-tag B4L0 > /persist/aligned.json
python3 - <<'PY'
import json
from pathlib import Path
v=json.loads(Path('/persist/aligned.json').read_text());p=v['result']['point']
assert p['accepts'] is True
assert p['proof_sha256'].startswith('db6d17a700c25457')
assert p['binding']['unbound']==[]
assert v['provenance']['unsound_skips']==[]
print('Aligned synthetic proof accepted; recorded digest matches; no open layer binding or skip.')
PY
/usr/bin/time -v cargo test --release --locked -j 4 --test synthetic_digest --test verify_shape_root --test model_tree_control -- --test-threads=1
printf 'All frozen Linux build gates passed. This is not an LLM response proof.\n'
