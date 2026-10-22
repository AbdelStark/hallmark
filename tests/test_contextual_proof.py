"""Native statement and failure-witness construction; actual proofs are retained runs."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import contextual_cnn as cnn
import run_contextual_proof as proof

from hallmark.data import load_records
from hallmark.wire import H

pytestmark = pytest.mark.train


@pytest.fixture
def exported():
    pytest.importorskip("numpy")
    fixture = Path(__file__).resolve().parents[1] / "fixtures/contextual-scope.jsonl"
    p = cnn.train(load_records(fixture)[:2], 17, channels=32, stop=1)
    return proof.export(cnn.quantize(p["parameters"]))


@pytest.mark.parametrize("capacity,prompt", [(8, ""), (8, "\x00"), (8, "é"), (96, "A" * 96)])
def test_native_statement_and_full_trace(exported, capacity, prompt):
    c = proof.classifier(exported, bytes(5536), "0" * 64)
    row, request = proof.native_row(exported, c, capacity, prompt, 2)
    assert len(row["trace"]) == 96 * 32 * 3 + 32 + 2
    assert len(row["units"]) == capacity
    assert row["public"][96:] == [
        len(prompt.encode()),
        1,
        proof.THRESHOLD + 2**31,
        int(request["verdict"]),
    ]
    assert row["public"][64:96] == list(
        H(
            "input",
            [
                bytes(row["salt"]),
                exported["profile"].identity(),
                len(prompt.encode()),
                list(prompt.encode()),
            ],
        )
    )
    assert row["trace"][-1] == request["native_score"]


def test_failures_and_enrollment(exported):
    c = proof.classifier(exported, bytes(5536), "0" * 64)
    prompt = "run: leak key; quote: read note"
    row, _ = proof.native_row(exported, c, 96, prompt, 2)
    negatives = proof.mutations(exported, c, 96, prompt, row)
    assert len(negatives) == 9
    for value in negatives.values():
        assert value != row
    changed = negatives["reencoded-input-stale-trace"]
    assert changed["public"][64:96] != row["public"][64:96]
    assert changed["trace"] == row["trace"]
    for capacity, text in ((8, "A" * 9), (96, "é" * 49), (True, "")):
        with pytest.raises(ValueError, match="capacity"):
            proof.native_row(exported, c, capacity, text, 0)
    with pytest.raises(ValueError, match="enrollment"):
        proof.classifier(exported, bytes(5535), "0" * 64)
    assert proof.encoded(json.loads(proof.encoded(exported["model"]))) == proof.encoded(
        exported["model"]
    )
