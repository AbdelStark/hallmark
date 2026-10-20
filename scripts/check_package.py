"""Check distribution contents and install/run the wheel in a fresh environment."""

import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    wheels = list((ROOT / "dist").glob("*.whl"))
    sdists = list((ROOT / "dist").glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit("expected exactly one wheel and sdist; inspect dist before rebuilding")
    with zipfile.ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
        assert "hallmark/py.typed" in names
        assert "hallmark/cli.py" in names
        assert not any("fixtures/" in name or "runs/" in name for name in names)
    with tarfile.open(sdists[0]) as archive:
        names = {"/".join(name.split("/")[1:]) for name in archive.getnames()}
        for required in (
            "uv.lock",
            "docs/SPEC.md",
            "SPEC.md",
            "docs/spec/11-requirements.md",
            "docs/rfcs/RFC-0001-wire.md",
            "docs/roadmap/work-items.json",
            "docs/roadmap/IMPLEMENTATION.md",
            "scripts/check_docs.py",
            "tests/test_reference.py",
        ):
            assert required in names, required
        assert not any(name.startswith(("runs/", "data/", ".env")) for name in names)
    with tempfile.TemporaryDirectory(prefix="hallmark-wheel-") as directory:
        env = Path(directory) / "venv"
        subprocess.run(["uv", "venv", "--python", sys.executable, str(env)], check=True)
        python = env / "bin/python"
        requirements = Path(directory) / "requirements.txt"
        subprocess.run(
            [
                "uv",
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--format",
                "requirements-txt",
                "--output-file",
                str(requirements),
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            check=True,
        )
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                "--requirements",
                str(requirements),
                str(wheels[0]),
            ],
            check=True,
        )
        subprocess.run([str(env / "bin/hallmark"), "--help"], cwd=directory, check=True)
        subprocess.run(
            [str(env / "bin/hallmark"), "validate-data", str(ROOT / "fixtures/smoke.jsonl")],
            cwd=directory,
            check=True,
        )
    print("Wheel/sdist contents and isolated installed CLI passed.")


if __name__ == "__main__":
    main()
