"""Reproduce the fixed public training fixture; never run or admit real data."""

import hashlib
import json
import re
import sys
from pathlib import Path

from hallmark._worker import json_new
from hallmark.classifier_manifest import ClassifierManifest, InputProfile
from hallmark.cli import _Parser
from hallmark.contracts import Record
from hallmark.errors import HallmarkError, sanitize_exception
from hallmark.integer_mlp import execute_mlp
from hallmark.integrity import parse_json, read_bytes
from hallmark.mlp_export import compile_mlp
from hallmark.mlp_training import (
    MlpCheckpoint,
    MlpFitConfig,
    _training,
    fit_mlp,
    quantize_mlp,
    runtime_record,
    score_float_mlp,
)
from hallmark.openings import TranscriptOpening


def check(path, expected, output=None):
    raw = read_bytes(path)
    if not re.fullmatch("[0-9a-f]{64}", expected) or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("fixture identity mismatch")
    fixture = parse_json(raw.decode())
    if (
        fixture["schema_id"] != "hallmark.mlp-training-fixture/1"
        or fixture["fixture_only"] is not True
        or type(fixture["numeric_error_bound"]) is not float
        or not 0 < fixture["numeric_error_bound"] < 1
    ):
        raise ValueError("invalid software fixture")
    configs = tuple(MlpFitConfig.model_validate_json(json.dumps(x)) for x in fixture["configs"])
    rows = tuple(Record.model_validate_json(json.dumps(x)) for x in fixture["records"])
    if tuple(c.seed for c in configs) != (17, 29, 43) or any(
        c.policy_id != "fixture.mlp-training" for c in configs
    ):
        raise ValueError("changed seed or policy roster")
    if len(fixture["probes"]) != 7 or len({p["name"] for p in fixture["probes"]}) != 7:
        raise ValueError("invalid probe roster")
    for cfg in configs:
        _training(rows, cfg)
        for probe in fixture["probes"]:
            if (
                not re.fullmatch("[a-z][a-z-]{0,63}", probe["name"])
                or len(probe["prompt"].encode()) > cfg.max_prompt_bytes
            ):
                raise ValueError("invalid probe")
    if output is None:
        return {
            "schema_id": "hallmark.mlp-training-contract-result/1",
            "status": "matched",
            "fixture_only": True,
            "seeds": [c.seed for c in configs],
            "training_executed": False,
        }
    output.mkdir(mode=0o700)
    completed = []
    try:
        json_new(output / "fixture.json", fixture)
        json_new(output / "environment.json", runtime_record())
        for cfg in configs:
            directory = output / f"seed-{cfg.seed}"
            directory.mkdir(mode=0o700)
            json_new(directory / "config.json", cfg.model_dump(mode="json"))
            partial, first = fit_mlp(rows, cfg, steps=31)
            json_new(directory / "partial.json", partial.model_dump(mode="json"))
            restored = MlpCheckpoint.model_validate_json((directory / "partial.json").read_bytes())
            resumed, second = fit_mlp(
                rows, cfg, checkpoint=restored, expected_checkpoint=partial.identity()
            )
            fresh, history = fit_mlp(rows, cfg)
            json_new(directory / "checkpoint.json", fresh.model_dump(mode="json"))
            json_new(directory / "resumed.json", resumed.model_dump(mode="json"))
            json_new(directory / "epochs.json", [s.model_dump(mode="json") for s in history])
            if fresh != resumed or history != (*first, *second):
                raise ValueError("resume mismatch")
            q = quantize_mlp(fresh, cfg)
            json_new(directory / "quantization.json", q.model_dump(mode="json"))
            profile = InputProfile(
                schema_id="hallmark/input-profile/1",
                encoding="utf8-bytes",
                tokenizer_files=(),
                prefix_tokens=(),
                suffix_tokens=(),
                chunk_size=cfg.chunk_bytes,
                overlap=0,
                max_units=cfg.max_prompt_bytes,
                padding_id=0,
                padding_side="right",
            )
            program, arithmetic, weights, params = compile_mlp(
                q.weights,
                profile,
                first_fraction=q.first_fraction,
                hidden_fraction=0,
                last_fraction=q.last_fraction,
            )
            json_new(
                directory / "export.json",
                {
                    "program": program.model_dump(mode="json"),
                    "arithmetic": arithmetic.model_dump(mode="json"),
                    "profile": profile.model_dump(mode="json"),
                    "weights_hex": weights.hex(),
                    "parameters": {k: v.hex() for k, v in params.items()},
                },
            )
            # Public fixture-only identities; no backend enrollment is created by export.
            classifier = ClassifierManifest(
                schema_id="hallmark/classifier/1",
                kind="mlp",
                program=program.identity(),
                weights=program.weights.sha256,
                tokenizer=None,
                input_profile=profile.identity(),
                arithmetic=arithmetic.identity(),
                threshold=0,
                scope="prompt",
                labels=("fixture-benign", "fixture-marker"),
                backend=b"b" * 32,
                verifier_key=b"k" * 32,
                setup=b"s" * 32,
            )
            scores = []
            for probe in fixture["probes"]:
                opening = TranscriptOpening(
                    schema_id="hallmark/transcript-opening/1",
                    salt=b"s" * 32,
                    system_ref=b"c" * 32,
                    prompt=probe["prompt"],
                    response="",
                )
                native = execute_mlp(
                    opening,
                    classifier,
                    program,
                    profile,
                    arithmetic,
                    weights=weights,
                    parameters=params,
                )
                floating = score_float_mlp(fresh.parameters, cfg, probe["prompt"])
                error = abs(native.score / q.score_scale - floating)
                if sum(c.unit_count for c in native.chunks) != len(probe["prompt"].encode()):
                    raise ValueError("omitted input")
                if error > fixture["numeric_error_bound"]:
                    raise ValueError("numeric fixture mismatch")
                scores.append(
                    {
                        "name": probe["name"],
                        "unit_count": native.unit_count,
                        "chunk_count": len(native.chunks),
                        "float_score": floating,
                        "integer_score": native.score,
                        "score_scale": q.score_scale,
                        "absolute_error": error,
                    }
                )
            result = {
                "seed": cfg.seed,
                "checkpoint": fresh.identity(),
                "program": program.identity().hex(),
                "resume_equal": True,
                "optimizer_status": "converged" if fresh.converged else "epoch-limit",
                "epochs": fresh.epoch,
                "first_epoch_loss": history[0].loss,
                "final_loss": fresh.loss,
                "scores": scores,
            }
            json_new(directory / "result.json", result)
            completed.append(result)
        result = {
            "schema_id": "hallmark.mlp-training-fixture-result/1",
            "status": "passed",
            "fixture_only": True,
            "fixture_sha256": expected,
            "seeds": completed,
            "quality_claim": False,
            "backend_enrolled": False,
            "missing": [
                "complete-comparison-roster",
                "grouped-selection",
                "calibration-evaluation",
                "admitted-real-data",
            ],
        }
        json_new(output / "result.json", result)
        return result
    except BaseException:
        json_new(
            output / "failure.json",
            {
                "schema_id": "hallmark.mlp-training-fixture-failure/1",
                "status": "failed",
                "completed_seeds": [r["seed"] for r in completed],
            },
        )
        raise


def main():
    parser = _Parser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--expected-fixture", required=True)
    parser.add_argument("--output", type=Path)
    try:
        args = parser.parse_args()
        result = check(args.fixture, args.expected_fixture, args.output)
    except (Exception, KeyboardInterrupt) as exc:
        error = (
            HallmarkError("RESOURCE_EXHAUSTED", "execute")
            if isinstance(exc, KeyboardInterrupt)
            else sanitize_exception(exc, stage="execute")
        )
        print(json.dumps(error.as_dict()), file=sys.stderr)
        return error.exit_code
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
