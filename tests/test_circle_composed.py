"""Real caller bindings with synthetic models/proof bytes; no crypto acceptance."""

import copy
import sys
from pathlib import Path

import pytest
from test_trained_common import fixture as fixture

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import circle_backend as circle
import composed_input
import trained_common_input as common
from check_circle_composed import binding_negatives, joined_jobs
from classifier_comparison import encoded, sha

pytestmark = pytest.mark.train


def test_circle_composed_exact_statement_and_rejected_bindings(fixture):
    _, _, _, _, originals, old_policy, *_ = fixture
    engines = {
        kind: encoded(
            dict(
                schema="hallmark.circle-enrollment/1",
                external_multiplicities=[1] * 103,
                program_sha256=str(i) * 64,
            )
        )
        for i, kind in enumerate(circle.KINDS)
    }
    enrollment = circle.enroll(engines, originals)
    records, policy, _ = circle.resolve(enrollment, sha(enrollment), originals, old_policy)
    expected, opening = composed_input.request(policy)
    rows = common.evaluate(records, policy, opening, expected)
    bundle = dict(
        schema_id="hallmark.circle-classifier-bundle/1",
        proofs=[
            dict(kind=k, public=r["public"], proof_hex=b"fake".hex())
            for k, r in zip(circle.KINDS, rows, strict=True)
        ],
    )
    assert (
        len(
            joined_jobs(
                enrollment, sha(enrollment), originals, old_policy, opening, expected, bundle
            )
        )
        == 3
    )
    rejected = binding_negatives(
        enrollment, sha(enrollment), originals, old_policy, opening, expected, bundle
    )
    assert len(rejected) == 14 and len(set(rejected)) == 14
    other_expected, other_opening = composed_input.request(policy)
    with pytest.raises(ValueError, match="binding mismatch"):
        joined_jobs(
            enrollment,
            sha(enrollment),
            originals,
            old_policy,
            other_opening,
            other_expected,
            bundle,
        )
    changed = copy.deepcopy(bundle)
    changed["proofs"][0]["public"][98] += 1
    with pytest.raises(ValueError, match="binding mismatch"):
        joined_jobs(enrollment, sha(enrollment), originals, old_policy, opening, expected, changed)
