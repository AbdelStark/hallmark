"""Comparison helpers: every recorded figure resolves in checked-in evidence; RSS parsing."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import compare_provers as cp


def test_every_recorded_figure_resolves_to_a_positive_number():
    numbers = cp.recorded()
    assert numbers.keys() == cp.RECORDED.keys()
    for row in numbers.values():
        assert isinstance(row["value"], (int, float)) and row["value"] > 0, row


def test_reads_peak_rss_from_macos_and_linux_time():
    assert cp.max_rss_bytes("   207257600  maximum resident set size\n") == 207257600
    assert cp.max_rss_bytes("\tMaximum resident set size (kbytes): 895472\n") == 895472 * 1024
    with pytest.raises(ValueError, match="no peak RSS"):
        cp.max_rss_bytes("no figure here")
