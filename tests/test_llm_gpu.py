"""Offline money/input/backend failures; these tests are not GPU proof evidence."""

import copy
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_llm_e2e as e2e
import run_llm_gpu as gpu

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def worker(monkeypatch):
    probe = ROOT / "research/probes/sash"
    monkeypatch.syspath_prepend(str(probe))
    spec = importlib.util.spec_from_file_location("relation", probe / "prove_response.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setitem(sys.modules, "relation", module)
    spec = importlib.util.spec_from_file_location("sash_gpu_worker", probe / "benchmark_gpu.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_gpu_budget_is_bounded_and_does_not_change_cpu_defaults():
    hardware = {
        name: SimpleNamespace(unit_label="minute", unit_cost_micro_usd=rate)
        for name, rate in (("cpu-upgrade", 500), ("h200", 83333), ("cpu-performance", 31667))
    }
    assert e2e.planned_cost(hardware, "5", gpu.PHASES) == 3_800_000
    assert gpu.planned_cost(hardware, "5") == 4_640_000
    assert (
        gpu.planned_cost(hardware, "5", {k: v for k, v in gpu.PHASES.items() if k != "build"})
        == 4_620_000
    )
    assert e2e.planned_cost(hardware, "2.10") == 1_960_000
    with pytest.raises(ValueError, match="cost ceiling"):
        e2e.planned_cost(hardware, "3.79", gpu.PHASES)
    with pytest.raises(ValueError, match="cost ceiling"):
        gpu.planned_cost(hardware, "4.63")
    assert gpu.PHASES["prove"] == ("h200", 2700, 4, 210)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "0", "4.63", ""])
def test_unverified_or_insufficient_credits_reject(value):
    with pytest.raises(ValueError, match="credit"):
        gpu.credit_guard(value, 4_640_000)


def test_sufficient_checked_credits():
    gpu.credit_guard("4.64", 4_640_000)


def input_case(tmp_path, monkeypatch):
    probe = tmp_path / "probe"
    probe.mkdir()
    case = probe / "response-case.json"
    case.write_text("{}\n")
    previous = tmp_path / "previous"
    previous.mkdir()
    for name in ("inputs.tar.gz", "inventory.json"):
        (previous / name).write_bytes(b"reviewed public fixture")
    baseline = dict(
        case_sha256=e2e.sha(case),
        artifact_sha256={
            name: e2e.sha(previous / name) for name in ("inputs.tar.gz", "inventory.json")
        },
    )
    evidence = tmp_path / "research/evidence"
    evidence.mkdir(parents=True)
    (evidence / "llm-e2e-reproduction-2026-10-23.json").write_text(json.dumps(baseline))
    monkeypatch.setattr(gpu, "ROOT", tmp_path)
    monkeypatch.setattr(gpu, "PROBE", probe)
    return previous, case


@pytest.mark.parametrize("changed", ["inputs.tar.gz", "inventory.json", "case"])
def test_changed_public_preparation_rejects_before_upload(tmp_path, monkeypatch, changed):
    previous, case = input_case(tmp_path, monkeypatch)
    assert len(gpu.admit_inputs(previous)) == 2
    (case if changed == "case" else previous / changed).write_bytes(b"changed")
    with pytest.raises(ValueError, match="differs|changed"):
        gpu.admit_inputs(previous)


def test_preparation_symlink_rejects(tmp_path, monkeypatch):
    previous, _ = input_case(tmp_path, monkeypatch)
    archive = previous / "inputs.tar.gz"
    archive.rename(previous / "target")
    archive.symlink_to(previous / "target")
    with pytest.raises(ValueError, match="regular"):
        gpu.admit_inputs(previous)


def test_cached_build_binds_case_source_binary_and_retention(tmp_path, monkeypatch):
    previous, _ = input_case(tmp_path, monkeypatch)
    for name in ("build_gpu.sh", "build_prover.sh"):
        (gpu.PROBE / name).write_text("public build fixture")

    def write(path, obj):
        path.write_text(json.dumps(obj))

    write(
        previous / "protocol.json",
        dict(
            case_sha256=e2e.sha(gpu.PROBE / "response-case.json"),
            source_files={
                "research/probes/sash/" + n: e2e.sha(gpu.PROBE / n)
                for n in ("build_gpu.sh", "build_prover.sh", "response-case.json")
            },
        ),
    )
    built = previous / "build/retained"
    built.mkdir(parents=True)
    for name in ("zk-prover-simd", "zk-prover-cuda"):
        (built / name).write_bytes(b"public binary fixture")
    receipt = dict(
        stage="COMPLETED",
        all_outputs_retained=True,
        bucket_deleted=True,
        outputs={n: dict(sha256=e2e.sha(built / n)) for n in ("zk-prover-simd", "zk-prover-cuda")},
    )
    write(previous / "build/retention.json", receipt)
    assert gpu.admit_build(previous) == built
    (built / "zk-prover-cuda").write_bytes(b"changed")
    with pytest.raises(ValueError, match="binary changed"):
        gpu.admit_build(previous)
    (built / "zk-prover-cuda").write_bytes(b"public binary fixture")
    receipt["bucket_deleted"] = False
    write(previous / "build/retention.json", receipt)
    with pytest.raises(ValueError, match="incomplete"):
        gpu.admit_build(previous)
    receipt["bucket_deleted"] = True
    write(previous / "build/retention.json", receipt)
    (gpu.PROBE / "build_gpu.sh").write_text("changed build source")
    with pytest.raises(ValueError, match="source changed"):
        gpu.admit_build(previous)


def test_wrong_backend_source_and_modes_reject(worker):
    case = {"source": {"revision": "expected"}}
    valid = {
        "provenance": dict(
            backend="cuda", commit="expected", dirty=False, unsound_skips=[], gpu="NVIDIA H200"
        ),
        "modes": {name: dict(value=0) for name in worker.HOST_MODES},
        "result": {},
    }
    worker.check_provenance(valid, case, "cuda")
    for field, value in (
        ("backend", "simd"),
        ("dirty", True),
        ("commit", "other"),
        ("unsound_skips", ["argmax"]),
        ("gpu", None),
    ):
        bad = copy.deepcopy(valid)
        bad["provenance"][field] = value
        with pytest.raises(ValueError):
            worker.check_provenance(bad, case, "cuda")
    bad = copy.deepcopy(valid)
    bad["modes"]["GENERATED_LOGUP"]["value"] = 3
    with pytest.raises(ValueError, match="path modes"):
        worker.check_provenance(bad, case, "cuda")


def test_synthetic_fixture_does_not_relax_llm_shape_enrollment(worker):
    case = {"source": {"revision": "expected"}}
    report = dict(
        provenance=dict(backend="simd", commit="expected", dirty=False, unsound_skips=[]),
        modes={name: dict(value=0) for name in worker.HOST_MODES},
        result=dict(
            point=dict(
                accepts=True,
                binding=dict(all_bound=True, unbound=[]),
                verdict=dict(stark_ok=True, error=None, shape_root_ok=None),
                ref_mismatch=0,
                proof_sha256="db6d17a700c25457fixture",
            )
        ),
    )
    worker.smoke_checked(report, case, "simd")
    with pytest.raises(ValueError, match="wrong shape"):
        worker.checked(report, case, "simd")
    report["result"]["point"]["proof_sha256"] = "wrong"
    with pytest.raises(ValueError, match="digest changed"):
        worker.smoke_checked(report, case, "simd")


@pytest.mark.parametrize("name,link", [("../escape", False), ("/escape", False), ("safe", True)])
def test_worker_archive_rejects_paths_and_links(worker, tmp_path, name, link):
    (tmp_path / "inventory.json").write_text(json.dumps({name: dict(bytes=1, sha256="0" * 64)}))
    with tarfile.open(tmp_path / "inputs.tar.gz", "w:gz") as tar:
        info = tarfile.TarInfo(name)
        info.size = 1
        if link:
            info.type = tarfile.SYMTYPE
            info.linkname = "elsewhere"
        tar.addfile(info, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="archive member"):
        worker.unpack(tmp_path, tmp_path / "work")


def test_gpu_telemetry_parses_actual_units(worker, tmp_path):
    path = tmp_path / "gpu.csv"
    path.write_text("2026/10/26 12:00:00, 2048, 75\n")
    assert worker.gpu_samples(path, 0)[0] == dict(
        timestamp="2026/10/26 12:00:00", memory_mib=2048, utilization=75
    )
    path.write_text("unexpected\n")
    with pytest.raises(ValueError, match="telemetry"):
        worker.gpu_samples(path, 0)


@pytest.mark.parametrize("status,expected", [("State: Z\n", 0), ("VmHWM: 2048 kB\n", 2097152)])
def test_memory_sampler_handles_exited_child(worker, monkeypatch, status, expected):
    monkeypatch.setattr(worker, "Path", lambda _: SimpleNamespace(read_text=lambda: status))
    assert worker.process_rss(123) == expected


def test_memory_sampler_handles_vanished_child(worker, monkeypatch):
    def disappeared():
        raise ProcessLookupError

    monkeypatch.setattr(worker, "Path", lambda _: SimpleNamespace(read_text=disappeared))
    assert worker.process_rss(123) == 0


def test_build_script_shell_syntax():
    subprocess.run(["bash", "-n", str(ROOT / "research/probes/sash/build_gpu.sh")], check=True)
