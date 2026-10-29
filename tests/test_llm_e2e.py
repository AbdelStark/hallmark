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


def test_budget_includes_all_jobs_startup_windows_and_reserve():
    # 40 + 70 + 40 billed minutes (timeouts plus one 600 s window each) and one cent.
    assert e2e.planned_cost(hardware(), "2.50") == 2_270_000
    with pytest.raises(ValueError, match="exceed"):
        e2e.planned_cost(hardware(), "2.26")
    expensive = hardware()
    expensive["cpu-performance"].unit_cost_micro_usd *= 2
    with pytest.raises(ValueError, match="exceed"):
        e2e.planned_cost(expensive, "2.50")


def test_startup_window_is_counted_exactly_once():
    one_minute = {"job": ("cpu-performance", 60, 1, 1)}
    # (1 + 10) minutes at 31,667 µ$/min rounds up to $0.35, plus the $0.01 reserve.
    assert e2e.planned_cost(hardware(), "1", one_minute) == 360_000


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


class ScriptedJob(CreationTimeout):
    """A created job whose inspected stages (or raised errors) follow a fixed script."""

    def __init__(self, script):
        super().__init__()
        self.script = list(script)
        self.cancelled = 0

    def run_job(self, **kwargs):
        return SimpleNamespace(id="fixture-job")

    def inspect_job(self, **kwargs):
        assert self.script, "polled past the scripted stages"
        step = self.script.pop(0)
        if isinstance(step, BaseException):
            raise step
        return SimpleNamespace(
            status=SimpleNamespace(stage=step), started_at=None, finished_at=None
        )

    def cancel_job(self, **kwargs):
        self.cancelled += 1

    def fetch_job_logs(self, **kwargs):
        return []

    def list_bucket_tree(self, *args, **kwargs):
        return []

    def download_bucket_files(self, *args, **kwargs):
        pass


@pytest.mark.parametrize(
    "script,cancelled,deleted,error,match",
    [
        # Polling keeps failing after the job exists: cancel, then clean up the bucket.
        ([ConnectionError("lost")] * 3 + ["CANCELED"], 1, True, ConnectionError, "lost"),
        # A provider-side deletion is terminal: no cancel, bucket cleaned, failure raised.
        (["RUNNING", "DELETED"], 0, True, ValueError, "build failed"),
        # Ctrl-C, then a cancel that never terminates: the live job's bucket is retained.
        ([KeyboardInterrupt()] + ["RUNNING"] * 30, 1, False, ValueError, "remains live"),
    ],
    ids=["poll-error", "deleted", "cancel-never-terminal"],
)
def test_created_job_failures_cancel_and_clean_up_as_intended(
    tmp_path, monkeypatch, script, cancelled, deleted, error, match
):
    pytest.importorskip("huggingface_hub")
    monkeypatch.setattr(e2e.time, "sleep", lambda _: None)
    script_path = tmp_path / "build.sh"
    script_path.write_text("exit 1\n")
    api = ScriptedJob(script)
    (tmp_path / "protocol.json").write_text(json.dumps({"source_files": {}}))
    with pytest.raises(error, match=match):
        e2e.cloud_job(
            api,
            "fixture-owner",
            "build",
            {"build_prover.sh": script_path},
            dict(source=dict(revision="f" * 40), image="fixture"),
            hardware(),
            tmp_path,
        )
    assert api.cancelled == cancelled
    assert api.deleted is deleted
    assert not api.script
    assert (tmp_path / "build/retention.json").is_file() is deleted


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
