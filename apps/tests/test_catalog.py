from pathlib import Path

import pytest

from hallmark_demo.catalog import CATALOG, money, plan, retained_path


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "0", "3", True, 1, "1;echo test"])
def test_cost_validation(value):
    with pytest.raises(ValueError):
        money(value, "2.10")


def test_command_arrays_and_unknown_parameters(root):
    args = plan(root, CATALOG["classifiers"], {}, Path("/tool/uv"))
    assert args["command"] == [
        "/tool/uv",
        "run",
        "--locked",
        "--python",
        "3.12.12",
        "--extra",
        "train",
        "python",
        "scripts/run_e2e.py",
    ]
    assert args["paid"] is False
    with pytest.raises(ValueError):
        plan(root, CATALOG["classifiers"], {"command": "sh"}, Path("/tool/uv"))
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
    directory = root / "runs/llm"
    directory.mkdir()
    plan_result = plan(root, CATALOG["composed"], {"llm_run": "runs/llm"}, Path("/tool/uv"))
    assert plan_result["paid"] is False and plan_result["ceiling"] == "0"
    assert "--llm-run" in plan_result["command"]


def test_circle_is_first_and_legacy_workflows_keep_their_meaning(root):
    from hallmark_demo.catalog import WORKFLOWS

    assert [w.id for w in WORKFLOWS[:2]] == ["classifiers-circle", "composed-circle"]
    assert "Groth16" in CATALOG["classifiers"].scheme
    new = plan(root, CATALOG["classifiers-circle"], {}, Path("/tool/uv"))
    assert new["command"][-1] == "scripts/run_circle_e2e.py" and new["paid"] is False
    (root / "runs/llm").mkdir()
    composed = plan(root, CATALOG["composed-circle"], {"llm_run": "runs/llm"}, Path("/tool/uv"))
    assert composed["paid"] is False and composed["ceiling"] == "0"
    assert "composed-circle" in composed["command"]
