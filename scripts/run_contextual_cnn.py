"""Run the frozen synthetic context screen with train/calibration/test separation."""

import argparse
import hashlib
import importlib.metadata
import math
import resource
import time
from collections import Counter
from pathlib import Path

import contextual_cnn as cnn

from hallmark._gnark_probe import json_new, read_regular, write_new
from hallmark.data import dataset_summary, load_records
from hallmark.evaluation import calibrate_threshold, metrics
from hallmark.integer_encoder import execute_encoder
from hallmark.integrity import parse_json
from hallmark.openings import TranscriptOpening

ROOT = Path(__file__).resolve().parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_record():
    paths = [
        *sorted((ROOT / "src/hallmark").glob("*.py")),
        ROOT / "scripts/contextual_cnn.py",
        Path(__file__),
        ROOT / "uv.lock",
    ]
    return {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths}


def native(exported, prompts):
    results = []
    for prompt in prompts:
        opening = TranscriptOpening(
            schema_id="hallmark/transcript-opening/1",
            system_ref=b"s" * 32,
            salt=b"t" * 32,
            prompt=prompt,
            response="",
        )
        result = execute_encoder(
            opening,
            exported["classifier"],
            exported["program"],
            exported["profile"],
            exported["arithmetic"],
            **{k: exported[k] for k in ("weights", "tokenizer", "parameters")},
        )
        results.append(result.score)
    return results


def run(output, expected_protocol):
    raw = read_regular(ROOT / "fixtures/contextual-protocol.json", 16384)
    if sha(raw) != expected_protocol:
        raise ValueError("protocol differs from caller pin")
    protocol = parse_json(raw.decode())
    if (
        protocol["seeds"] != [17, 29, 43]
        or protocol["fit"]
        != (cnn.FIT | {"optimizer": "full-batch Adam", "dtype": "float64", "device": "cpu"})
        or protocol["architecture"] != dict(capacity=96, kernel=24, embedding=4, channels=8)
    ):
        raise ValueError("protocol does not describe this candidate")
    for filename, key in (
        ("contextual-scope.jsonl", "dataset_sha256"),
        ("contextual-source.json", "source_sha256"),
    ):
        if sha(read_regular(ROOT / "fixtures" / filename, 1024**2)) != protocol[key]:
            raise ValueError("dataset/source pin mismatch")
    rows = load_records(ROOT / "fixtures/contextual-scope.jsonl")
    if any(
        r.source_id != "owned-synthetic-contextual"
        or r.source_revision != protocol["source_sha256"]
        or r.license_id != "LicenseRef-Proprietary"
        or r.policy_id != "synthetic-run-quote-scope-v1"
        or r.response
        for r in rows
    ):
        raise ValueError("unreviewed record source or task")
    groups = {}
    for row in rows:
        groups.setdefault(row.group_id, []).append(row)
    if len(groups) != 100 or any(
        len(g) != 2
        or {r.label for r in g} != {0, 1}
        or Counter(g[0].prompt.encode()) != Counter(g[1].prompt.encode())
        for g in groups.values()
    ):
        raise ValueError("paired histogram baseline does not apply")
    splits = {s: tuple(r for r in rows if r.split == s) for s in ("train", "calibration", "test")}
    if [len(x) for x in splits.values()] != [120, 40, 40]:
        raise ValueError("wrong frozen split roster")
    env = cnn.runtime()
    if any(v != "1" for v in env["threads"].values()):
        raise ValueError("run needs the three declared one-thread environment variables")
    output.mkdir(mode=0o700)
    start = time.monotonic()
    source = source_record()
    write_new(output / "protocol.json", raw)
    json_new(
        output / "environment.json",
        env
        | {"packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}},
    )
    json_new(output / "source-before.json", source)
    json_new(
        output / "admission.json",
        dict(
            dataset_sha256=protocol["dataset_sha256"],
            source_sha256=protocol["source_sha256"],
            summary=dataset_summary(rows),
            agent_review=True,
            policy_quality_claim=False,
        ),
    )
    summary = []
    try:
        for seed in protocol["seeds"]:
            directory = output / str(seed)
            directory.mkdir(mode=0o700)
            t0 = time.monotonic()
            checkpoint = cnn.train(splits["train"], seed)
            json_new(directory / "checkpoint.json", checkpoint)
            partial = cnn.train(splits["train"], seed, stop=100)
            json_new(directory / "resume-100.json", partial)
            resumed = cnn.train(splits["train"], seed, checkpoint=partial)
            json_new(directory / "resumed.json", resumed)
            if resumed != checkpoint:
                raise ValueError("resume differs from uninterrupted training")
            fit_seconds = time.monotonic() - t0
            q = cnn.quantize(checkpoint["parameters"])
            json_new(directory / "quantization.json", q)
            e = cnn.export(q)
            # Freeze the uncalibrated export before any calibration/test scoring.
            for name in ("program", "profile", "arithmetic"):
                write_new(directory / (name + ".cbor"), e[name].encode())
            write_new(directory / "weights.cbor", e["weights"])
            write_new(directory / "tokenizer.json", e["tokenizer"])
            for path, value in e["parameters"].items():
                target = directory / path
                target.parent.mkdir(exist_ok=True)
                write_new(target, value)
            json_new(directory / "operator-map.json", e["arithmetic"].model_dump(mode="json"))
            calibration = splits["calibration"]
            scores = native(e, [r.prompt for r in calibration])
            if scores != cnn.integer_scores(q, [r.prompt for r in calibration]):
                raise ValueError("calibration integer oracle disagreement")
            threshold = calibrate_threshold(
                tuple(scores),
                tuple(r.label for r in calibration),
                protocol["target_calibration_fpr"],
            )
            float_parameters = cnn.arrays(checkpoint["parameters"])
            float_cal, _ = cnn.forward(
                float_parameters, *cnn.inputs([r.prompt for r in calibration])
            )
            float_threshold = math.nextafter(
                max(float(s) for s, r in zip(float_cal, calibration, strict=True) if r.label == 0),
                math.inf,
            )
            json_new(
                directory / "calibration.json",
                dict(threshold=threshold, scores=scores, float_threshold=float_threshold),
            )
            e["classifier"] = e["classifier"].model_copy(update={"threshold": threshold})
            write_new(directory / "classifier.cbor", e["classifier"].encode())
            enrolled = {
                str(p.relative_to(directory)): sha(p.read_bytes())
                for p in sorted(directory.rglob("*"))
                if p.is_file()
            }
            json_new(directory / "pre-test-enrollment.json", enrolled)
            print(f"seed {seed}: training/export/calibration frozen; scoring test once", flush=True)
            test = splits["test"]
            scores = native(e, [r.prompt for r in test])
            if scores != cnn.integer_scores(q, [r.prompt for r in test]):
                raise ValueError("test integer oracle disagreement")
            float_test, _ = cnn.forward(float_parameters, *cnn.inputs([r.prompt for r in test]))
            predictions = [
                dict(
                    record_id=r.record_id,
                    group_id=r.group_id,
                    label=r.label,
                    score=s,
                    float_score=float(f),
                    block=s >= threshold,
                )
                for r, s, f in zip(test, scores, float_test, strict=True)
            ]
            json_new(directory / "test-predictions.json", predictions)
            result = metrics(tuple(r.label for r in test), tuple(scores), threshold)
            result.update(
                seed=seed,
                threshold=threshold,
                float_threshold=float_threshold,
                float_integer_max_error=max(
                    abs(float(f) - s / 256) for f, s in zip(float_test, scores, strict=True)
                ),
                float_at_integer_threshold_flips=sum(
                    (float(f) >= threshold / 256) != (s >= threshold)
                    for f, s in zip(float_test, scores, strict=True)
                ),
                separately_calibrated_float_flips=sum(
                    (float(f) >= float_threshold) != (s >= threshold)
                    for f, s in zip(float_test, scores, strict=True)
                ),
                final_train_loss=checkpoint["history"][-1],
                training_termination="fixed-200-epoch-budget",
                resume_exact=True,
                fit_and_resume_seconds=fit_seconds,
                seconds=time.monotonic() - t0,
                operator_count=len(e["arithmetic"].nodes),
                graph_work=e["graph"].work,
                quantization_sha256=sha((directory / "quantization.json").read_bytes()),
                program=e["program"].identity().hex(),
                arithmetic=e["arithmetic"].identity().hex(),
                classifier=e["classifier"].identity().hex(),
            )
            result["screen_pass"] = (
                result["tpr"] >= protocol["screen"]["min_test_tpr"]
                and result["fpr"] <= protocol["screen"]["max_test_fpr"]
            )
            json_new(directory / "results.json", result)
            summary.append(result)
            print(
                f"seed {seed}: tp={result['tp']} fp={result['fp']} "
                f"tn={result['tn']} fn={result['fn']}; screen={result['screen_pass']}",
                flush=True,
            )
        after = source_record()
        json_new(output / "source-after.json", after)
        if after != source:
            raise ValueError("runtime source changed during measurement")
        result = dict(
            schema_id="hallmark.contextual-result/1",
            results=summary,
            all_seeds_pass=all(r["screen_pass"] for r in summary),
            actual_seconds=time.monotonic() - start,
            peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            new_compute_usd=0,
            policy_quality_claim=False,
            proof_claim=False,
        )
        json_new(output / "results.json", result)
        manifest = {
            str(p.relative_to(output)): sha(p.read_bytes())
            for p in sorted(output.rglob("*"))
            if p.is_file()
        }
        json_new(output / "manifest.json", manifest)
        print("manifest_sha256=" + sha((output / "manifest.json").read_bytes()), flush=True)
        return result
    except Exception:
        json_new(
            output / "failure.json",
            dict(
                schema_id="hallmark.contextual-failure/1",
                completed_seeds=[r["seed"] for r in summary],
                failed=True,
            ),
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-protocol", required=True)
    args = parser.parse_args()
    run(args.output, args.expected_protocol)
