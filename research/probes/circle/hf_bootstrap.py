"""Bounded public-source HF CPU job; no system packages or provider credential."""

import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path, PurePosixPath


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def extract(archive, destination, maximum):
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        if len(members) > 20000 or sum(m.size for m in members) > maximum:
            raise ValueError("archive inventory exceeds its admission bound")
        for member in members:
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts or not (member.isfile() or member.isdir()):
                raise ValueError("unsafe archive member")
        source.extractall(destination, members=members, filter="data")


def download(spec, destination):
    maximum = spec.get("bytes", spec.get("max_bytes"))
    with (
        urllib.request.urlopen(spec["url"], timeout=120) as source,
        destination.open("xb") as target,
    ):
        copied = 0
        while chunk := source.read(1024**2):
            copied += len(chunk)
            if copied > maximum:
                raise ValueError("download exceeds frozen size")
            target.write(chunk)
    if ("bytes" in spec and copied != spec["bytes"]) or sha(destination) != spec["sha256"]:
        raise ValueError("download differs from admitted tool")


def main():
    if sys.version_info[:3] != (3, 12, 12):
        raise ValueError("pinned Python image required")
    mounted = Path("/persist")
    work = Path("/work/hallmark-classifiers")
    work.mkdir(parents=True)
    stage = os.environ["CLASSIFIER_STAGE"]
    if stage not in ("fixture", "benchmark"):
        raise ValueError("unknown job stage")
    if sha(mounted / "hf-job.json") != os.environ["CONFIG_SHA256"]:
        raise ValueError("caller budget/tool configuration mismatch")
    config = json.loads((mounted / "hf-job.json").read_bytes())
    if (
        sha(mounted / "source.tar.gz") != os.environ["SOURCE_SHA256"]
        or sha(mounted / "inputs.tar.gz") != os.environ["INPUTS_SHA256"]
    ):
        raise ValueError("caller archive pin mismatch")
    extract(mounted / "source.tar.gz", work, 64 * 1024**2)
    extract(mounted / "inputs.tar.gz", work, 4 * 1024**2)
    root = work / "source"
    prepared = work / "prepared"
    commit = os.environ["SOURCE_COMMIT"]
    if re.fullmatch("[0-9a-f]{40}", commit) is None:
        raise ValueError("invalid source commit")
    (root / "SOURCE_COMMIT").write_text(commit + "\n")
    env = os.environ.copy()
    tools = work / "tools"
    tools.mkdir()
    env |= dict(
        CARGO_HOME=str(tools / "cargo"),
        RUSTUP_HOME=str(tools / "rustup"),
        OMP_NUM_THREADS="4",
        OPENBLAS_NUM_THREADS="4",
        VECLIB_MAXIMUM_THREADS="4",
        RAYON_NUM_THREADS="4",
        GOTOOLCHAIN="local",
        GOTELEMETRY="off",
        CGO_ENABLED="0",
        GOMAXPROCS="4",
        GOFLAGS="-p=1",
        HF_HUB_DISABLE_TELEMETRY="1",
        PYTHONUNBUFFERED="1",
    )
    started = time.monotonic()
    commands = []

    def run(name, args, *, cwd=None):
        begin = time.monotonic()
        with (work / (name + ".log")).open("xb") as output:
            subprocess.run(
                list(map(str, args)),
                cwd=cwd,
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=min(1800, max(1, 3600 - (time.monotonic() - started))),
            )
        commands.append(dict(name=name, seconds=time.monotonic() - begin))
        (mounted / "bootstrap-progress.json").write_text(json.dumps(commands) + "\n")

    try:
        for binary in ("gcc", "git", "bash"):
            run("tool-" + binary, [binary, "--version"])
        uv_wheel = work / "uv-0.9.18-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
        download(config["uv"], uv_wheel)
        bootstrap = tools / "bootstrap"
        run("bootstrap-env", [sys.executable, "-m", "venv", bootstrap])
        run("install-uv", [bootstrap / "bin/pip", "install", "--no-deps", "--no-index", uv_wheel])
        uv = bootstrap / "bin/uv"
        init = work / "rustup-init"
        download(config["rustup"], init)
        init.chmod(0o700)
        run(
            "rust-toolchain",
            [
                init,
                "-y",
                "--profile",
                "minimal",
                "--default-toolchain",
                "nightly-2025-07-14",
                "--no-modify-path",
            ],
        )
        env["PATH"] = str(tools / "cargo/bin") + ":" + str(bootstrap / "bin") + ":" + env["PATH"]
        toolchain = prepared / "toolchain"
        toolchain.mkdir()
        go_archive = work / "go.tar.gz"
        download(config["go"], go_archive)
        # Upstream Go uses safe internal links; caller source archives admit regular files only.
        with tarfile.open(go_archive, "r:gz") as source:
            source.extractall(toolchain, filter="data")
        env |= dict(
            GOROOT=str(toolchain / "go"),
            GOPATH=str(prepared / "gopath"),
            GOMODCACHE=str(prepared / "gomodcache"),
        )
        go = toolchain / "go/bin/go"
        run(
            "python-project",
            [uv, "sync", "--locked", "--extra", "train", "--python", "3.12.12"],
            cwd=root,
        )
        run("separate-verifier-env", [uv, "venv", "--python", "3.12.12", prepared / "verifier-env"])
        run(
            "separate-verifier-wheels",
            [
                uv,
                "pip",
                "install",
                "--python",
                prepared / "verifier-env/bin/python",
                "--require-hashes",
                "--only-binary",
                ":all:",
                "-r",
                root / "research/probes/py_ecc/requirements.txt",
            ],
        )
        run("go-dependencies", [go, "mod", "download"], cwd=root / "research/probes/gnark")
        run("go-dependency-integrity", [go, "mod", "verify"], cwd=root / "research/probes/gnark")
        run(
            "rust-dependencies",
            [
                tools / "cargo/bin/cargo",
                "+nightly-2025-07-14",
                "fetch",
                "--locked",
                "--manifest-path",
                root / "research/probes/circle/Cargo.toml",
            ],
        )
        env["HF_HUB_OFFLINE"] = "1"
        env["PYTHONPATH"] = str(root / "src") + ":" + str(root / "scripts")
        args = [
            root / ".venv/bin/python",
            root / "scripts/benchmark_classifiers.py",
            "--profile",
            "hf",
            "--classifier-run",
            prepared,
            "--expected-enrollment",
            os.environ["ORIGINAL_ENROLLMENT"],
            "--output",
            root / "runs/campaign",
        ]
        if stage == "fixture":
            args.append("--fixture")
        sys.path.insert(0, str(root / "scripts"))
        from run_e2e import command

        remaining = config["provider_seconds"][stage] - (time.monotonic() - started) - 600
        if remaining <= 0:
            raise TimeoutError("bootstrap exhausted job time reserved for archival")
        command(args, mounted / "campaign.log", env, time.monotonic() + remaining, cwd=root)
        (mounted / "worker-result.json").write_text(
            json.dumps(
                dict(
                    status="passed",
                    stage=stage,
                    bootstrap=commands,
                    elapsed_seconds=time.monotonic() - started,
                )
            )
            + "\n"
        )
    except BaseException as error:
        (mounted / "worker-failure.json").write_text(
            json.dumps(
                dict(
                    status="failed",
                    stage=stage,
                    error_type=type(error).__name__,
                    error=str(error),
                    bootstrap=commands,
                )
            )
            + "\n"
        )
        raise
    finally:
        output = mounted / "outputs.tar.gz"
        with tarfile.open(output, "w:gz", compresslevel=6, dereference=True) as archive:
            for path in sorted((root / "runs").rglob("*")):
                if path.is_file() and not path.is_symlink():
                    archive.add(
                        path,
                        arcname="runs/" + str(path.relative_to(root / "runs")),
                        recursive=False,
                    )
            for path in sorted(work.glob("*.log")):
                archive.add(path, arcname="bootstrap/" + path.name, recursive=False)
        if output.stat().st_size > config["max_download_bytes"]:
            raise ValueError("retained archive exceeds 2 GiB limit")
        (mounted / "output-receipt.json").write_text(
            json.dumps(dict(bytes=output.stat().st_size, sha256=sha(output))) + "\n"
        )


if __name__ == "__main__":
    main()
