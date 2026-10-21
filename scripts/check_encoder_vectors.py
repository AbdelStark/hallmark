"""Check caller-pinned synthetic encoder traces using the installed native runtime."""

import argparse
import hashlib
import json
from pathlib import Path

from hallmark.classifier_manifest import ArithmeticProfile, ClassifierManifest, InputProfile
from hallmark.integer_encoder import EncoderProgram, execute_encoder
from hallmark.openings import TranscriptOpening


def check(path: Path, expected: str) -> dict:
    with path.open("rb") as stream:
        raw = stream.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("fixture pin or size mismatch")
    fixture = json.loads(raw)
    if (
        fixture["schema_id"] != "hallmark/encoder-fixture/1"
        or fixture["qualified_backend"] is not False
    ):
        raise ValueError("not a synthetic native fixture")
    artifacts = []
    for name, cls in (
        ("classifier", ClassifierManifest),
        ("program", EncoderProgram),
        ("input_profile", InputProfile),
        ("arithmetic", ArithmeticProfile),
    ):
        record = fixture["records"][name]
        artifact = cls.decode(bytes.fromhex(record["cbor_hex"]))
        if artifact.identity().hex() != record["identity_hex"]:
            raise ValueError("record pin mismatch")
        artifacts.append(artifact)
    tensors = 0
    for case in fixture["cases"]:
        result = execute_encoder(
            TranscriptOpening.decode(bytes.fromhex(case["opening_cbor_hex"])),
            *artifacts,
            weights=bytes.fromhex(fixture["weights_cbor_hex"]),
            tokenizer=bytes.fromhex(fixture["tokenizer_hex"]),
            parameters={key: bytes.fromhex(value) for key, value in fixture["parameters"].items()},
        )
        if [chunk.model_dump(mode="json") for chunk in result.chunks] != case["chunks"] or (
            result.score,
            result.verdict,
        ) != (case["score"], case["verdict"]):
            raise ValueError("native encoder trace mismatch")
        tensors += sum(len(chunk.tensors) for chunk in result.chunks)
    return dict(
        schema_id="hallmark/encoder-vector-check/1",
        cases=len(fixture["cases"]),
        tensors=tensors,
        fixture_sha256=expected,
        qualified_backend=False,
        evidence_class="synthetic-native-conformance",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--expected-fixture", required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.fixture, args.expected_fixture), sort_keys=True))
