# Reproducible package checks

Run these from a reviewed Git checkout with the locked development environment:

```sh
make package-check
make package-check-train
```

The first gate installs only core dependencies; it requires scikit-learn to be
absent and runs all installed runtime/CLI fixtures. The second additionally
creates a separate train environment, executes the synthetic fit and caller-pinned
replay, and rejects an altered result. There is no skip path for installed training.
Both use one BLAS/OpenMP thread. No model or research-data download occurs.

## Inputs and environment

Use uv **0.9.18** and a supported CPython **3.12, 3.13 or 3.14** interpreter.
Linux `ubuntu-24.04` and macOS `macos-15` CI run each Python version's core/package
and required-train/package contracts. A runner label is not an immutable OS image;
the actual interpreter, OS/architecture and dependency inventory are recorded.
No Windows support or cross-platform byte equality is claimed.

Hatchling **1.32.4**, packaging **26.3**, pathspec **1.1.1**, pluggy **1.7.0**,
tomlkit **0.15.2** and trove-classifiers **2026.9.21.13** are exact in
`build-system.requires`, the build dependency group and `uv.lock`. The gate
exports hash-pinned requirements, creates one fresh build environment and installs
only locked wheels. It verifies the actual installed inventory against the lock.
Builds then run offline with build isolation disabled because that environment
has already been provisioned. No inherited `PYTHONPATH`, `UV_*` or `HATCH_*`
settings select another toolchain. Package installation may fetch locked software
wheels; this is not an OS network sandbox for arbitrary backend code.

`SOURCE_DATE_EPOCH=315532800` and `PYTHONHASHSEED=0` are fixed by the gate.
[Hatch documents epoch-based reproducibility](https://hatch.pypa.io/latest/config/build/#reproducible-builds),
and [uv documents the build flow](https://docs.astral.sh/uv/guides/package/).
The report records the interpreter binary, ABI, zlib runtime, uv binary and actual
build package hashes. Reproduction means identical artifacts under those recorded
inputs; a different environment must run its own comparison.

## Reviewed source and archive boundaries

The source snapshot uses tracked or newly staged Git paths beneath the explicit
sdist roots, with their **current working bytes** and Git file modes. Review and
stage exact new files before checking. Untracked files are not silently admitted;
local runs, credentials and the ignored agent harness stay outside the snapshot.
Dirty tracked source is allowed for development, so the source-tree hash is the
identity of the checked input; the recorded HEAD alone is not that identity.

Two new source directories receive the same bounded inventory, normalized mtimes
and empty VCS boundary directories. The latter prevent Hatch from importing a
parent directory's `.gitignore` or `.hgignore`; no Git history is copied.
Two wheel/sdist builds must have identical SHA-256 values. The sdist's contents
are independently checked, then rebuilt into the same wheel without the original
checkout. Installation checks use fixtures/scripts from that extracted sdist.

Archives must contain exactly the reviewed source plus generated package metadata,
or the exact runtime code/type files and wheel metadata/licence. Missing or extra
files, changed payloads, incorrect wheel RECORD hashes, duplicate/case-aliasing
paths, traversal, links and nonregular members fail. Source aliases and changes
detected during snapshotting also fail. Input limits are 2,048 files, 8 MiB per
file and 64 MiB of aggregate file content/archive bytes. These are parser bounds,
not a peak-RSS or adversarial process-isolation guarantee.

Known private/generated paths and recognizable PEM, GitHub, AWS and Hugging Face
credential patterns reject. This is a defence in addition to reviewed Git paths
and exact inventory matching; no automated scanner can certify arbitrary content
as non-confidential. Public synthetic fixture keys/weights remain fixtures and do
not grant operational authority. Audit source changes before sharing artifacts.

## Retained results and failures

Every invocation creates a fresh private directory under `dist/package-check-*`.
It retains source inventory/hash, two source copies, build environment/inventory,
requirements, raw command logs, both distributions, extracted source, installed
core/train environments and the structured result. Failed invocations retain
`failure.json` and available partial outputs; never reuse a failed directory.
The final output identifies the retained directory and artifact hashes.

These are local build records, not uploaded CI artifacts or a signed release
packet. They may contain paths and private operator context in command logs.
Keep them outside git and follow the owner's local retention policy. Nothing
publishes to a package index, adds reviewers, or changes repository visibility.
The source, dependency and distribution inventories support engineering review;
release approval, independent verification and scientific/hardware evidence remain
separate gates. See [licences](DEPENDENCIES.md) and [decision 0016](decisions/0016-reproducible-packaging.md).
