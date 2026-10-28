set -euo pipefail
mkdir -p /work/source
exec > >(tee /persist/worker.log) 2>&1
trap 'rc=$?; printf "{\"exit_code\":%s}\n" "$rc" > /persist/exit.json' EXIT
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends build-essential cmake curl ca-certificates git pkg-config python3 time
python3 - <<'PY'
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'/persist')
from reference_files import check_archive
root=Path('/persist')
for name,pin in json.loads((root/'protocol.json').read_text())['inputs'].items():
    with (root/name).open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==pin
check_archive(root/'source.tar.gz',json.loads((root/'source-inventory.json').read_text()),Path('/work/source/tree'))
PY
curl -fLsS --max-time 120 https://static.rust-lang.org/rustup/archive/1.29.1/x86_64-unknown-linux-gnu/rustup-init -o /work/rustup-init
curl -fLsS --max-time 120 https://static.rust-lang.org/rustup/archive/1.29.1/x86_64-unknown-linux-gnu/rustup-init.sha256 -o /work/rustup-init.sha256
(cd /work && sha256sum -c rustup-init.sha256)
chmod +x /work/rustup-init
/work/rustup-init -y --profile minimal --default-toolchain nightly-2025-07-14 --no-modify-path
export PATH=/root/.cargo/bin:$PATH
export RUSTFLAGS='-C target-cpu=x86-64-v3'
export CARGO_BUILD_JOBS=4 RAYON_NUM_THREADS=4 CUDAHOSTCXX=/usr/bin/g++
case "${HALLMARK_CUDA_ARCH:-90}" in 80|90) ;; *) exit 2 ;; esac
printf 'set(CMAKE_CUDA_ARCHITECTURES "%s")\n' "${HALLMARK_CUDA_ARCH:-90}" > /work/architecture.cmake
export CMAKE_TOOLCHAIN_FILE=/work/architecture.cmake
rustc --version
cargo --version
nvcc --version
dpkg-query -W > /persist/os-packages.txt
python3 - <<'PY'
import hashlib,json,subprocess,time
from pathlib import Path
root=Path('/work/source/tree')
rows=[]
for name,crate,args in [
    ('stock-verifier','circle',['--no-default-features','--bin','circle-verify']),
    ('stock-prover','circle',['--features','prover','--bin','circle-prove']),
    ('cuda-prover','circle-cuda',['--features','prover,cuda','--bin','circle-prove']),
]:
    t=time.monotonic()
    p=subprocess.run(['cargo','build','--locked','--release','-j','4',*args],cwd=root/crate)
    rows.append(dict(stage=name,seconds=time.monotonic()-t,exit_code=p.returncode))
    Path('/persist/build-times.json').write_text(json.dumps(rows,indent=2)+'\n')
    p.check_returncode()
    src=root/crate/'target/release'/('circle-verify' if name=='stock-verifier' else 'circle-prove')
    dst=Path('/persist')/dict([('stock-verifier','circle-verify'),('stock-prover','circle-prove-cpu'),('cuda-prover','circle-prove-cuda')])[name]
    dst.write_bytes(src.read_bytes());dst.chmod(0o755)
bins={}
for name in ['circle-verify','circle-prove-cpu','circle-prove-cuda']:
    with (Path('/persist')/name).open('rb') as f: bins[name]=hashlib.file_digest(f,'sha256').hexdigest()
Path('/persist/binaries.json').write_text(json.dumps(bins,indent=2)+'\n')
PY
cuobjdump --list-elf /persist/circle-prove-cuda > /persist/cuda-elf.txt
python3 - <<'PY'
from pathlib import Path
s=Path('/persist/cuda-elf.txt').read_text()
import os
arch=os.environ.get('HALLMARK_CUDA_ARCH','90')
assert ('sm_'+arch) in s and 'sm_89' not in s
PY
