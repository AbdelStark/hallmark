"""Check a caller-pinned complete synthetic encoder at eight-unit proof capacity."""

import json
import platform
import time
from pathlib import Path

from check_gnark_input_scale import vector

from hallmark._gnark_probe import (
    MAX_BINARY,
    MODULUS,
    PinnedArtifact,
    RunBudget,
    digest,
    invoke,
    json_new,
    read_regular,
    run_cli,
    write_new,
)
from hallmark.classifier_manifest import ArithmeticProfile, ClassifierManifest, InputProfile
from hallmark.integer_encoder import EncoderProgram, execute_encoder
from hallmark.integrity import parse_json
from hallmark.openings import TranscriptOpening, derive_input_salt
from hallmark.receipts import ProofInputs

NATIVE_PIN = "8d0551ac2e9c9e2527004bc4a33392844963ffcb17b9589139448db3f068ee7d"
NAMES = (
    "empty",
    "one",
    "exact",
    "tail",
    "multichunk",
    "unicode",
    "nul",
    "newline",
    "near-capacity",
    "capacity",
    "threshold-equal",
    "threshold-above",
    "threshold-below",
    "threshold-minimum",
    "threshold-maximum",
)
PRIVATE = ("salt", "units", "encoded", "positions", "unit_active", "encoded_active")
MAX_FILE = 2 * 1024**3


def assignment(row, private):
    values = list(row["public"])
    if private:
        values += [v for name in PRIVATE for v in row[name]]
        values += [v + 2**31 for v in row["trace"]]
    return "".join(f"{n}\n" for n in values).encode("ascii")


def validate_fixture(raw, native_raw):
    if digest(native_raw) != NATIVE_PIN:
        raise ValueError("unsupported native fixture")
    native = parse_json(native_raw.decode())
    objects = {}
    for name, cls in (
        ("classifier", ClassifierManifest),
        ("program", EncoderProgram),
        ("input_profile", InputProfile),
        ("arithmetic", ArithmeticProfile),
    ):
        record = native["records"][name]
        obj = cls.decode(bytes.fromhex(record["cbor_hex"]))
        if obj.identity().hex() != record["identity_hex"]:
            raise ValueError("native identity mismatch")
        objects[name] = obj
    base, program, profile, arithmetic = (
        objects[k] for k in ("classifier", "program", "input_profile", "arithmetic")
    )
    kwargs = dict(
        weights=bytes.fromhex(native["weights_cbor_hex"]),
        tokenizer=bytes.fromhex(native["tokenizer_hex"]),
        parameters={k: bytes.fromhex(v) for k, v in native["parameters"].items()},
    )
    f = parse_json(raw.decode())
    if (
        set(f)
        != {
            "schema_id",
            "qualified_backend",
            "capacity",
            "profile_maximum",
            "program",
            "native_fixture_sha256",
            "warning",
            "cases",
        }
        or f["schema_id"] != "hallmark.gnark-encoder-fixture/1"
        or f["qualified_backend"] is not False
        or type(f["capacity"]) is not int
        or f["capacity"] != 8
        or type(f["profile_maximum"]) is not int
        or f["profile_maximum"] != 32768
        or f["program"] != program.identity().hex()
        or f["native_fixture_sha256"] != NATIVE_PIN
        or type(f["cases"]) is not list
        or tuple(row["name"] for row in f["cases"]) != NAMES
    ):
        raise ValueError("invalid encoder roster")
    thresholds = [base.threshold] * 10 + [-4, -3, -5, -(2**31), 2**31 - 1]
    for row, threshold in zip(f["cases"], thresholds, strict=True):
        if set(row) != {
            "name",
            "opening_cbor_hex",
            "classifier_cbor_hex",
            "native_score",
            "public",
            "trace",
            *PRIVATE,
        }:
            raise ValueError("unexpected encoder fields")
        for name, size in (
            ("public", 100),
            ("salt", 32),
            ("units", 8),
            ("encoded", 22),
            ("positions", 9),
            ("unit_active", 8),
            ("encoded_active", 22),
            ("trace", 484),
        ):
            if (
                type(row[name]) is not list
                or len(row[name]) != size
                or any(type(n) is not int for n in row[name])
            ):
                raise ValueError("invalid encoder assignment shape")
        opening = TranscriptOpening.decode(bytes.fromhex(row["opening_cbor_hex"]))
        units = opening.prompt.encode()
        c = ClassifierManifest.decode(bytes.fromhex(row["classifier_cbor_hex"]))
        if len(units) > 8 or c != base.model_copy(update={"threshold": threshold})._validated():
            raise ValueError("unsupported classifier or capacity")
        result = execute_encoder(opening, c, program, profile, arithmetic, **kwargs)
        if type(row["native_score"]) is not int or row["native_score"] != result.score:
            raise ValueError("native score mismatch")
        public = ProofInputs(
            schema_id="hallmark/proof-inputs/1",
            context=b"c" * 32,
            classifier=c.identity(),
            input_digest=result.input_digest,
            unit_count=result.unit_count,
            chunk_count=len(result.chunks),
            threshold=c.threshold,
            verdict=result.verdict,
        )
        expected = vector(8, units)
        expected["salt"] = list(derive_input_salt(opening.salt, c.identity()))
        expected["public"] = list(public.to_fields())
        empty = execute_encoder(
            opening.model_copy(update={"prompt": ""}), c, program, profile, arithmetic, **kwargs
        )
        layers = [chunk.tensors for chunk in result.chunks] + [empty.chunks[0].tensors] * (
            4 - len(result.chunks)
        )
        expected["trace"] = [
            v for layer in layers for node in arithmetic.nodes for v in layer[node.output]
        ]
        if any(row[name] != expected[name] for name in (*PRIVATE, "public", "trace")):
            raise ValueError("native assignment mismatch")
    return f


def batch_roster(frozen):
    rows = {row["name"]: row for row in frozen["cases"]}
    valid = [dict(name=name, valid=True) for name in NAMES]
    maximum = rows["capacity"]
    for i in range(484):
        name = f"trace-{i:03d}"
        row = {**maximum, "trace": maximum["trace"].copy()}
        row["trace"][i] ^= 1
        rows[name] = row
        valid.append(dict(name=name, valid=False))
    for key, index in (
        ("salt", 31),
        ("units", 7),
        ("encoded", 0),
        ("positions", 8),
        ("unit_active", 7),
        ("encoded_active", 21),
    ):
        name = "changed-" + key.replace("_", "-")
        row = {**maximum, key: maximum[key].copy()}
        row[key][index] ^= 1
        rows[name] = row
        valid.append(dict(name=name, valid=False))
    for key, index in (("units", 7), ("encoded", 21), ("unit_active", 7), ("encoded_active", 21)):
        name = "empty-" + key.replace("_", "-")
        row = {**rows["empty"], key: rows["empty"][key].copy()}
        row[key][index] = 1
        rows[name] = row
        valid.append(dict(name=name, valid=False))
    return rows, valid


def check(binary, expected_binary, fixture, expected_fixture, output):
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise ValueError("requires the admitted Mac host")
    binary_raw = read_regular(binary, MAX_BINARY)
    fixture_raw = read_regular(fixture, 1024**2)
    native_raw = read_regular(
        Path(__file__).resolve().parents[1] / "fixtures/wire/integer-encoder-v1.json", 1024**2
    )
    if digest(binary_raw) != expected_binary or digest(fixture_raw) != expected_fixture:
        raise ValueError("caller pin mismatch")
    frozen = validate_fixture(fixture_raw, native_raw)
    rows, roster = batch_roster(frozen)
    output.mkdir(mode=0o700)
    output = output.resolve()
    binary = output / "probe"
    write_new(binary, binary_raw, 0o500)
    write_new(output / "fixture.json", fixture_raw)
    write_new(output / "native-fixture.json", native_raw)
    started = time.monotonic()
    budget = RunBudget(output, started + 1800, 900, 10, 3600, 4, 8 * 1024**3, 8 * 1024**3)
    json_new(
        output / "protocol.json",
        dict(
            schema_id="hallmark.encoder-proof-protocol/1",
            binary_sha256=expected_binary,
            fixture_sha256=expected_fixture,
            native_fixture_sha256=NATIVE_PIN,
            controller_sha256=digest(Path(__file__).read_bytes()),
            worker_sha256=digest(Path(invoke.__code__.co_filename).read_bytes()),
            platform=platform.platform(),
            batch_roster=roster,
            case_seconds=900,
            total_seconds=1800,
            max_rss_bytes=budget.max_rss_bytes,
            max_output_bytes=budget.max_output_bytes,
            tested_capacity=8,
            profile_maximum=32768,
            qualified_backend=False,
        ),
    )
    cases = []

    def case(name, action, inputs, outputs=(), expected=0):
        budget.inspect()
        work = output / name
        work.mkdir(mode=0o700)
        for filename, raw in inputs.items():
            if isinstance(raw, PinnedArtifact):
                raw.copy_to(work / filename, MAX_FILE)
            else:
                write_new(work / filename, raw)
        cost = invoke(
            binary,
            work,
            ["encoder-" + action, "8"],
            seconds=budget.case_seconds,
            cpu_seconds=budget.cpu_seconds,
            budget=budget,
            max_file=MAX_FILE,
        )
        cases.append(dict(name=name, **cost))
        if cost["exit_code"] != expected or set(cost["files"]) != {
            *inputs,
            *outputs,
            "sandbox.sb",
            "plan.json",
            "stdout.txt",
            "stderr.txt",
        }:
            raise ValueError("unexpected encoder worker outcome")
        for filename, raw in inputs.items():
            wanted = (
                {"sha256": raw.sha256, "bytes": raw.size}
                if isinstance(raw, PinnedArtifact)
                else {"sha256": digest(raw), "bytes": len(raw)}
            )
            if cost["files"][filename] != wanted:
                raise ValueError("worker changed a pinned input")
        report = parse_json(read_regular(work / "stdout.txt", 4096).decode())
        if (
            set(report) != {"schema_id", "status", "constraints", "elapsed_ns"}
            or report["schema_id"] != "hallmark.gnark-installation-probe/1"
            or report["status"] != ("passed" if expected == 0 else "failed")
            or any(
                type(report[k]) is not int or report[k] < 0 for k in ("constraints", "elapsed_ns")
            )
        ):
            raise ValueError("invalid worker report")
        return {
            name: PinnedArtifact(
                work / name, cost["files"][name]["sha256"], cost["files"][name]["bytes"]
            )
            for name in outputs
        }

    try:
        setup = case("setup", "setup", {}, ("circuit.r1cs", "pk.bin", "vk.bin"))
        json_new(
            output / "key-enrollment.json",
            {name: {"sha256": p.sha256, "bytes": p.size} for name, p in setup.items()},
        )
        batch_inputs = {name: setup[name] for name in ("circuit.r1cs", "pk.bin")}
        batch_inputs["cases.json"] = (json.dumps(roster, separators=(",", ":")) + "\n").encode()
        batch_inputs.update({name + ".txt": assignment(row, True) for name, row in rows.items()})
        outputs = [item["name"] + ".json" for item in roster] + [name + ".proof" for name in NAMES]
        batch = case("batch", "batch", batch_inputs, outputs)
        for item in roster:
            outcome = read_regular(batch[item["name"] + ".json"].path, 1024)
            if parse_json(outcome.decode()) != {"expected_outcome_observed": True}:
                raise ValueError("invalid batch report")
        for name in NAMES:
            case(
                "verify-" + name,
                "verify",
                {
                    "vk.bin": setup["vk.bin"],
                    "proof.bin": batch[name + ".proof"],
                    "assignment.txt": assignment(rows[name], False),
                },
            )
        row = rows["capacity"]
        verifier = {
            "vk.bin": setup["vk.bin"],
            "proof.bin": batch["capacity.proof"],
            "assignment.txt": assignment(row, False),
        }
        for i in range(100):
            changed = {**row, "public": row["public"].copy()}
            changed["public"][i] ^= 1
            case(
                f"public-{i:03d}",
                "verify",
                verifier | {"assignment.txt": assignment(changed, False)},
                expected=1,
            )
        changed = {**row, "public": row["public"].copy()}
        changed["public"][0] += MODULUS
        case(
            "field-alias",
            "verify",
            verifier | {"assignment.txt": assignment(changed, False)},
            expected=1,
        )
        case(
            "leading-zero",
            "verify",
            verifier | {"assignment.txt": b"0" + assignment(row, False)},
            expected=1,
        )
        changed = {**row, "trace": [2**31, *row["trace"][1:]]}
        case("trace-overflow", "prove", {"assignment.txt": assignment(changed, True)}, expected=1)
        proof = read_regular(batch["capacity.proof"].path, 65536)
        for name, raw in (
            ("changed-proof", bytes([proof[0] ^ 1]) + proof[1:]),
            ("trailing-proof", proof + b"\x00"),
        ):
            case(name, "verify", verifier | {"proof.bin": raw}, expected=1)
        second = case("other-setup", "setup", {}, ("circuit.r1cs", "pk.bin", "vk.bin"))
        if second["vk.bin"].sha256 == setup["vk.bin"].sha256:
            raise ValueError("fresh setup unexpectedly matches")
        case("wrong-key", "verify", verifier | {"vk.bin": second["vk.bin"]}, expected=1)
        result = dict(
            schema_id="hallmark.encoder-proof-result/1",
            status="small-capacity-passed",
            qualified_backend=False,
            independent_verifier=False,
            tested_capacity=8,
            profile_maximum=32768,
            profile_maximum_proven=False,
            binary_sha256=expected_binary,
            fixture_sha256=expected_fixture,
            native_fixture_sha256=NATIVE_PIN,
            circuit_sha256=setup["circuit.r1cs"].sha256,
            vk_sha256=setup["vk.bin"].sha256,
            proofs={
                name: {
                    "bytes": batch[name + ".proof"].size,
                    "sha256": batch[name + ".proof"].sha256,
                }
                for name in NAMES
            },
            batch_cases=len(roster),
            private_tensor_rejections=484,
            public_mutation_rejections=100,
            cases=cases,
            elapsed_seconds=time.monotonic() - started,
            measured_artifact_bytes=budget.inspect(),
        )
        json_new(output / "result.json", result)
        return result
    except BaseException:
        json_new(
            output / "failure.json", dict(schema_id="hallmark.encoder-proof-failure/1", cases=cases)
        )
        raise


if __name__ == "__main__":
    raise SystemExit(run_cli(check, fixture=True))
