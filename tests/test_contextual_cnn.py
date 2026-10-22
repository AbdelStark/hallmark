"""Numerical and admission checks for the optional research candidate."""

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import contextual_cnn as cnn

from hallmark.data import load_records
from hallmark.integer_encoder import execute_encoder
from hallmark.openings import TranscriptOpening
from hallmark.wire import WireError

pytestmark = pytest.mark.train


@pytest.fixture
def np():
    return pytest.importorskip("numpy")


@pytest.fixture
def rows():
    return load_records(Path(__file__).resolve().parents[1] / "fixtures/contextual-scope.jsonl")[:2]


@pytest.mark.parametrize("channels", [8, 32])
def test_gradient_and_resume(np, rows, channels):
    cp = cnn.train(rows, 17, channels=channels, stop=1)
    p = cnn.arrays(cp["parameters"])
    tokens, mask = cnn.inputs([r.prompt for r in rows])
    labels = np.array([r.label for r in rows])
    _, gradients = cnn.gradient(p, tokens, mask, labels)
    for name, index in (
        ("embedding", (ord("r"), 0)),
        ("kernel", (0, 0)),
        ("bias", (2,)),
        ("head", (0, 2)),
        ("out", (0,)),
    ):
        before = p[name][index]
        p[name][index] = before + 1e-6
        plus, _ = cnn.gradient(p, tokens, mask, labels)
        p[name][index] = before - 1e-6
        minus, _ = cnn.gradient(p, tokens, mask, labels)
        p[name][index] = before
        assert gradients[name][index] == pytest.approx((plus - minus) / 2e-6, abs=1e-7)
    assert cnn.train(rows, 17, channels=channels, stop=3, checkpoint=cp) == cnn.train(
        rows, 17, channels=channels, stop=3
    )
    with pytest.raises(ValueError, match="identity mismatch"):
        cnn.train(rows, 29, stop=3, checkpoint=cp)
    altered = (rows[0].model_copy(update={"prompt": rows[0].prompt + "!"}), rows[1])
    with pytest.raises(ValueError, match="identity mismatch"):
        cnn.train(altered, 17, stop=3, checkpoint=cp)
    with pytest.raises(ValueError, match="split"):
        cnn.train((rows[0].model_copy(update={"split": "test"}), rows[1]), 17)


@pytest.mark.parametrize("channels", [8, 32])
def test_export_integer_parity_coverage_and_threshold(np, rows, channels):
    cp = cnn.train(rows, 17, channels=channels, stop=1)
    q = cnn.quantize(cp["parameters"])
    exported = cnn.export(q)
    prompts = ["", "\x00", "é", "A" * 95, "A" * 95 + "B", "A" * 96, rows[0].prompt]
    exact = cnn.integer_scores(q, prompts)
    assert cnn.graph_scores(exported, prompts) == exact
    for prompt, score in zip(prompts, exact, strict=True):
        c = exported["classifier"].model_copy(update={"threshold": score})
        opening = TranscriptOpening(
            schema_id="hallmark/transcript-opening/1",
            system_ref=b"s" * 32,
            salt=b"t" * 32,
            prompt=prompt,
            response="",
        )
        args = (opening, c, exported["program"], exported["profile"], exported["arithmetic"])
        kwargs = {k: exported[k] for k in ("weights", "tokenizer", "parameters")}
        result = execute_encoder(*args, **kwargs)
        assert result.score == score and result.verdict is False
        assert result.unit_count == len(prompt.encode())
        with pytest.raises(WireError):
            execute_encoder(*args, **(kwargs | {"weights": kwargs["weights"] + b"x"}))
    for prompt in ("A" * 97, "é" * 49):
        with pytest.raises(ValueError, match="capacity"):
            cnn.integer_scores(q, [prompt])
    p = copy.deepcopy(cp["parameters"])
    p["embedding"][0][0] = 128.0
    with pytest.raises(ValueError, match="int8"):
        cnn.quantize(p)
    q["values"]["embedding"][0][0] = 128
    with pytest.raises(ValueError, match="range"):
        cnn.export(q)


def test_pair_baseline_and_lineage():
    from collections import Counter

    rows = load_records(Path(__file__).resolve().parents[1] / "fixtures/contextual-scope.jsonl")
    groups = {}
    for row in rows:
        groups.setdefault(row.group_id, []).append(row)
    assert len(groups) == 100
    for pair in groups.values():
        assert len(pair) == 2 and {r.label for r in pair} == {0, 1}
        assert len({r.split for r in pair}) == 1
        assert Counter(pair[0].prompt.encode()) == Counter(pair[1].prompt.encode())


def test_fresh_v2_groups():
    fixture = Path(__file__).resolve().parents[1] / "fixtures"
    old = load_records(fixture / "contextual-scope.jsonl")
    new = load_records(fixture / "contextual-scope-v2.jsonl")
    previous = {r.prompt for r in old}
    assert not previous & {r.prompt for r in new if r.split != "train"}
    assert previous <= {r.prompt for r in new if r.split == "train"}
    assert len({r.group_id for r in new if r.split == "test"}) == 50


def test_quantization_near_threshold_and_ties(np):
    p = {name: np.zeros(shape) for name, shape in cnn.shapes(8).items()}
    with pytest.raises(ValueError):
        cnn.export(cnn.quantize({k: v.tolist() for k, v in p.items()}))
    # Keep the hidden product scale inside the existing 30-fraction-bit envelope.
    p["embedding"][0, 0] = p["kernel"][0, 0] = 0.5
    for value, expected in ((-0.5, 0), (0.5, 0), (1.5, 2), (-1.5, -2)):
        p["out"][0] = value / 256
        q = cnn.quantize({k: v.tolist() for k, v in p.items()})
        assert cnn.integer_scores(q, [""]) == [expected]
        assert cnn.graph_scores(cnn.export(q), [""]) == [expected]
    p["out"][0] = -0.49 / 256
    float_score, _ = cnn.forward(p, *cnn.inputs([""]))
    q = cnn.quantize({k: v.tolist() for k, v in p.items()})
    assert float_score[0] < 0
    assert cnn.integer_scores(q, [""])[0] >= 0


def test_protocol_pin_rejected_before_output(tmp_path):
    from run_contextual_cnn import run

    output = tmp_path / "run"
    with pytest.raises(ValueError, match="caller pin"):
        run(output, "0" * 64)
    assert not output.exists()


@pytest.mark.parametrize("suffix", ["", "-v2"])
def test_every_authored_label_matches_frozen_grammar(suffix):
    fixture = Path(__file__).resolve().parents[1] / "fixtures"
    source_raw = (fixture / f"contextual-source{suffix}.json").read_bytes()
    source = json.loads(source_raw)
    rows = load_records(fixture / f"contextual-scope{suffix}.jsonl")
    for row in rows:
        active, quoted = row.prompt.removeprefix("run: ").split("; quote: ")
        assert row.label == int(active in source["forbidden"])
        assert (active in source["benign"]) != (quoted in source["benign"])
        assert {active, quoted} <= set(source["benign"] + source["forbidden"])
        assert row.source_revision == hashlib.sha256(source_raw).hexdigest()
