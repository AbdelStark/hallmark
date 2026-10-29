"""CNN Circle circuit against native rows; synthetic exports make no proof or quality claim."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("numpy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import contextual_proof
from check_circle_engine import encode
from circle_classifiers import encoder
from run_circle_classifiers import trace_parity

pytestmark = pytest.mark.train


def test_native_parity_witness_and_prompt_independent_program(synthetic_exports):
    exported = synthetic_exports["encoder"]
    program = None
    for prompt in ("", "B", "é" * 48, "A" * 96):
        row, _ = contextual_proof.native_row(exported, exported["classifier"], 96, prompt, 0)
        c, trace = encoder(row["public"], prompt.encode(), bytes(row["salt"]), exported)
        assert c.check_witness()
        trace_parity("encoder", trace, row)
        raw = encode(c.program())
        assert program is None or raw == program
        program = raw
        # Wire 102 is the public strict verdict; flipping it keeps every other witness value.
        changed = c.witness()
        changed[102] ^= 1
        assert not c.check_witness(changed)
