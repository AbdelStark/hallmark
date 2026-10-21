"""Bounded commitment-scaling experiment; no classifier or backend qualification."""

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

from hallmark._gnark_probe import (
    MAX_BINARY,
    MODULUS,
    RunBudget,
    digest,
    invoke,
    json_new,
    read_regular,
    write_new,
)
from hallmark.wire import H, encode

MAX_FILE = 256 * 1024**2
SIZES = (8, 32, 256, 32768)


def vector(size, units):
    if size not in SIZES or type(units) is not bytes or len(units) > size:
        raise ValueError("invalid commitment input")
    count = len(units)
    integer = encode(count)
    array = bytes([integer[0] + 0x80]) + integer[1:]
    encoded = integer + array
    positions = [len(encoded)]
    for unit in units:
        encoded += bytes([unit]) if unit < 24 else bytes([24, unit])
        positions.append(len(encoded))
    salt, profile = b"s" * 32, b"p" * 32
    body = b"\x84\x58\x20" + salt + b"\x58\x20" + profile + encoded
    assert body == encode([salt, profile, count, list(units)])
    tag = b"hallmark/v1/input"
    hashed = hashlib.sha256(len(tag).to_bytes(4, "big") + tag + body).digest()
    assert hashed == H("input", [salt, profile, count, list(units)])
    return {
        "public": [count, *hashed],
        "salt": list(salt),
        "units": list(units) + [0] * (size - count),
        "encoded": list(encoded) + [0] * (2 * size + 6 - len(encoded)),
        "positions": positions + [positions[-1]] * (size - count),
    }


def assignment(value, private=True):
    fields = value["public"]
    if private:
        fields = fields + value["salt"] + value["units"] + value["encoded"] + value["positions"]
    return "".join(f"{n}\n" for n in fields).encode("ascii")


def resource_limited(cost, budget):
    if cost.get("memory_monitor_failed", False):
        raise ValueError("worker memory monitor failed")
    return (
        cost.get("memory_limit_exceeded", False)
        or cost["exit_code"] < 0
        or cost["timed_out"]
        or cost["max_rss_bytes"] > budget.max_rss_bytes
        or cost["user_seconds"] + cost["system_seconds"] > budget.cpu_seconds
    )


def check(binary, expected_binary, output):
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise ValueError("requires admitted macOS arm64 host")
    raw = read_regular(binary, MAX_BINARY)
    if digest(raw) != expected_binary:
        raise ValueError("binary pin mismatch")
    output.mkdir(mode=0o700)
    output = output.resolve()
    binary = output / "probe"
    write_new(binary, raw, 0o500)
    started = time.monotonic()
    budget = RunBudget(output, started + 420, 120, 10, 480, 4, 16 * 1024**3, 4 * 1024**3)
    vectors = {
        "empty": vector(8, b""),
        "near": vector(8, bytes([0, 23, 24, 255, 1, 128, 22])),
        "maximum": vector(8, bytes([0, 23, 24, 255, 1, 128, 22, 31])),
    }
    boundaries = {
        str(n): vector(256, bytes(i % 256 for i in range(n))) for n in (0, 23, 24, 255, 256)
    }
    json_new(
        output / "protocol.json",
        {
            "schema_id": "hallmark.input-scale-protocol/1",
            "binary_sha256": expected_binary,
            "controller_sha256": digest(Path(__file__).read_bytes()),
            "worker_sha256": digest(Path(invoke.__code__.co_filename).read_bytes()),
            "vectors": vectors,
            "boundary_vectors": boundaries,
            "compile_sizes": [32, 32768],
            "seconds": 420,
            "max_rss_bytes": budget.max_rss_bytes,
            "max_output_bytes": budget.max_output_bytes,
            "qualified_backend": False,
        },
    )
    cases = []

    def case(name, action, size, inputs=None, outputs=(), expected=0, resource_probe=False):
        inputs = inputs or {}
        budget.inspect()
        directory = output / name
        directory.mkdir(mode=0o700)
        for filename, content in inputs.items():
            write_new(directory / filename, content)
        # Keep the measured failed maximum attempt instead of turning it into success.
        try:
            cost = invoke(
                binary,
                directory,
                [f"input-{action}", str(size)],
                seconds=90 if resource_probe else 120,
                cpu_seconds=360 if resource_probe else 480,
                max_file=MAX_FILE,
                budget=budget,
            )
        except (MemoryError, TimeoutError):
            if not resource_probe or not (directory / "cost.json").is_file():
                raise
            cost = json.loads((directory / "cost.json").read_text())
        cases.append({"name": name, **cost})
        if resource_probe and resource_limited(cost, budget):
            return {"resource_limited": True}
        if cost["exit_code"] != expected or cost["timed_out"]:
            raise ValueError("unexpected worker result")
        report = json.loads(read_regular(directory / "stdout.txt", 4096))
        if (
            report["status"] != ("passed" if expected == 0 else "failed")
            or type(report["constraints"]) is not int
            or report["constraints"] < 0
            or set(cost["files"])
            != {*inputs, *outputs, "sandbox.sb", "plan.json", "stdout.txt", "stderr.txt"}
        ):
            raise ValueError("invalid worker result or inventory")
        return {name: read_regular(directory / name, MAX_FILE) for name in outputs}

    def batch(size, setup, values, invalid=None):
        invalid = invalid or {}
        roster = [{"name": name, "valid": name in values} for name in (*values, *invalid)]
        inputs = {name: setup[name] for name in ("circuit.r1cs", "pk.bin")}
        inputs["cases.json"] = json.dumps(roster).encode()
        inputs.update(
            {f"{name}.txt": assignment(value) for name, value in (values | invalid).items()}
        )
        outputs = [f"{name}.json" for name in (*values, *invalid)]
        outputs += [f"{name}.proof" for name in values]
        result = case(f"batch-{size}", "batch", size, inputs, outputs=outputs)
        for name in (*values, *invalid):
            if json.loads(result[f"{name}.json"]) != {"expected_outcome_observed": True}:
                raise ValueError("invalid batch outcome")
        return result

    try:
        setup = case("setup-8", "setup", 8, outputs=("circuit.r1cs", "pk.bin", "vk.bin"))
        value = vectors["maximum"]
        invalid = {}
        mutations = [
            ("unit", "units", 0, 1),
            ("unit-range", "units", 0, 256),
            ("salt", "salt", 0, 256),
            ("count", "public", 0, 9),
            ("header", "encoded", 0, 24),
            ("array", "encoded", 1, 0x89),
            ("body", "encoded", 2, 1),
            ("tail-padding", "encoded", 21, 1),
            ("prefix-start", "positions", 0, 3),
            ("prefix-gap", "positions", 4, 9),
            ("prefix-end", "positions", 8, 21),
        ]
        for name, key, index, number in mutations:
            changed = {**value, key: list(value[key])}
            changed[key][index] = number
            invalid[f"invalid-{name}"] = changed
        invalid["invalid-unit-padding"] = {
            **vectors["near"],
            "units": [*vectors["near"]["units"][:7], 1],
        }
        proofs = batch(8, setup, vectors, invalid)
        for name, value in vectors.items():
            verifier = {
                "vk.bin": setup["vk.bin"],
                "proof.bin": proofs[f"{name}.proof"],
                "assignment.txt": assignment(value, False),
            }
            case(f"verify-{name}", "verify", 8, verifier)
        for i in range(33):
            changed = {**value, "public": list(value["public"])}
            changed["public"][i] ^= 1
            case(
                f"public-{i}",
                "verify",
                8,
                verifier | {"assignment.txt": assignment(changed, False)},
                expected=1,
            )
        changed = {**value, "public": [MODULUS + 8, *value["public"][1:]]}
        case(
            "field-alias",
            "verify",
            8,
            verifier | {"assignment.txt": assignment(changed, False)},
            expected=1,
        )
        case(
            "changed-proof",
            "verify",
            8,
            verifier
            | {"proof.bin": bytes([verifier["proof.bin"][0] ^ 1]) + verifier["proof.bin"][1:]},
            expected=1,
        )
        other = case("other-setup", "setup", 8, outputs=("circuit.r1cs", "pk.bin", "vk.bin"))
        case("wrong-key", "verify", 8, verifier | {"vk.bin": other["vk.bin"]}, expected=1)
        larger = case("setup-256", "setup", 256, outputs=("circuit.r1cs", "pk.bin", "vk.bin"))
        named = {f"boundary-{name}": value for name, value in boundaries.items()}
        proofs = batch(256, larger, named)
        for name, value in named.items():
            case(
                f"verify-{name}",
                "verify",
                256,
                {
                    "vk.bin": larger["vk.bin"],
                    "proof.bin": proofs[f"{name}.proof"],
                    "assignment.txt": assignment(value, False),
                },
            )
        case("compile-32", "compile", 32)
        maximum = case("compile-32768", "compile", 32768, resource_probe=True)
        result = {
            "schema_id": "hallmark.input-scale-result/1",
            "status": "incomplete",
            "component_checks": "passed",
            "qualified_backend": False,
            "maximum_compile": "failed-or-resource-limited" if maximum else "compiled-not-proved",
            "elapsed_seconds": time.monotonic() - started,
            "cases": cases,
            "limitations": [
                "33 public commitment fields; no classifier, tokenizer or enrolled input profile.",
                "Eight actual proofs cover small/header boundaries. Maximum input has no proof.",
                "Fresh local setup; shared verifier library; security and hiding unqualified.",
                "Live RSS sampling and post-exit RSS/storage checks are not hard OS quotas.",
            ],
        }
        json_new(output / "result.json", result)
        return result
    except BaseException:
        json_new(
            output / "failure.json",
            {
                "status": "failed",
                "qualified_backend": False,
                "elapsed_seconds": time.monotonic() - started,
                "completed_cases": len(cases),
            },
        )
        raise


if __name__ == "__main__":

    class Parser(argparse.ArgumentParser):
        def error(self, message):
            raise ValueError("invalid arguments")

    parser = Parser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--expected-binary", required=True)
    parser.add_argument("--output", type=Path, required=True)
    try:
        report = check(**vars(parser.parse_args()))
        print(json.dumps({key: value for key, value in report.items() if key != "cases"}))
    except (Exception, KeyboardInterrupt):
        print(json.dumps({"status": "failed", "qualified_backend": False}))
    raise SystemExit(3)
