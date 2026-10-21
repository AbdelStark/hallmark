"""Lower the frozen native encoder data into a separate complete-input proof fixture."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from build_encoder_fixture import oracle
from check_gnark_input_scale import vector

from hallmark.classifier_manifest import ArithmeticProfile, ClassifierManifest, InputProfile
from hallmark.integer_encoder import EncoderConstants, EncoderProgram, execute_encoder
from hallmark.openings import TranscriptOpening, derive_input_salt
from hallmark.receipts import ProofInputs

NATIVE = Path(__file__).resolve().parents[1] / "fixtures/wire/integer-encoder-v1.json"


def build(expected_native):
    raw = NATIVE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_native:
        raise ValueError("native fixture pin mismatch")
    f = json.loads(raw)
    records = {}
    for name, cls in (
        ("classifier", ClassifierManifest),
        ("program", EncoderProgram),
        ("input_profile", InputProfile),
        ("arithmetic", ArithmeticProfile),
    ):
        record = f["records"][name]
        value = cls.decode(bytes.fromhex(record["cbor_hex"]))
        if value.identity().hex() != record["identity_hex"]:
            raise ValueError("native record pin mismatch")
        records[name] = value
    classifier, program, inputs, arithmetic = (
        records[n] for n in ("classifier", "program", "input_profile", "arithmetic")
    )
    weights, tokenizer = bytes.fromhex(f["weights_cbor_hex"]), bytes.fromhex(f["tokenizer_hex"])
    parameters = {k: bytes.fromhex(v) for k, v in f["parameters"].items()}
    classifier.validate_profiles(inputs, arithmetic, parameters=parameters)
    if (
        inputs.chunk_size,
        inputs.max_units,
        inputs.prefix_tokens,
        inputs.suffix_tokens,
        inputs.padding_id,
    ) != (2, 32768, (), (), 0):
        raise ValueError("unsupported frozen graph profile")
    constants = EncoderConstants.decode(weights).tensors
    specs = {t.name: t for t in arithmetic.tensors}
    order = [n.output for n in arithmetic.nodes]
    if len(order) != 39 or sum(math.prod(specs[n].shape) for n in order) != 121:
        raise ValueError("unsupported graph shape")
    graph = dict(
        schema_id="hallmark.gnark-encoder-graph/1",
        native_fixture_sha256=expected_native,
        program=program.identity().hex(),
        input_profile=inputs.identity().hex(),
        arithmetic=arithmetic.identity().hex(),
        weights_sha256=hashlib.sha256(weights).hexdigest(),
        trace=[
            dict(
                name=n,
                count=math.prod(specs[n].shape),
                minimum=specs[n].minimum,
                maximum=specs[n].maximum,
            )
            for n in order
        ],
        constants=constants,
    )
    requests = [
        (c["name"], TranscriptOpening.decode(bytes.fromhex(c["opening_cbor_hex"])), classifier)
        for c in f["cases"]
    ]
    base = requests[1][1]
    for name, text in (("near-capacity", "xxxxxxA"), ("capacity", "xxxxxxAA")):
        requests.append((name, base.model_copy(update={"prompt": text}), classifier))
    # Prespecified conformance boundaries, not calibrated task-quality thresholds.
    score = f["cases"][1]["score"]
    for name, threshold in (
        ("threshold-equal", score),
        ("threshold-above", score + 1),
        ("threshold-below", score - 1),
        ("threshold-minimum", -(2**31)),
        ("threshold-maximum", 2**31 - 1),
    ):
        requests.append((name, base, classifier.model_copy(update={"threshold": threshold})))
    cases = []
    for name, opening, c in requests:
        result = execute_encoder(
            opening,
            c,
            program,
            inputs,
            arithmetic,
            weights=weights,
            tokenizer=tokenizer,
            parameters=parameters,
        )
        units = opening.prompt.encode()
        data = vector(8, units)
        data["salt"] = list(derive_input_salt(opening.salt, c.identity()))
        public = ProofInputs(
            schema_id="hallmark/proof-inputs/1",
            context=b"c" * 32,
            classifier=c.identity(),
            input_digest=result.input_digest,
            unit_count=result.unit_count,
            chunk_count=len(result.chunks),
            threshold=c.threshold,
            verdict=result.verdict,
        )
        data["public"] = list(public.to_fields())
        layers = [chunk.tensors for chunk in result.chunks]
        for chunk in result.chunks:
            if chunk.tensors != oracle(chunk.tokens, chunk.mask, arithmetic):
                raise ValueError("native/oracle mismatch")
        layers += [oracle((0, 0), (0, 0), arithmetic)] * (4 - len(layers))
        data["trace"] = [n for layer in layers for node in order for n in layer[node]]
        assert len(data["trace"]) == 484
        cases.append(
            dict(
                name=name,
                opening_cbor_hex=opening.encode().hex(),
                classifier_cbor_hex=c.encode().hex(),
                native_score=result.score,
                **data,
            )
        )
    fixture = dict(
        schema_id="hallmark.gnark-encoder-fixture/1",
        qualified_backend=False,
        capacity=8,
        profile_maximum=32768,
        program=program.identity().hex(),
        native_fixture_sha256=expected_native,
        warning=(
            "Complete graph at eight-unit circuit capacity only; "
            "synthetic classifier tags and setup, no operational enrollment."
        ),
        cases=cases,
    )
    return graph, fixture


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-native", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    graph, fixture = build(args.expected_native)
    args.output.mkdir()
    for name, value in (("encoder-graph.json", graph), ("encoder-fixture.json", fixture)):
        (args.output / name).write_text(
            json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
        )
