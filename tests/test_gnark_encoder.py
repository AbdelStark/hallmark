"""Frozen native correspondence and fail-closed proof controller boundaries."""

import importlib.util
import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "research/probes/gnark/encoder-fixture.json"
NATIVE = ROOT / "fixtures/wire/integer-encoder-v1.json"


@pytest.fixture
def probe(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "encoder_probe", ROOT / "scripts/check_gnark_encoder.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_encoder_graph_and_assignments_reproduce(probe):
    builder = runpy.run_path(str(ROOT / "scripts/build_gnark_encoder_fixture.py"))
    graph, fixture = builder["build"](probe.NATIVE_PIN)
    for name, value in (("encoder-graph.json", graph), ("encoder-fixture.json", fixture)):
        assert (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode() == (
            ROOT / "research/probes/gnark" / name
        ).read_bytes()
    assert probe.validate_fixture(FIXTURE.read_bytes(), NATIVE.read_bytes()) == fixture
    with pytest.raises(ValueError, match="pin"):
        builder["build"]("0" * 64)


@pytest.mark.parametrize(
    "change",
    [
        "native",
        "roster",
        "capacity",
        "boolean",
        "trace-shape",
        "trace-value",
        "public",
        "salt",
        "classifier",
    ],
)
def test_controller_rejects_changed_frozen_inputs(probe, change):
    f = json.loads(FIXTURE.read_bytes())
    native = NATIVE.read_bytes()
    row = f["cases"][0]
    if change == "native":
        native += b"\n"
    elif change == "roster":
        f["cases"][-1] = row
    elif change == "capacity":
        f["capacity"] = 32768
    elif change == "boolean":
        row["trace"][0] = False
    elif change == "trace-shape":
        row["trace"].pop()
    elif change == "trace-value":
        row["trace"][0] ^= 1
    elif change in ("public", "salt"):
        row[change][0] ^= 1
    else:
        row["classifier_cbor_hex"] = f["cases"][-1]["classifier_cbor_hex"]
    with pytest.raises(ValueError):
        probe.validate_fixture(json.dumps(f).encode(), native)


def test_roster_changes_each_private_tensor_and_preserves_original(probe):
    f = json.loads(FIXTURE.read_bytes())
    before = json.dumps(f)
    rows, roster = probe.batch_roster(f)
    assert len(rows) == len(roster) == 509 and sum(c["valid"] for c in roster) == 15
    assert len({c["name"] for c in roster}) == 509
    base = probe.assignment(rows["capacity"], True).splitlines()
    for i in range(484):
        changed = probe.assignment(rows[f"trace-{i:03d}"], True).splitlines()
        assert [
            j for j, pair in enumerate(zip(base, changed, strict=True)) if pair[0] != pair[1]
        ] == [len(base) - 484 + i]
    assert json.dumps(f) == before
    assert len(base) == 685 and len(probe.assignment(rows["capacity"], False).splitlines()) == 100


@pytest.mark.parametrize("failure", ["worker", "changed-input", "report"])
def test_worker_failure_retains_evidence_without_success(probe, tmp_path, monkeypatch, failure):
    binary = tmp_path / "binary"
    binary.write_bytes(b"not executed")
    monkeypatch.setattr(probe.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(probe.platform, "machine", lambda: "arm64")
    calls = []

    def worker(binary, work, args, **kwargs):
        assert kwargs["seconds"] == 900 and kwargs["cpu_seconds"] == 3600
        calls.append(args[0])
        if failure == "worker":
            raise OSError("private sentinel")
        if args[0] == "encoder-setup":
            for name in ("circuit.r1cs", "pk.bin", "vk.bin"):
                (work / name).write_bytes(name.encode())
        else:
            for item in json.loads((work / "cases.json").read_bytes()):
                (work / (item["name"] + ".json")).write_text('{"expected_outcome_observed":true}')
                if item["valid"]:
                    (work / (item["name"] + ".proof")).write_bytes(b"proof")
            (work / "pk.bin").write_bytes(b"changed by worker")
        for name in ("sandbox.sb", "plan.json", "stderr.txt"):
            (work / name).write_bytes(b"")
        (work / "stdout.txt").write_text(
            json.dumps(
                dict(
                    schema_id="hallmark.gnark-installation-probe/1",
                    status="passed",
                    constraints=True if failure == "report" else 1,
                    elapsed_ns=1,
                )
            )
        )
        return dict(
            exit_code=0,
            files={
                p.name: {"sha256": probe.digest(p.read_bytes()), "bytes": p.stat().st_size}
                for p in work.iterdir()
            },
        )

    monkeypatch.setattr(probe, "invoke", worker)
    out = tmp_path / "output"
    with pytest.raises((OSError, ValueError)):
        probe.check(
            binary,
            probe.digest(binary.read_bytes()),
            FIXTURE,
            probe.digest(FIXTURE.read_bytes()),
            out,
        )
    assert calls == (
        ["encoder-setup", "encoder-batch"] if failure == "changed-input" else ["encoder-setup"]
    )
    assert (out / "failure.json").is_file() and not (out / "result.json").exists()
    assert "private sentinel" not in (out / "failure.json").read_text()
