"""Build a reproducible CUDA source overlay without changing the Mac backend."""

import argparse
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

from run_e2e import sha, write_json
from run_llm_e2e import archive, fetch, require

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "research/probes/circle-gpu"
SOURCES = {
    "stwo": (
        "https://static.crates.io/crates/stwo/stwo-2.2.0.crate",
        "d400ae91acbeafa6f80070a03e1117a794a95f295050f44538a4c7dd55abd491",
        202664,
    ),
    "nitroo": (
        "https://codeload.github.com/AntChainOpenLabs/NitrooZK-stwo/tar.gz/"
        "41c2a05bdb1fc3e3762bc7804108e8bc269bb6fc",
        "85d4e95eda24a5a446dd41fbe5df48d25cee81b0552c649ab7bf24ef60d7e91f",
        1062345,
    ),
}


def unpack(path, target):
    """Accept source directories/regular files only; strip one archive root."""
    seen = set()
    total = 0
    with tarfile.open(path) as source:
        for member in source:
            name = Path(member.name)
            require(
                not name.is_absolute()
                and ".." not in name.parts
                and (member.isfile() or member.isdir()),
                "unsafe source member",
            )
            relative = Path(*name.parts[1:])
            if str(relative) == ".":
                continue
            require(str(relative) not in seen, "duplicate source member")
            seen.add(str(relative))
            total += member.size
            require(
                0 <= member.size < 8 * 1024**2 and total < 64 * 1024**2, "oversized source archive"
            )
            destination = target / relative
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with source.extractfile(member) as src, destination.open("xb") as dst:
                    shutil.copyfileobj(src, dst)


def patch(folder, path):
    env = os.environ | {"GIT_CEILING_DIRECTORIES": str(folder.parent)}
    for flags in (["--check"], []):
        subprocess.run(["git", "apply", *flags, path], cwd=folder, env=env, check=True, timeout=30)


def prepare(output):
    output.mkdir()
    upstream = output / "upstream"
    upstream.mkdir()
    for name, (url, pin, size) in SOURCES.items():
        compressed = output / (name + ".tar.gz")
        fetch(url, compressed, pin, size)
        unpack(compressed, upstream / name)
    tree = output / "tree"
    tree.mkdir()
    stwo = tree / "stwo"
    shutil.copytree(upstream / "stwo", stwo)
    cuda = upstream / "nitroo/crates/stwo"
    for name in ("src/prover/backend/cuda", "src/stwo_cuda", "build.rs"):
        src, dst = cuda / name, stwo / name
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copyfile(src, dst)
    shutil.copyfile(upstream / "nitroo/LICENSE", stwo / "LICENSE.nitroo")
    patch(stwo, PROBE / "stwo22.patch")
    shutil.copyfile(PROBE / "hallmark.cu", stwo / "src/stwo_cuda/cuda/hallmark.cu")
    # The independently built verifier keeps the exact original dependency lock.
    for name in ("circle", "circle-cuda"):
        dest = tree / name
        dest.mkdir()
        for path in (ROOT / "research/probes/circle").iterdir():
            if path.name == "src":
                shutil.copytree(path, dest / "src")
            elif path.is_file():
                shutil.copyfile(path, dest / path.name)
    patch(tree / "circle-cuda", PROBE / "adapter.patch")
    shutil.copyfile(PROBE / "Cargo.lock", tree / "circle-cuda/Cargo.lock")
    shutil.copyfile(PROBE / "component.rs", tree / "circle-cuda/src/gpu_component.rs")
    for path in (upstream / "stwo/src/core").rglob("*"):
        if path.is_file():
            require(
                sha(path) == sha(stwo / path.relative_to(upstream / "stwo")),
                "CPU verifier core changed",
            )
    pins = archive(
        {str(p.relative_to(tree)): p for p in tree.rglob("*") if p.is_file()},
        output / "source.tar.gz",
    )
    write_json(output / "source-inventory.json", pins)
    write_json(
        output / "source.json",
        dict(
            schema_id="hallmark.classifier-cuda-source/1",
            sources=SOURCES,
            source_archive_sha256=sha(output / "source.tar.gz"),
            source_inventory_sha256=sha(output / "source-inventory.json"),
            overlays={p.name: sha(p) for p in sorted(PROBE.iterdir()) if p.is_file()},
            verifier_core_unchanged=True,
            qualified_backend=False,
        ),
    )
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    print(prepare(parser.parse_args().out.resolve()))
