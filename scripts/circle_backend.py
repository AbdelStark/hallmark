"""Caller-owned enrollment and opened binding for experimental classifier STARKs.

This module reconstructs the existing native statements. It returns proof-only
jobs; acceptance additionally requires each separate STWO verifier invocation.
"""

from pathlib import Path

import circle_classifiers as circuits
import trained_common_input as common
from classifier_comparison import encoded, sha

from hallmark.integrity import parse_json
from hallmark.wire import H

ROOT = Path(__file__).resolve().parents[1]
KINDS = ("rule", "mlp", "encoder")


def source_identity():
    paths = [
        *(ROOT / "research/probes/circle").glob("src/**/*.rs"),
        *(
            ROOT / "research/probes/circle" / n
            for n in ("Cargo.toml", "Cargo.lock", "rust-toolchain.toml")
        ),
        *(
            ROOT / "scripts" / n
            for n in (
                "circle_backend.py",
                "circle_classifiers.py",
                "circle_integer.py",
                "circle_circuit.py",
            )
        ),
    ]
    files = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted(paths)}
    return H("backend", ["hallmark-circle-classifiers-research/1", files]), files


def compile_case(kind, row, raw, exported):
    if kind == "rule":
        return circuits.rule(row["public"], raw, bytes(row["salt"])), {}
    function = {"mlp": circuits.mlp, "encoder": circuits.encoder}[kind]
    return function(row["public"], raw, bytes(row["salt"]), exported[kind])


def enroll(engine_enrollments, original_records):
    if set(engine_enrollments) != set(KINDS):
        raise ValueError("incomplete Circle enrollment roster")
    backend, sources = source_identity()
    rows = []
    for kind, original in zip(KINDS, original_records, strict=True):
        raw = engine_enrollments[kind]
        value = parse_json(raw.decode())
        if (
            value.get("schema") != "hallmark.circle-enrollment/1"
            or len(value.get("external_multiplicities", [])) != 103
            or any(m <= 0 for m in value["external_multiplicities"][2:])
        ):
            raise ValueError("unsupported classifier engine enrollment")
        rows.append(
            dict(
                kind=kind,
                native_program=original["program"].identity().hex(),
                program_sha256=value["program_sha256"],
                engine_enrollment_hex=raw.hex(),
                engine_enrollment_sha256=sha(raw),
            )
        )
    return encoded(
        dict(
            schema_id="hallmark.circle-classifiers-enrollment/1",
            backend=backend.hex(),
            sources=sources,
            programs=rows,
        )
    )


def resolve(raw, expected_pin, original_records, original_policy):
    if type(raw) is not bytes or len(raw) > 65536 or sha(raw) != expected_pin:
        raise ValueError("caller Circle enrollment pin mismatch")
    value = parse_json(raw.decode())
    try:
        engines = {r["kind"]: bytes.fromhex(r["engine_enrollment_hex"]) for r in value["programs"]}
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("malformed Circle enrollment") from error
    if raw != enroll(engines, original_records):
        raise ValueError("Circle source/program/roster enrollment mismatch")
    records = []
    backend, _ = source_identity()
    for kind, original in zip(KINDS, original_records, strict=True):
        record = original.copy()
        c = record["classifier"]
        e = parse_json(engines[kind].decode())
        record["classifier"] = c.model_copy(
            update=dict(
                backend=backend,
                verifier_key=H("key", engines[kind]),
                setup=H("setup", [c.program, e["program_sha256"], sha(engines[kind])]),
            )
        )._validated()
        records.append(record)
    policy = original_policy.model_copy(
        update=dict(classifiers=tuple(r["classifier"].identity() for r in records))
    )._validated()
    policy.validate_classifiers(tuple(r["classifier"] for r in records))
    return records, policy, engines


def expected_request(original_expected, policy):
    # The caller creates and retains the new policy expectation before proving.
    return original_expected.model_copy(update=dict(policy=policy.identity()))._validated()


def check_bundle(
    enrollment, enrollment_pin, original_records, original_policy, opening, expected, bundle
):
    records, policy, engines = resolve(
        enrollment, enrollment_pin, original_records, original_policy
    )
    rows = common.evaluate(records, policy, opening, expected)
    if (
        type(bundle) is not dict
        or set(bundle) != {"schema_id", "proofs"}
        or bundle["schema_id"] != "hallmark.circle-classifier-bundle/1"
        or type(bundle["proofs"]) is not list
        or len(bundle["proofs"]) != 3
    ):
        raise ValueError("incomplete Circle classifier proof coverage")
    jobs = []
    for kind, row, supplied in zip(KINDS, rows, bundle["proofs"], strict=True):
        if (
            type(supplied) is not dict
            or set(supplied) != {"kind", "public", "proof_hex"}
            or supplied["kind"] != kind
            or supplied["public"] != row["public"]
            or type(supplied["proof_hex"]) is not str
        ):
            raise ValueError("Circle request/classifier/public binding mismatch")
        circuits.public_values(supplied["public"])
        proof = bytes.fromhex(supplied["proof_hex"])
        if not proof or len(proof) > 64 * 1024**2 or proof.hex() != supplied["proof_hex"]:
            raise ValueError("noncanonical Circle proof bytes")
        jobs.append(
            dict(
                kind=kind,
                enrollment=engines[kind],
                enrollment_pin=sha(engines[kind]),
                public=circuits.public_values(row["public"]),
                proof=proof,
            )
        )
    return jobs
