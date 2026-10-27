"""Offline admission checks; complete published-weight replay is release evidence."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from predict_published_classifier import predict


@pytest.mark.parametrize("prompt", ["A" * 97, "é" * 49, "😀" * 25])
def test_byte_capacity_rejects_before_loading_weights(prompt):
    with pytest.raises(ValueError, match="96 UTF-8 bytes"):
        predict("cnn", Path("missing.json"), prompt)


@pytest.mark.parametrize("kind", ["mlp", "cnn"])
def test_changed_quantization_rejects_before_parsing(tmp_path, kind):
    path = tmp_path / "quantization.json"
    path.write_text('{"weights": "untrusted"}')
    with pytest.raises(ValueError, match="differs from the published"):
        predict(kind, path, "")


def test_unknown_model_rejects_before_loading():
    with pytest.raises(ValueError, match="choose mlp or cnn"):
        predict("other", Path("missing.json"), "")


def test_symlink_weights_reject(tmp_path):
    path = tmp_path / "weights.json"
    path.write_text("{}")
    link = tmp_path / "quantization.json"
    link.symlink_to(path)
    with pytest.raises(OSError):
        predict("mlp", link, "")
