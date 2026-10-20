"""Build twice from reviewed Git paths; retain inventories, logs and failures locally."""

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from package_inventory import (
    MAX_FILE,
    MAX_TOTAL,
    archive_files,
    canonical,
    check_archives,
    digest,
    file_inventory,
    safe_name,
)

ROOT = Path(__file__).resolve().parents[1]
BUILD_EPOCH = "315532800"
UV_VERSION = "0.9.18"


def command(args, *, cwd, output, env):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=55)
    output.write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("package subprocess failed; inspect retained local log")
    return result.stdout


def build_environment():
    env = {
        key: os.environ[key]
        for key in ("PATH", "HOME", "TMPDIR", "SSL_CERT_FILE")
        if key in os.environ
    }
    env.update(
        SOURCE_DATE_EPOCH=BUILD_EPOCH,
        PYTHONHASHSEED="0",
        PYTHONNOUSERSITE="1",
        UV_PYTHON_DOWNLOADS="never",
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
    )
    return env


def reviewed_source(root):
    config = tomllib.loads((root / "pyproject.toml").read_text())
    includes = config["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]
    if any(safe_name(name) != name or any(c in name for c in "*?[") for name in includes):
        raise ValueError("sdist roots must be explicit paths")
    listing = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=root)
    files, modes = {}, {}
    for record in listing.split(b"\0"):
        if not record:
            continue
        header, raw_name = record.split(b"\t", 1)
        mode, _, stage = header.decode().split()
        name = raw_name.decode("utf-8")
        if not any(name == prefix or name.startswith(prefix + "/") for prefix in includes):
            continue
        safe_name(name)
        path = root / name
        if any(
            parent.is_symlink()
            for parent in path.parents
            if parent != root and root in parent.parents
        ):
            raise ValueError("symlinked source parent")
        info = path.lstat()
        if (
            stage != "0"
            or mode not in ("100644", "100755")
            or not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_size > MAX_FILE
        ):
            raise ValueError("unmerged, missing or unsafe reviewed source")
        with path.open("rb") as handle:
            raw = handle.read(MAX_FILE + 1)
        if len(raw) != info.st_size or path.stat() != info:
            raise ValueError("source changed during snapshot")
        files[name] = raw
        modes[name] = int(mode, 8) & 0o777
    inventory = file_inventory(files)
    if not files or any(
        not any(p == prefix or p.startswith(prefix + "/") for p in files) for prefix in includes
    ):
        raise ValueError("empty source or missing declared sdist root")
    for item in inventory:
        item["mode"] = modes[item["path"]]
    return files, inventory


def validate_build_inputs(files):
    config = tomllib.loads(files["pyproject.toml"].decode())
    declared = config["build-system"]["requires"]
    if declared != config["dependency-groups"]["build"]:
        raise ValueError("PEP 517 and locked build requirements differ")
    expected = dict(requirement.split("==") for requirement in declared)
    lock = tomllib.loads(files["uv.lock"].decode())
    locked = {p["name"]: p["version"] for p in lock["package"]}
    if any(locked.get(name) != version for name, version in expected.items()):
        raise ValueError("build dependency pins differ from lock")
    review = json.loads(files["research/evidence/w37-dependencies-2026-10-20.json"])
    reviewed = {p["name"]: p["version"] for p in review["packages"]}
    if (
        review["lock_sha256"] != digest(files["uv.lock"])
        or reviewed
        != {name: version for name, version in locked.items() if name != "hallmark-research"}
        or len(reviewed) != len(review["packages"])
    ):
        raise ValueError("dependency review is stale or incomplete")
    if any(
        not (
            p["license_expression"]
            or p["legacy_license_label"]
            or p["license_classifiers"]
            or p["license_notices_when_metadata_missing"]
        )
        for p in review["packages"]
    ):
        raise ValueError("dependency licence evidence is missing")
    return expected


def copy_source(target, files, inventory):
    target.mkdir()
    # Stop Hatch from importing a parent directory's VCS exclusion files.
    (target / ".git").mkdir()
    (target / ".hg").mkdir()
    for item in inventory:
        path = target / item["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(files[item["path"]])
        path.chmod(item["mode"])
        os.utime(path, (int(BUILD_EPOCH), int(BUILD_EPOCH)))


def require_same(first, second):
    def hashes(directory):
        result = {}
        for path in directory.iterdir():
            if path.name == ".gitignore":
                continue
            if (
                path.suffix not in (".whl", ".gz")
                or path.is_symlink()
                or not path.is_file()
                or path.stat().st_size > MAX_TOTAL
            ):
                raise ValueError("unexpected or oversized build output")
            result[path.name] = digest(path.read_bytes())
        return result

    left, right = hashes(first), hashes(second)
    if len(left) != 2 or left != right:
        raise ValueError("repeated distribution hashes differ")
    return left


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--train", action="store_true", help="also install and exercise train extra"
    )
    args = parser.parse_args()
    output_root = ROOT / "dist"
    output_root.mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="package-check-", dir=output_root))
    env = build_environment()
    try:
        uv = command(["uv", "--version"], cwd=ROOT, output=output / "uv.log", env=env).decode()
        if uv.split()[1] != UV_VERSION:
            raise ValueError("package gate requires the recorded uv version")
        files, inventory = reviewed_source(ROOT)
        expected_build = validate_build_inputs(files)
        source_id = digest(canonical(inventory))
        (output / "source-inventory.json").write_bytes(
            canonical(
                {
                    "schema_id": "hallmark/package-source/1",
                    "source_id": source_id,
                    "files": inventory,
                }
            )
        )
        roots = [output / "source-1", output / "source-2"]
        for root in roots:
            copy_source(root, files, inventory)
        requirements = output / "build-requirements.txt"
        command(
            [
                "uv",
                "export",
                "--locked",
                "--only-group",
                "build",
                "--no-emit-project",
                "--no-header",
                "--no-annotate",
                "--no-config",
                "--output-file",
                str(requirements),
            ],
            cwd=roots[0],
            output=output / "export-build.log",
            env=env,
        )
        build_env = output / "build-env"
        command(
            ["uv", "venv", "--no-config", "--python", sys.executable, str(build_env)],
            cwd=output,
            output=output / "build-env.log",
            env=env,
        )
        python = build_env / "bin/python"
        command(
            [
                "uv",
                "pip",
                "install",
                "--no-config",
                "--python",
                str(python),
                "--require-hashes",
                "--no-deps",
                "--only-binary",
                ":all:",
                "-r",
                str(requirements),
            ],
            cwd=output,
            output=output / "build-install.log",
            env=env,
        )
        build_inventory = json.loads(
            command(
                [
                    str(python),
                    str(roots[0] / "scripts/package_inventory.py"),
                    "--lock",
                    str(roots[0] / "uv.lock"),
                ],
                cwd=output,
                output=output / "build-inventory.log",
                env=env,
            )
        )
        actual_build = {p["name"]: p["version"] for p in build_inventory["packages"]}
        if actual_build != expected_build:
            raise ValueError("installed build environment differs from exact pins")
        (output / "build-environment.json").write_bytes(canonical(build_inventory))
        artifacts = [output / "build-1", output / "build-2"]
        for index, (root, destination) in enumerate(zip(roots, artifacts, strict=True), 1):
            command(
                [
                    "uv",
                    "build",
                    str(root),
                    "--out-dir",
                    str(destination),
                    "--no-build-isolation",
                    "--no-sources",
                    "--no-config",
                    "--offline",
                    "--python",
                    str(python),
                    "--no-python-downloads",
                ],
                cwd=output,
                output=output / f"build-{index}.log",
                env=env,
            )
        equal_hashes = require_same(*artifacts)
        config = tomllib.loads(files["pyproject.toml"].decode())
        distribution = (
            config["project"]["name"].replace("-", "_") + "-" + config["project"]["version"]
        )
        wheel = artifacts[0] / (distribution + "-py3-none-any.whl")
        sdist = artifacts[0] / (distribution + ".tar.gz")
        archives = check_archives(wheel, sdist, files, distribution)
        # A source archive must build the same wheel without the original checkout.
        unpacked = output / "unpacked"
        unpacked.mkdir()
        for name, raw in archive_files(sdist).items():
            path = unpacked / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        archive_root = unpacked / distribution
        (archive_root / ".git").mkdir()
        (archive_root / ".hg").mkdir()
        command(
            [
                "uv",
                "build",
                str(archive_root),
                "--wheel",
                "--out-dir",
                str(output / "rebuilt"),
                "--no-build-isolation",
                "--no-sources",
                "--no-config",
                "--offline",
                "--python",
                str(python),
                "--no-python-downloads",
            ],
            cwd=output,
            output=output / "sdist-rebuild.log",
            env=env,
        )
        if digest((output / "rebuilt" / wheel.name).read_bytes()) != equal_hashes[wheel.name]:
            raise ValueError("wheel rebuilt from sdist differs")
        command(
            [
                sys.executable,
                str(archive_root / "scripts/check_package.py"),
                "--source",
                str(archive_root),
                "--dist",
                str(artifacts[0]),
                "--report",
                str(output / "installed-environments.json"),
                *(["--train"] if args.train else []),
            ],
            cwd=output,
            output=output / "installed-check.log",
            env=env,
        )
        result = {
            "schema_id": "hallmark/package-check/1",
            "source_id": source_id,
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "source_kind": "reviewed Git paths with current working bytes",
            "lock_sha256": digest(files["uv.lock"]),
            "uv": uv.strip(),
            "uv_binary_sha256": digest(Path(shutil.which("uv")).read_bytes()),
            "epoch": int(BUILD_EPOCH),
            "build_environment_sha256": digest(canonical(build_inventory)),
            "build_requirements_sha256": digest(requirements.read_bytes()),
            "equal_build_hashes": equal_hashes,
            "sdist_rebuild_matches": True,
            "distributions": archives,
            "installed_environments_sha256": digest(
                (output / "installed-environments.json").read_bytes()
            ),
            "installed_train_checked": args.train,
            "secret_check": (
                "reviewed paths, exact archive membership and recognizable "
                "credential patterns; not a universal detector"
            ),
        }
        (output / "result.json").write_bytes(canonical(result))
        print(
            json.dumps(
                {
                    "status": "passed",
                    "source_id": source_id,
                    "distributions": equal_hashes,
                    "installed_train_checked": args.train,
                    "retained": str(output),
                }
            )
        )
    except Exception as exc:
        (output / "failure.json").write_bytes(
            canonical(
                {
                    "schema_id": "hallmark/package-failure/1",
                    "status": "failed",
                    "type": type(exc).__name__,
                }
            )
        )
        raise SystemExit(f"Package gate failed; retained diagnostics: {output}") from None


if __name__ == "__main__":
    main()
