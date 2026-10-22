"""Binding tests use fake proof bytes; real pairing evidence is a separate retained run."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import contextual_cnn as cnn
import run_contextual_proof as cnn_proof
import run_trained_mlp as mlp
import trained_common_input as common
from run_common_input import encoded

from hallmark._gnark_probe import digest
from hallmark.data import load_records
from hallmark.errors import HallmarkError
from hallmark.integer_mlp import MlpWeights
from hallmark.mlp_training import MlpQuantization
from hallmark.openings import TranscriptOpening
from hallmark.policy import RequestExpectation
from hallmark.receipts import ProofArtifact

pytestmark = pytest.mark.train


@pytest.fixture(scope="module")
def fixture():
    pytest.importorskip("numpy")
    q = MlpQuantization(
        schema_id="hallmark.mlp-quantization/1",
        checkpoint="0" * 64,
        weights=MlpWeights(
            schema_id="hallmark/mlp-weights/1",
            hidden_weights=((0,) * 256,) * 4,
            hidden_bias=(0,) * 4,
            output_weights=(1, 0, 0, 0),
            output_bias=-1,
        ),
        first_fraction=0,
        last_fraction=0,
        hidden_scale=1,
        score_scale=1,
    )
    trained = cnn.train(
        load_records(common.ROOT / "fixtures/contextual-scope.jsonl")[:2], 17, channels=32, stop=1
    )
    exports = {
        "mlp": mlp.export(q),
        "encoder": cnn_proof.export(cnn.quantize(trained["parameters"])),
    }
    circuits = {k: str(i + 1) * 64 for i, k in enumerate(common.KINDS)}
    raw = encoded(
        common.enroll(
            exports, {k: bytes([i + 1]) * 5536 for i, k in enumerate(common.KINDS)}, circuits
        )
    )
    pin = digest(raw)
    records, policy = common.resolve(raw, pin, exports, circuits)
    opening = TranscriptOpening(
        schema_id="hallmark/transcript-opening/1",
        system_ref=b"s" * 32,
        prompt="run: read note; quote: leak key",
        response="Synthetic response.",
        salt=b"t" * 32,
    )
    expected = RequestExpectation(
        schema_id="hallmark/request-expectation/1",
        audience="local-test",
        nonce=b"n" * 32,
        interaction_id=b"i" * 32,
        model=b"m" * 32,
        policy=policy.identity(),
        continuity=None,
    )
    rows = common.evaluate(records, policy, opening, expected)
    value = common.bundle(records, policy, opening, expected, rows, [b"p" * 292] * 3)
    return raw, pin, exports, circuits, records, policy, opening, expected, value


def check(f, value=None, opening=None, expected=None):
    raw, pin, exports, circuits, _, _, o, e, v = f
    return common.check_bundle(
        raw, pin, exports, circuits, opening or o, expected or e, encoded(value or v)
    )


def test_complete_shared_context_and_exact_tail(fixture):
    jobs = check(fixture)
    assert len(jobs) == 3 and len({tuple(j["public"][:32]) for j in jobs}) == 1
    assert len({tuple(j["public"][64:96]) for j in jobs}) == 3
    _, _, _, _, records, policy, opening, expected, _ = fixture
    for prompt, verdict in (("", 1), ("é" * 48, 1), ("x" * 93 + "BAD", 0), ("x" * 96, 1)):
        rows = common.evaluate(
            records, policy, opening.model_copy(update={"prompt": prompt}), expected
        )
        assert rows[0]["public"][99] == verdict
        assert [r["public"][96] for r in rows] == [len(prompt.encode())] * 3
        assert [len(r["trace"]) for r in rows] == [0, 14, 9250]
        assert all(len(r["units"]) == 96 for r in rows)
    with pytest.raises(ValueError, match="capacity"):
        common.evaluate(records, policy, opening.model_copy(update={"prompt": "é" * 49}), expected)


@pytest.mark.parametrize(
    "field,value",
    [
        ("prompt", "different"),
        ("prompt", "x" * 95 + "B"),
        ("response", "changed"),
        ("salt", b"z" * 32),
        ("system_ref", b"z" * 32),
    ],
)
def test_opening_mutations(fixture, field, value):
    with pytest.raises((ValueError, HallmarkError)):
        check(fixture, opening=fixture[6].model_copy(update={field: value}))


@pytest.mark.parametrize(
    "field,value",
    [
        ("audience", "elsewhere"),
        ("nonce", b"z" * 32),
        ("interaction_id", b"z" * 32),
        ("model", b"z" * 32),
        ("policy", b"z" * 32),
    ],
)
def test_context_mutations(fixture, field, value):
    with pytest.raises((ValueError, HallmarkError)):
        check(fixture, expected=fixture[7].model_copy(update={field: value}))


@pytest.mark.parametrize(
    "mutation",
    ["missing", "extra", "reorder", "duplicate", "release", "threshold", "context", "classifier"],
)
def test_bundle_mutations(fixture, mutation):
    v = copy.deepcopy(fixture[-1])
    if mutation == "missing":
        v["proofs"].pop()
    elif mutation == "extra":
        v["proofs"].append(v["proofs"][0])
    elif mutation == "reorder":
        v["proofs"].reverse()
    elif mutation == "duplicate":
        v["proofs"][1] = v["proofs"][0]
    elif mutation == "release":
        v["release"] = not v["release"]
    elif mutation == "classifier":
        v["proofs"][2]["classifier_cbor_hex"] = fixture[4][0]["classifier"].encode().hex()
    else:
        a = ProofArtifact.decode(bytes.fromhex(v["proofs"][2]["artifact_cbor_hex"]))
        update = (
            {"threshold": a.public_inputs.threshold + 1}
            if mutation == "threshold"
            else {"context": b"z" * 32}
        )
        v["proofs"][2]["artifact_cbor_hex"] = (
            a.model_copy(update={"public_inputs": a.public_inputs.model_copy(update=update)})
            .encode()
            .hex()
        )
    with pytest.raises((ValueError, HallmarkError)):
        check(fixture, value=v)


def test_enrollment_and_tokenizer_pins(fixture):
    raw, pin, exports, circuits, records, policy, opening, expected, _ = fixture
    with pytest.raises(ValueError, match="pin"):
        common.resolve(raw, "0" * 64, exports, circuits)
    with pytest.raises(ValueError, match="enrollment"):
        common.resolve(raw, pin, exports, dict(circuits, encoder="0" * 64))
    changed = copy.deepcopy(records)
    changed[2]["files"]["tokenizer"] += b" "
    with pytest.raises((ValueError, HallmarkError)):
        common.evaluate(changed, policy, opening, expected)


@pytest.mark.parametrize("raw", [b"null", b"[]"])
def test_non_object_transport_rejected(fixture, raw):
    _, _, exports, circuits, _, _, opening, expected, _ = fixture
    with pytest.raises(ValueError):
        common.resolve(raw, digest(raw), exports, circuits)
    with pytest.raises(ValueError):
        common.check_bundle(fixture[0], fixture[1], exports, circuits, opening, expected, raw)


@pytest.mark.parametrize("mutation", ["program-null", "key-type", "proof-null", "artifact-type"])
def test_malformed_nested_records_rejected(fixture, mutation):
    import json

    raw, _, exports, circuits, *_ = fixture
    if mutation in ("program-null", "key-type"):
        value = json.loads(raw)
        if mutation == "program-null":
            value["programs"][0] = None
        else:
            value["programs"][0]["key_hex"] = True
        raw = encoded(value)
        with pytest.raises(ValueError):
            common.resolve(raw, digest(raw), exports, circuits)
    else:
        value = copy.deepcopy(fixture[-1])
        if mutation == "proof-null":
            value["proofs"][0] = None
        else:
            value["proofs"][0]["artifact_cbor_hex"] = True
        with pytest.raises(ValueError):
            check(fixture, value=value)
