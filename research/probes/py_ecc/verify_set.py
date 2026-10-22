"""Verify three caller-pinned pairing jobs with the separately implemented arithmetic."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify import verify  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from hallmark._gnark_probe import read_regular  # noqa: E402


def check(raw, expected):
    if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("pairing job enrollment mismatch")
    jobs = json.loads(raw)
    if type(jobs) is not list or len(jobs) != 3:
        raise ValueError("expected three pairing jobs")
    for job in jobs:
        if set(job) != {"key_hex", "expected_key_sha256", "proof_hex", "public"}:
            raise ValueError("invalid pairing job")
        if not verify(
            bytes.fromhex(job["key_hex"]),
            bytes.fromhex(job["proof_hex"]),
            job["public"],
            expected_key_sha256=job["expected_key_sha256"],
        ):
            raise ValueError("proof failed")
    return {"status": "passed", "proofs_verified": 3, "qualified_backend": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--expected-jobs", required=True)
    args = parser.parse_args()
    print(json.dumps(check(read_regular(args.jobs, 65536), args.expected_jobs)))
