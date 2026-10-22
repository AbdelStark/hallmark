"""Opened, caller-pinned composition of rule, trained MLP and CNN research proofs."""

import run_contextual_proof as cnn
import run_trained_mlp as mlp
from check_gnark_input_scale import vector
from common_input import KINDS, native
from common_input import ROOT as ROOT
from common_input import bundle as bundle

from hallmark._gnark_probe import digest
from hallmark.integer_encoder import execute_encoder
from hallmark.integer_mlp import execute_mlp
from hallmark.integrity import parse_json
from hallmark.openings import derive_input_salt
from hallmark.policy import Policy
from hallmark.receipts import ProofArtifact, ProofInputs
from hallmark.rule import execute_rule
from hallmark.wire import H

CAPACITY = 96


def rule_native():
    n = native()[0]
    profile = n["input_profile"].model_copy(update={"max_units": CAPACITY})._validated()
    program = n["program"].model_copy(update={"input_profile": profile.identity()})._validated()
    n["classifier"] = (
        n["classifier"]
        .model_copy(update={"input_profile": profile.identity(), "program": program.identity()})
        ._validated()
    )
    n["input_profile"], n["program"] = profile, program
    return n


def enroll(exports, keys, circuits):
    if set(keys) != set(KINDS) or set(circuits) != set(KINDS):
        raise ValueError("invalid key/circuit roster")
    for kind in KINDS:
        if type(keys[kind]) is not bytes or len(keys[kind]) != 5536:
            raise ValueError("invalid key")
        pin = circuits[kind]
        if type(pin) is not str or len(pin) != 64 or bytes.fromhex(pin).hex() != pin:
            raise ValueError("invalid circuit pin")
    programs = [rule_native()["program"], exports["mlp"]["program"], exports["encoder"]["program"]]
    return dict(
        schema_id="hallmark.trained-common-enrollment/1",
        programs=[
            dict(
                kind=k,
                program=p.identity().hex(),
                circuit_sha256=circuits[k],
                key_hex=keys[k].hex(),
            )
            for k, p in zip(KINDS, programs, strict=True)
        ],
    )


def resolve(raw, pin, exports, circuits):
    if type(raw) is not bytes or len(raw) > 65536 or digest(raw) != pin:
        raise ValueError("enrollment pin mismatch")
    value = parse_json(raw.decode())
    if (
        type(value) is not dict
        or set(value) != {"schema_id", "programs"}
        or value["schema_id"] != "hallmark.trained-common-enrollment/1"
        or type(value["programs"]) is not list
        or len(value["programs"]) != 3
    ):
        raise ValueError("invalid enrollment")
    keys = {}
    for kind, row in zip(KINDS, value["programs"], strict=True):
        if (
            type(row) is not dict
            or set(row) != {"kind", "program", "circuit_sha256", "key_hex"}
            or type(row["key_hex"]) is not str
        ):
            raise ValueError("invalid program enrollment")
        key = bytes.fromhex(row["key_hex"])
        if len(key) != 5536 or key.hex() != row["key_hex"]:
            raise ValueError("noncanonical key")
        keys[kind] = key
    if value != enroll(exports, keys, circuits):
        raise ValueError("program enrollment mismatch")
    records = [rule_native()]
    c = records[0]["classifier"]
    records[0]["classifier"] = c.model_copy(
        update=dict(
            backend=H("backend", "scaled-rule-research/1"),
            verifier_key=H("key", keys["rule"]),
            setup=H("setup", [c.program, circuits["rule"], digest(keys["rule"])]),
        )
    )._validated()
    for kind, module in (("mlp", mlp), ("encoder", cnn)):
        e = exports[kind]
        records.append(
            dict(
                classifier=module.classifier(e, keys[kind], circuits[kind])._validated(),
                program=e["program"],
                input_profile=e["profile"],
                arithmetic=e["arithmetic"],
                files={k: e[k] for k in ("weights", "parameters", "tokenizer") if k in e},
                exported=e,
            )
        )
    for kind, n in zip(KINDS, records, strict=True):
        n["key"] = keys[kind]
        n["classifier"].validate_profiles(
            n["input_profile"], n["arithmetic"], parameters=n["files"]["parameters"]
        )
    policy = Policy(
        schema_id="hallmark/policy/1",
        rubric=H("policy", "synthetic-trained-common/1"),
        classifiers=tuple(n["classifier"].identity() for n in records),
        combination="all-pass",
        language="en",
        scope="prompt",
        max_prompt_bytes=CAPACITY,
        max_response_bytes=128,
    )
    policy.validate_classifiers(tuple(n["classifier"] for n in records))
    return records, policy


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
            row = vector(256, opening.prompt.encode())
            row["trace"] = []
        elif kind == "mlp":
            row, _ = mlp.native_row(n["exported"], c, 1024, opening.prompt, 0)
            row["trace"] = row["trace"][:14]
        else:
            row, _ = cnn.native_row(n["exported"], c, CAPACITY, opening.prompt, 0)
        for name in ("units", "unit_active"):
            row[name] = row[name][:CAPACITY]
        row["positions"] = row["positions"][: CAPACITY + 1]
        for name in ("encoded", "encoded_active"):
            row[name] = row[name][: 2 * CAPACITY + 6]
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


def check_bundle(enrollment_raw, enrollment_pin, exports, circuits, opening, expected, raw):
    """Return pairing jobs only after reconstructing the caller's exact opened statement."""
    if type(raw) is not bytes or len(raw) > 65536:
        raise ValueError("bundle size limit")
    records, policy = resolve(enrollment_raw, enrollment_pin, exports, circuits)
    native_rows = evaluate(records, policy, opening, expected)
    value = parse_json(raw.decode())
    if (
        type(value) is not dict
        or set(value) != {"schema_id", "context", "policy", "release", "proofs"}
        or value["schema_id"] != "hallmark.common-input-bundle/1"
        or value["context"] != opening.context(expected).hex()
        or value["policy"] != policy.identity().hex()
        or type(value["release"]) is not bool
        or value["release"] != all(row["public"][99] == 1 for row in native_rows)
        or type(value["proofs"]) is not list
        or len(value["proofs"]) != 3
    ):
        raise ValueError("bundle binding mismatch")
    jobs = []
    for kind, n, row, submitted in zip(KINDS, records, native_rows, value["proofs"], strict=True):
        if (
            type(submitted) is not dict
            or set(submitted) != {"kind", "classifier_cbor_hex", "artifact_cbor_hex"}
            or type(submitted["artifact_cbor_hex"]) is not str
            or submitted["kind"] != kind
            or submitted["classifier_cbor_hex"] != n["classifier"].encode().hex()
        ):
            raise ValueError("classifier enrollment mismatch")
        artifact = ProofArtifact.decode(bytes.fromhex(submitted["artifact_cbor_hex"]))
        artifact.validate_inputs(
            ProofInputs.from_fields(tuple(row["public"])),
            n["classifier"],
            n["input_profile"],
            max_proof_bytes=292,
        )
        if len(artifact.proof) != 292:
            raise ValueError("unsupported proof length")
        jobs.append(
            dict(
                key_hex=n["key"].hex(),
                expected_key_sha256=digest(n["key"]),
                proof_hex=artifact.proof.hex(),
                public=row["public"],
            )
        )
    return jobs
