import hashlib
import json
import math
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from hallmark.group_evaluation import (
    GroupReportPlan,
    ReportExclusion,
    ReportObservation,
    ReportUnavailable,
    _bootstrap,
    dataset_identity,
    group_report,
)
from hallmark.selection import representatives, threshold

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def packet():
    return runpy.run_path(str(ROOT / "scripts/check_group_evaluation.py"))["fixture"]()


def invoke(packet, **changes):
    plan, rows, observations, source, provenance = packet
    return group_report(
        plan,
        rows,
        observations,
        expected_plan=changes.pop("expected_plan", plan.identity()),
        source=changes.pop("source", source),
        provenance=changes.pop("provenance", provenance),
        **changes,
    )


def replace_plan(packet, **changes):
    plan, *rest = packet
    return GroupReportPlan.model_validate(plan.model_dump() | changes), *rest


def test_reproducible_pairs_all_seeds_and_negative_results(packet):
    first = invoke(packet)
    assert first == invoke(packet)
    assert first["all_rows_count"] == 36
    assert len(first["primary_representatives"]) == 12
    assert {m["seed"] for m in first["members"].values()} == {17, 29, 43}
    native = first["members"]["toy-native-17"]
    assert (native["primary"]["tp"], native["primary"]["fp"]) == (5, 1)
    assert native["primary"]["power_status"] == "insufficient-evidence"
    assert native["all_rows"]["fpr_wilson_interval"] is None
    assert native["all_rows"]["power_status"] == "not-applicable-correlated-descendants"
    for pair in first["comparisons"]:
        assert sum(pair["bootstrap"]["joint_cell_counts"]) == 12
        for metric in ("tpr", "fpr"):
            stats = pair["bootstrap"][metric]
            assert stats["valid_resamples"] + stats["null_resamples"] == 10000
            assert len(stats["distribution"]) == 64
        assert pair["drift"]["positive_regressions"] == 1
        assert pair["drift"]["positive_improvements"] == 0
        assert pair["drift"]["net_tpr_loss"] == 1 / 6
        assert pair["drift"]["max_primary_score_error"] == 1.5
        assert pair["observed_delta"]["tpr"] == pytest.approx(-1 / 6)
    assert first["members"]["encoder-29"]["status"] == "unavailable"
    missing = next(s for s in first["seed_summaries"] if s["family"] == "encoder")
    assert not missing["all_seeds_available"] and missing["tpr"] is None
    assert first["quality_claim"] is False
    assert first["confirmatory_decision"] == "not-evaluated"
    assert "marker " not in json.dumps(first)


def test_paired_resampling_keeps_correlation_and_null_draws():
    equal = _bootstrap((1, 0, 0, 0, 0, 0, 0, 1), 7)
    assert equal["tpr"]["delta_interval"] == [0.0, 0.0]
    assert equal["fpr"]["delta_interval"] == [0.0, 0.0]
    assert equal["tpr"]["null_resamples"] > 0
    negative_only = _bootstrap((2, 0, 0, 0, 0, 0, 0, 0), 7)
    assert negative_only["tpr"]["delta_interval"] is None
    assert negative_only["tpr"]["null_resamples"] == 10000
    # Independent oracle: with two groups, each replicate has 0, 1 or 2 regressions.
    known = _bootstrap((0, 0, 0, 0, 1, 0, 1, 0), 7)
    assert known["tpr"]["delta_interval"] == [-1.0, 0.0]
    assert known["tpr"]["valid_resamples"] == 10000


def test_descendants_do_not_add_independent_bootstrap_units(packet):
    full = invoke(packet)
    plan, rows, observations, source, provenance = packet
    rows = representatives(rows)
    ids = {r.record_id for r in rows}
    observations = {
        name: obs.model_copy(
            update={"predictions": tuple(p for p in obs.predictions if p.record_id in ids)}
        )
        if isinstance(obs, ReportObservation)
        else obs
        for name, obs in observations.items()
    }
    reduced = replace_plan(
        (plan, rows, observations, source, provenance),
        dataset=dataset_identity(rows),
        annotations=tuple(a for a in plan.annotations if a.record_id in ids),
    )
    report = invoke(reduced)
    assert report["all_rows_count"] == 12
    assert [c["bootstrap"] for c in report["comparisons"]] == [
        c["bootstrap"] for c in full["comparisons"]
    ]


def test_slices_empty_denominators_and_explicit_missing_annotations(packet):
    report = invoke(packet)
    slices = report["members"]["toy-native-17"]["slices"]
    empty = next(s for s in slices if (s["dimension"], s["value"]) == ("length", "0"))
    assert empty["primary"]["n"] == 0 and empty["primary"]["tpr"] is None
    assert empty["primary"]["fpr"] is None
    positives = next(s for s in slices if s["value"] == "family-1")
    assert positives["primary"]["fpr"] is None
    assert positives["primary"]["tpr"] == 5 / 6
    assert {s["dimension"] for s in slices} == {
        "language",
        "source",
        "family",
        "length",
        "obfuscation",
        "benign-hard-negative",
    }
    assert {s["value"] for s in slices if s["dimension"] == "obfuscation"} == {"unavailable"}


def test_group_exclusion_is_frozen_and_disclosed(packet):
    report = invoke(
        replace_plan(
            packet,
            exclusions=(ReportExclusion(group_id="g-01", reason="predeclared-fixture-check"),),
        )
    )
    assert report["all_rows_count"] == 33
    assert report["excluded_groups"] == [
        {"group_id": "g-01", "reason": "predeclared-fixture-check"}
    ]
    assert report["comparisons"][0]["drift"]["positive_regressions"] == 0
    assert report["resampling_exclusions"] == []


def test_no_fitting_scoring_calibration_or_winner_selection(packet, monkeypatch):
    import hallmark.comparison as comparison
    import hallmark.selection as selection

    def forbidden(*args, **kwargs):
        pytest.fail("report attempted to select or score a model")

    for module, names in (
        (selection, ("threshold", "score_fitted", "fit_candidate", "grouped_selection")),
        (comparison, ("calibrate_fitted", "evaluate_fitted")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    assert invoke(packet)["threshold_selection"] == "none-consumes-caller-frozen-calibration"


def test_adaptive_set_cannot_be_confirmatory(packet):
    with pytest.raises(ValueError):
        replace_plan(packet, evidence_class="confirmatory", adaptive=True)
    report = invoke(replace_plan(packet, evidence_class="exploratory", adaptive=True))
    assert report["adaptive"] and report["confirmatory_decision"] == "not-evaluated"
    report = invoke(replace_plan(packet, evidence_class="confirmatory"))
    assert report["confirmatory_decision"] == "inconclusive" and not report["quality_claim"]


def test_tied_calibration_and_no_benign_calibration():
    assert threshold((5, 5, 9), (0, 0, 1), "0.01") == 6
    assert threshold((5.0, 5.0, 9.0), (0, 0, 1), "0.01") == math.nextafter(5.0, math.inf)
    with pytest.raises(ValueError):
        threshold((5,), (1,), "0.01")


@pytest.mark.parametrize("field", ["dataset", "evaluator", "source", "provenance"])
def test_changed_protocol_bindings_reject(packet, field):
    with pytest.raises(ValueError):
        invoke(replace_plan(packet, **{field: "0" * 64}))


@pytest.mark.parametrize("field", ["source", "provenance", "expected_plan"])
def test_external_pin_and_documents_reject(packet, field):
    with pytest.raises(ValueError):
        invoke(packet, **{field: "0" * 64 if field == "expected_plan" else b"changed"})


@pytest.mark.parametrize(
    "mutation",
    ["drop-seed", "duplicate", "bad-pair", "cross-seed", "reversed-drift", "wrong-resamples"],
)
def test_roster_never_silently_omits_seeds(packet, mutation):
    plan = packet[0]
    changes = {}
    if mutation == "drop-seed":
        changes["roster"] = plan.roster[:-1]
    elif mutation == "duplicate":
        changes["roster"] = (*plan.roster, plan.roster[0])
    elif mutation == "wrong-resamples":
        changes["resamples"] = 9999
    else:
        pair = plan.pairs[0]
        changes["pairs"] = (
            pair.model_copy(
                update={
                    "left": "missing"
                    if mutation == "bad-pair"
                    else "toy-float-29"
                    if mutation == "cross-seed"
                    else "toy-native-17",
                    "right": pair.right if mutation != "reversed-drift" else "toy-float-17",
                }
            ),
        )
    with pytest.raises(ValueError):
        replace_plan(packet, **changes)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "extra",
        "drop-prediction",
        "duplicate-prediction",
        "label",
        "group",
        "block",
        "score-type",
        "infinity",
        "threshold",
        "fit",
        "overlap-group",
        "overlap-prompt",
    ],
)
def test_observation_tampering_rejects(packet, mutation):
    plan, rows, observations, source, provenance = packet
    observations = dict(observations)
    name = "toy-native-17"
    obs = observations[name]
    if mutation == "missing":
        del observations[name]
    elif mutation == "extra":
        observations["extra"] = obs
    elif mutation in ("drop-prediction", "duplicate-prediction"):
        observations[name] = obs.model_copy(
            update={
                "predictions": obs.predictions[:-1]
                if mutation == "drop-prediction"
                else (*obs.predictions, obs.predictions[0])
            }
        )
    elif mutation in ("label", "group", "block", "score-type", "infinity"):
        p = obs.predictions[0]
        update = (
            {"label": 1}
            if mutation == "label"
            else {"group_id": "wrong"}
            if mutation == "group"
            else {"block": not p.block}
            if mutation == "block"
            else {"score": float(p.score) if mutation == "score-type" else float("inf")}
        )
        observations[name] = obs.model_copy(
            update={"predictions": (p.model_copy(update=update), *obs.predictions[1:])}
        )
    else:
        cal = obs.calibration
        update = (
            {"threshold": cal.threshold + 1}
            if mutation == "threshold"
            else {"fit": "0" * 64}
            if mutation == "fit"
            else {"groups": (rows[0].group_id,)}
            if mutation == "overlap-group"
            else {"prompts": (hashlib.sha256(rows[0].prompt.encode()).hexdigest(),)}
        )
        changed = cal.model_copy(update=update)
        observations[name] = obs.model_copy(update={"calibration": changed})
        if mutation.startswith("overlap"):
            plan = GroupReportPlan.model_validate(
                plan.model_dump()
                | {
                    "roster": tuple(
                        m.model_copy(update={"calibration": changed.identity()})
                        if m.name == name
                        else m
                        for m in plan.roster
                    )
                }
            )
    with pytest.raises(ValueError):
        invoke((plan, rows, observations, source, provenance))


def test_missing_run_stays_missing_in_summary_and_pair(packet):
    plan, rows, observations, source, provenance = packet
    observations["toy-native-29"] = ReportUnavailable(
        schema_id="hallmark/report-unavailable/1", reason="nonconverged"
    )
    report = invoke((plan, rows, observations, source, provenance))
    summary = next(
        s for s in report["seed_summaries"] if s["family"] == "toy" and s["variant"] == "native"
    )
    assert summary["tpr"] is None and not summary["all_seeds_available"]
    assert report["comparisons"][1]["status"] == "unavailable"


def test_no_independence_from_identical_prompts(packet):
    plan, rows, *rest = packet
    rows = (rows[0].model_copy(update={"prompt": rows[3].prompt}), *rows[1:])
    packet = replace_plan((plan, rows, *rest), dataset=dataset_identity(rows))
    with pytest.raises(ValueError):
        invoke(packet)


def test_all_excluded_and_unmapped_metadata_reject(packet):
    plan, rows, *_ = packet
    with pytest.raises(ValueError):
        invoke(
            replace_plan(
                packet,
                exclusions=tuple(
                    ReportExclusion(group_id=g, reason="excluded")
                    for g in sorted({r.group_id for r in rows})
                ),
            )
        )
    with pytest.raises(ValueError):
        invoke(replace_plan(packet, annotations=plan.annotations[:-1]))
    annotations = tuple(
        a.model_copy(update={"benign_hard_negative": True}) for a in plan.annotations
    )
    with pytest.raises(ValueError):
        invoke(replace_plan(packet, annotations=annotations))


def test_schema_snapshots():
    for model, path in (
        (GroupReportPlan, "group-report-plan-v1.json"),
        (ReportObservation, "report-observation-v1.json"),
        (ReportUnavailable, "report-unavailable-v1.json"),
    ):
        assert json.loads((ROOT / "docs/schemas" / path).read_text()) == model.model_json_schema()


def test_fixture_cli_repeats_and_never_overwrites(tmp_path):
    for name in ("first", "repeat"):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/check_group_evaluation.py"),
                "--output",
                str(tmp_path / name),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0, result.stderr
    assert (tmp_path / "first/report.json").read_bytes() == (
        tmp_path / "repeat/report.json"
    ).read_bytes()
    before = (tmp_path / "first/report.json").read_bytes()
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_group_evaluation.py"),
            "--output",
            str(tmp_path / "first"),
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 2 and str(tmp_path) not in result.stderr
    assert (tmp_path / "first/report.json").read_bytes() == before


def test_reporting_command_freezes_inputs_retains_failures_and_sanitizes(packet, tmp_path):
    plan, rows, observations, source, provenance = packet
    (tmp_path / "plan.json").write_text(plan.model_dump_json())
    (tmp_path / "records.jsonl").write_text("\n".join(r.model_dump_json() for r in rows) + "\n")
    (tmp_path / "observations.json").write_text(
        json.dumps({n: o.model_dump(mode="json") for n, o in observations.items()})
    )
    (tmp_path / "source.json").write_bytes(source)
    (tmp_path / "provenance.json").write_bytes(provenance)
    command = [sys.executable, str(ROOT / "scripts/report_groups.py")]
    for name, file in (
        ("plan", "plan.json"),
        ("records", "records.jsonl"),
        ("observations", "observations.json"),
        ("source", "source.json"),
        ("provenance", "provenance.json"),
    ):
        command.extend(["--" + name, str(tmp_path / file)])
    good = subprocess.run(
        [*command, "--expected-plan", plan.identity(), "--output", str(tmp_path / "good")],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert good.returncode == 0, good.stderr
    assert json.loads((tmp_path / "good/report.json").read_text()) == invoke(packet)
    bad = subprocess.run(
        [*command, "--expected-plan", "0" * 64, "--output", str(tmp_path / "bad")],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert bad.returncode == 2 and str(tmp_path) not in bad.stderr
    assert (tmp_path / "bad/failure.json").is_file() and not (tmp_path / "bad/report.json").exists()
