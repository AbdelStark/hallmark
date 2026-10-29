import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import classifier_comparison as comparison


def test_frozen_cases_protocol_and_scalar_semantics():
    plan, corpus = comparison.documents()
    assert plan["capacity_bytes"] == 96 and plan["circle"]["fri_queries"] == 80
    assert comparison.scalar_conformance(corpus) == 20
    assert [r["verdicts"] for r in corpus["requests"]] == [[1, 1, 1], [1, 1, 0], [0, 1, 1]]
    assert len(corpus["rejection_boundary"]) == 13
    for row in corpus["input_boundaries"]:
        raw = (row["unit"] * row["repeat"] + row["suffix"]).encode()
        assert (len(raw) <= 96) is row["accepted"]
        if row["accepted"]:
            assert int(b"BAD" not in raw) == row["rule_verdict"]


def test_model_admission_rejects_modified_quantization(tmp_path):
    path = tmp_path / "mlp-training/seed-17"
    path.mkdir(parents=True)
    (path / "quantization.json").write_text("{}")
    with pytest.raises(ValueError, match="frozen published"):
        comparison.exports(tmp_path)


def test_scalar_contract_does_not_silently_accept_changed_rounding():
    _, corpus = comparison.documents()
    corpus["rounding"][0]["expected"] += 1
    with pytest.raises(ValueError, match="rounding contract"):
        comparison.scalar_conformance(corpus)


@pytest.mark.train
def test_cnn_admission_bound_rejects_possible_i32_overflow(synthetic_exports):
    from hallmark.wire import decode, encode

    exported = synthetic_exports["encoder"]
    assert comparison.cnn_integer_bounds(exported)["head_max_absolute_partial_or_product"] < 2**31
    weights = decode(exported["weights"])
    weights["tensors"]["convolution-w"] = [2**31] * len(weights["tensors"]["convolution-w"])
    with pytest.raises(ValueError, match="i32 bounds"):
        comparison.cnn_integer_bounds(dict(exported, weights=encode(weights)))
