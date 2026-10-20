"""Run a caller-enrolled local comparison dossier; never infer approval from its contents."""

import json
import sys
from pathlib import Path

from hallmark.cli import _Parser
from hallmark.comparison_run import run_comparisons
from hallmark.errors import HallmarkError, sanitize_exception
from hallmark.manifests import ArtifactDigest


def main():
    parser = _Parser(description=__doc__)
    parser.add_argument("--dossier", type=Path, required=True)
    parser.add_argument("--guard-assets", type=Path, required=True)
    parser.add_argument("--expected-review", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture-only", action="store_true")
    try:
        args = parser.parse_args()
        result = run_comparisons(
            args.dossier,
            args.guard_assets,
            args.output,
            expected_review=ArtifactDigest(bytes.fromhex(args.expected_review)),
            fixture_only=args.fixture_only,
        )
    except (Exception, KeyboardInterrupt) as exc:
        error = (
            HallmarkError("RESOURCE_EXHAUSTED", "execute")
            if isinstance(exc, KeyboardInterrupt)
            else sanitize_exception(exc, stage="execute")
        )
        print(json.dumps(error.as_dict()), file=sys.stderr)
        return error.exit_code
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "schema_id",
                    "fixture_only",
                    "baseline_complete",
                    "full_study_complete",
                    "quality_claim",
                )
            }
        )
    )
    return 0 if result["baseline_complete"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
