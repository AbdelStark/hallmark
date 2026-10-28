"""Admission checks run offline; real CUDA acceptance is a separate paid gate."""

import importlib.util
import io
import json
import sys
import tarfile
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_classifier_gpu  # noqa: E402
from prepare_classifier_gpu import unpack  # noqa: E402
from run_classifier_gpu import ROSTER, measurement_roster  # noqa: E402


@pytest.mark.parametrize(
    "name,kind",
    [
        ("root/../../escape", tarfile.REGTYPE),
        ("/absolute", tarfile.REGTYPE),
        ("root/link", tarfile.SYMTYPE),
        ("root/link", tarfile.LNKTYPE),
    ],
)
def test_source_archive_rejects_unsafe_members(tmp_path, name, kind):
    path = tmp_path / "source.tar"
    with tarfile.open(path, "w") as archive:
        member = tarfile.TarInfo(name)
        member.type = kind
        member.linkname = "/escape"
        archive.addfile(member, io.BytesIO(b""))
    with pytest.raises(ValueError, match="unsafe"):
        unpack(path, tmp_path / "out")


def test_source_archive_preserves_bytes_and_rejects_duplicates(tmp_path):
    path = tmp_path / "source.tar"
    with tarfile.open(path, "w") as archive:
        for _ in range(2):
            member = tarfile.TarInfo("root/src/file")
            member.size = 3
            archive.addfile(member, io.BytesIO(b"abc"))
    with pytest.raises(ValueError, match="duplicate"):
        unpack(path, tmp_path / "out")
    assert (tmp_path / "out/src/file").read_bytes() == b"abc"


def test_cuda_overlay_does_not_patch_the_stock_verifier():
    root = Path(__file__).resolve().parents[1]
    patch = (root / "research/probes/circle-gpu/stwo22.patch").read_text()
    targets = [
        line.removeprefix("+++ b/") for line in patch.splitlines() if line.startswith("+++ b/")
    ]
    assert targets and all(not name.startswith("src/core/") for name in targets)
    assert not any(name.startswith("src/prover/pcs/") for name in targets)


def test_measurement_roster_rejects_duplicates_substitutions_and_missing_cases():
    rows = [
        dict(iteration=i, backend=b, case=c)
        for i in range(3)
        for b in ("cpu", "cuda")
        for c in sorted(ROSTER)
    ]
    measurement_roster(rows)
    for invalid in (
        rows[:-1],
        rows[:-1] + rows[:1],
        rows + rows[:1],
        rows[:-1] + [dict(iteration=2, backend="cuda", case="../outside")],
    ):
        with pytest.raises(ValueError, match="roster"):
            measurement_roster(invalid)


def test_worker_command_retains_deadline_failure_and_honest_output(tmp_path):
    path = Path(__file__).resolve().parents[1] / "research/probes/circle-gpu/benchmark.py"
    spec = importlib.util.spec_from_file_location("classifier_gpu_worker", path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    good = tmp_path / "good"
    result = worker.run([sys.executable, "-c", "print('ok')"], good, time.monotonic() + 10)
    assert result["exit_code"] == 0
    assert (good / "stdout.txt").read_text().strip() == "ok"
    failed = tmp_path / "failed"
    with pytest.raises(TimeoutError):
        worker.run(
            [sys.executable, "-c", "import time; time.sleep(60)"], failed, time.monotonic() - 1
        )
    cost = json.loads((failed / "cost.json").read_text())
    assert cost["exit_code"] != 0 and cost["failure_type"] == "TimeoutError"


def test_source_admission_rejects_archive_and_overlay_drift(tmp_path, monkeypatch):
    probe = tmp_path / "probe"
    probe.mkdir()
    (probe / "kernel.cu").write_text("frozen")
    source = tmp_path / "source"
    source.mkdir()
    (source / "source.tar.gz").write_bytes(b"archive")
    (source / "source-inventory.json").write_bytes(b"{}")
    pins = dict(
        source_archive_sha256=run_classifier_gpu.sha(source / "source.tar.gz"),
        source_inventory_sha256=run_classifier_gpu.sha(source / "source-inventory.json"),
        overlays={"kernel.cu": run_classifier_gpu.sha(probe / "kernel.cu")},
    )
    (source / "source.json").write_text(json.dumps(pins))
    monkeypatch.setattr(run_classifier_gpu, "PROBE", probe)
    assert run_classifier_gpu.admit_source(source) == pins
    (probe / "kernel.cu").write_text("changed")
    with pytest.raises(ValueError, match="overlay"):
        run_classifier_gpu.admit_source(source)
    (source / "source.tar.gz").write_bytes(b"changed")
    with pytest.raises(ValueError, match="archive"):
        run_classifier_gpu.admit_source(source)
