"""Native export/witness boundaries; actual proof evidence lives in retained runs."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import trained_mlp as trained

from hallmark.classifier_manifest import ClassifierManifest
from hallmark.integer_mlp import MlpWeights
from hallmark.mlp_training import MlpQuantization
from hallmark.wire import H


@pytest.fixture
def exported():
    row = [0] * 256
    row[ord("A")], row[ord("B")] = -1, 1
    q = MlpQuantization(
        schema_id="hallmark.mlp-quantization/1",
        checkpoint="0" * 64,
        weights=MlpWeights(
            schema_id="hallmark/mlp-weights/1",
            hidden_weights=(tuple(row), *((0,) * 256 for _ in range(3))),
            hidden_bias=(0, 0, 0, 0),
            output_weights=(1, 0, 0, 0),
            output_bias=-1,
        ),
        first_fraction=0,
        last_fraction=0,
        hidden_scale=1,
        score_scale=1,
    )
    return trained.export(q)


def manifest(exported, tag="k"):
    return ClassifierManifest(
        schema_id="hallmark/classifier/1",
        kind="mlp",
        program=exported["program"].identity(),
        weights=exported["program"].weights.sha256,
        tokenizer=None,
        input_profile=exported["profile"].identity(),
        arithmetic=exported["arithmetic"].identity(),
        threshold=0,
        scope="prompt",
        labels=("fixture-benign", "fixture-marker"),
        backend=H("backend", tag),
        verifier_key=H("key", tag),
        setup=H("setup", tag),
    )


@pytest.mark.parametrize(
    "capacity,prompt,score,chunks",
    [
        (8, "", -1, 1),
        (8, "A", -1, 1),
        (8, "B", 0, 1),
        (8, "éB", 0, 1),
        (1024, "A" * 512, -1, 1),
        (1024, "B" * 512, 511, 1),
        (1024, "A" * 512 + "B" * 512, 511, 2),
        (1024, "A" * 1023 + "B", -1, 2),
    ],
    ids=[
        "empty",
        "one-pass",
        "tie-block",
        "unicode",
        "full-pass",
        "full-block",
        "two-chunks",
        "tail",
    ],
)
def test_exact_export_inputs_and_chunk_scores(exported, capacity, prompt, score, chunks):
    c = manifest(exported)
    row, metadata = trained.native_row(exported, c, capacity, prompt, 0)
    assert metadata["native_score"] == score
    assert metadata["verdict"] == (score < 0)
    assert row["public"][96:] == [len(prompt.encode()), chunks, 2**31, int(score < 0)]
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
    assert len(row["trace"]) == ((capacity + 511) // 512) * 14


def test_enrollment_changes_bind_all_public_inputs(exported):
    a, b = manifest(exported, "k"), manifest(exported, "j")
    assert a.identity() != b.identity()
    x, _ = trained.native_row(exported, a, 8, "B", 0)
    y, _ = trained.native_row(exported, b, 8, "B", 0)
    assert x["public"][:96] != y["public"][:96]
    assert x["public"][96:] == y["public"][96:]


@pytest.mark.parametrize("capacity,prompt", [(8, "x" * 9), (1024, "é" * 513), (32, "x")])
def test_capacity_rejects_without_truncation(exported, capacity, prompt):
    c = manifest(exported)
    with pytest.raises(ValueError, match="capacity"):
        trained.native_row(exported, c, capacity, prompt, 0)
