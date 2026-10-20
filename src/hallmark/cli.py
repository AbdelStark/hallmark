"""Local research commands. No external service, attestation or proof stub."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

from hallmark.contracts import Contract, Experiment, LinearArtifact, Record, RunManifest
from hallmark.data import dataset_summary, load_records
from hallmark.errors import HallmarkError, Stage, sanitize_exception
from hallmark.experiment import audit_run, run_experiment
from hallmark.integrity import load_contract
from hallmark.reference import decision


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # argparse's message may contain arbitrary argument text or a private path.
        raise HallmarkError("INPUT_INVALID", "parse")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="hallmark", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    schemas: dict[str, type[Contract]] = {
        "record": Record,
        "experiment": Experiment,
        "model": LinearArtifact,
        "run": RunManifest,
    }
    schema = sub.add_parser("schema", help="emit a machine-readable JSON input contract")
    schema.add_argument("contract", choices=schemas)
    validate = sub.add_parser("validate-data", help="validate records and cross-split leakage")
    validate.add_argument("dataset", type=Path)
    run = sub.add_parser("run", help="train and evaluate the offline linear research baseline")
    run.add_argument("config", type=Path)
    run.add_argument("--output", type=Path, required=True)
    audit = sub.add_parser("audit-run", help="replay a caller-pinned research run, not a ZK proof")
    audit.add_argument("run_directory", type=Path)
    audit.add_argument("--dataset", type=Path, required=True)
    audit.add_argument("--expected-manifest", required=True)
    predict = sub.add_parser("predict", help="integer baseline prediction on a local text file")
    predict.add_argument("model", type=Path)
    predict.add_argument("text_file", type=Path)
    registry = sub.add_parser(
        "registry-check", help="verify and persist external registry enrollment"
    )
    registry.add_argument("snapshot", type=Path)
    registry.add_argument("--trust", type=Path, required=True)
    registry.add_argument("--state", type=Path, required=True)
    registry.add_argument("--now", type=int, required=True)
    registry.add_argument("--history", type=Path, nargs="*", default=[])
    registry.add_argument("--old-trust", type=Path)
    registry.add_argument("--transition", type=Path)
    registry.add_argument("--previous", type=Path)
    qualify_parser = sub.add_parser("qualify", help="run pinned local backend qualification stages")
    qualify_parser.add_argument("protocol", type=Path)
    qualify_parser.add_argument("--expected-protocol", required=True)
    qualify_parser.add_argument("--output", type=Path, required=True)
    stage: Stage = "parse"
    result: dict[str, Any]
    try:
        args = parser.parse_args(argv)
        stage = "execute"
        if args.command == "schema":
            result = schemas[args.contract].model_json_schema()
        elif args.command == "validate-data":
            result = {"status": "valid", "splits": dataset_summary(load_records(args.dataset))}
        elif args.command == "run":
            result = {"manifest_sha256": run_experiment(args.config, args.output)}
        elif args.command == "audit-run":
            result = audit_run(args.run_directory, args.dataset, args.expected_manifest)
        elif args.command == "qualify":
            from hallmark.qualification import qualify

            result = qualify(args.protocol, args.expected_protocol, args.output)
            print(json.dumps(result, sort_keys=True, allow_nan=False))
            return 3
        elif args.command == "registry-check":
            from hallmark.registry_cli import check_registry

            result = check_registry(
                args.snapshot,
                args.trust,
                args.state,
                args.now,
                history_paths=tuple(args.history),
                old_trust_path=args.old_trust,
                transition_path=args.transition,
                previous_path=args.previous,
            )
        else:
            from hallmark.integrity import read_bytes

            result = decision(
                load_contract(args.model, LinearArtifact),
                read_bytes(args.text_file).decode("utf-8"),
            )
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except Exception as exc:
        failure = sanitize_exception(exc, stage=stage)
    print(json.dumps(failure.as_dict(), sort_keys=True, allow_nan=False), file=sys.stderr)
    return failure.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
