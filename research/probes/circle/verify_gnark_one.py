"""Fresh single-proof timing entry point for the unchanged py-ecc verifier."""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_ecc"))
from verify import verify  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from hallmark._gnark_probe import read_regular  # noqa: E402


def check(raw, expected):
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("caller pairing-job pin mismatch")
    job = json.loads(raw)
    if type(job) is not dict or set(job) != {
        "key_hex",
        "expected_key_sha256",
        "proof_hex",
        "public",
    }:
        raise ValueError("unexpected single-proof job")
    started = time.perf_counter()
    if not verify(
        bytes.fromhex(job["key_hex"]),
        bytes.fromhex(job["proof_hex"]),
        job["public"],
        expected_key_sha256=job["expected_key_sha256"],
    ):
        raise ValueError("pairing proof failed")
    return dict(
        status="passed",
        proofs_verified=1,
        qualified_backend=False,
        decode_and_pairing_seconds=time.perf_counter() - started,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--job", type=Path, required=True)
    p.add_argument("--expected-job", required=True)
    a = p.parse_args()
    print(json.dumps(check(read_regular(a.job, 65536), a.expected_job)))
