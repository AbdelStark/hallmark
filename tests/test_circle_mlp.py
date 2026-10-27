import sys
from pathlib import Path

from test_trained_mlp import exported as exported

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_trained_mlp as native
from check_circle_engine import encode
from circle_classifiers import mlp
from run_circle_classifiers import trace_parity


def test_complete_counts_native_parity_and_witness_independent_program(exported):
    classifier = native.classifier(exported, b"k" * 5536, "c" * 64)
    program = None
    for prompt in ("", "B", "A" * 96, "é" * 48):
        row, _ = native.native_row(exported, classifier, 1024, prompt, 0)
        row["trace"] = row["trace"][:14]
        c, trace = mlp(row["public"], prompt.encode(), bytes(row["salt"]), exported)
        assert c.check_witness()
        trace_parity("mlp", trace, row)
        assert [w.value for w in trace["counts"]] == [prompt.encode().count(i) for i in range(256)]
        raw = encode(c.program())
        assert program is None or raw == program
        program = raw
        # This changes the claimed strict verdict while keeping the complete witness.
        changed = c.witness()
        changed[102] ^= 1
        assert not c.check_witness(changed)
