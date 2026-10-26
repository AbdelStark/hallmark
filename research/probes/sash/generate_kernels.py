"""Generate the enrolled constraint shapes and install upstream CUDA kernels."""

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inventory(root):
    return {
        str(p.relative_to(root)): dict(bytes=p.stat().st_size, sha256=sha(p))
        for p in sorted(root.rglob("*"))
        if p.is_file() and "target" not in p.relative_to(root).parts
    }


def parameters(root, destination):
    pins = json.loads((root / "kernel-params-inventory.json").read_text())
    assert len(pins) == 23 and sum(p["bytes"] for p in pins.values()) < 8 * 1024**2
    seen = set()
    with tarfile.open(root / "kernel-params.tar.gz", "r|gz") as tar:
        for member in tar:
            name = Path(member.name)
            assert member.isfile() and member.name in pins and member.name not in seen
            assert not name.is_absolute() and ".." not in name.parts
            assert member.size == pins[member.name]["bytes"]
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as src, path.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            assert sha(path) == pins[member.name]["sha256"]
            seen.add(member.name)
    assert seen == pins.keys()
    return sorted(destination.glob("params/*.fixed.json"))


def main():
    root, source = Path("/persist"), Path("/work/source")
    before = inventory(source)
    files = parameters(root, Path("/work/kernel-inputs"))
    store = root / "constraint-kernels"
    logs = root / "emit"
    logs.mkdir()
    cpu = root / "zk-prover-simd"
    # The same smallest fixture that the unmodified SIMD build just verified.
    files.insert(0, root / "aligned-proof/B4L0.fixed.json")
    for path in files:
        with (
            (logs / (path.stem + ".json")).open("xb") as out,
            (logs / (path.stem + ".log")).open("xb") as err,
        ):
            subprocess.run(
                [cpu, "cudaemit", "--params", path, "--out", store, "--seg-cap", "3000"],
                cwd=source,
                stdout=out,
                stderr=err,
                check=True,
                timeout=180,
            )
        print("Generated constraint shapes: " + path.name, flush=True)
    manifest = json.loads((store / "manifest.json").read_text())
    assert manifest["kernels"] > 0 and manifest["families"]
    subprocess.run(
        [
            "python3",
            source / "prover/kernels/install_constraint_kernels.py",
            "--fork",
            source / "nitroo",
            "--gen",
            store,
        ],
        check=True,
        timeout=60,
    )
    shutil.copyfile(store / "cudakernels.rs", source / "prover/src/cudakernels.rs")
    env = os.environ | {"GIT_CEILING_DIRECTORIES": str(source.parent)}
    for flags in (["--check"], []):
        subprocess.run(
            ["git", "apply", *flags, root / "kernel-guard.patch"],
            cwd=source,
            env=env,
            check=True,
            timeout=30,
        )
    (source / ".source-commit").write_text(os.environ["SOURCE_COMMIT"] + " dirty\n")
    after = inventory(source)
    changed = {name: record for name, record in after.items() if before.get(name) != record}
    assert not before.keys() - after.keys()
    cuda = "nitroo/crates/stwo/src/stwo_cuda/cuda/"
    allowed = {
        ".source-commit",
        "prover/src/cudakernels.rs",
        "nitroo/crates/stwo/build.rs",
        "nitroo/crates/constraint-framework/src/prover/component_prover.rs",
        cuda + "CMakeLists.txt",
        cuda + "evaluate_constraints.cu",
        cuda + "zk_ops.cuh",
        *(
            cuda + f"evaluate_{f['family']}.{ext}"
            for f in manifest["families"]
            for ext in ("cu", "cuh")
        ),
    }
    assert changed.keys() <= allowed
    report = dict(
        schema_id="hallmark.sash-generated-constraints/1",
        source_commit=os.environ["SOURCE_COMMIT"],
        source_dirty=True,
        generated_constraint_kernels=True,
        generated_witness_kernels=False,
        compile_jobs=2,
        kernel_count=manifest["kernels"],
        families=len(manifest["families"]),
        parameters=inventory(Path("/work/kernel-inputs")),
        patch_sha256=sha(root / "kernel-guard.patch"),
        generated_files=inventory(store),
        modified_source_files=changed,
    )
    (root / "kernel-build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                kernels=manifest["kernels"],
                families=len(manifest["families"]),
                modified_files=len(changed),
            )
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
