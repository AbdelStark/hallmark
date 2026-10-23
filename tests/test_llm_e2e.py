"""Offline failure tests for orchestration, not simulated cryptographic success."""

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_llm_e2e as e2e


def hardware():
    return {
        name: SimpleNamespace(unit_label="minute", unit_cost_micro_usd=rate)
        for name, rate in [("cpu-upgrade", 500), ("cpu-performance", 31667)]
    }


def test_budget_includes_all_jobs_and_reserve():
    assert e2e.planned_cost(hardware(), "2.10") == 1_960_000
    with pytest.raises(ValueError, match="exceed"):
        e2e.planned_cost(hardware(), "1.95")
    expensive = hardware()
    expensive["cpu-performance"].unit_cost_micro_usd *= 2
    with pytest.raises(ValueError, match="exceed"):
        e2e.planned_cost(expensive, "2.10")


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "0", "not-a-price"])
def test_bad_cost_limit_rejects(value):
    with pytest.raises(ValueError, match="cost ceiling"):
        e2e.planned_cost(hardware(), value)


def test_archive_rejects_traversal_and_symlinks(tmp_path):
    data = tmp_path / "array"
    data.write_bytes(b"public fixture")
    with pytest.raises(ValueError, match="unsafe archive path"):
        e2e.archive({"../escape": data}, tmp_path / "bad-path.tar.gz")
    link = tmp_path / "link"
    link.symlink_to(data)
    with pytest.raises(ValueError, match="nonregular"):
        e2e.archive({"array": link}, tmp_path / "bad-link.tar.gz")


def test_archive_tracks_exact_input_bytes(tmp_path):
    data = tmp_path / "array"
    data.write_bytes(b"public fixture")
    inventory = e2e.archive({"witness/array": data}, tmp_path / "inputs.tar.gz")
    assert inventory == {"witness/array": dict(bytes=14, sha256=e2e.sha(data))}


def test_patch_applies_inside_an_enclosing_checkout(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    source = tmp_path / "extracted"
    quant = source / "harness/witness/quant.py"
    quant.parent.mkdir(parents=True)
    original = (
        "def int_gemm_exact(qa, qb, bound):\n"
        '    """Exact integer matmul.\n'
        "    B5's numerator matmul reaches 255 * 127 * C, not 127^2 * C.\n"
        '    """\n'
        "    dt = torch.float32 if bound < (1 << 24) else torch.float64\n"
        "    return (qa.to(dt) @ qb.to(dt)).float()\n"
    )
    quant.write_text(original)
    e2e.patch_source(source, tmp_path, dict(os.environ), time.monotonic() + 10)
    assert quant.read_text() == original.replace(
        "(qa.to(dt) @ qb.to(dt)).float()", "qa.to(dt) @ qb.to(dt)"
    )


def test_malformed_token_does_not_leak_value(tmp_path, monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.setattr(e2e, "ROOT", tmp_path)
    (tmp_path / ".env").write_text('HF_TOKEN="hf_private_unclosed\n')
    with pytest.raises(ValueError, match="Malformed HF_TOKEN") as error:
        e2e.token()
    assert "hf_private" not in str(error.value)
    assert error.value.__suppress_context__


class CreationTimeout:
    def __init__(self):
        self.deleted = False
        self.attempts = 0

    def create_bucket(self, *args, **kwargs):
        pass

    def batch_bucket_files(self, *args, **kwargs):
        pass

    def run_job(self, **kwargs):
        self.attempts += 1
        raise TimeoutError("response lost; server may have created the job")

    def delete_bucket(self, *args, **kwargs):
        self.deleted = True


def test_uncertain_job_creation_preserves_bucket_and_never_retries(tmp_path):
    pytest.importorskip("huggingface_hub")
    script = tmp_path / "build.sh"
    script.write_text("exit 1\n")
    api = CreationTimeout()
    (tmp_path / "protocol.json").write_text(json.dumps({"source_files": {}}))
    with pytest.raises(RuntimeError, match="creation uncertain"):
        e2e.cloud_job(
            api,
            "fixture-owner",
            "build",
            {"build_prover.sh": script},
            dict(source=dict(revision="f" * 40), image="fixture"),
            hardware(),
            tmp_path,
        )
    assert api.attempts == 1
    assert not api.deleted
    assert (tmp_path / "build/bucket.json").is_file()


def test_retention_rejects_remote_path_escape(tmp_path):
    api = SimpleNamespace(
        list_bucket_tree=lambda *a, **k: [SimpleNamespace(path="../private", size=1)]
    )
    with pytest.raises(ValueError, match="unsafe remote output path"):
        e2e.retain(api, "bucket", {}, tmp_path / "output")


def test_missing_output_download_prevents_retention_success(tmp_path):
    def missing(*args, **kwargs):
        raise FileNotFoundError("missing provider output")

    api = SimpleNamespace(
        list_bucket_tree=lambda *a, **k: [SimpleNamespace(path="result.json", size=10)],
        download_bucket_files=missing,
    )
    with pytest.raises(FileNotFoundError):
        e2e.retain(api, "bucket", {}, tmp_path / "output")


def test_detailed_open_binding_cannot_hide_behind_summary():
    sys.path.insert(0, str(e2e.PROBE))
    spec = importlib.util.spec_from_file_location("prove_response", e2e.PROBE / "prove_response.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    point = dict(
        accepts=True,
        binding=dict(all_bound=True, unbound=[]),
        verdict=dict(
            shape_root_ok=True,
            error=None,
            rq_scale_open=[],
            deq_out_open=[],
            nn_open=False,
            ao_q_open=False,
            sums_cancel=True,
        ),
    )
    module.closed(point)
    point["verdict"]["rq_scale_open"] = ["qkv/v"]
    with pytest.raises(ValueError, match="open scale"):
        module.closed(point)


def test_case_contains_no_run_paths_and_matches_accepted_prompt():
    raw = (e2e.PROBE / "response-case.json").read_text()
    assert "/Users/" not in raw and ".env" not in raw
    case = json.loads(raw)
    assert len(case["prompt_ids"]) == 25
    assert case["answer_ids"] == [1576, 7483, 310, 3444, 338, 3681, 29889, 2]
    assert len(case["expected_roots"]) == 23
