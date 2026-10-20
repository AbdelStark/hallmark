"""Build public marker vectors with an independent complete-byte slice oracle."""

import argparse
import hashlib
import json
from pathlib import Path

from hallmark.classifier_manifest import (
    ArithmeticProfile,
    ClassifierManifest,
    InputProfile,
    NodeSpec,
    TensorSpec,
)
from hallmark.manifests import FileRef
from hallmark.openings import TranscriptOpening
from hallmark.rule import RuleProgram
from hallmark.wire import encode

PROVENANCE = b"""{"schema_id":"hallmark/rule-fixture-provenance/1",
"source":"hand-authored harmless markers, no external dataset",
"purpose":"native matching and boundary tests",
"approval_basis":"authorized engineering fixtures; no operational policy admission",
"licence":"existing repository licence; no additional grant",
"coverage":"literal byte equality only, no intent or general injection detection"}\n"""


def export(patterns, inputs):
    def ref(path, raw):
        return FileRef(path=path, size=len(raw), sha256=hashlib.sha256(raw).digest())

    parameters = {
        "params/relu.cbor": encode({"schema_id": "hallmark/operator-parameters/1", "op": "relu"})
    }
    arithmetic = ArithmeticProfile(
        schema_id="hallmark/arithmetic/1",
        tensors=tuple(
            TensorSpec(
                name=name, shape=(1,), signed_bits=2, fractional_bits=0, minimum=0, maximum=1
            )
            for name in ("matched", "score")
        ),
        nodes=(
            NodeSpec(
                id="boolean-score",
                op="relu",
                inputs=("matched",),
                output="score",
                parameters=ref("params/relu.cbor", parameters["params/relu.cbor"]),
            ),
        ),
        output="score",
    )
    program = RuleProgram(
        schema_id="hallmark/rule-program/1",
        input_profile=inputs.identity(),
        arithmetic=arithmetic.identity(),
        patterns=tuple(sorted(patterns)),
        provenance=ref("provenance/rule.json", PROVENANCE),
    )
    classifier = ClassifierManifest(
        schema_id="hallmark/classifier/1",
        kind="rule",
        program=program.identity(),
        weights=None,
        tokenizer=None,
        input_profile=inputs.identity(),
        arithmetic=arithmetic.identity(),
        threshold=1,
        scope="prompt",
        labels=("fixture-absent", "fixture-marker"),
        backend=b"b" * 32,
        verifier_key=b"k" * 32,
        setup=b"s" * 32,
    )
    return classifier, program, inputs, arithmetic, PROVENANCE, parameters


def oracle(text, patterns, chunk_size):
    raw = text.encode("utf-8")
    ends = {
        end
        for pattern in patterns
        for end in range(len(pattern), len(raw) + 1)
        if raw[end - len(pattern) : end] == pattern
    }
    return [
        int(any(start < end <= start + chunk_size for end in ends))
        for start in range(0, max(1, len(raw)), chunk_size)
    ]


def build():
    inputs = InputProfile(
        schema_id="hallmark/input-profile/1",
        encoding="utf8-bytes",
        tokenizer_files=(),
        prefix_tokens=(),
        suffix_tokens=(),
        chunk_size=2,
        overlap=0,
        max_units=32768,
        padding_id=0,
        padding_side="right",
    )
    classifier, program, inputs, arithmetic, provenance, parameters = export(
        (b"\0", b"ABCDEF", b"MARK", "é".encode()), inputs
    )
    cases = []
    for name, text in (
        ("empty", ""),
        ("absent", "ordinary"),
        ("case-sensitive", "mark"),
        ("boundary", "xMARKy"),
        ("many-boundaries", "xABCDEF"),
        ("unicode-boundary", "xéy"),
        ("normalization-distinct", "xe\u0301y"),
        ("real-nul", "\0"),
        ("padding-not-content", "x"),
        ("early-and-late", "MARK" + "x" * 513 + "MARK"),
        ("late-match", "x" * 513 + "MARK"),
    ):
        opening = TranscriptOpening(
            schema_id="hallmark/transcript-opening/1",
            system_ref=b"r" * 32,
            prompt=text,
            response="Unused harmless fixture response.",
            salt=b"t" * 32,
        )
        scores = oracle(text, program.patterns, inputs.chunk_size)
        cases.append(
            {
                "case_id": name,
                "opening_cbor_hex": opening.encode().hex(),
                "chunk_scores": scores,
                "score": max(scores),
                "verdict": max(scores) < 1,
            }
        )
    return {
        "schema_id": "hallmark/rule-fixture/1",
        "fixture_only": True,
        "purpose": "Native complete-input matching; no quality, enrollment or proof claim.",
        "records": {
            name: {"cbor_hex": value.encode().hex(), "identity_hex": value.identity().hex()}
            for name, value in (
                ("classifier", classifier),
                ("program", program),
                ("input_profile", inputs),
                ("arithmetic", arithmetic),
            )
        },
        "provenance_hex": provenance.hex(),
        "parameters": {name: value.hex() for name, value in parameters.items()},
        "cases": cases,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.output.open("x") as output:
        output.write(json.dumps(build(), indent=2, sort_keys=True) + "\n")
