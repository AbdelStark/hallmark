"""Synthetic timing records test reporting, never cryptographic acceptance."""

import copy
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from benchmark_classifiers import spread, summarize


def matrix():
    plan = dict(repetitions=dict(fresh=3, warm=5), case_ids=["allow", "cnn-block", "rule-block"])
    samples = []
    for phase, count in plan["repetitions"].items():
        for backend in ("gnark", "circle"):
            for rep in range(count):
                cases = []
                for index, name in enumerate(plan["case_ids"]):
                    proofs = []
                    for k, kind in enumerate(("rule", "mlp", "encoder")):
                        value = 1 + index * 100 + k * 10 + rep
                        key = "stark_proving" if backend == "circle" else "groth16_proving"
                        proofs.append(
                            dict(
                                kind=kind,
                                witness_seconds=0.5,
                                materialization_seconds=0.01,
                                serialization_seconds=0.02,
                                proof_bytes=1000 + k,
                                worker_timing=dict(engine=dict(stages_seconds={key: value})),
                                prover_cost=dict(elapsed_seconds=value + 1, max_rss_bytes=1000000),
                                verifier_cost=dict(elapsed_seconds=0.1),
                            )
                        )
                    cases.append(
                        dict(
                            case_id=name,
                            proofs=proofs,
                            native_inference_seconds=0.2,
                            native_plus_binding_seconds=0.3,
                            caller_binding_seconds=0.4,
                        )
                    )
                samples.append(
                    dict(
                        phase=phase,
                        backend=backend,
                        repetition=rep,
                        status="passed",
                        cases=cases,
                        full_wall_seconds=123 + rep,
                        sampled_process_tree_peak_rss_bytes=2000000,
                    )
                )
    return plan, samples


def test_summary_keeps_workloads_separate_and_uses_frozen_spread():
    plan, samples = matrix()
    result = summarize(samples, plan)
    assert len(result["workflows"]) == 4 and len(result["proofs"]) == 36
    allow = next(
        p
        for p in result["proofs"]
        if p["phase"] == "fresh"
        and p["backend"] == "gnark"
        and p["case_id"] == "allow"
        and p["kind"] == "rule"
    )
    assert allow["proving_seconds"] == dict(successful=3, median=2, minimum=1, maximum=3, iqr=1)
    other = next(
        p
        for p in result["proofs"]
        if p["phase"] == "warm"
        and p["backend"] == "circle"
        and p["case_id"] == "cnn-block"
        and p["kind"] == "encoder"
    )
    assert other["proving_seconds"]["median"] == 123 and other["proving_seconds"]["iqr"] == 2


@pytest.mark.parametrize(
    "mutation",
    ["failed", "missing-sample", "duplicate-repetition", "missing-classifier", "changed-case"],
)
def test_incomplete_or_failed_matrix_cannot_be_a_passed_report(mutation):
    plan, samples = matrix()
    samples = copy.deepcopy(samples)
    if mutation == "failed":
        samples[0]["status"] = "failed"
    elif mutation == "missing-sample":
        samples.pop(0)
    elif mutation == "duplicate-repetition":
        samples[1]["repetition"] = 0
    elif mutation == "missing-classifier":
        samples[0]["cases"][0]["proofs"].pop()
    else:
        samples[0]["cases"][0]["case_id"] = "other"
    with pytest.raises(ValueError):
        summarize(samples, plan)


@pytest.mark.parametrize("value", [-1, True, math.nan, math.inf])
def test_invalid_or_unavailable_measurements_are_not_encoded_as_zero(value):
    with pytest.raises(ValueError):
        spread([value])
    assert spread([])["median"] is None
