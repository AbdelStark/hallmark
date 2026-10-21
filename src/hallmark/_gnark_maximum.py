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
)

CAPACITY = 32768
CIRCUIT_SHA = "cd91ff70e706fb2d3aecb83d40eae5d82c34611923b67b16a539f69291d0e489"
MAX_FILE = 24 * 1024**3


def retain_outputs(source: Path, destination: Path) -> None:
    """Copy stopped local workers to object storage; check remote bytes after download."""
    if not source.is_dir() or source.is_symlink():
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
            if total > 96 * 1024**3 or len(pins) >= 20000:
                raise ValueError("retention budget exceeded")
            pins[str((current / name).relative_to(source))] = stream_regular(
                current / name, MAX_FILE, destination=target / name
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
    return "".join(
        f"{n}\n" for key in (fields if private else fields[:1]) for n in value[key]
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


def check(binary: Path, expected_binary: str, output: Path) -> dict[str, Any]:
    if digest(read_regular(binary, 128 * 1024**2)) != expected_binary:
        raise ValueError("binary pin mismatch")
    output.mkdir(mode=0o700)
    started = time.monotonic()
    budget = RunBudget(
        output, started + 6600, 3600, 30, 48 * 3600, 48, 170_000_000_000, 96 * 1024**3
    )
    rows = fixtures()
    report: dict[str, Any] = {
        "schema_id": "hallmark.maximum-commitment-result/1",
        "status": "incomplete",
        "qualified_backend": False,
        "full_input_proof": False,
        "cases": [],
        "binary_sha256": expected_binary,
        "proof_records": [],
    }
    json_new(
        output / "protocol.json",
        {
            "schema_id": "hallmark.maximum-commitment-protocol/1",
            "binary_sha256": expected_binary,
            "controller_sha256": digest(Path(__file__).read_bytes()),
            "expected_circuit_sha256": CIRCUIT_SHA,
            "fixtures": {
                name: {"valid": valid, "assignment_sha256": digest(assignment(row))}
                for name, (row, valid) in rows.items()
            },
            "max_rss_bytes": budget.max_rss_bytes,
            "live_cutoff_bytes": 150_000_000_000,
            "max_output_bytes": budget.max_output_bytes,
            "max_file_bytes": MAX_FILE,
            "seconds": 6600,
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
        cost = invoke(
            [str(binary), *args],
            output / name,
            seconds=seconds,
            max_rss=budget.max_rss_bytes,
            cutoff=150_000_000_000,
            budget=budget,
            max_file=MAX_FILE,
            inputs=inputs,
        )
        report["cases"].append({"name": name, **cost})
        if cost["exit_code"] != expected or not cost["within_limits"]:
            raise ValueError("unexpected worker outcome")
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
        exported = case("maximum-export", ["input-export", str(CAPACITY)], 600)
        if exported["circuit.r1cs"].sha256 != CIRCUIT_SHA:
            raise ValueError("maximum circuit differs from enrolled Mac export")
        setup = case(
            "maximum-setup",
            ["input-setup-compiled", str(CAPACITY)],
            3600,
            {"circuit.r1cs": exported["circuit.r1cs"]},
        )
        json_new(
            output / "key-enrollment.json",
            {
                "circuit_sha256": CIRCUIT_SHA,
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
        proofs = case("maximum-batch", ["input-batch", str(CAPACITY)], 1800, inputs)
        for name in ["empty", "near", "maximum"]:
            public = assignment(rows[name][0], False)
            verifier: dict[str, bytes | PinnedArtifact] = {
                "vk.bin": setup["vk.bin"],
                "proof.bin": proofs[name + ".proof"],
                "assignment.txt": public,
            }
            case("verify-" + name, ["input-verify", str(CAPACITY)], 30, verifier)
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
        for index in range(33):
            changed = copy.deepcopy(rows["maximum"][0])
            changed["public"][index] ^= 1
            case(
                f"changed-public-{index}",
                ["input-verify", str(CAPACITY)],
                30,
                verifier | {"assignment.txt": assignment(changed, False)},
                1,
            )
        changed = copy.deepcopy(rows["maximum"][0])
        changed["public"][1] += MODULUS
        case(
            "field-alias",
            ["input-verify", str(CAPACITY)],
            30,
            verifier | {"assignment.txt": assignment(changed, False)},
            1,
        )
        raw = read_regular(proofs["maximum.proof"].path, 4096)
        case(
            "changed-proof",
            ["input-verify", str(CAPACITY)],
            30,
            verifier | {"proof.bin": bytes([raw[0] ^ 1]) + raw[1:]},
            1,
        )
        small = case("other-key", ["input-setup", "8"], 60)
        case(
            "wrong-key",
            ["input-verify", str(CAPACITY)],
            30,
            verifier | {"vk.bin": small["vk.bin"]},
            1,
        )
        report.update(status="component-passed", full_input_proof=True)
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
    args = parser.parse_args()
    check(**vars(args))
