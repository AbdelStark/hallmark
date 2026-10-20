import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import hallmark.comparison_run as run
from hallmark.admission import AdmissionProtocol, AdmissionReview
from hallmark.errors import HallmarkError
from hallmark.manifests import FileRef

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def dossier(tmp_path, monkeypatch):
    for package in ("onnx", "onnxruntime", "tokenizers", "numpy", "sklearn", "scipy"):
        pytest.importorskip(package)
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    builder = runpy.run_path(str(ROOT / "scripts/check_comparison_run.py"))
    return builder["fixture"](tmp_path / "input")


def reenroll(dossier, *, protocol_changes=None, plan_changes=None):
    """Invent a new external fixture pin to test relational checks beyond byte corruption."""
    root, guard, _ = dossier
    protocol = AdmissionProtocol.decode((root / "protocol.cbor").read_bytes())
    review = AdmissionReview.decode((root / "review.cbor").read_bytes())
    if plan_changes is not None:
        plan = run.ComparisonRunPlan.model_validate_json((root / "comparison.json").read_bytes())
        raw = run.json_bytes(plan.model_copy(update=plan_changes).model_dump(mode="json"))
        (root / "comparison.json").write_bytes(raw)
        (root / "documents/review/comparison-plan.json").write_bytes(raw)
        protocol = protocol.model_copy(
            update={
                "candidate_roster": tuple(
                    c.model_copy(update={"config": hashlib.sha256(raw).digest()})
                    if c.id != "compact-encoder"
                    else c
                    for c in protocol.candidate_roster
                )
            }
        )
    protocol = AdmissionProtocol.model_validate(protocol.model_dump() | (protocol_changes or {}))
    refs = tuple(
        FileRef(path=r.path, size=len(raw), sha256=hashlib.sha256(raw).digest())
        for r in review.evidence
        for raw in [(root / "documents" / r.path).read_bytes()]
    )
    review = review.model_copy(update={"terms": protocol.review_terms(), "evidence": refs})
    protocol = protocol.model_copy(update={"approval_ref": review.identity()})
    (root / "protocol.cbor").write_bytes(protocol.encode())
    (root / "review.cbor").write_bytes(review.encode())
    return root, guard, review.identity()


def invoke(dossier, output, *, fixture_only=True):
    root, guard, pin = dossier
    return run.run_comparisons(root, guard, output, expected_review=pin, fixture_only=fixture_only)


def test_full_flow_freezes_every_fit_and_threshold_before_test(dossier, tmp_path, monkeypatch):
    output = tmp_path / "output"
    events = []
    original_select, original_fit = run.grouped_selection, run.fit_candidate
    original_calibrate, original_evaluate = run.calibrate_fitted, run.evaluate_fitted

    def select(rows, *args):
        assert {r.split for r in rows} == {"train"}
        events.append("select")
        return original_select(rows, *args)

    def fit(rows, *args):
        assert {r.split for r in rows} == {"train"}
        assert "calibrate" not in events and "test" not in events
        events.append("fit")
        return original_fit(rows, *args)

    def calibrate(fitted, rows, **kwargs):
        assert {r.split for r in rows} == {"calibration"}
        assert "test" not in events
        events.append("calibrate")
        return original_calibrate(fitted, rows, **kwargs)

    def evaluate(fitted, frozen, rows, **kwargs):
        assert {r.split for r in rows} == {"test"}
        assert len(json.loads((output / "frozen.json").read_text())) == 10
        assert len(list(output.glob("*-fit.json"))) == 10
        assert len(list(output.glob("*-calibration.json"))) == 10
        events.append("test")
        return original_evaluate(fitted, frozen, rows, **kwargs)

    monkeypatch.setattr(run, "grouped_selection", select)
    monkeypatch.setattr(run, "fit_candidate", fit)
    monkeypatch.setattr(run, "calibrate_fitted", calibrate)
    monkeypatch.setattr(run, "evaluate_fitted", evaluate)
    result = invoke(dossier, output)
    assert events == ["select"] + ["fit"] * 9 + ["calibrate"] * 10 + ["test"] * 10
    assert result["baseline_complete"] and not result["quality_claim"]
    assert result["unavailable"] == [{"kind": "compact-encoder", "reason": "W16-not-executed"}]
    assert result["controls"]["pass-all"]["primary"]["tp"] == 0
    assert result["controls"]["block-all"]["primary"]["tn"] == 0
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in output.iterdir())


@pytest.mark.parametrize(
    "mutation", ["review", "config", "source", "raw", "records", "import", "dataset"]
)
def test_changed_inputs_reject_before_model_or_fitting(dossier, tmp_path, monkeypatch, mutation):
    root, guard, pin = dossier
    if mutation == "review":
        dossier = root, guard, b"x" * 32
    elif mutation == "source":
        monkeypatch.setattr(run, "execution_inventory", lambda: b"changed implementation")
    else:
        paths = {
            "config": root / "comparison.json",
            "raw": root / "sources/raw/authored.jsonl",
            "records": root / "dataset/records.jsonl",
            "import": root / "import.cbor",
            "dataset": root / "dataset.cbor",
        }
        path = paths[mutation]
        path.write_bytes(path.read_bytes() + b" ")
    monkeypatch.setattr(
        run, "LocalGuard", lambda *_a, **_k: pytest.fail("model loaded before rejection")
    )
    with pytest.raises(ValueError):
        invoke(dossier, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "mutation",
    [
        "seeds",
        "alpha",
        "evaluator",
        "split",
        "source",
        "code",
        "guard",
        "jobs",
        "cost",
        "tiny-budget",
    ],
)
def test_new_review_cannot_hide_incoherent_terms(dossier, tmp_path, monkeypatch, mutation):
    root = dossier[0]
    protocol = AdmissionProtocol.decode((root / "protocol.cbor").read_bytes())
    changes = {}
    if mutation == "seeds":
        changes["seeds"] = (1, 2, 3)
    elif mutation == "alpha":
        changes["alpha"] = "0.1"
    elif mutation in ("evaluator", "split"):
        changes["evaluator" if mutation == "evaluator" else "split_manifest"] = protocol.rubric
    elif mutation == "source":
        changes["sources"] = (protocol.sources[0].model_copy(update={"purpose": "other"}),)
    elif mutation in ("code", "guard"):
        roster = list(protocol.candidate_roster)
        if mutation == "code":
            roster[0] = roster[0].model_copy(update={"code": protocol.rubric})
        else:
            refs = list(roster[4].base_files)
            refs[0] = refs[0].model_copy(update={"sha256": b"x" * 32})
            roster[4] = roster[4].model_copy(update={"base_files": tuple(refs)})
        changes["candidate_roster"] = tuple(roster)
    else:
        changes["budget"] = protocol.budget.model_copy(
            update={
                "jobs"
                if mutation == "jobs"
                else "max_cost_minor"
                if mutation == "cost"
                else "max_disk_bytes": 2 if mutation == "jobs" else 1
            }
        )
    dossier = reenroll(dossier, protocol_changes=changes)
    monkeypatch.setattr(
        run, "LocalGuard", lambda *_a, **_k: pytest.fail("model loaded before rejection")
    )
    with pytest.raises(HallmarkError):
        invoke(dossier, tmp_path / "output")


def test_fixture_authority_is_explicit_and_cannot_be_relabelled(dossier, tmp_path):
    with pytest.raises(HallmarkError):
        invoke(dossier, tmp_path / "implicit", fixture_only=False)
    dossier = reenroll(dossier, plan_changes={"fixture_only": False})
    with pytest.raises(HallmarkError):
        invoke(dossier, tmp_path / "relabelled", fixture_only=False)


@pytest.mark.parametrize("field", ["dataset", "import_plan", "guard"])
def test_reviewed_plan_must_match_import_and_policy(dossier, tmp_path, field):
    plan = run.ComparisonRunPlan.model_validate_json((dossier[0] / "comparison.json").read_bytes())
    value = (
        plan.guard.model_copy(update={"max_prompt_bytes": 128}) if field == "guard" else "f" * 64
    )
    dossier = reenroll(dossier, plan_changes={field: value})
    with pytest.raises(HallmarkError):
        invoke(dossier, tmp_path / "out")


def test_nonconverged_family_is_preserved_and_command_reports_partial(dossier, tmp_path):
    plan = run.ComparisonRunPlan.model_validate_json((dossier[0] / "comparison.json").read_bytes())
    candidates = tuple(
        c.model_copy(update={"mlp": c.mlp.model_copy(update={"tolerance": 0.0})})
        if c.mlp is not None
        else c
        for c in plan.selection.candidates
    )
    dossier = reenroll(
        dossier,
        plan_changes={"selection": plan.selection.model_copy(update={"candidates": candidates})},
    )
    root, guard, pin = dossier
    output = tmp_path / "out"
    process = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_comparisons.py"),
            "--dossier",
            str(root),
            "--guard-assets",
            str(guard),
            "--expected-review",
            pin.hex(),
            "--output",
            str(output),
            "--fixture-only",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert process.returncode == 3 and not process.stderr
    result = json.loads((output / "result.json").read_text())
    assert not result["baseline_complete"] and not result["quality_claim"]
    assert len(result["evaluated"]) == 7
    assert [m["reason"] for m in result["unavailable"]].count(
        "no-eligible-train-only-candidate"
    ) == 3
    selection = json.loads((output / "selection.json").read_text())
    assert (
        sum(r["status"] == "nonconverged" for c in selection["candidates"] for r in c["rotations"])
        == 30
    )


def test_run_plan_schema_snapshot():
    assert run.ComparisonRunPlan.model_json_schema() == json.loads(
        (ROOT / "fixtures/comparison-run.schema.json").read_text()
    )


def test_existing_output_survives(dossier, tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    (output / "keep").write_text("unchanged")
    with pytest.raises(FileExistsError):
        invoke(dossier, output)
    assert [p.name for p in output.iterdir()] == ["keep"]
    assert (output / "keep").read_text() == "unchanged"


@pytest.mark.parametrize("stage", ["selection", "evaluation", "disk", "deadline"])
def test_failed_attempt_retains_sanitized_partial_output(dossier, tmp_path, monkeypatch, stage):
    def fail(*_a, **_k):
        raise ValueError("PRIVATE_SENTINEL")

    if stage in ("selection", "evaluation"):
        monkeypatch.setattr(
            run, "grouped_selection" if stage == "selection" else "evaluate_fitted", fail
        )
    elif stage == "disk":
        protocol = AdmissionProtocol.decode((dossier[0] / "protocol.cbor").read_bytes())
        dossier = reenroll(
            dossier,
            protocol_changes={
                "budget": protocol.budget.model_copy(update={"max_disk_bytes": 4096})
            },
        )
    else:
        ticks = iter((0, 61))
        monkeypatch.setattr(run, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    output = tmp_path / "output"
    with pytest.raises(ValueError):
        invoke(dossier, output)
    failure = (output / "failure.json").read_text()
    assert "PRIVATE_SENTINEL" not in failure
    assert not (output / "result.json").exists()
    assert json.loads(failure)["code"] in ("INPUT_INVALID", "RESOURCE_EXHAUSTED")


def test_command_rejects_bad_pin_without_leaking_paths(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_comparisons.py"),
            "--dossier",
            str(tmp_path / "PRIVATE_SENTINEL"),
            "--guard-assets",
            str(tmp_path),
            "--expected-review",
            "PRIVATE_SENTINEL",
            "--output",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2 and not result.stdout
    assert "PRIVATE_SENTINEL" not in result.stderr and str(tmp_path) not in result.stderr
    assert json.loads(result.stderr)["code"] == "INPUT_INVALID"


def test_core_import_does_not_load_optional_libraries():
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import hallmark.comparison_run; "
            "assert not {'onnx', 'onnxruntime', 'tokenizers', 'numpy', 'sklearn'} "
            "& sys.modules.keys()",
        ],
        check=True,
        timeout=10,
    )
