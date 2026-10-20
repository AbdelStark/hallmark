"""Run a pinned eight-byte rule experiment; never publish backend qualification."""

import argparse
import json
import platform
import re
import time
from pathlib import Path

from check_gnark_probe import MAX_BINARY, MODULUS, digest, invoke, json_new, read_regular, write_new

MAX_ARTIFACT = 256 * 1024 * 1024


def assignment(case, private):
    fields = case["public"] + (case["salt"] + case["units"] if private else [])
    return ("".join(f"{n}\n" for n in fields)).encode("ascii")


def validate_fixture(raw):
    value = json.loads(raw)
    if (
        value["schema_id"] != "hallmark.gnark-rule-fixture/1"
        or value["qualified_backend"] is not False
        or len(value["cases"]) != 9
    ):
        raise ValueError("invalid frozen fixture")
    names = set()
    for case in value["cases"]:
        name = case["name"]
        if not re.fullmatch("[a-z][a-z0-9-]{0,63}", name) or name in names:
            raise ValueError("invalid case name")
        names.add(name)
        for key, size in (("public", 100), ("salt", 32), ("units", 8)):
            if (
                type(case[key]) is not list
                or len(case[key]) != size
                or any(type(n) is not int or not 0 <= n <= 2**32 - 1 for n in case[key])
            ):
                raise ValueError("invalid assignment")
    return value


def check(binary, expected_binary, fixture, expected_fixture, output):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("this admitted probe requires macOS arm64")
    raw_binary = read_regular(binary, MAX_BINARY)
    raw_fixture = read_regular(fixture, 1024 * 1024)
    if digest(raw_binary) != expected_binary or digest(raw_fixture) != expected_fixture:
        raise ValueError("input identity mismatch")
    frozen = validate_fixture(raw_fixture)
    output.mkdir(mode=0o700)
    output = output.resolve()
    binary = output / "probe"
    write_new(binary, raw_binary, 0o500)
    write_new(output / "fixture.json", raw_fixture)
    json_new(
        output / "protocol.json",
        {
            "schema_id": "hallmark.gnark-rule-protocol/1",
            "binary_sha256": expected_binary,
            "fixture_sha256": expected_fixture,
            "runner_sha256": digest(Path(__file__).read_bytes()),
            "worker_runner_sha256": digest(
                Path(__file__).with_name("check_gnark_probe.py").read_bytes()
            ),
            "platform": platform.platform(),
            "qualified_backend": False,
            "private_inputs": False,
            "statement": "Exact H(input), 0..8 bytes, BAD marker, chunk size 4, 100 public fields.",
            "limits": {
                "total_seconds": 1800,
                "case_seconds": 120,
                "case_cpu_seconds": 120,
                "go_threads": 4,
                "go_memory_soft_limit": "1GiB",
                "max_measured_process_rss_bytes": 16 * 1024**3,
                "per_file_bytes": MAX_ARTIFACT,
                "max_measured_output_bytes": 4 * 1024**3,
                "cost_minor": 0,
            },
            "limitations": [
                "Memory and total disk are checked after a case; no hard aggregate quota.",
                "RLIMIT_CPU is requested; measured CPU overages reject after exit.",
                "Synthetic classifier enrollment tags; setup is local and research-only.",
                "Fresh verifier processes share gnark; no independent verifier implementation.",
                "No full encoder, side-channel, security or end-to-end privacy qualification.",
            ],
        },
    )
    started = time.monotonic()
    cases = []
    measured_bytes = len(raw_binary) + len(raw_fixture)

    def case(name, command, inputs, outputs=(), expected=0):
        nonlocal measured_bytes
        if time.monotonic() - started > 1680:
            raise TimeoutError("rule-probe budget exhausted")
        directory = output / name
        directory.mkdir(mode=0o700)
        for filename, raw in inputs.items():
            write_new(directory / filename, raw)
        cost = invoke(
            binary, directory, [command], max_file=MAX_ARTIFACT, seconds=120, cpu_seconds=120
        )
        cases.append({"name": name, **cost})
        measured_bytes += sum(item["bytes"] for item in cost["files"].values())
        if (
            cost["exit_code"] != expected
            or cost["timed_out"]
            or cost["max_rss_bytes"] > 16 * 1024**3
            or cost["user_seconds"] + cost["system_seconds"] > 120
            or measured_bytes > 4 * 1024**3
            or set(cost["files"])
            != {*inputs, *outputs, "sandbox.sb", "plan.json", "stdout.txt", "stderr.txt"}
        ):
            raise ValueError("rule-probe process or inventory failed")
        report = json.loads(read_regular(directory / "stdout.txt", 4096))
        if (
            set(report) != {"schema_id", "status", "constraints", "elapsed_ns"}
            or report["schema_id"] != "hallmark.gnark-installation-probe/1"
            or report["status"] != ("passed" if expected == 0 else "failed")
            or type(report["constraints"]) is not int
            or report["constraints"] < 0
            or type(report["elapsed_ns"]) is not int
            or report["elapsed_ns"] < 0
        ):
            raise ValueError("invalid rule-probe result")
        return {name: read_regular(directory / name, MAX_ARTIFACT) for name in outputs}

    try:
        setup = case("setup", "rule-setup", {}, ("circuit.r1cs", "pk.bin", "vk.bin"))
        key_pin = digest(setup["vk.bin"])
        proving = {name: setup[name] for name in ("circuit.r1cs", "pk.bin")}
        for vector in frozen["cases"]:
            proof = case(
                "prove-" + vector["name"],
                "rule-prove",
                proving | {"assignment.txt": assignment(vector, True)},
                ("proof.bin",),
            )
            verifier = {
                "vk.bin": setup["vk.bin"],
                "proof.bin": proof["proof.bin"],
                "assignment.txt": assignment(vector, False),
            }
            case("verify-" + vector["name"], "rule-verify", verifier)
        # The last vector supplies a valid proof for every public-field mutation.
        for i in range(100):
            changed = {**vector, "public": list(vector["public"])}
            changed["public"][i] ^= 1
            case(
                f"public-{i:03d}",
                "rule-verify",
                verifier | {"assignment.txt": assignment(changed, False)},
                expected=1,
            )
        for name, index, value in (
            ("field-alias", 0, vector["public"][0] + MODULUS),
            ("digest-byte-range", 0, 256),
            ("count-range", 96, 9),
            ("boolean-range", 99, 2),
        ):
            changed = {**vector, "public": list(vector["public"])}
            changed["public"][index] = value
            case(
                name,
                "rule-verify",
                verifier | {"assignment.txt": assignment(changed, False)},
                expected=1,
            )
        for name, key, index, value in (
            ("changed-witness", "units", 0, ord("y")),
            ("byte-range", "units", 0, 256),
            ("salt-range", "salt", 0, 256),
            ("nonzero-padding", "units", 7, ord("D")),
            ("changed-verdict", "public", 99, 1),
            ("omitted-final-byte", "public", 96, vector["public"][96] - 1),
            ("wrong-chunk-count", "public", 97, 1),
        ):
            changed = {**vector, key: list(vector[key])}
            changed[key][index] = value
            case(
                name,
                "rule-prove",
                proving | {"assignment.txt": assignment(changed, True)},
                expected=1,
            )
        for name, raw in (
            ("changed-proof", bytes([proof["proof.bin"][0] ^ 1]) + proof["proof.bin"][1:]),
            ("trailing-proof", proof["proof.bin"] + b"\0"),
        ):
            case(name, "rule-verify", verifier | {"proof.bin": raw}, expected=1)
        second = case("other-setup", "rule-setup", {}, ("circuit.r1cs", "pk.bin", "vk.bin"))
        if digest(second["vk.bin"]) == key_pin:
            raise ValueError("independent random setups unexpectedly agree")
        case("wrong-key", "rule-verify", verifier | {"vk.bin": second["vk.bin"]}, expected=1)
        result = {
            "schema_id": "hallmark.gnark-rule-result/1",
            "status": "passed",
            "qualified_backend": False,
            "binary_sha256": expected_binary,
            "fixture_sha256": expected_fixture,
            "setup_vk_sha256": key_pin,
            "circuit_sha256": digest(setup["circuit.r1cs"]),
            "proof_sha256": digest(proof["proof.bin"]),
            "proof_bytes": len(proof["proof.bin"]),
            "cases": cases,
            "elapsed_seconds": time.monotonic() - started,
            "measured_artifact_bytes": measured_bytes,
        }
        json_new(output / "result.json", result)
        return result
    except BaseException:
        json_new(
            output / "failure.json",
            {"schema_id": "hallmark.gnark-rule-failure/1", "cases": cases},
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--expected-binary", required=True)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--expected-fixture", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = check(
            args.binary, args.expected_binary, args.fixture, args.expected_fixture, args.output
        )
    except Exception:
        print(json.dumps({"status": "failed", "qualified_backend": False}))
        raise SystemExit(3) from None
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}))
