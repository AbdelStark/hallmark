"""Check public fixed MLP layer vectors against the actual installed runtime."""

import json
import sys
from pathlib import Path

from hallmark.classifier_manifest import ArithmeticProfile, ClassifierManifest, InputProfile
from hallmark.integer_mlp import MlpProgram, execute_mlp
from hallmark.openings import TranscriptOpening


def check(path: Path) -> None:
    vector = json.loads(path.read_text())
    records = vector["records"]
    classifier = ClassifierManifest.decode(bytes.fromhex(records["classifier"]["cbor_hex"]))
    program = MlpProgram.decode(bytes.fromhex(records["program"]["cbor_hex"]))
    inputs = InputProfile.decode(bytes.fromhex(records["input_profile"]["cbor_hex"]))
    arithmetic = ArithmeticProfile.decode(bytes.fromhex(records["arithmetic"]["cbor_hex"]))
    for name, value in (
        ("classifier", classifier),
        ("program", program),
        ("input_profile", inputs),
        ("arithmetic", arithmetic),
    ):
        assert value.identity().hex() == records[name]["identity_hex"]
    for case in vector["cases"]:
        result = execute_mlp(
            TranscriptOpening.decode(bytes.fromhex(case["opening_cbor_hex"])),
            classifier,
            program,
            inputs,
            arithmetic,
            weights=bytes.fromhex(vector["weights_cbor_hex"]),
            parameters={key: bytes.fromhex(value) for key, value in vector["parameters"].items()},
        )
        assert [chunk.model_dump(mode="json") for chunk in result.chunks] == case["chunks"]
        assert (result.score, result.verdict) == (case["score"], case["verdict"])
    print(f"{len(vector['cases'])} native MLP vectors matched at every layer; no proof verified.")


if __name__ == "__main__":
    check(Path(sys.argv[1]))
