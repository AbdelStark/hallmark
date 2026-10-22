"""Pinned eight-byte, synthetic three-classifier composition; no hardware acceptance."""

from pathlib import Path

from build_encoder_fixture import oracle
from check_gnark_input_scale import vector

from hallmark._gnark_probe import digest, read_regular
from hallmark.classifier_manifest import ArithmeticProfile, ClassifierManifest, InputProfile
from hallmark.integer_encoder import EncoderProgram, execute_encoder
from hallmark.integer_mlp import MlpProgram, execute_mlp
from hallmark.integrity import parse_json
from hallmark.openings import derive_input_salt
from hallmark.policy import Policy
from hallmark.receipts import ProofArtifact, ProofInputs
from hallmark.rule import RuleProgram, execute_rule
from hallmark.wire import H

ROOT = Path(__file__).resolve().parents[1]
KINDS = ("rule", "mlp", "encoder")
CASES = {"allow": "okayxxxx", "rule-block": "xxBADxxx", "mlp-block": "xxxxAAzz"}
CIRCUITS = {
    "rule": "c0a58141345b708f9633987f2254e3039f8f5e21ff239ee35a55c1b5cf4f7c4a",
    "mlp": "7e699bdbe80cd6375230bda9fec992d74c9a2d5b43a4142cf0a962d5bc01baed",
    "encoder": "ad8bf9b2e401fdebc2e0a0077cf3dd91a8004e1b3ec9e408534087701cd0328a",
}
SOURCES = (
    (
        "research/probes/gnark/rule-fixture.json",
        "681cc89e3059e54ab387d41770ce9a44380755af3cfe23f11171359d4512db6f",
        RuleProgram,
    ),
    (
        "research/probes/gnark/mlp-fixture.json",
        "db1e5792c87d8e66617ba39a9ecb588dcb637e885211d5f241bdaf632b51f1fd",
        MlpProgram,
    ),
    (
        "fixtures/wire/integer-encoder-v1.json",
        "8d0551ac2e9c9e2527004bc4a33392844963ffcb17b9589139448db3f068ee7d",
        EncoderProgram,
    ),
)


def native():
    records = []
    for path, pin, program_type in SOURCES:
        raw = read_regular(ROOT / path, 1024**2)
        if digest(raw) != pin:
            raise ValueError("native fixture changed")
        f = parse_json(raw.decode())
        objects = {}
        for name, cls in (
            ("classifier", ClassifierManifest),
            ("program", program_type),
            ("input_profile", InputProfile),
            ("arithmetic", ArithmeticProfile),
        ):
            record = f["records"][name]
            obj = cls.decode(bytes.fromhex(record["cbor_hex"]))
            if obj.identity().hex() != record["identity_hex"]:
                raise ValueError("native identity mismatch")
            objects[name] = obj
        objects["files"] = {"parameters": {k: bytes.fromhex(v) for k, v in f["parameters"].items()}}
        for source, target in (
            ("provenance_hex", "provenance"),
            ("weights_cbor_hex", "weights"),
            ("tokenizer_hex", "tokenizer"),
        ):
            if source in f:
                objects["files"][target] = bytes.fromhex(f[source])
        records.append(objects)
    return records


def enroll(keys):
    """Call only after checking setup circuit bytes, and pin this record before proving."""
    if set(keys) != set(KINDS) or any(
        type(k) is not bytes or len(k) != 5536 for k in keys.values()
    ):
        raise ValueError("invalid key roster")
    return {
        "schema_id": "hallmark.common-input-enrollment/1",
        "programs": [
            dict(
                kind=kind,
                program=n["program"].identity().hex(),
                circuit_sha256=CIRCUITS[kind],
                key_hex=keys[kind].hex(),
            )
            for kind, n in zip(KINDS, native(), strict=True)
        ],
    }


def resolve(raw, expected_pin):
    if len(raw) > 65536 or digest(raw) != expected_pin:
        raise ValueError("enrollment pin mismatch")
    enrollment = parse_json(raw.decode())
    if (
        set(enrollment) != {"schema_id", "programs"}
        or enrollment["schema_id"] != "hallmark.common-input-enrollment/1"
        or type(enrollment["programs"]) is not list
        or len(enrollment["programs"]) != 3
    ):
        raise ValueError("invalid enrollment")
    records = native()
    for kind, row, n in zip(KINDS, enrollment["programs"], records, strict=True):
        if (
            set(row) != {"kind", "program", "circuit_sha256", "key_hex"}
            or row["kind"] != kind
            or row["program"] != n["program"].identity().hex()
            or row["circuit_sha256"] != CIRCUITS[kind]
        ):
            raise ValueError("program enrollment mismatch")
        key = bytes.fromhex(row["key_hex"])
        if len(key) != 5536 or key.hex() != row["key_hex"]:
            raise ValueError("noncanonical key")
        n["key"] = key
    # These are research descriptors, never BackendQualification admission evidence.
    setup = H("setup", enrollment)
    backend = H("backend", ["common-input-research/1", setup])
    classifiers = []
    for n in records:
        c = (
            n["classifier"]
            .model_copy(
                update={"backend": backend, "setup": setup, "verifier_key": H("key", n["key"])}
            )
            ._validated()
        )
        c.validate_profiles(
            n["input_profile"], n["arithmetic"], parameters=n["files"]["parameters"]
        )
        n["classifier"] = c
        classifiers.append(c)
    policy = Policy(
        schema_id="hallmark/policy/1",
        rubric=H("policy", "synthetic-markers"),
        classifiers=tuple(c.identity() for c in classifiers),
        combination="all-pass",
        language="en",
        scope="prompt",
        max_prompt_bytes=8,
        max_response_bytes=128,
    )
    policy.validate_classifiers(tuple(classifiers))
    return records, policy


def evaluate(records, policy, opening, expected):
    """Reconstruct public inputs from caller-owned opening/expectations, outside the prover."""
    opening, expected = opening._validated(), expected._validated()
    if (
        expected.policy != policy.identity()
        or len(opening.prompt.encode()) > 8
        or len(opening.response.encode()) > policy.max_response_bytes
    ):
        raise ValueError("request binding or capacity mismatch")
    rows = []
    for kind, n, execute in zip(
        KINDS, records, (execute_rule, execute_mlp, execute_encoder), strict=True
    ):
        c, program, profile, arithmetic = (
            n[k] for k in ("classifier", "program", "input_profile", "arithmetic")
        )
        result = execute(opening, c, program, profile, arithmetic, **n["files"])
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
        row = dict(
            public=list(public.to_fields()),
            salt=list(derive_input_salt(opening.salt, c.identity())),
            units=list(opening.prompt.encode()) + [0] * (8 - len(opening.prompt.encode())),
        )
        if kind == "mlp":
            # The unused second slot must still satisfy the frozen arithmetic graph.
            empty = opening.model_copy(update={"prompt": ""})
            slots = list(result.chunks)
            if len(slots) == 1:
                slots += list(execute(empty, c, program, profile, arithmetic, **n["files"]).chunks)
            row["trace"] = [
                v
                for chunk in slots
                for v in (
                    *chunk.hidden_accumulators,
                    *chunk.hidden,
                    *chunk.activated,
                    chunk.output_accumulator,
                    chunk.score,
                )
            ]
        elif kind == "encoder":
            row.update(
                {
                    k: v
                    for k, v in vector(8, opening.prompt.encode()).items()
                    if k not in ("public", "salt", "units")
                }
            )
            layers = [chunk.tensors for chunk in result.chunks]
            for chunk in result.chunks:
                if chunk.tensors != oracle(chunk.tokens, chunk.mask, arithmetic):
                    raise ValueError("native encoder oracle mismatch")
            layers += [oracle((0, 0), (0, 0), arithmetic)] * (4 - len(layers))
            row["trace"] = [
                v for layer in layers for node in arithmetic.nodes for v in layer[node.output]
            ]
        rows.append(row)
    return rows


def check_bundle(enrollment_raw, enrollment_pin, opening, expected, raw):
    """Bind a candidate bundle; returned pairing jobs are not yet cryptographic acceptance."""
    if type(raw) is not bytes or len(raw) > 65536:
        raise ValueError("bundle size limit")
    records, policy = resolve(enrollment_raw, enrollment_pin)
    native_rows = evaluate(records, policy, opening, expected)
    bundle = parse_json(raw.decode())
    if (
        set(bundle) != {"schema_id", "context", "policy", "release", "proofs"}
        or bundle["schema_id"] != "hallmark.common-input-bundle/1"
        or bundle["context"] != opening.context(expected).hex()
        or bundle["policy"] != policy.identity().hex()
        or type(bundle["release"]) is not bool
        or bundle["release"] != all(row["public"][99] == 1 for row in native_rows)
        or type(bundle["proofs"]) is not list
        or len(bundle["proofs"]) != 3
    ):
        raise ValueError("bundle binding mismatch")
    jobs = []
    for kind, n, row, submitted in zip(KINDS, records, native_rows, bundle["proofs"], strict=True):
        if (
            set(submitted) != {"kind", "classifier_cbor_hex", "artifact_cbor_hex"}
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


def bundle(records, policy, opening, expected, rows, proofs):
    return dict(
        schema_id="hallmark.common-input-bundle/1",
        context=opening.context(expected).hex(),
        policy=policy.identity().hex(),
        release=all(row["public"][99] == 1 for row in rows),
        proofs=[
            dict(
                kind=kind,
                classifier_cbor_hex=n["classifier"].encode().hex(),
                artifact_cbor_hex=ProofArtifact(
                    schema_id="hallmark/proof-artifact/1",
                    backend=n["classifier"].backend,
                    verifier_key=n["classifier"].verifier_key,
                    public_inputs=ProofInputs.from_fields(tuple(row["public"])),
                    proof=proof,
                )
                .encode()
                .hex(),
            )
            for kind, n, row, proof in zip(KINDS, records, rows, proofs, strict=True)
        ],
    )
