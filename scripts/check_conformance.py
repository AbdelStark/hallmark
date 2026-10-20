"""Run frozen conformance cases. Required unavailable evidence makes the default gate fail."""

import json
import sys
from pathlib import Path

from hallmark.cli import _Parser
from hallmark.conformance import implementation_identity, load_corpus, run_corpus
from hallmark.errors import sanitize_exception
from hallmark.manifests import ArtifactDigest
from hallmark.wire import WireError

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--expected-corpus", required=True)
    parser.add_argument("--software-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    try:
        args = parser.parse_args(argv)
        if len(args.expected_corpus) != 64:
            raise WireError("INPUT_INVALID")
        expected = ArtifactDigest(bytes.fromhex(args.expected_corpus))
        corpus = load_corpus(args.corpus)
        primary = implementation_identity(ROOT)
        report = run_corpus(
            corpus,
            args.corpus.parent,
            expected_corpus=expected,
            primary=primary,
            software_only=args.software_only,
        )
        if args.self_test:
            if not report.software_passed or not report.unavailable:
                raise WireError("INPUT_INVALID")
            first = next(case for case in corpus.cases if case.check != "unavailable")
            wrong = first.expected.model_copy(update={"integers": first.expected.integers + (123,)})
            mutant = corpus.model_copy(
                update={
                    "cases": tuple(
                        case.model_copy(update={"expected": wrong})
                        if case.case_id == first.case_id
                        else case
                        for case in corpus.cases
                    )
                }
            )
            rejected = run_corpus(
                mutant,
                args.corpus.parent,
                expected_corpus=mutant.identity(),
                primary=primary,
                software_only=True,
            )
            if rejected.exit_code() != 1 or rejected.mismatched != 1:
                raise RuntimeError("expected-result corruption was not rejected")
            strict = report.model_copy(update={"scope": "all-required-evidence"})._validated()
            if strict.exit_code() != 3:
                raise RuntimeError("required missing evidence was not rejected")
            report = report.model_copy(update={"self_tested": True})._validated()
        print(report.model_dump_json())
        return report.exit_code()
    except Exception as exc:
        failure = sanitize_exception(exc, stage="execute")
    print(json.dumps(failure.as_dict(), sort_keys=True), file=sys.stderr)
    return failure.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
