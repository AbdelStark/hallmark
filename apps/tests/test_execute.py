import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from hallmark_demo.execute import admission


@pytest.fixture
def e2e(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    return importlib.import_module("run_llm_e2e")


def hardware():
    return {
        name: SimpleNamespace(unit_label="minute", unit_cost_micro_usd=rate)
        for name, rate in [("cpu-upgrade", 500), ("cpu-performance", 31667)]
    }


def test_startup_cost_guard_closes_the_original_timeout_only_gap(e2e):
    assert e2e.planned_cost(hardware(), "2.10") == 1960000
    with pytest.raises(ValueError, match="cost ceiling"):
        admission(e2e, hardware(), "llm", "2.10")
    plan = admission(e2e, hardware(), "llm", "2.50")
    assert plan["conservative_bound_micro_usd"] == 2270000
    assert plan["automatic_retries"] == 0
    assert plan["phases"]["prove"]["worker_seconds"] == 3600
    assert plan["phases"]["prove"]["creation_seconds"] == 600


def test_gpu_cached_build_uses_exactly_one_startup_window(e2e):
    gpu = SimpleNamespace(PHASES=e2e.PHASES)
    plan = admission(e2e, hardware(), "gpu", "2.50", gpu=gpu, build_reused=True)
    assert "build" not in plan["phases"]
    assert plan["conservative_bound_micro_usd"] == 2250000


def test_gpu_dispatch_preserves_named_credit_and_build_arguments(tmp_path, monkeypatch):
    import sys

    from hallmark_demo import execute

    monitor = tmp_path / "runs/workbench/0123456789ab"
    monitor.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    calls = []
    gpu = SimpleNamespace(run=lambda *a, **kw: calls.append((a, kw)), credit_guard=lambda *a: None)
    e2e = SimpleNamespace(token=lambda: "test-only")
    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        SimpleNamespace(HfApi=lambda **kw: SimpleNamespace(list_jobs_hardware=lambda: [])),
    )
    monkeypatch.setattr(
        execute.importlib, "import_module", lambda name: gpu if name == "run_llm_gpu" else e2e
    )
    monkeypatch.setattr(execute, "admission", lambda *a, **kw: {"conservative_bound_micro_usd": 1})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "execute",
            "--root",
            str(tmp_path),
            "--workflow",
            "gpu",
            "--max-cost-usd",
            "5.00",
            "--monitor-dir",
            str(monitor),
            "--llm-run",
            "runs/llm",
            "--credit-balance-usd",
            "6.00",
            "--build-run",
            "runs/build",
        ],
    )
    execute.main()
    assert calls == [
        ((Path("runs/llm"),), dict(balance="6.00", maximum="5.00", build_run=Path("runs/build")))
    ]


def test_retained_circle_composition_preserves_authority_without_paid_admission(
    tmp_path, monkeypatch
):
    import sys

    from hallmark_demo import execute

    monitor = tmp_path / "runs/workbench/0123456789ab"
    monitor.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM_ENROLLMENT", "caller-enrollment.cbor")
    monkeypatch.setenv("LLM_TRUST_KEY", "caller-public-key")
    calls = []
    composed = SimpleNamespace(run=lambda **kw: calls.append(kw))
    monkeypatch.setattr(execute.importlib, "import_module", lambda name: composed)
    monkeypatch.setattr(execute, "admission", lambda *a, **kw: pytest.fail("paid admission"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "execute",
            "--root",
            str(tmp_path),
            "--workflow",
            "composed-circle",
            "--max-cost-usd",
            "2.50",
            "--monitor-dir",
            str(monitor),
            "--llm-run",
            "runs/llm",
        ],
    )
    execute.main()
    assert calls == [
        dict(
            llm_run=Path("runs/llm"),
            classifier_run=None,
            enrollment="caller-enrollment.cbor",
            trusted_key="caller-public-key",
        )
    ]
