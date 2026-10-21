"""Run caller-pinned harmless guard probes into a fresh local evidence directory."""

import hashlib
import json
import sys
from pathlib import Path

from check_selection import put

from hallmark.cli import _Parser
from hallmark.errors import HallmarkError, sanitize_exception
from hallmark.guard import GuardSpec, LocalGuard
from hallmark.integrity import load_contract, parse_json, read_bytes


def run(args):
    spec = load_contract(args.spec, GuardSpec)
    if spec.identity() != args.expected_spec:
        raise ValueError("spec pin mismatch")
    raw = read_bytes(args.inputs)
    if hashlib.sha256(raw).hexdigest() != args.expected_inputs:
        raise ValueError("input pin mismatch")
    inputs = parse_json(raw.decode())
    if (
        type(inputs) is not dict
        or set(inputs) != {"schema_id", "fixture_only", "prompts"}
        or inputs["schema_id"] != "hallmark/guard-probes/1"
        or inputs["fixture_only"] is not True
        or type(inputs["prompts"]) is not list
        or not 1 <= len(inputs["prompts"]) <= 16
        or any(
            type(p) is not str or len(p.encode()) > spec.max_prompt_bytes for p in inputs["prompts"]
        )
    ):
        raise ValueError("invalid engineering probes")
    args.output.mkdir(mode=0o700)
    try:
        put(args.output / "inputs.json", inputs)
        put(args.output / "spec.json", spec.model_dump(mode="json"))
        guard = LocalGuard(args.assets, spec, expected_spec=args.expected_spec)
        put(args.output / "runtime.json", guard.record)
        scores = []
        for index, prompt in enumerate(inputs["prompts"]):
            score = guard.score(prompt)
            put(args.output / f"score-{index:02}.json", score)
            scores.append(score)
        result = {
            "schema_id": "hallmark/guard-probe-result/1",
            "runtime": guard.identity,
            "inputs_sha256": args.expected_inputs,
            "probe_count": len(scores),
            "chunks": sum(len(s["chunks"]) for s in scores),
            "fixture_only": True,
            "quality_claim": False,
            "proof_claim": False,
            "passed": all(s["chunks"][-1]["stop"] == s["token_count"] for s in scores),
        }
        put(args.output / "result.json", result)
        return result
    except BaseException:
        put(
            args.output / "failure.json",
            {"schema_id": "hallmark/guard-probe-failure/1", "failed": True},
        )
        raise


def main():
    parser = _Parser(description=__doc__)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--expected-spec", required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--expected-inputs", required=True)
    parser.add_argument("--output", type=Path, required=True)
    try:
        result = run(parser.parse_args())
    except (Exception, KeyboardInterrupt) as exc:
        error = (
            HallmarkError("RESOURCE_EXHAUSTED", "execute")
            if isinstance(exc, KeyboardInterrupt)
            else sanitize_exception(exc, stage="execute")
        )
        print(json.dumps(error.as_dict()), file=sys.stderr)
        return error.exit_code
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
