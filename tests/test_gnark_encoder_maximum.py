"""Native whole-input evidence, frozen witness pins and maximum-run admission."""

import json
import runpy
from pathlib import Path

import pytest

from hallmark import _gnark_maximum as maximum
from hallmark._gnark_probe import digest

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "research/probes/gnark/encoder-maximum-fixture.json"


def test_maximum_fixture_reproduces_every_native_and_oracle_tensor(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    builder = runpy.run_path(str(ROOT / "scripts/build_gnark_encoder_maximum_fixture.py"))
    fixture, assignments = builder["build"](builder["NATIVE_PIN"])
    assert (
        json.dumps(fixture, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode() == FIXTURE.read_bytes()
    assert digest(FIXTURE.read_bytes()) == maximum.ENCODER_FIXTURE_SHA
    rows = maximum.encoder_fixtures(FIXTURE.read_bytes(), maximum.ENCODER_FIXTURE_SHA)
    for case in fixture["cases"]:
        row, valid = rows[case["name"]]
        assert valid and maximum.assignment(row) == assignments[case["name"]]
        assert len(row["public"]) == 100
        assert len(row["trace"]) == 16384 * 121
        assert row["public"][96:98] == [len(case["prompt"]), case["native_chunks"]]
    assert [case["native_score"] for case in fixture["cases"]] == [0, -4, -5]
    with pytest.raises(ValueError, match="pin"):
        builder["build"]("0" * 64)


def test_maximum_negative_roster_preserves_all_other_values():
    rows = maximum.encoder_fixtures(FIXTURE.read_bytes(), maximum.ENCODER_FIXTURE_SHA)
    assert len(rows) == 15 and sum(valid for _, valid in rows.values()) == 3
    for name, (row, valid) in rows.items():
        if valid:
            continue
        original = rows["empty" if name.startswith("empty-") else "maximum"][0]
        changed = [key for key in row if row[key] is not original[key]]
        assert len(changed) == 1
        key = changed[0]
        assert sum(a != b for a, b in zip(row[key], original[key], strict=True)) == 1
    fixture = json.loads(FIXTURE.read_bytes())
    for case in fixture["cases"]:
        assert digest(maximum.assignment(rows[case["name"]][0])) == case["assignment_sha256"]


@pytest.mark.parametrize("rehash", [False, True])
def test_changed_fixture_rejects_even_with_a_new_self_supplied_pin(rehash):
    changed = FIXTURE.read_bytes() + b"\n"
    with pytest.raises(ValueError, match="pin"):
        maximum.encoder_fixtures(
            changed, digest(changed) if rehash else maximum.ENCODER_FIXTURE_SHA
        )


@pytest.mark.parametrize("missing", ["fixture", "pin"])
def test_fixture_and_external_pin_are_required_before_output(tmp_path, missing):
    kwargs = {"encoder_fixture": FIXTURE, "expected_fixture": maximum.ENCODER_FIXTURE_SHA}
    kwargs["encoder_fixture" if missing == "fixture" else "expected_fixture"] = None
    with pytest.raises(ValueError, match="together"):
        maximum.check(tmp_path / "absent", "0" * 64, tmp_path / "output", **kwargs)
    assert not (tmp_path / "output").exists()


def test_unknown_encoder_fixture_fails_before_output(tmp_path):
    binary = tmp_path / "binary"
    binary.write_bytes(b"not executed")
    with pytest.raises(ValueError, match="pin"):
        maximum.check(
            binary,
            digest(binary.read_bytes()),
            tmp_path / "output",
            encoder_fixture=FIXTURE,
            expected_fixture="0" * 64,
        )
    assert not (tmp_path / "output").exists()
