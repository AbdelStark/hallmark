# End-to-end classifier demo

Train two models, export their integer graphs, generate real proofs and verify
three classifiers against the same caller-owned request. This walkthrough uses
only authored synthetic data. It needs **no hardware attestation, GPU, API token,
cloud account or model download**.

The result is a research classifier gate. It does not generate an LLM response,
qualify a cryptographic backend or establish safety. Read the [results and
limitations](RESULTS.md) alongside the output.

## Requirements and cost

| Requirement | This walkthrough |
|---|---|
| Host | Apple Silicon Mac (`Darwin`, `arm64`); the combined controller enforces this |
| Python | CPython 3.12.12 for the recorded training reproduction |
| Package manager | uv 0.9.18, already installed and on `PATH` |
| Native toolchain | Go 1.26.8; downloaded and hash-checked below, without a system install |
| Network | Dependency acquisition only; no external training data or inference |
| Storage | Allow at least 12 GiB free for environments, toolchain, caches and one fresh campaign |
| Time | Recorded training about 3 minutes; combined proof campaign about 15 minutes; acquisition/build extra |

Those timings are observations on an M4 Max with 48 GiB RAM. The proof controller
caps its campaign at 7,200 seconds, four worker threads, 8 GiB worker RSS and 8 GiB
output. RSS is sampled, not a hard OS memory quota. Training needs caller
supervision under the declared 7,200-second/8 GiB envelope. Do not run concurrent
campaigns. Existing research checkouts must also respect their recorded retention
ceiling; the owner's current ceiling is 256 GiB.

Linux CI checks smaller proof artifacts and the separate verifier. It does not
establish support for this full Mac controller on Linux.

## 1. Prepare a fresh workspace

From a new checkout, use a Bash or Zsh shell. Keep the same shell for all steps;
subsequent commands use the variables set here. If already in the checkout, omit
the first two commands.

```sh
git clone https://github.com/AbdelStark/hallmark.git
cd hallmark
uv --version
uv sync --locked --python 3.12.12 --extra train

export DEMO="$PWD/runs/demo-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 "$DEMO"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

git rev-parse HEAD > "$DEMO/source-commit.txt"
git status --short > "$DEMO/source-status.txt"
git diff --binary HEAD > "$DEMO/source-diff.patch"
uv --version > "$DEMO/uv-version.txt"
uv run --locked --extra train python --version > "$DEMO/python-version.txt"
uv pip freeze --python .venv/bin/python > "$DEMO/python-packages.txt"
df -h .
```

Check that uv reports `0.9.18` and Python reports `3.12.12`. `runs/` is ignored by
git. Every child output below must be new: retries use a new `DEMO`, never overwrite
a failed run. Keep raw runs, checkpoints and generated setup material local.

Record hashes of the tracked source before running:

```sh
uv run --locked python - <<'PY'
import hashlib
import json
import os
import subprocess
from pathlib import Path

paths = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
pins = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths if p}
(Path(os.environ["DEMO"]) / "source-pins.json").write_text(
    json.dumps(pins, sort_keys=True, indent=2) + "\n"
)
PY
```

The local commit, source inventory and later binary digest identify this run.
They do not authenticate an arbitrary checkout. Review the source and
[dependency inventory](../research/evidence/w18-backend-dependencies-2026-10-20.json)
before enrolling a binary for a real relying party.

## 2. Build the dedicated circuits

This fetches the exact reviewed **macOS arm64** Go archive, verifies its SHA-256,
and isolates the build/module caches under this run. The modules are pinned by
`go.mod` and `go.sum`; automatic toolchain selection is disabled.

```sh
curl --fail --silent --show-error --location --max-time 120 \
  https://go.dev/dl/go1.26.8.darwin-arm64.tar.gz \
  --output "$DEMO/go.tar.gz"
printf '%s  %s\n' \
  a012b25b571bd0138a03dcd25375ceba866fe5ca822f426d2c66a4de56fd3f4b \
  "$DEMO/go.tar.gz" | shasum -a 256 --check
mkdir "$DEMO/toolchain"
tar -xzf "$DEMO/go.tar.gz" -C "$DEMO/toolchain"

export GOROOT="$DEMO/toolchain/go"
export GOPATH="$DEMO/gopath" GOMODCACHE="$DEMO/gomodcache"
export GOCACHE="$DEMO/gocache" GOTOOLCHAIN=local GOTELEMETRY=off
export CGO_ENABLED=0 GOFLAGS=-p=2 GOMAXPROCS=2 GOMEMLIMIT=1GiB
export PROBE_BINARY="$DEMO/probe"
"$GOROOT/bin/go" version > "$DEMO/go-version.txt"
(
  cd research/probes/gnark
  "$GOROOT/bin/go" mod download
  "$GOROOT/bin/go" mod verify
  "$GOROOT/bin/go" build -trimpath -buildvcs=false -mod=readonly -o "$PROBE_BINARY" .
)
export PROBE_SHA256="$(shasum -a 256 "$PROBE_BINARY" | cut -d ' ' -f 1)"
printf '%s\n' "$PROBE_SHA256" > "$DEMO/probe.sha256"
```

The circuit implementation uses gnark as a library for specialized classifier
relations. It does not execute an arbitrary program inside a zkVM. The build
covers the rule, trained MLP and contextual CNN, including their input-binding
relations.

## 3. Install the separate verifier

The verifier has its own hash-pinned environment. It shares no gnark decoder,
pairing implementation or verification code. Its experimental py-ecc dependency
is not an independent security audit; see the [verifier guide](../research/probes/py_ecc/README.md).

```sh
uv venv --python 3.12.12 "$DEMO/verifier-env"
export VERIFIER_PYTHON="$DEMO/verifier-env/bin/python"
uv pip install --python "$VERIFIER_PYTHON" \
  --require-hashes --only-binary :all: \
  -r research/probes/py_ecc/requirements.txt
```

Keep this virtual-environment invocation path. Resolving its Python symlink to
the base interpreter would lose the installed verifier packages.

## 4. Train and export both models

The MLP fixture checks seeds 17/29/43 and optimizer resume. Its marker task checks
training/arithmetic behavior; it is not the CNN scope-quality experiment.

```sh
uv run --locked --extra train python scripts/check_mlp_training.py \
  fixtures/mlp-training.json \
  --expected-fixture "$(cat fixtures/mlp-training.sha256)" \
  --output "$DEMO/mlp-training" > "$DEMO/mlp-training.log"
```

The CNN command runs the fixed v2 protocol: three seeds, full/resumed training,
integer export, separate calibration and the frozen synthetic test screen.

```sh
uv run --locked --extra train python scripts/run_contextual_cnn.py \
  --study v2 \
  --expected-protocol 3c47c07a5a3413f00814b957ae8752bcb3f786b0c6484becd6cab5290beb5394 \
  --output "$DEMO/cnn-training"
```

Expect `screen=True` for all three seeds and a final `manifest_sha256`. Save that
printed manifest hash separately from the bundle. Check
`cnn-training/results.json`: `all_seeds_pass` must be true. A completed training
command can still report a failed quality screen.

The combined proof controller requires these exact seed-17 quantization files;
it does not silently accept a newly trained model with a different identity:

```sh
printf '%s  %s\n' \
  f8090161455ee56cdcd73eaab44437efa3b278a786d7c246491da5f1e1431a9c \
  "$DEMO/mlp-training/seed-17/quantization.json" \
  8de31ae0215178f5c74aa43e58dd63511bc3b6a881c2045cc96def9e149b8f0b \
  "$DEMO/cnn-training/17/quantization.json" | shasum -a 256 --check
```

A mismatch is a failed reproduction. Preserve it and investigate the environment;
do not replace the expected hashes or tune on the test data to make this run pass.

## 5. Prove and verify the common request

```sh
uv run --locked --extra train python scripts/run_trained_common.py \
  --binary "$PROBE_BINARY" --expected-binary "$PROBE_SHA256" \
  --verifier-python "$VERIFIER_PYTHON" \
  --mlp-quantization "$DEMO/mlp-training/seed-17/quantization.json" \
  --cnn-quantization "$DEMO/cnn-training/17/quantization.json" \
  --output "$DEMO/proofs"
```

The controller first creates fresh circuit/key material and pins enrollment.
For each fixed input it computes the native classifier outputs, produces three
real proofs, reconstructs the public inputs from the caller's opening/context,
and invokes the separate verifier. It then checks cross-request substitutions
and the arithmetic mutation corpus. Progress appears once each case is verified;
setup and individual proof workers can be quiet for minutes.

Expected case records (`1` means pass, `0` means block):

```json
{"name":"allow","proofs_verified":3,"release":true,"verdicts":[1,1,1]}
{"name":"cnn-block","proofs_verified":3,"release":false,"verdicts":[1,1,0]}
{"name":"rule-block","proofs_verified":3,"release":false,"verdicts":[0,1,1]}
```

A successful `proofs/result.json` has `status: "passed"`, 18 entries in
`cross_request_rejections`, and 135 `arithmetic_cases` for each of `rule`, `mlp`
and `encoder` (the CNN occupies the encoder slot). The arithmetic roster includes
valid controls as well as rejection cases. It always retains
`qualified_backend: false` and `hardware_claim: "not-accepted"`.

## 6. Inspect and retain the evidence

| Artifact under `DEMO` | What to inspect |
|---|---|
| `source-pins.json`, version files, `probe.sha256` | Source/environment and locally enrolled binary identity |
| `mlp-training/`, `cnn-training/` | Checkpoints, exports, calibration and predictions |
| `proofs/protocol.json` | Frozen inputs, capacities, code/binary pins and resource caps |
| `proofs/enrollment.json`, `enrollment-pin.json`, `circuit-pins.json` | Model/program/circuit/key roster established before proving |
| `proofs/*-request.json`, `*-bundle.json` | Caller expectations and produced proof bundles |
| Worker `plan.json`, `cost.json`, `stdout.txt`, `stderr.txt` | Exact invocation, measured resources and failures |
| `proofs/result.json` or `failure.json` | Final completed outcome or retained failure |

Retain the enrollment digest outside the prover's bundle. A digest obtained only
from an untrusted bundle cannot authenticate its enrollment. The binding helper
constructs pairing jobs; only the separate arithmetic verifier checks the proofs.

Confirm that source bytes remained unchanged:

```sh
uv run --locked python - <<'PY'
import hashlib
import json
import os
from pathlib import Path

pins = json.loads((Path(os.environ["DEMO"]) / "source-pins.json").read_text())
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in pins.items())
print("source-pins-matched")
PY
```

Repeat from step 1 with a new `DEMO` to check reproduction. Compare learned model
and circuit identities, verdicts and rejection rosters. Random setup keys/proofs,
wall time and RSS need not match. Do not overwrite the earlier evidence.

## Troubleshooting

| Symptom | Meaning and next step |
|---|---|
| `this controller requires the approved Mac host` | Use a native arm64 Mac environment. Linux support for this controller is not implemented. |
| `selected quantization pin mismatch` | Training did not reproduce the frozen export. Keep the output; compare Python, lock, protocol and thread settings. |
| `binary enrollment mismatch` | The binary changed after hashing, or the wrong path/pin was supplied. Review and rebuild before starting a fresh campaign. |
| Missing py-ecc import | Use `verifier-env/bin/python` from step 3, without resolving its symlink. |
| Output directory already exists | Use a fresh run directory; failed artifacts are intentionally retained. |
| Timeout or memory/storage limit | Inspect the last worker's `cost.json` and stderr. A resource failure is not a proof rejection or a pass. |
| No final `result.json` | The campaign is incomplete. Inspect `failure.json` and worker records rather than assuming acceptance. |

For smaller circuit experiments and historical reproduction commands, see
[operations](OPERATIONS.md) and the [proof probe guide](../research/probes/gnark/README.md).
