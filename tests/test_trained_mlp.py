"""Native export/witness boundaries; actual proof evidence lives in retained runs."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_trained_mlp as trained

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
    c = trained.classifier(exported, b"k" * 5536, "c" * 64)
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
    assert len(row["units"]) == capacity
    assert len(row["encoded"]) == 2 * capacity + 6
    assert len(row["trace"]) == ((capacity + 511) // 512) * 14
    assert sum(row["unit_active"]) == len(prompt.encode())
    assert all(x == 0 for x in row["encoded"][row["positions"][-1] :])


def test_enrollment_changes_bind_all_public_inputs(exported):
    a = trained.classifier(exported, b"k" * 5536, "c" * 64)
    b = trained.classifier(exported, b"j" * 5536, "c" * 64)
    assert a.identity() != b.identity()
    x, _ = trained.native_row(exported, a, 8, "B", 0)
    y, _ = trained.native_row(exported, b, 8, "B", 0)
    assert x["public"][:96] != y["public"][:96]
    assert x["public"][96:] == y["public"][96:]
    assert trained.classifier(exported, b"k" * 5536, "d" * 64).identity() != a.identity()


@pytest.mark.parametrize("capacity,prompt", [(8, "x" * 9), (1024, "é" * 513), (32, "x")])
def test_capacity_rejects_without_truncation(exported, capacity, prompt):
    c = trained.classifier(exported, b"k" * 5536, "c" * 64)
    with pytest.raises(ValueError, match="capacity"):
        trained.native_row(exported, c, capacity, prompt, 0)


def test_bad_key_rejects(exported):
    with pytest.raises(ValueError, match="key"):
        trained.classifier(exported, b"k", "c" * 64)


def test_bad_binary_is_rejected_before_output(monkeypatch, tmp_path):
    monkeypatch.setattr(trained.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(trained.platform, "machine", lambda: "arm64")
    binary = tmp_path / "binary"
    binary.write_bytes(b"invalid")
    with pytest.raises(ValueError, match="binary pin"):
        trained.run(binary, "0" * 64, Path(sys.executable), tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_cli_preserves_verifier_virtual_environment(monkeypatch, tmp_path):
    interpreter = tmp_path / "venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.symlink_to(sys.executable)
    calls = []
    monkeypatch.setattr(trained, "run", lambda *args: calls.append(args))
    trained.main(
        [
            "--binary",
            str(tmp_path / "probe"),
            "--expected-binary",
            "0" * 64,
            "--verifier-python",
            str(interpreter),
            "--output",
            str(tmp_path / "output"),
        ]
    )
    assert calls[0][2] == interpreter
    assert calls[0][2] != interpreter.resolve()
