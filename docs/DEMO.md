# Run the classifier end-to-end demo

From the repository root:

```sh
make e2e
```

This trains an MLP and a contextual byte CNN, exports their integer graphs, builds
specialized circuits, and generates and separately verifies rule/MLP/CNN proofs
for three fixed requests. It also checks substituted proofs and an arithmetic
mutation corpus. **No hardware attestation, GPU, API token, cloud account or
model download is needed.** All training data is authored and synthetic.

`make e2e` runs **classifiers only**, using dedicated gnark/Groth16 circuits and
separate py-ecc verification. For actual LLM generation/proving use
[`make e2e-llm`](LLM-PROOF.md); to join both use
[`make e2e-composed`](COMPOSED-DEMO.md). The [architecture guide](ARCHITECTURE.md)
maps every command to its proof system and shows the complete data flows.

Read [what the proofs mean](PROOFS.md) before interpreting the result. A proved
classifier verdict is a claim about exact computation, not a guarantee that the
classifier's judgment is correct.

## Prerequisites

| Requirement | Supported path |
|---|---|
| Host | Native Apple Silicon Mac (`Darwin`, `arm64`) |
| Tools on `PATH` | Git, Make, curl and **uv 0.9.18** |
| Python | **CPython 3.12.12**, selected/acquired by uv |
| Network | Initial Python, Go and dependency acquisition; no external data or inference |
| Storage | At least **12 GiB free** before starting |
| Time | About **20 minutes plus dependency/build time** on the recorded M4 Max, 48 GiB RAM |

For a fresh checkout:

```sh
git clone https://github.com/AbdelStark/hallmark.git
cd hallmark
make e2e
```

The target prepares the locked project `.venv` with the training extra. It checks
the exact uv/Python versions, downloads and SHA-256-checks Go 1.26.8, builds the
circuits using pinned Go modules, and installs the separate verifier in its own
hash-pinned environment. No system package install or credential setup is needed.
See the [reviewed dependency inventory](../research/evidence/w18-backend-dependencies-2026-10-20.json).

The full controller is Mac-only. Linux CI tests smaller proof artifacts and the
separate verifier; it does not validate this entire workflow on Linux. For a
quick software-only check on either platform, run `make check-conformance`.

## Progress and expected output

The command prints a fresh evidence directory, then each stage and its log path:

```text
Evidence: .../runs/e2e-<unique-id>
Expect about 20 minutes plus dependency/build time.
Running python-packages; log: ...
...
Running mlp-training; log: ...
Running cnn-training; log: ...
Running proofs; log: ...
```

The proof stage includes fresh setup and negative checks, so it is the longest
stage. It can be quiet for several minutes. To see completed case records while
it runs, use the printed directory in a second terminal:

```sh
tail -f runs/e2e-<unique-id>/proofs.log
```

A successful run exits zero and ends with:

```text
PASS: 9 proofs verified; 18 cross-request substitutions rejected; 405 arithmetic cases matched.
  allow: [1, 1, 1] release=true
  cnn-block: [1, 1, 0] release=false
  rule-block: [0, 1, 1] release=false
Results: .../runs/e2e-<unique-id>/result.json
Proof meaning: docs/PROOFS.md
```

`1` means classifier pass; `0` means block. **All nine proofs must verify**, including
proofs of blocked decisions. `release` is the host's all-pass classifier gate,
not authorization to release a real model response. The 405 arithmetic cases
include valid controls as well as rejected cases.

The entrypoint returns nonzero if a subprocess fails, the CNN's frozen synthetic
screen fails, either integer export differs from its expected hash, proof results
are missing/unexpected, or pipeline source bytes change during the run. A final
`result.json` with `status: "passed"` is written only after these checks.

## Evidence and resource bounds

Every invocation creates a new private `runs/e2e-*` directory. Retries preserve
previous successes and failures. Outputs stay local and are ignored by git.

| Artifact under the printed directory | Contents |
|---|---|
| `result.json` / `failure.json` | Overall success, or failed stage and error type |
| `*.log` | Output of each preparation, training and proof stage |
| `source-pins.json`, `environment.json`, `probe.sha256` | Executable source/config/fixture hashes, versions and locally enrolled binary identity |
| `mlp-training/`, `cnn-training/` | Training checkpoints, exports, calibration, predictions and model results |
| `proofs/protocol.json` | Frozen inputs, capacities, source/binary pins and proof resource caps |
| `proofs/enrollment.json`, `enrollment-pin.json`, `circuit-pins.json` | Program/circuit/key roster pinned before proving |
| `proofs/*-request.json`, `*-bundle.json` | Caller expectations and proof bundles |
| Worker `plan.json`, `cost.json`, `stdout.txt`, `stderr.txt` | Exact invocation, resources and failures |
| `proofs/result.json` | Three verified decisions, rejection roster and arithmetic-case counts |

The driver has a **7,200-second shared deadline** after uv bootstraps the project
environment. Training uses one BLAS thread. The proof controller caps its work at
four worker threads, 8 GiB worker RSS and 8 GiB output; RSS is sampled rather than
an OS quota. There is no hard quota on the entire run directory. The previous
campaign retained about 2.57 GB of proof artifacts, plus environments and build
caches. Run one campaign at a time and retain failures for diagnosis. Maintainer
runs also follow [research authority](../research/AUTHORITY.json).

The driver checks hashes of tracked pipeline files before and after execution;
documentation edits do not affect this check. These hashes identify local inputs.
They do not authenticate an arbitrary checkout or a prover-supplied key. Keep the
enrollment digest outside an untrusted proof bundle.

## Troubleshooting

| Failure | Next step |
|---|---|
| Host or version check | Use native Mac arm64, uv 0.9.18 and the target's pinned Python; do not change export pins to fit another environment |
| Download/build/install failure | Inspect the named log; fix network/tool availability and rerun `make e2e` |
| CNN screen or quantization mismatch | Retain the run and compare environment/protocol identities; do not tune on test or replace expected hashes |
| Proof failure, timeout or resource limit | Inspect `failure.json`, `proofs/failure.json` and the last worker's logs/cost record |
| Interrupted or missing final result | Treat the run as incomplete; rerun into a fresh directory |

[`scripts/run_e2e.py`](../scripts/run_e2e.py) contains the exact preparation
commands and pins. It delegates to the existing [MLP fixture](../scripts/check_mlp_training.py),
[CNN study](../scripts/run_contextual_cnn.py) and [common-request proof controller](../scripts/run_trained_common.py).
For focused experiments, see [operations](OPERATIONS.md) and the [proof probe guide](../research/probes/gnark/README.md).
