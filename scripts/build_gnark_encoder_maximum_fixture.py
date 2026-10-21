"""Freeze native-checked maximum encoder assignments without publishing full traces."""

import argparse
import json
from pathlib import Path

from build_encoder_fixture import oracle

from hallmark._gnark_maximum import CAPACITY, ENCODER_CIRCUIT_SHA, assignment, vector
from hallmark._gnark_probe import digest, write_new
from hallmark.classifier_manifest import ArithmeticProfile, ClassifierManifest, InputProfile
from hallmark.integer_encoder import EncoderProgram, execute_encoder
from hallmark.openings import TranscriptOpening, derive_input_salt
from hallmark.receipts import ProofInputs

NATIVE = Path(__file__).resolve().parents[1] / "fixtures/wire/integer-encoder-v1.json"
NATIVE_PIN = "8d0551ac2e9c9e2527004bc4a33392844963ffcb17b9589139448db3f068ee7d"


def build(expected_native):
    raw = NATIVE.read_bytes()
    if expected_native != NATIVE_PIN or digest(raw) != expected_native:
        raise ValueError("native fixture pin mismatch")
    native = json.loads(raw)
    objects = {}
    for name, cls in (
        ("classifier", ClassifierManifest),
        ("program", EncoderProgram),
        ("input_profile", InputProfile),
        ("arithmetic", ArithmeticProfile),
    ):
        record = native["records"][name]
        value = cls.decode(bytes.fromhex(record["cbor_hex"]))
        if value.identity().hex() != record["identity_hex"]:
            raise ValueError("native identity mismatch")
        objects[name] = value
    classifier, program, profile, arithmetic = (
        objects[k] for k in ("classifier", "program", "input_profile", "arithmetic")
    )
    base = TranscriptOpening.decode(bytes.fromhex(native["cases"][1]["opening_cbor_hex"]))
    order = [node.output for node in arithmetic.nodes]
    if profile.chunk_size != 2 or profile.max_units != CAPACITY or len(order) != 39:
        raise ValueError("unsupported native profile")
    cases, traces, oracles, assignments = [], {}, {}, {}
    kwargs = dict(
        weights=bytes.fromhex(native["weights_cbor_hex"]),
        tokenizer=bytes.fromhex(native["tokenizer_hex"]),
        parameters={k: bytes.fromhex(v) for k, v in native["parameters"].items()},
    )
    for name, count in (("empty", 0), ("near", CAPACITY - 1), ("maximum", CAPACITY)):
        prompt = "x" * (count - 1) + "A" if count else ""
        opening = base.model_copy(update={"prompt": prompt})._validated()
        result = execute_encoder(opening, classifier, program, profile, arithmetic, **kwargs)
        row = vector(prompt.encode("ascii"))
        row["salt"] = list(derive_input_salt(opening.salt, classifier.identity()))
        public = ProofInputs(
            schema_id="hallmark/proof-inputs/1",
            context=b"c" * 32,
            classifier=classifier.identity(),
            input_digest=result.input_digest,
            unit_count=count,
            chunk_count=len(result.chunks),
            threshold=classifier.threshold,
            verdict=result.verdict,
        )
        row["public"], row["trace"] = list(public.to_fields()), []
        for chunk in result.chunks:
            key = bytes(chunk.tokens).hex() + ":" + "".join(str(n) for n in chunk.mask)
            if key not in oracles:
                oracles[key] = oracle(chunk.tokens, chunk.mask, arithmetic)
            if chunk.tensors != oracles[key]:
                raise ValueError("native/independent oracle mismatch")
            values = [v for node in order for v in chunk.tensors[node]]
            if len(values) != 121 or (key in traces and values != traces[key]):
                raise ValueError("invalid deterministic chunk trace")
            traces[key] = values
            row["trace"].extend(values)
        row["trace"].extend(traces["0000:00"] * (CAPACITY // 2 - len(result.chunks)))
        if len(row["trace"]) != CAPACITY // 2 * 121:
            raise ValueError("incomplete circuit trace")
        assignments[name] = assignment(row)
        cases.append(
            dict(
                name=name,
                prompt=prompt,
                native_score=result.score,
                public=row["public"],
                assignment_sha256=digest(assignments[name]),
                assignment_bytes=len(assignments[name]),
                native_chunks=len(result.chunks),
            )
        )
    return dict(
        schema_id="hallmark.encoder-maximum-fixture/1",
        qualified_backend=False,
        native_fixture_sha256=NATIVE_PIN,
        circuit_sha256=ENCODER_CIRCUIT_SHA,
        records={k: native["records"][k] for k in objects},
        opening_salt_hex=base.salt.hex(),
        salt=list(derive_input_salt(base.salt, classifier.identity())),
        chunk_traces=traces,
        cases=cases,
        source="Owned synthetic pipeline fixtures; no quality or independent review claim.",
    ), assignments


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-native", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fixture, assignments = build(args.expected_native)
    args.output.mkdir(mode=0o700)
    write_new(
        args.output / "encoder-maximum-fixture.json",
        (json.dumps(fixture, sort_keys=True, separators=(",", ":")) + "\n").encode(),
    )
    for name, raw in assignments.items():
        write_new(args.output / (name + ".txt"), raw)
