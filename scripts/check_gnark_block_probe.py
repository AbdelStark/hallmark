"""Prove the exhaustive pinned attention block; never qualify an encoder or backend."""

import argparse
import itertools
import json
import platform
import time
from pathlib import Path

from check_gnark_probe import (
    MAX_BINARY,
    MAX_FILE,
    MODULUS,
    digest,
    invoke,
    json_new,
    read_regular,
    write_new,
)


def assignment(vector, private):
    values = vector["public"] + ([n + 2**31 for n in vector["trace"]] if private else [])
    return "".join(f"{n}\n" for n in values).encode("ascii")


def validate_fixture(raw):
    value = json.loads(raw)
    if (
        value["schema_id"] != "hallmark.gnark-block-fixture/1"
        or value["qualified_backend"] is not False
        or type(value["cases"]) is not list
        or len(value["cases"]) != 64
    ):
        raise ValueError("invalid frozen block fixture")
    graph = json.dumps(
        value["graph"], sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    if digest(graph) != value["graph_sha256"]:
        raise ValueError("changed graph description")
    roster = set()
    for vector in value["cases"]:
        for key, count, low, high in (("public", 5, 0, 2**32), ("trace", 89, -(2**31), 2**31)):
            if (
                type(vector[key]) is not list
                or len(vector[key]) != count
                or any(type(n) is not int or not low <= n < high for n in vector[key])
            ):
                raise ValueError("invalid block assignment")
        a, b, x, y, score = vector["public"]
        if (
            vector["name"] != f"tokens-{a}-{b}-mask-{x}-{y}"
            or score != vector["trace"][-1] + 2**31
            or (a, b, x, y) in roster
        ):
            raise ValueError("invalid block vector")
        roster.add((a, b, x, y))
    if roster != set(itertools.product(range(4), range(4), range(2), range(2))):
        raise ValueError("incomplete block domain")
    return value


def check(binary, expected_binary, fixture, expected_fixture, output):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("this admitted probe requires macOS arm64")
    raw_binary = read_regular(binary, MAX_BINARY)
    raw_fixture = read_regular(fixture, 2 * 1024**2)
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
            "schema_id": "hallmark.gnark-block-protocol/1",
            "binary_sha256": expected_binary,
            "fixture_sha256": expected_fixture,
            "graph_sha256": frozen["graph_sha256"],
            "runner_sha256": digest(Path(__file__).read_bytes()),
            "worker_runner_sha256": digest(
                Path(__file__).with_name("check_gnark_probe.py").read_bytes()
            ),
            "platform": platform.platform(),
            "qualified_backend": False,
            "private_inputs": False,
            "public_fields": frozen["public_fields"],
            "valid_cases": 64,
            "private_trace_fields": 89,
            "limits": {
                "total_seconds": 900,
                "case_seconds": 45,
                "case_cpu_seconds": 40,
                "go_threads": 4,
                "go_memory_soft_limit": "1GiB",
                "max_measured_process_rss_bytes": 2 * 1024**3,
                "per_file_bytes": MAX_FILE,
                "max_measured_output_bytes": 2 * 1024**3,
                "cost_minor": 0,
            },
            "limitations": [
                "Five-field synthetic block; not the 100-field Hallmark proof statement.",
                "No complete encoder, tokenizer, layer normalization or model-quality evidence.",
                "Local setup and shared verifier library; no independent security/hiding review.",
                "CPU, RSS and total storage are measured postconditions, not hard quotas.",
            ],
        },
    )
    started, measured_bytes, cases = time.monotonic(), len(raw_binary) + len(raw_fixture), []

    def case(name, command, inputs, outputs=(), expected=0):
        nonlocal measured_bytes
        if time.monotonic() - started > 855:
            raise TimeoutError("block-probe budget exhausted")
        work = output / name
        work.mkdir(mode=0o700)
        for filename, raw in inputs.items():
            write_new(work / filename, raw)
        cost = invoke(binary, work, [command])
        cases.append({"name": name, **cost})
        measured_bytes += sum(item["bytes"] for item in cost["files"].values())
        if (
            cost["exit_code"] != expected
            or cost["timed_out"]
            or cost["max_rss_bytes"] > 2 * 1024**3
            or cost["user_seconds"] + cost["system_seconds"] > 40
            or measured_bytes > 2 * 1024**3
            or set(cost["files"])
            != {*inputs, *outputs, "sandbox.sb", "plan.json", "stdout.txt", "stderr.txt"}
        ):
            raise ValueError("block-probe process or inventory failed")
        report = json.loads(read_regular(work / "stdout.txt", 4096))
        if (
            set(report) != {"schema_id", "status", "constraints", "elapsed_ns"}
            or report["schema_id"] != "hallmark.gnark-installation-probe/1"
            or report["status"] != ("passed" if expected == 0 else "failed")
            or type(report["constraints"]) is not int
            or report["constraints"] < 0
            or type(report["elapsed_ns"]) is not int
            or report["elapsed_ns"] < 0
        ):
            raise ValueError("invalid block-probe result")
        return {name: read_regular(work / name, MAX_FILE) for name in outputs}

    try:
        setup = case("setup", "block-setup", {}, ("circuit.r1cs", "pk.bin", "vk.bin"))
        proving = {name: setup[name] for name in ("circuit.r1cs", "pk.bin")}
        key_pin = digest(setup["vk.bin"])
        for vector in frozen["cases"]:
            proof = case(
                "prove-" + vector["name"],
                "block-prove",
                proving | {"assignment.txt": assignment(vector, True)},
                ("proof.bin",),
            )
            verifier = {
                "vk.bin": setup["vk.bin"],
                "proof.bin": proof["proof.bin"],
                "assignment.txt": assignment(vector, False),
            }
            case("verify-" + vector["name"], "block-verify", verifier)
        for i in range(5):
            altered = {**vector, "public": list(vector["public"])}
            altered["public"][i] ^= 1
            case(
                f"public-{i}",
                "block-verify",
                verifier | {"assignment.txt": assignment(altered, False)},
                expected=1,
            )
        for i in range(89):
            altered = {**vector, "trace": list(vector["trace"])}
            altered["trace"][i] ^= 1
            case(
                f"trace-{i:02d}",
                "block-prove",
                proving | {"assignment.txt": assignment(altered, True)},
                expected=1,
            )
        for name, index, value in (
            ("token-range", 0, 4),
            ("mask-range", 2, 2),
            ("score-mismatch", 4, vector["public"][4] ^ 1),
        ):
            altered = {**vector, "public": list(vector["public"])}
            altered["public"][index] = value
            case(
                name,
                "block-prove",
                proving | {"assignment.txt": assignment(altered, True)},
                expected=1,
            )
        alias = {**vector, "public": [vector["public"][0] + MODULUS, *vector["public"][1:]]}
        case(
            "field-alias",
            "block-verify",
            verifier | {"assignment.txt": assignment(alias, False)},
            expected=1,
        )
        malformed = {**vector, "trace": [2**31, *vector["trace"][1:]]}
        case(
            "signed-trace-range",
            "block-prove",
            proving | {"assignment.txt": assignment(malformed, True)},
            expected=1,
        )
        case(
            "assignment-leading-zero",
            "block-verify",
            verifier | {"assignment.txt": b"0" + assignment(vector, False)},
            expected=1,
        )
        for name, raw in (
            ("changed-proof", bytes([proof["proof.bin"][0] ^ 1]) + proof["proof.bin"][1:]),
            ("trailing-proof", proof["proof.bin"] + b"\0"),
        ):
            case(name, "block-verify", verifier | {"proof.bin": raw}, expected=1)
        second = case("other-setup", "block-setup", {}, ("circuit.r1cs", "pk.bin", "vk.bin"))
        if digest(second["vk.bin"]) == key_pin:
            raise ValueError("independent random setups unexpectedly agree")
        case("wrong-key", "block-verify", verifier | {"vk.bin": second["vk.bin"]}, expected=1)
        assert len(cases) == 233
        result = {
            "schema_id": "hallmark.gnark-block-result/1",
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
            output / "failure.json", {"schema_id": "hallmark.gnark-block-failure/1", "cases": cases}
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--expected-binary", required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--expected-fixture", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = check(
            args.binary, args.expected_binary, args.fixture, args.expected_fixture, args.output
        )
    except Exception:
        print(json.dumps({"status": "failed", "qualified_backend": False}))
        raise SystemExit(3) from None
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}))
