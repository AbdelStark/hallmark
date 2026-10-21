"""Freeze every numerical chunk class of the fixed synthetic encoder."""

import hashlib
import itertools
import json
from pathlib import Path

from build_encoder_fixture import oracle
from check_gnark_input_scale import vector

from hallmark.classifier_manifest import ArithmeticProfile, ClassifierManifest, InputProfile
from hallmark.integer_encoder import EncoderConstants, EncoderProgram, execute_encoder
from hallmark.openings import TranscriptOpening, derive_input_salt
from hallmark.receipts import ProofInputs

NATIVE = Path(__file__).resolve().parents[1] / "fixtures/wire/integer-encoder-v1.json"
NATIVE_PIN = "8d0551ac2e9c9e2527004bc4a33392844963ffcb17b9589139448db3f068ee7d"


def build(expected_native):
    raw = NATIVE.read_bytes()
    if expected_native != NATIVE_PIN or hashlib.sha256(raw).hexdigest() != expected_native:
        raise ValueError("native fixture pin mismatch")
    native = json.loads(raw)
    objects = []
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
        objects.append(value)
    classifier, program, profile, arithmetic = objects
    kwargs = dict(
        weights=bytes.fromhex(native["weights_cbor_hex"]),
        tokenizer=bytes.fromhex(native["tokenizer_hex"]),
        parameters={k: bytes.fromhex(v) for k, v in native["parameters"].items()},
    )
    table = EncoderConstants.decode(kwargs["weights"]).tensors["embedding-table"]
    classes = {}
    for token in range(256):
        classes.setdefault(table[2 * token : 2 * token + 2], []).append(token)
    if (len(table), len(classes), profile.chunk_size, profile.max_units) != (512, 4, 2, 32768):
        raise ValueError("unsupported numerical class profile")
    representatives = [tokens[0] for tokens in classes.values()]
    if representatives != [0, 1, 2, 3]:
        raise ValueError("unsupported byte representatives")
    base = TranscriptOpening.decode(bytes.fromhex(native["cases"][1]["opening_cbor_hex"]))
    order = [node.output for node in arithmetic.nodes]
    empty = oracle((0, 0), (0, 0), arithmetic)
    padding = [v for node in order for v in empty[node]]
    roster = [()] + [(x,) for x in representatives]
    roster += list(itertools.product(representatives, repeat=2))
    cases = []
    for tokens in roster:
        prompt = bytes(tokens).decode("ascii")
        opening = base.model_copy(update={"prompt": prompt})._validated()
        result = execute_encoder(opening, *objects, **kwargs)
        chunk = result.chunks[0]
        if len(result.chunks) != 1 or chunk.tensors != oracle(chunk.tokens, chunk.mask, arithmetic):
            raise ValueError("native/independent oracle mismatch")
        trace = [v for node in order for v in chunk.tensors[node]]
        if len(trace) != 121 or len(padding) != 121:
            raise ValueError("unexpected tensor coverage")
        public = ProofInputs(
            schema_id="hallmark/proof-inputs/1",
            context=b"c" * 32,
            classifier=classifier.identity(),
            input_digest=result.input_digest,
            unit_count=len(tokens),
            chunk_count=1,
            threshold=classifier.threshold,
            verdict=result.verdict,
        )
        row = vector(8, bytes(tokens))
        row.update(
            name="empty" if not tokens else "bytes-" + bytes(tokens).hex(),
            opening_cbor_hex=opening.encode().hex(),
            native_score=result.score,
            public=list(public.to_fields()),
            salt=list(derive_input_salt(opening.salt, classifier.identity())),
            trace=trace + padding * 3,
        )
        cases.append(row)
    return dict(
        schema_id="hallmark.encoder-class-fixture/1",
        native_fixture_sha256=expected_native,
        capacity=8,
        numerical_chunk_classes=21,
        embedding_classes=[dict(embedding=key, tokens=value) for key, value in classes.items()],
        qualified_backend=False,
        warning="Numerical chunk classes only; no exhaustive transcript, proof or security claim.",
        cases=cases,
    )


if __name__ == "__main__":
    print(json.dumps(build(NATIVE_PIN), sort_keys=True, separators=(",", ":")))
