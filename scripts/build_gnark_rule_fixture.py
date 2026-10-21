"""Freeze harmless native rule inputs for a separate, unqualified proof experiment."""

import json

from build_rule_fixture import export

from hallmark.classifier_manifest import InputProfile
from hallmark.openings import TranscriptOpening, derive_input_salt
from hallmark.receipts import ProofInputs
from hallmark.rule import execute_rule


def build():
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
    classifier, program, profile, arithmetic, provenance, parameters = export((b"BAD",), profile)
    cases = []
    for name, text in (
        ("empty", ""),
        ("small-cbor-byte", "\0\x17"),
        ("wide-cbor-byte", "\x18\x7f"),
        ("four", "okay"),
        ("near-boundary", "xxBADxx"),
        ("maximum-absent", "okayxxxx"),
        ("maximum-cross-chunk", "xxBADxxx"),
        ("maximum-final-byte", "xxxxxBAD"),
        ("utf8", "xéBAD"),
    ):
        opening = TranscriptOpening(
            schema_id="hallmark/transcript-opening/1",
            system_ref=b"r" * 32,
            prompt=text,
            response="Unused harmless fixture response.",
            salt=b"t" * 32,
        )
        result = execute_rule(
            opening,
            classifier,
            program,
            profile,
            arithmetic,
            provenance=provenance,
            parameters=parameters,
        )
        public = ProofInputs(
            schema_id="hallmark/proof-inputs/1",
            context=b"c" * 32,
            classifier=classifier.identity(),
            input_digest=result.input_digest,
            unit_count=result.unit_count,
            chunk_count=len(result.chunk_scores),
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
                "native_chunk_scores": list(result.chunk_scores),
            }
        )
    return {
        "schema_id": "hallmark.gnark-rule-fixture/1",
        "qualified_backend": False,
        "warning": "Synthetic classifier backend/key/setup tags; no operational enrollment.",
        "records": {
            name: {"cbor_hex": value.encode().hex(), "identity_hex": value.identity().hex()}
            for name, value in (
                ("classifier", classifier),
                ("program", program),
                ("input_profile", profile),
                ("arithmetic", arithmetic),
            )
        },
        "provenance_hex": provenance.hex(),
        "parameters": {name: raw.hex() for name, raw in parameters.items()},
        "cases": cases,
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
