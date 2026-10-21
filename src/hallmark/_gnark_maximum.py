"""One bounded synthetic maximum-input campaign; no backend qualification."""

import argparse
import base64
import copy
import json
import os
import stat
import sys
import time
from pathlib import Path
from typing import Any

from ._gnark_linux_compile import container_memory_limit, invoke
from ._gnark_probe import (
    MODULUS,
    PinnedArtifact,
    RunBudget,
    digest,
    json_new,
    read_regular,
    stream_regular,
    write_new,
)

CAPACITY = 32768
CIRCUIT_SHA = "cd91ff70e706fb2d3aecb83d40eae5d82c34611923b67b16a539f69291d0e489"
MAX_FILE = 24 * 1024**3
ENCODER_CIRCUIT_SHA = "7ac28b310c9727aef8c98c3d2a4944a6730d7696ddad40ef4aba1b31a6f5451a"
ENCODER_FIXTURE_SHA = "a5a7dcc541edb5e75fc634b1b0d90326c891c3247ab49da7cae61368990188d3"


def retain_outputs(source: Path, destination: Path, *, encoder: bool = False) -> None:
    """Copy stopped local workers to object storage; check remote bytes after download."""
    if type(encoder) is not bool or not source.is_dir() or source.is_symlink():
        raise ValueError("invalid retention source")
    destination.mkdir(mode=0o700)
    pins: dict[str, dict[str, Any]] = {}
    total = 0

    def walk_failed(error: OSError) -> None:
        raise error

    for directory, children, files in os.walk(source, followlinks=False, onerror=walk_failed):
        current = Path(directory)
        target = destination / current.relative_to(source)
        for name in children:
            if not stat.S_ISDIR((current / name).lstat().st_mode):
                raise ValueError("unsafe retention directory")
            (target / name).mkdir(mode=0o700)
        for name in files:
            size = (current / name).lstat().st_size
            total += size
            if total > (128 if encoder else 96) * 1024**3 or len(pins) >= 20000:
                raise ValueError("retention budget exceeded")
            pins[str((current / name).relative_to(source))] = stream_regular(
                current / name, 48 * 1024**3 if encoder else MAX_FILE, destination=target / name
            )
    json_new(
        destination / "retention.json",
        {"schema_id": "hallmark.hf-retention/1", "files": pins, "total_bytes": total},
    )


def vector(units: bytes) -> dict[str, list[int]]:
    """Frozen synthetic fixture codec, checked against the canonical native encoder."""
    count = len(units)
    if type(units) is not bytes or count > CAPACITY:
        raise ValueError("invalid synthetic fixture")
    header = (
        bytes([count])
        if count < 24
        else (bytes([24, count]) if count < 256 else b"\x19" + count.to_bytes(2, "big"))
    )
    encoded = bytearray(header + bytes([header[0] + 0x80]) + header[1:])
    positions = [len(encoded)]
    for unit in units:
        encoded.extend(bytes([unit]) if unit < 24 else bytes([24, unit]))
        positions.append(len(encoded))
    salt = b"s" * 32
    body = b"\x84\x58\x20" + salt + b"\x58\x20" + b"p" * 32 + encoded
    tag = b"hallmark/v1/input"
    hashed = bytes.fromhex(digest(len(tag).to_bytes(4, "big") + tag + body))
    return {
        "public": [count, *hashed],
        "salt": list(salt),
        "units": list(units) + [0] * (CAPACITY - count),
        "encoded": list(encoded) + [0] * (2 * CAPACITY + 6 - len(encoded)),
        "positions": positions + [positions[-1]] * (CAPACITY - count),
        "unit_active": [1] * count + [0] * (CAPACITY - count),
        "encoded_active": [1] * len(encoded) + [0] * (2 * CAPACITY + 6 - len(encoded)),
    }


def assignment(value: dict[str, list[int]], private: bool = True) -> bytes:
    fields = ["public", "salt", "units", "encoded", "positions", "unit_active", "encoded_active"]
    if "trace" in value:
        fields.append("trace")
    return "".join(
        f"{n + (2**31 if key == 'trace' else 0)}\n"
        for key in (fields if private else fields[:1])
        for n in value[key]
    ).encode("ascii")


def fixtures() -> dict[str, tuple[dict[str, list[int]], bool]]:
    rows = {
        name: (vector(bytes(i % 256 for i in range(count))), True)
        for name, count in [("empty", 0), ("near", CAPACITY - 1), ("maximum", CAPACITY)]
    }
    for name, origin, field, index, value in [
        ("last-unit", "maximum", "units", CAPACITY - 1, 254),
        ("encoded-padding", "maximum", "encoded", -1, 1),
        ("last-encoding", "maximum", "encoded", rows["maximum"][0]["positions"][-1] - 1, 254),
        ("last-position", "maximum", "positions", CAPACITY, 1),
        ("wrong-count", "maximum", "public", 0, CAPACITY - 1),
        ("unit-range", "maximum", "units", 0, 256),
        ("prefix-hole", "maximum", "unit_active", CAPACITY // 2, 0),
        ("empty-padding", "empty", "encoded", -1, 1),
        ("salt-range", "maximum", "salt", 0, 256),
    ]:
        changed = copy.deepcopy(rows[origin][0])
        assert changed[field][index] != value
        changed[field][index] = value
        rows[name] = changed, False
    return rows


def encoder_fixtures(raw: bytes, expected: str) -> dict[str, tuple[dict[str, list[int]], bool]]:
    """Expand only the separately frozen, native-checked synthetic roster."""
    if expected != ENCODER_FIXTURE_SHA or digest(raw) != expected:
        raise ValueError("encoder fixture pin mismatch")
    fixture = json.loads(raw)
    rows: dict[str, tuple[dict[str, list[int]], bool]] = {}
    for case in fixture["cases"]:
        units = case["prompt"].encode("ascii")
        row = vector(units)
        row["public"], row["salt"] = case["public"], fixture["salt"]
        row["trace"] = []
        for index in range(0, CAPACITY, 2):
            pair = units[index : index + 2].ljust(2, b"\x00")
            mask = f"{int(index < len(units))}{int(index + 1 < len(units))}"
            row["trace"].extend(fixture["chunk_traces"][pair.hex() + ":" + mask])
        if digest(assignment(row)) != case["assignment_sha256"]:
            raise ValueError("encoder assignment differs from native pin")
        rows[case["name"]] = row, True
    maximum, empty = rows["maximum"][0], rows["empty"][0]
    for name, origin, field, index, value in [
        ("last-unit", maximum, "units", CAPACITY - 1, maximum["units"][-1] ^ 1),
        ("last-encoding", maximum, "encoded", maximum["positions"][-1] - 1, 64),
        ("last-position", maximum, "positions", CAPACITY, 1),
        ("wrong-count", maximum, "public", 96, CAPACITY - 1),
        ("unit-range", maximum, "units", 0, 256),
        ("prefix-hole", maximum, "unit_active", CAPACITY // 2, 0),
        ("empty-padding", empty, "encoded", -1, 1),
        ("empty-unit-padding", empty, "units", -1, 1),
        ("salt-range", maximum, "salt", 0, 256),
        *(
            ("trace-" + name, maximum, "trace", index, maximum["trace"][index] ^ 1)
            for name, index in [("first", 0), ("middle", len(maximum["trace"]) // 2), ("last", -1)]
        ),
    ]:
        changed = {**origin, field: origin[field].copy()}
        assert changed[field][index] != value
        changed[field][index] = value
        rows[name] = changed, False
    return rows


def check(
    binary: Path,
    expected_binary: str,
    output: Path,
    *,
    encoder_fixture: Path | None = None,
    expected_fixture: str | None = None,
) -> dict[str, Any]:
    if (encoder_fixture is None) != (expected_fixture is None):
        raise ValueError("encoder fixture and external pin required together")
    if digest(read_regular(binary, 128 * 1024**2)) != expected_binary:
        raise ValueError("binary pin mismatch")
    encoder = encoder_fixture is not None
    frozen = read_regular(encoder_fixture, 1024**2) if encoder_fixture is not None else None
    rows = (
        encoder_fixtures(frozen, expected_fixture)
        if frozen is not None and expected_fixture is not None
        else fixtures()
    )
    relation = "encoder" if encoder else "input"
    circuit_sha = ENCODER_CIRCUIT_SHA if encoder else CIRCUIT_SHA
    max_file = 48 * 1024**3 if encoder else MAX_FILE
    seconds = 15000 if encoder else 6600
    setup_seconds = 6600 if encoder else 3600
    cutoff = 210_000_000_000 if encoder else 150_000_000_000
    output.mkdir(mode=0o700)
    started = time.monotonic()
    budget = RunBudget(
        output,
        started + seconds,
        setup_seconds,
        30,
        48 * setup_seconds,
        48,
        230_000_000_000 if encoder else 170_000_000_000,
        (128 if encoder else 96) * 1024**3,
    )
    report: dict[str, Any] = {
        "schema_id": "hallmark.maximum-encoder-result/1"
        if encoder
        else "hallmark.maximum-commitment-result/1",
        "status": "incomplete",
        "qualified_backend": False,
        "full_input_proof": False,
        "cases": [],
        "binary_sha256": expected_binary,
        "proof_records": [],
    }
    if frozen is not None:
        write_new(output / "fixture.json", frozen)
        report.update(full_encoder_proof=False, fixture_sha256=expected_fixture)
    json_new(
        output / "protocol.json",
        {
            "schema_id": "hallmark.maximum-encoder-protocol/1"
            if encoder
            else "hallmark.maximum-commitment-protocol/1",
            "binary_sha256": expected_binary,
            "controller_sha256": digest(Path(__file__).read_bytes()),
            "expected_circuit_sha256": circuit_sha,
            "fixtures": {
                name: {"valid": valid, "assignment_sha256": digest(assignment(row))}
                for name, (row, valid) in rows.items()
            },
            "max_rss_bytes": budget.max_rss_bytes,
            "live_cutoff_bytes": cutoff,
            "max_output_bytes": budget.max_output_bytes,
            "max_file_bytes": max_file,
            "seconds": seconds,
            "threads": 48,
            "setup": "fresh local research setup; no ceremony",
            "independent_verifier": False,
            "operational_enrollment": False,
        },
    )

    def case(
        name: str,
        args: list[str],
        seconds: int,
        inputs: dict[str, bytes | PinnedArtifact] | None = None,
        expected: int = 0,
    ) -> dict[str, PinnedArtifact]:
        print(json.dumps({"starting_case": name, "timeout_seconds": seconds}), flush=True)
        cost = invoke(
            [str(binary), *args],
            output / name,
            seconds=seconds,
            max_rss=budget.max_rss_bytes,
            cutoff=cutoff,
            budget=budget,
            max_file=max_file,
            inputs=inputs,
        )
        report["cases"].append({"name": name, **cost})
        if cost["exit_code"] != expected or not cost["within_limits"]:
            raise ValueError("unexpected worker outcome")
        for filename, value in (inputs or {}).items():
            pin = (
                {"sha256": value.sha256, "bytes": value.size}
                if isinstance(value, PinnedArtifact)
                else {"sha256": digest(value), "bytes": len(value)}
            )
            if cost["files"].get(filename) != pin:
                raise ValueError("worker changed an enrolled input")
        result = json.loads(read_regular(output / name / "stdout.txt", 65536))
        if result["status"] != ("passed" if expected == 0 else "failed"):
            raise ValueError("worker report disagrees")
        return {
            filename: PinnedArtifact(output / name / filename, pin["sha256"], pin["bytes"])
            for filename, pin in cost["files"].items()
        }

    try:
        report["container_memory_limit_bytes"] = container_memory_limit(budget.max_rss_bytes)
        # Actual network denial is a gate before any expensive worker.
        smoke = (
            "import socket,errno\ntry: socket.socket()\n"
            "except OSError as e: assert e.errno==errno.EPERM\n"
            "else: raise AssertionError('network available')\n"
        )
        cost = invoke([sys.executable, "-c", smoke], output / "network-smoke", seconds=5)
        if cost["exit_code"] != 0 or not cost["within_limits"]:
            raise ValueError("network filter failed")
        tiny = case("tiny-setup", ["setup"], 10)
        tiny_proof = case(
            "tiny-prove", ["prove", "3", "35"], 10, {n: tiny[n] for n in ["circuit.r1cs", "pk.bin"]}
        )
        tiny_inputs: dict[str, bytes | PinnedArtifact] = {
            "vk.bin": tiny["vk.bin"],
            "proof.bin": tiny_proof["proof.bin"],
        }
        case("tiny-verify", ["verify", "35"], 10, tiny_inputs)
        case("tiny-changed", ["verify", "36"], 10, tiny_inputs, 1)
        other_key = None
        if encoder:
            small = case("small-encoder-setup", ["encoder-setup", "8"], 120)
            empty = rows["empty"][0]
            small_empty = {
                name: empty[name][:count]
                for name, count in [
                    ("public", 100),
                    ("salt", 32),
                    ("units", 8),
                    ("encoded", 22),
                    ("positions", 9),
                    ("unit_active", 8),
                    ("encoded_active", 22),
                    ("trace", 484),
                ]
            }
            small_proof = case(
                "small-encoder-prove",
                ["encoder-prove", "8"],
                120,
                {
                    **{n: small[n] for n in ["circuit.r1cs", "pk.bin"]},
                    "assignment.txt": assignment(small_empty),
                },
            )
            small_verifier: dict[str, bytes | PinnedArtifact] = {
                "vk.bin": small["vk.bin"],
                "proof.bin": small_proof["proof.bin"],
                "assignment.txt": assignment(small_empty, False),
            }
            case("small-encoder-verify", ["encoder-verify", "8"], 30, small_verifier)
            changed = {"public": small_empty["public"].copy()}
            changed["public"][99] ^= 1
            case(
                "small-encoder-changed",
                ["encoder-verify", "8"],
                30,
                small_verifier | {"assignment.txt": assignment(changed, False)},
                1,
            )
            other_key = small["vk.bin"]
        exported = case(
            "maximum-export", [relation + "-export", str(CAPACITY)], 900 if encoder else 600
        )
        if exported["circuit.r1cs"].sha256 != circuit_sha:
            raise ValueError("maximum circuit differs from enrolled Mac export")
        setup = case(
            "maximum-setup",
            [relation + "-setup-compiled", str(CAPACITY)],
            setup_seconds,
            {"circuit.r1cs": exported["circuit.r1cs"]},
        )
        json_new(
            output / "key-enrollment.json",
            {
                "circuit_sha256": circuit_sha,
                "verification_key_sha256": setup["vk.bin"].sha256,
                "proving_key_sha256": setup["pk.bin"].sha256,
                "operational_enrollment": False,
            },
        )
        inputs: dict[str, bytes | PinnedArtifact] = {
            n: setup[n] for n in ["circuit.r1cs", "pk.bin"]
        }
        inputs.update({name + ".txt": assignment(row) for name, (row, _) in rows.items()})
        inputs["cases.json"] = json.dumps(
            [{"name": name, "valid": valid} for name, (_, valid) in rows.items()]
        ).encode()
        proofs = case(
            "maximum-batch", [relation + "-batch", str(CAPACITY)], 6600 if encoder else 1800, inputs
        )
        for name in rows:
            if json.loads(read_regular(proofs[name + ".json"].path, 1024)) != {
                "expected_outcome_observed": True
            }:
                raise ValueError("batch outcome mismatch")
        for name in ["empty", "near", "maximum"]:
            public = assignment(rows[name][0], False)
            verifier: dict[str, bytes | PinnedArtifact] = {
                "vk.bin": setup["vk.bin"],
                "proof.bin": proofs[name + ".proof"],
                "assignment.txt": public,
            }
            case("verify-" + name, [relation + "-verify", str(CAPACITY)], 30, verifier)
            report["proof_records"].append(
                {
                    "name": name,
                    "public_assignment": public.decode(),
                    "vk_base64": base64.b64encode(
                        read_regular(setup["vk.bin"].path, 1024**2)
                    ).decode(),
                    "proof_base64": base64.b64encode(
                        read_regular(proofs[name + ".proof"].path, 4096)
                    ).decode(),
                    "vk_sha256": setup["vk.bin"].sha256,
                    "proof_sha256": proofs[name + ".proof"].sha256,
                }
            )
        for index in range(100 if encoder else 33):
            changed = {"public": rows["maximum"][0]["public"].copy()}
            changed["public"][index] ^= 1
            case(
                f"changed-public-{index}",
                [relation + "-verify", str(CAPACITY)],
                30,
                verifier | {"assignment.txt": assignment(changed, False)},
                1,
            )
        changed = {"public": rows["maximum"][0]["public"].copy()}
        changed["public"][1] += MODULUS
        case(
            "field-alias",
            [relation + "-verify", str(CAPACITY)],
            30,
            verifier | {"assignment.txt": assignment(changed, False)},
            1,
        )
        raw = read_regular(proofs["maximum.proof"].path, 4096)
        case(
            "changed-proof",
            [relation + "-verify", str(CAPACITY)],
            30,
            verifier | {"proof.bin": bytes([raw[0] ^ 1]) + raw[1:]},
            1,
        )
        if other_key is None:
            small = case("other-key", ["input-setup", "8"], 60)
            other_key = small["vk.bin"]
        case(
            "wrong-key",
            [relation + "-verify", str(CAPACITY)],
            30,
            verifier | {"vk.bin": other_key},
            1,
        )
        report.update(status="component-passed", full_input_proof=True)
        if encoder:
            report.update(status="synthetic-encoder-passed", full_encoder_proof=True)
    finally:
        report["elapsed_seconds"] = time.monotonic() - started
        json_new(output / "result.json", report)
        print(json.dumps({"result": report}), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--expected-binary", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--encoder-fixture", type=Path)
    parser.add_argument("--expected-fixture")
    args = parser.parse_args()
    check(**vars(args))
