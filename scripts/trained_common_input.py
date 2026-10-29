"""Opened, caller-pinned native statements for the rule, trained MLP and CNN classifiers."""

from pathlib import Path

import contextual_proof as cnn
import trained_mlp as mlp

from hallmark._worker import digest, read_regular
from hallmark.classifier_manifest import ArithmeticProfile, ClassifierManifest, InputProfile
from hallmark.integer_encoder import execute_encoder
from hallmark.integer_mlp import execute_mlp
from hallmark.integrity import parse_json
from hallmark.openings import derive_input_salt
from hallmark.receipts import ProofInputs
from hallmark.rule import RuleProgram, execute_rule

ROOT = Path(__file__).resolve().parents[1]
KINDS = ("rule", "mlp", "encoder")
CAPACITY = 96
RULE = ROOT / "fixtures/rule-program.json"
RULE_PIN = "a604a56a7768e5d13168bb874388a53ed7574a09b802f20d0592b798f39d0c1d"


def rule_native():
    raw = read_regular(RULE, 1024**2)
    if digest(raw) != RULE_PIN:
        raise ValueError("native fixture changed")
    f = parse_json(raw.decode())
    n = {}
    for name, cls in (
        ("classifier", ClassifierManifest),
        ("program", RuleProgram),
        ("input_profile", InputProfile),
        ("arithmetic", ArithmeticProfile),
    ):
        record = f["records"][name]
        obj = cls.decode(bytes.fromhex(record["cbor_hex"]))
        if obj.identity().hex() != record["identity_hex"]:
            raise ValueError("native identity mismatch")
        n[name] = obj
    n["files"] = {"parameters": {k: bytes.fromhex(v) for k, v in f["parameters"].items()}}
    for source, target in (
        ("provenance_hex", "provenance"),
        ("weights_cbor_hex", "weights"),
        ("tokenizer_hex", "tokenizer"),
    ):
        if source in f:
            n["files"][target] = bytes.fromhex(f[source])
    profile = n["input_profile"].model_copy(update={"max_units": CAPACITY})._validated()
    program = n["program"].model_copy(update={"input_profile": profile.identity()})._validated()
    n["classifier"] = (
        n["classifier"]
        .model_copy(update={"input_profile": profile.identity(), "program": program.identity()})
        ._validated()
    )
    n["input_profile"], n["program"] = profile, program
    return n


def evaluate(records, policy, opening, expected):
    opening, expected = opening._validated(), expected._validated()
    policy.validate_classifiers(tuple(n["classifier"] for n in records))
    if (
        expected.policy != policy.identity()
        or len(opening.prompt.encode()) > CAPACITY
        or len(opening.response.encode()) > policy.max_response_bytes
    ):
        raise ValueError("request binding or capacity mismatch")
    rows = []
    for kind, n, execute in zip(
        KINDS, records, (execute_rule, execute_mlp, execute_encoder), strict=True
    ):
        c, p, profile, arithmetic = (
            n[k] for k in ("classifier", "program", "input_profile", "arithmetic")
        )
        result = execute(opening, c, p, profile, arithmetic, **n["files"])
        if kind == "rule":
            row = dict(trace=[])
        elif kind == "mlp":
            row, _ = mlp.native_row(n["exported"], c, 1024, opening.prompt, 0)
            row["trace"] = row["trace"][:14]
        else:
            row, _ = cnn.native_row(n["exported"], c, CAPACITY, opening.prompt, 0)
        chunks = result.chunk_scores if kind == "rule" else result.chunks
        public = ProofInputs(
            schema_id="hallmark/proof-inputs/1",
            context=opening.context(expected),
            classifier=c.identity(),
            input_digest=result.input_digest,
            unit_count=result.unit_count,
            chunk_count=len(chunks),
            threshold=c.threshold,
            verdict=result.verdict,
        )
        public.validate_profile(c, profile)
        row["public"] = list(public.to_fields())
        row["salt"] = list(derive_input_salt(opening.salt, c.identity()))
        rows.append(row)
    return rows
