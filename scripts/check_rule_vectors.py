"""Check fixed public rule vectors using the installed native runtime."""

import json
import sys
from pathlib import Path

from hallmark.classifier_manifest import ArithmeticProfile, ClassifierManifest, InputProfile
from hallmark.openings import TranscriptOpening
from hallmark.rule import RuleProgram, execute_rule


def check(path: Path) -> None:
    vector = json.loads(path.read_text())
    records = vector["records"]
    types = (ClassifierManifest, RuleProgram, InputProfile, ArithmeticProfile)
    names = ("classifier", "program", "input_profile", "arithmetic")
    artifacts = [
        cls.decode(bytes.fromhex(records[name]["cbor_hex"]))
        for cls, name in zip(types, names, strict=True)
    ]
    for name, artifact in zip(names, artifacts, strict=True):
        assert artifact.identity().hex() == records[name]["identity_hex"]
    for case in vector["cases"]:
        result = execute_rule(
            TranscriptOpening.decode(bytes.fromhex(case["opening_cbor_hex"])),
            *artifacts,
            provenance=bytes.fromhex(vector["provenance_hex"]),
            parameters={name: bytes.fromhex(raw) for name, raw in vector["parameters"].items()},
        )
        assert list(result.chunk_scores) == case["chunk_scores"]
        assert (result.score, result.verdict) == (case["score"], case["verdict"])
    print(f"{len(vector['cases'])} complete-byte rule vectors matched; no proof verified.")


if __name__ == "__main__":
    check(Path(sys.argv[1]))
