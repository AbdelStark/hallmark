from pathlib import Path

import pytest

from hallmark_demo.catalog import CATALOG, money, plan, retained_path


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "0", "3", True, 1, "1;echo test"])
def test_cost_validation(value):
    with pytest.raises(ValueError):
        money(value, "2.10")


def test_command_arrays_and_unknown_parameters(root):
    args = plan(root, CATALOG["classifiers-circle"], {}, Path("/tool/uv"))
    assert args["command"] == [
        "/tool/uv",
        "run",
        "--locked",
        "--python",
        "3.12.12",
        "--extra",
        "train",
        "python",
        "scripts/run_circle_e2e.py",
    ]
    assert args["paid"] is False
    with pytest.raises(ValueError):
        plan(root, CATALOG["classifiers-circle"], {"command": "sh"}, Path("/tool/uv"))
    with pytest.raises(ValueError):
        plan(root, CATALOG["llm"], {"max_cost": False}, Path("/tool/uv"))


def test_retained_inputs_cannot_escape_runs_or_follow_symlinks(root, tmp_path):
    with pytest.raises(ValueError):
        retained_path(root, "../other", True)
    target = root / "runs/retained"
    target.mkdir()
    link = root / "runs/link"
    link.symlink_to(target)
    with pytest.raises(ValueError):
        retained_path(root, str(link), True)
    assert retained_path(root, "runs/retained", True) == target


def test_retained_composition_has_no_paid_execution(root):
    from hallmark_demo.catalog import WORKFLOWS

    assert [w.id for w in WORKFLOWS[:2]] == ["classifiers-circle", "composed-circle"]
    (root / "runs/llm").mkdir()
    composed = plan(root, CATALOG["composed-circle"], {"llm_run": "runs/llm"}, Path("/tool/uv"))
    assert composed["paid"] is False and composed["ceiling"] == "0"
    assert "--llm-run" in composed["command"] and "composed-circle" in composed["command"]


def test_composed_preflight_needs_only_retained_run_storage(root, monkeypatch):
    from collections import namedtuple

    from hallmark_demo import catalog

    usage = namedtuple("usage", "total used free")
    monkeypatch.setattr(catalog.shutil, "disk_usage", lambda _: usage(0, 0, 20 * 1024**3))
    checks = catalog.preflight(root, CATALOG["composed-circle"], Path("/tool/uv"))
    storage = next(c for c in checks if c["label"] == "Free storage")
    assert storage["ok"] and storage["detail"].endswith("/ 12 GiB required")
