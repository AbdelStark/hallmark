"""Documentation figures must be regenerated from the frozen evidence, never hand-edited."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import render_figures


def test_committed_figures_match_the_evidence():
    for name, svg in render_figures.render().items():
        committed = render_figures.OUT / name
        assert committed.read_text() == svg, f"{name} is stale; run scripts/render_figures.py"


def test_figures_are_self_contained_and_themed():
    for name, svg in render_figures.render().items():
        assert "<title" in svg and "<desc" in svg, name
        assert "prefers-color-scheme:dark" in svg, name
        assert "href=" not in svg and "@import" not in svg, name


def test_headline_numbers_come_from_the_reference_record():
    figures = render_figures.render()
    assert "547.75 s" in figures["perf-llm-gpu.svg"]
    assert "53.94 s" in figures["perf-llm-gpu.svg"]
    assert "10.15×" in figures["perf-llm-gpu.svg"]
    assert "24.06 s" in figures["perf-classifier-c1.svg"]
    assert "18,063,779 bytes" in figures["perf-classifier-c1.svg"]
    assert "4.16×" in figures["perf-classifier-gpu.svg"]
    assert "298.88 s" in figures["perf-backends.svg"]
