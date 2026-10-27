"""Local trust-boundary checks; these tests never provision paid compute."""

import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_classifier_benchmark_hf import admission, validate_retention  # noqa: E402


def test_finite_startup_inclusive_budget_and_changed_quote():
    config = json.loads((ROOT / "configs/circle-classifiers/hf-job.json").read_bytes())
    item = SimpleNamespace(cpu="8 vCPU", ram="32 GB", unit_label="minute", unit_cost_micro_usd=500)
    assert admission(config, {"cpu-upgrade": item}, []) == 280000
    with pytest.raises(ValueError, match="overlap"):
        admission(config, {"cpu-upgrade": item}, ["other-job"])
    item.unit_cost_micro_usd = 501
    with pytest.raises(ValueError, match="price"):
        admission(config, {"cpu-upgrade": item}, [])


def load_bootstrap():
    spec = importlib.util.spec_from_file_location(
        "classifier_hf_bootstrap", ROOT / "research/probes/circle/hf_bootstrap.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "name,kind",
    [("../escape", tarfile.REGTYPE), ("/escape", tarfile.REGTYPE), ("link", tarfile.SYMTYPE)],
)
def test_source_archive_rejects_paths_and_links(tmp_path, name, kind):
    archive = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo(name)
        info.type = kind
        info.linkname = "../escape"
        tar.addfile(info)
    with pytest.raises(ValueError, match="unsafe"):
        load_bootstrap().extract(archive, tmp_path / "out", 1024)


def test_retention_requires_hash_and_safe_complete_inventory(tmp_path):
    archive = tmp_path / "outputs.tar.gz"
    raw = b'{"status":"fixture-passed"}'
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo("runs/campaign/result.json")
        info.size = len(raw)
        tar.addfile(info, io.BytesIO(raw))
    receipt = dict(
        bytes=archive.stat().st_size, sha256=hashlib.sha256(archive.read_bytes()).hexdigest()
    )
    (tmp_path / "output-receipt.json").write_text(json.dumps(receipt))
    assert validate_retention(tmp_path, 10000)["status"] == "fixture-passed"
    with archive.open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ValueError, match="receipt"):
        validate_retention(tmp_path, 10000)


def test_materializer_checks_inputs_before_exec(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"caller input")
    executable = Path(sys.executable).resolve()
    manifest = dict(
        schema_id="hallmark.classifier-worker-inputs/1",
        binary=str(executable),
        binary_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
        arguments=[
            "-c",
            'from pathlib import Path; assert Path("data").read_bytes() == b"caller input"',
        ],
        files=dict(
            data=dict(
                path=str(source), sha256=hashlib.sha256(source.read_bytes()).hexdigest(), bytes=12
            )
        ),
    )
    raw = json.dumps(manifest).encode()
    work = tmp_path / "work"
    work.mkdir()
    (work / "manifest.json").write_bytes(raw)
    command = [
        sys.executable,
        str(ROOT / "research/probes/circle/materialize_worker.py"),
        "manifest.json",
        hashlib.sha256(raw).hexdigest(),
    ]
    result = subprocess.run(command, cwd=work, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads((work / "materialization.json").read_bytes())["files"] == 1
    source.write_bytes(b"tampered!!!!")
    (work / "data").unlink()
    result = subprocess.run(command, cwd=work, capture_output=True, text=True)
    assert result.returncode != 0
