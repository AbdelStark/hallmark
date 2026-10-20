"""Freeze native integer MLP layers and inputs for a separate bounded proof experiment."""

import json

from build_mlp_fixture import build as native_fixture
from build_mlp_fixture import export, formula

from hallmark.classifier_manifest import InputProfile
from hallmark.integer_mlp import MlpWeights, execute_mlp
from hallmark.openings import TranscriptOpening, derive_input_salt
from hallmark.receipts import ProofInputs


def build():
    weights = MlpWeights.decode(bytes.fromhex(native_fixture()["weights_cbor_hex"]))
    profile = InputProfile(
        schema_id="hallmark/input-profile/1",
        encoding="utf8-bytes",
        tokenizer_files=(),
        prefix_tokens=(),
        suffix_tokens=(),
        chunk_size=4,
        overlap=0,
        max_units=8,
        padding_id=0,
        padding_side="right",
    )
    classifier, program, profile, arithmetic, raw, parameters = export(weights, profile)
    cases = []
    for name, text in (
        ("empty", ""),
        ("one", "A"),
        ("threshold-equality", "AA"),
        ("negative", "x"),
        ("exact", "xxxx"),
        ("late-positive", "xxxxAA"),
        ("real-nul", "\0\0\0"),
        ("maximum", "AAxxxxxx"),
        ("unicode-boundary", "\0Aéx"),
    ):
        opening = TranscriptOpening(
            schema_id="hallmark/transcript-opening/1",
            system_ref=b"r" * 32,
            prompt=text,
            response="Unused harmless fixture response.",
            salt=b"t" * 32,
        )
        result = execute_mlp(
            opening, classifier, program, profile, arithmetic, weights=raw, parameters=parameters
        )
        expected = formula(text, weights, 4, 1, 0, 1)
        assert [chunk.model_dump(mode="json") for chunk in result.chunks] == expected
        # A second unused slot evaluates the empty chunk but never enters the maximum.
        slots = expected if len(expected) == 2 else [*expected, *formula("", weights, 4, 1, 0, 1)]
        trace = [
            value
            for chunk in slots
            for value in (
                *chunk["hidden_accumulators"],
                *chunk["hidden"],
                *chunk["activated"],
                chunk["output_accumulator"],
                chunk["score"],
            )
        ]
        public = ProofInputs(
            schema_id="hallmark/proof-inputs/1",
            context=b"c" * 32,
            classifier=classifier.identity(),
            input_digest=result.input_digest,
            unit_count=result.unit_count,
            chunk_count=len(result.chunks),
            threshold=result.threshold,
            verdict=result.verdict,
        )
        cases.append(
            {
                "name": name,
                "opening_cbor_hex": opening.encode().hex(),
                "public": list(public.to_fields()),
                "salt": list(derive_input_salt(opening.salt, classifier.identity())),
                "units": list(text.encode()) + [0] * (8 - len(text.encode())),
                "trace": trace,
                "native_chunks": expected,
                "native_score": result.score,
            }
        )
    return {
        "schema_id": "hallmark.gnark-mlp-fixture/1",
        "qualified_backend": False,
        "warning": "Synthetic weights and classifier enrollment tags; no operational enrollment.",
        "records": {
            name: {"cbor_hex": value.encode().hex(), "identity_hex": value.identity().hex()}
            for name, value in (
                ("classifier", classifier),
                ("program", program),
                ("input_profile", profile),
                ("arithmetic", arithmetic),
            )
        },
        "weights_cbor_hex": raw.hex(),
        "parameters": {name: content.hex() for name, content in parameters.items()},
        "cases": cases,
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
