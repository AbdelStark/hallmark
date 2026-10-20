"""Build public synthetic MLP vectors in a new file; expectations use integer division."""

import argparse
import json
from pathlib import Path

from hallmark.classifier_manifest import (
    ClassifierManifest,
    InputProfile,
)
from hallmark.integer_mlp import MlpWeights
from hallmark.mlp_export import compile_mlp
from hallmark.openings import TranscriptOpening


def rounded(value, source, target=0):
    shift = source - target
    if shift <= 0:
        return value << -shift
    divisor = 1 << shift
    quotient, remainder = divmod(abs(value), divisor)
    quotient += 2 * remainder > divisor or (2 * remainder == divisor and quotient % 2 == 1)
    return -quotient if value < 0 else quotient


def export(weights, inputs, *, first_fraction=1, hidden_fraction=0, last_fraction=1, threshold=2):
    """Fixture-only assembly of the documented explicit export; no training or admission."""
    program, arithmetic, raw, parameters = compile_mlp(
        weights,
        inputs,
        first_fraction=first_fraction,
        hidden_fraction=hidden_fraction,
        last_fraction=last_fraction,
    )
    classifier = ClassifierManifest(
        schema_id="hallmark/classifier/1",
        kind="mlp",
        program=program.identity(),
        weights=program.weights.sha256,
        tokenizer=None,
        input_profile=inputs.identity(),
        arithmetic=arithmetic.identity(),
        threshold=threshold,
        scope="prompt",
        labels=("fixture-benign", "fixture-marker"),
        backend=b"b" * 32,
        verifier_key=b"k" * 32,
        setup=b"s" * 32,
    )
    return classifier, program, inputs, arithmetic, raw, parameters


def formula(text, weights, chunk_size, first_fraction, hidden_fraction, last_fraction):
    """Separate direct byte-sum formula, without primary runtime or rounding helpers."""
    raw = text.encode()
    chunks = []
    for index, start in enumerate(range(0, max(1, len(raw)), chunk_size)):
        content = raw[start : start + chunk_size]
        counts = [content.count(byte) for byte in range(256)]
        accumulators = [
            bias + sum(row[byte] for byte in content)
            for row, bias in zip(weights.hidden_weights, weights.hidden_bias, strict=True)
        ]
        hidden = [rounded(value, first_fraction, hidden_fraction) for value in accumulators]
        activated = [max(0, value) for value in hidden]
        output = weights.output_bias + sum(
            value * weight for value, weight in zip(activated, weights.output_weights, strict=True)
        )
        chunks.append(
            dict(
                index=index,
                unit_count=len(content),
                counts=counts,
                hidden_accumulators=accumulators,
                hidden=hidden,
                activated=activated,
                output_accumulator=output,
                score=rounded(output, hidden_fraction + last_fraction),
            )
        )
    return chunks


def build():
    rows = [[0] * 256 for _ in range(3)]
    for byte, value in ((ord("A"), 3), (ord("x"), -3), (0, 1)):
        rows[0][byte], rows[1][byte] = value, -value
    rows[2][ord("B")] = 1
    weights = MlpWeights(
        schema_id="hallmark/mlp-weights/1",
        hidden_weights=tuple(tuple(r) for r in rows),
        hidden_bias=(-1, 1, -3),
        output_weights=(3, -3, 1),
        output_bias=-1,
    )
    inputs = InputProfile(
        schema_id="hallmark/input-profile/1",
        encoding="utf8-bytes",
        tokenizer_files=(),
        prefix_tokens=(),
        suffix_tokens=(),
        chunk_size=4,
        overlap=0,
        max_units=4096,
        padding_id=ord("A"),
        padding_side="right",
    )
    classifier, program, inputs, arithmetic, raw, parameters = export(weights, inputs)
    cases = []
    for name, text in (
        ("empty", ""),
        ("one", "A"),
        ("threshold-equality", "AA"),
        ("negative", "x"),
        ("exact", "xxxx"),
        ("late-positive", "xxxxAA"),
        ("unicode-boundary", "\x00Aéx"),
        ("real-nul", "\x00\x00\x00"),
        ("multichunk", "AAxxxxxx"),
    ):
        opening = TranscriptOpening(
            schema_id="hallmark/transcript-opening/1",
            system_ref=b"r" * 32,
            prompt=text,
            response="Harmless unused fixture response.",
            salt=b"t" * 32,
        )
        chunks = formula(text, weights, inputs.chunk_size, 1, 0, 1)
        score = max(chunk["score"] for chunk in chunks)
        cases.append(
            dict(
                case_id=name,
                opening_cbor_hex=opening.encode().hex(),
                chunks=chunks,
                score=score,
                verdict=score < classifier.threshold,
            )
        )
    return dict(
        schema_id="hallmark/mlp-fixture/1",
        evidence_class="public-synthetic-software-vectors",
        purpose="Exact native arithmetic only; no policy or proof acceptance.",
        provenance="Hand-specified marker weights; no checkpoint or private data.",
        licence="Existing repository licence; no additional grant.",
        records={
            name: dict(cbor_hex=value.encode().hex(), identity_hex=value.identity().hex())
            for name, value in (
                ("classifier", classifier),
                ("program", program),
                ("input_profile", inputs),
                ("arithmetic", arithmetic),
            )
        },
        weights_cbor_hex=raw.hex(),
        parameters={key: value.hex() for key, value in parameters.items()},
        cases=cases,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.output.open("x") as output:
        output.write(json.dumps(build(), indent=2, sort_keys=True) + "\n")
