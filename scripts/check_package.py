"""Check distribution contents and install/run the wheel in a fresh environment."""

import json
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
        assert "hallmark/manifests.py" in names
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
            "tests/test_wire.py",
            "tests/test_manifests.py",
            "fixtures/wire/model-manifest-v1.json",
            "docs/schemas/model-manifest-v1.json",
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
            [
                str(python),
                "-c",
                "from hallmark.wire import encode, decode, H; "
                "assert encode({'a': 1}) == bytes.fromhex('a1616101'); "
                "assert decode(bytes.fromhex('a1616101')) == {'a': 1}; "
                "assert len(H('policy', {'a': 1})) == 32",
            ],
            cwd=directory,
            check=True,
        )
        subprocess.run(
            [
                str(python),
                "-c",
                "import json, sys; from pathlib import Path; "
                "from hallmark.manifests import ModelManifest, verify_model_files; "
                "v = json.loads(Path(sys.argv[1]).read_text()); "
                "m = ModelManifest.decode(bytes.fromhex(v['cbor_hex'])); "
                "assert m.identity().hex() == v['identity_hex']; "
                "assert m.encode().hex() == v['cbor_hex']; "
                "Path('weights.bin').write_bytes(v['content_utf8'].encode('utf-8')); "
                "verify_model_files(m, Path('.'), max_bytes=3)",
                str(ROOT / "fixtures/wire/model-manifest-v1.json"),
            ],
            cwd=directory,
            check=True,
        )
        subprocess.run(
            [str(env / "bin/hallmark"), "validate-data", str(ROOT / "fixtures/smoke.jsonl")],
            cwd=directory,
            check=True,
        )
        failed = subprocess.run(
            [str(env / "bin/hallmark"), "schema", "PRIVATE_ERROR_SENTINEL"],
            cwd=directory,
            capture_output=True,
            text=True,
            check=False,
        )
        assert failed.returncode == 2 and not failed.stdout
        assert "PRIVATE_ERROR_SENTINEL" not in failed.stderr
        assert json.loads(failed.stderr)["code"] == "INPUT_INVALID"
    print("Wheel/sdist contents and isolated installed CLI passed.")


if __name__ == "__main__":
    main()
