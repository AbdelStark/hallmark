"""Recompute public reference numbers from the retained reports; never sum nested timers."""

import argparse
import json
from pathlib import Path

from hallmark._gnark_probe import write_new


def load(path):
    return json.loads(path.read_text())


def classifier(root):
    report = load(root / "proofs/result.json")
    costs = report["costs"]
    proves = [c for c in costs if "-prove-" in c["name"]]
    verifies = [c for c in costs if "-verify-" in c["name"]]
    rejects = [c for c in costs if "-reject-" in c["name"]]
    enrolls = [c for c in costs if c["name"].startswith("enroll-")]
    if (
        report["status"] != "passed"
        or len(proves) not in (3, 9)
        or len(verifies) != len(proves)
        or len(rejects) != 7 * len(proves)
        or len(enrolls) != 3
        or any(c["exit_code"] != (1 if "-reject-" in c["name"] else 0) for c in costs)
    ):
        raise ValueError("incomplete classifier timing campaign")
    rows = []
    for p in proves:
        v = next(c for c in verifies if c["name"] == p["name"].replace("-prove-", "-verify-"))
        rows.append(
            dict(
                name=p["name"],
                witness_seconds=p["python_witness_seconds"],
                prover_command_seconds=p["elapsed_seconds"],
                verify_command_seconds=v["elapsed_seconds"],
                engine_stages_seconds=p["engine_timing"]["stages_seconds"],
                input_parse_seconds=p["cli_timing"]["input_parse_seconds"],
                serialization_seconds=p["cli_timing"]["serialize_write_seconds"],
                proof_bytes=p["files"]["proof.json"]["bytes"],
                proof_sha256=p["files"]["proof.json"]["sha256"],
            )
        )
    return dict(
        proofs=len(proves),
        rows=rows,
        witness_seconds=sum(r["witness_seconds"] for r in rows),
        prover_commands_seconds=sum(r["prover_command_seconds"] for r in rows),
        verify_commands_seconds=sum(r["verify_command_seconds"] for r in rows),
        proof_bytes=sum(r["proof_bytes"] for r in rows),
        engine_stages_seconds={
            k: sum(r["engine_stages_seconds"][k] for r in rows)
            for k in rows[0]["engine_stages_seconds"]
        },
        input_parse_seconds=sum(r["input_parse_seconds"] for r in rows),
        serialization_seconds=sum(r["serialization_seconds"] for r in rows),
        enroll_commands_seconds=sum(c["elapsed_seconds"] for c in enrolls),
        rejection_commands_seconds=sum(c["elapsed_seconds"] for c in rejects),
        proof_campaign_seconds=report["elapsed_seconds"],
        sampled_peak_rss_bytes=max(c["sampled_peak_rss_bytes"] for c in costs),
        direct_public_rejections=len(rejects),
        cross_request_rejections=len(report["cross_request_rejections"]),
        roster_rejections=report["roster_rejections"],
    )


def llm(root):
    output = root / "jobs/prove/output"
    commands = load(output / "commands.json")
    runs = {}
    for backend in ("simd", "cuda"):
        rows = []
        for tag in [*[f"B0L{i}" for i in range(22)], "head"]:
            name = backend + "-0-" + tag
            raw = load(output / (name + ".stdout"))
            p = raw["result"]["point"]
            c = next(c for c in commands if c["name"] == name)
            if c["exit_code"] != 0 or p["accepts"] is not True:
                raise ValueError("failed LLM segment")
            rows.append(
                dict(
                    tag=tag,
                    trace_seconds=p["trace_secs"],
                    interaction_seconds=p["interaction_secs"],
                    prove_seconds=p["prove_secs"],
                    inline_verify_seconds=p["verify_secs"],
                    command_seconds=c["seconds"],
                    proof_bytes=p["proof_ser_bytes"],
                    sampled_peak_rss_bytes=c["sampled_peak_rss_bytes"],
                    phases=p["phases"],
                    env=raw["env"],
                    security=raw["security"],
                )
            )
        grid = next(c for c in commands if c["name"] == backend + "-0-verify")
        runs[backend] = dict(
            rows=rows,
            **{
                key: sum(r[key] for r in rows)
                for key in (
                    "trace_seconds",
                    "interaction_seconds",
                    "prove_seconds",
                    "inline_verify_seconds",
                    "command_seconds",
                    "proof_bytes",
                )
            },
            grid_verify_seconds=grid["seconds"],
            sampled_peak_rss_bytes=max(r["sampled_peak_rss_bytes"] for r in rows),
        )
    recorded = load(root / "result.json")
    for row in recorded["measurements"]:
        computed = runs[row["backend"]]
        if (
            abs(computed["prove_seconds"] - row["prove_seconds"]) > 1e-6
            or abs(computed["command_seconds"] - row["commands_seconds"]) > 1e-6
            or computed["proof_bytes"] != row["serialized_proof_bytes"]
        ):
            raise ValueError("LLM aggregate differs from raw logs")
    return dict(
        backends=runs,
        roots_command_seconds=next(c["seconds"] for c in commands if c["name"] == "roots"),
        build_job_running_seconds=load(root / "jobs/build/retention.json")["running_seconds"],
        workflow_seconds=recorded["seconds"],
        preparation_reused=True,
        build_reused=True,
        fresh_preparation_seconds=None,
        serialization_seconds=None,
        unmeasured_reason=(
            "Preparation reused; isolated LLM serialization unmeasured; "
            "complete commands include it."
        ),
    )


def report(root):
    return dict(
        schema_id="hallmark.public-reference-metrics/1",
        classifiers=classifier(root / "classifiers/controls"),
        composed_classifiers=classifier(root / "classifiers/composed"),
        timing=load(root / "timing/result.json"),
        machine=load(root / "timing/protocol.json"),
        llm=llm(root / "llm"),
        composition=load(root / "composition/result.json"),
        native_gpu=load(root / "native/gpu/result.json"),
        native_gpu_cases=load(root / "native/gpu/verification/output/cases.json"),
        timer_rules=[
            "LLM interaction timer is nested inside prove_secs; do not add it.",
            "Circle engine stages sit inside complete prover commands; do not add them twice.",
            "Host witness generation is outside classifier prover commands.",
            "Different machines/component runs do not form one measured end-to-end duration.",
        ],
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--records", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    write_new(
        args.output, (json.dumps(report(args.records), sort_keys=True, indent=2) + "\n").encode()
    )
