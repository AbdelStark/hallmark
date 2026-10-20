"""Exercise public marker vectors; never grant real policy or execution authority."""

import json
from pathlib import Path

from hallmark.admission import (
    AdmissionProtocol,
    AdmissionReview,
    StudyPolicy,
    validate_reviewed_admission,
)
from hallmark.errors import HallmarkError
from hallmark.manifests import ArtifactDigest

ROOT = Path(__file__).resolve().parents[1]


def main():
    vector = json.loads((ROOT / "fixtures/wire/admission-v1.json").read_text())
    assert vector["fixture_only"] and vector["measurement_permitted"] is False
    policy = StudyPolicy.decode(bytes.fromhex(vector["study-policy"]["cbor_hex"]))
    protocol = AdmissionProtocol.decode(bytes.fromhex(vector["admission"]["cbor_hex"]))
    review = AdmissionReview.decode(bytes.fromhex(vector["admission-review"]["cbor_hex"]))
    files = {k: bytes.fromhex(v) for k, v in vector["files"].items()}
    expected = ArtifactDigest(bytes.fromhex(vector["admission-review"]["identity_hex"]))
    validate_reviewed_admission(protocol, policy, review, expected_review=expected, files=files)
    for pin, documents in ((ArtifactDigest(b"x" * 32), files), (expected, {})):
        try:
            validate_reviewed_admission(
                protocol, policy, review, expected_review=pin, files=documents
            )
        except HallmarkError:
            continue
        raise AssertionError("missing pin/evidence accepted")
    print(
        json.dumps(
            {
                "schema_id": "hallmark/admission-fixture-result/1",
                "status": "matched",
                "protocol": protocol.identity().hex(),
                "negative_checks": 2,
                "measurement_permitted": False,
                "owner_approval_verified": False,
            }
        )
    )


if __name__ == "__main__":
    main()
