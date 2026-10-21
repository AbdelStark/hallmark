"""Bounded real proofs for a frozen integer normalization component on the Mac."""

import argparse
import itertools
import json
import platform
import time
from pathlib import Path

from hallmark._gnark_probe import (
    MAX_BINARY,
    MAX_FILE,
    MODULUS,
    RunBudget,
    digest,
    invoke,
    json_new,
    read_regular,
    write_new,
)
from hallmark.integrity import parse_json


def validate_fixture(raw):
    value = parse_json(raw.decode("utf-8"))
    if (
        set(value) != {"schema_id", "qualified_backend", "graph", "graph_sha256", "cases"}
        or value["schema_id"] != "hallmark.gnark-normalization-fixture/1"
        or value["qualified_backend"] is not False
        or type(value["cases"]) is not list
        or len(value["cases"]) != 289
    ):
        raise ValueError("invalid normalization fixture")
    if (
        digest(json.dumps(value["graph"], sort_keys=True, separators=(",", ":")).encode())
        != value["graph_sha256"]
    ):
        raise ValueError("changed graph")
    for row, (a, b) in zip(value["cases"], itertools.product(range(-8, 9), repeat=2), strict=True):
        if set(row) != {"name", "public", "trace"} or row["name"] != f"input-{a + 8}-{b + 8}":
            raise ValueError("invalid normalization roster")
        for key, count, low, high in [("public", 4, 0, 2**32), ("trace", 11, -(2**31), 2**31)]:
            if (
                type(row[key]) is not list
                or len(row[key]) != count
                or any(type(n) is not int or not low <= n < high for n in row[key])
            ):
                raise ValueError("invalid normalization assignment")
        if row["public"][:2] != [a + 2**31, b + 2**31] or row["public"][2:] != [
            n + 2**31 for n in row["trace"][-2:]
        ]:
            raise ValueError("inconsistent public values")
    return value


def assignment(row, private):
    return "".join(
        f"{n}\n" for n in row["public"] + ([n + 2**31 for n in row["trace"]] if private else [])
    ).encode()


def check(binary, expected_binary, fixture, expected_fixture, output):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("this admitted probe requires macOS arm64")
    binary_raw, fixture_raw = read_regular(binary, MAX_BINARY), read_regular(fixture, 2 * 1024**2)
    if digest(binary_raw) != expected_binary or digest(fixture_raw) != expected_fixture:
        raise ValueError("input identity mismatch")
    frozen = validate_fixture(fixture_raw)
    output.mkdir(mode=0o700)
    output = output.resolve()
    binary = output / "probe"
    write_new(binary, binary_raw, 0o500)
    write_new(output / "fixture.json", fixture_raw)
    started = time.monotonic()
    budget = RunBudget(output, started + 900, 45, 10, 40, 4, 2 * 1024**3, 2 * 1024**3)
    json_new(
        output / "protocol.json",
        {
            "schema_id": "hallmark.normalization-proof-protocol/1",
            "binary_sha256": expected_binary,
            "fixture_sha256": expected_fixture,
            "controller_sha256": digest(Path(__file__).read_bytes()),
            "boundary_helper_sha256": digest(Path(invoke.__code__.co_filename).read_bytes()),
            "seconds": 900,
            "threads": 4,
            "max_rss_bytes": budget.max_rss_bytes,
            "max_output_bytes": budget.max_output_bytes,
            "private_inputs": False,
            "qualified_backend": False,
            "independent_verifier": False,
        },
    )
    cases = []

    def case(name, action, inputs, outputs=(), expected=0):
        work = output / name
        work.mkdir(mode=0o700)
        for filename, raw in inputs.items():
            write_new(work / filename, raw)
        cost = invoke(binary, work, ["normalization-" + action], budget=budget)
        cases.append({"name": name, **cost})
        if cost["exit_code"] != expected or set(cost["files"]) != {
            *inputs,
            *outputs,
            "sandbox.sb",
            "plan.json",
            "stdout.txt",
            "stderr.txt",
        }:
            raise ValueError("unexpected normalization worker outcome")
        report = parse_json(read_regular(work / "stdout.txt", 4096).decode())
        if (
            set(report) != {"schema_id", "status", "constraints", "elapsed_ns"}
            or report["schema_id"] != "hallmark.gnark-installation-probe/1"
            or report["status"] != ("passed" if expected == 0 else "failed")
            or any(
                type(report[k]) is not int or report[k] < 0 for k in ["constraints", "elapsed_ns"]
            )
        ):
            raise ValueError("invalid normalization worker report")
        return {name: read_regular(work / name, MAX_FILE) for name in outputs}

    try:
        setup = case("setup", "setup", {}, ("circuit.r1cs", "pk.bin", "vk.bin"))
        json_new(output / "key-enrollment.json", {name: digest(raw) for name, raw in setup.items()})
        proving = {name: setup[name] for name in ("circuit.r1cs", "pk.bin")}
        for row in frozen["cases"]:
            proof = case(
                "prove-" + row["name"],
                "prove",
                proving | {"assignment.txt": assignment(row, True)},
                ("proof.bin",),
            )
            verifier = {
                "vk.bin": setup["vk.bin"],
                **proof,
                "assignment.txt": assignment(row, False),
            }
            case("verify-" + row["name"], "verify", verifier)
        for field in range(4):
            changed = {**row, "public": row["public"].copy()}
            changed["public"][field] ^= 1
            case(
                f"public-{field}",
                "verify",
                verifier | {"assignment.txt": assignment(changed, False)},
                expected=1,
            )
        for field in range(11):
            changed = {**row, "trace": row["trace"].copy()}
            changed["trace"][field] ^= 1
            case(
                f"trace-{field}",
                "prove",
                proving | {"assignment.txt": assignment(changed, True)},
                expected=1,
            )
        for field, value in itertools.product(range(2), [-9, 9]):
            changed = {**row, "public": row["public"].copy()}
            changed["public"][field] = value + 2**31
            case(
                f"range-{field}-{value + 9}",
                "prove",
                proving | {"assignment.txt": assignment(changed, True)},
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
        changed = {**row, "trace": [2**31, *row["trace"][1:]]}
        case(
            "trace-range",
            "prove",
            proving | {"assignment.txt": assignment(changed, True)},
            expected=1,
        )
        case(
            "leading-zero",
            "verify",
            verifier | {"assignment.txt": b"0" + assignment(row, False)},
            expected=1,
        )
        for name, raw in [
            ("changed-proof", bytes([proof["proof.bin"][0] ^ 1]) + proof["proof.bin"][1:]),
            ("trailing-proof", proof["proof.bin"] + b"\0"),
        ]:
            case(name, "verify", verifier | {"proof.bin": raw}, expected=1)
        second = case("other-setup", "setup", {}, ("circuit.r1cs", "pk.bin", "vk.bin"))
        if digest(second["vk.bin"]) == digest(setup["vk.bin"]):
            raise ValueError("fresh setup unexpectedly matches")
        case("wrong-key", "verify", verifier | {"vk.bin": second["vk.bin"]}, expected=1)
        assert len(cases) == 605
        result = {
            "schema_id": "hallmark.normalization-proof-result/1",
            "status": "component-passed",
            "qualified_backend": False,
            "independent_verifier": False,
            "binary_sha256": expected_binary,
            "fixture_sha256": expected_fixture,
            "circuit_sha256": digest(setup["circuit.r1cs"]),
            "vk_sha256": digest(setup["vk.bin"]),
            "proof_bytes": len(proof["proof.bin"]),
            "cases": cases,
            "elapsed_seconds": time.monotonic() - started,
            "measured_artifact_bytes": budget.inspect(),
        }
        json_new(output / "result.json", result)
        return result
    except BaseException:
        json_new(
            output / "failure.json",
            {"schema_id": "hallmark.normalization-proof-failure/1", "cases": cases},
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["binary", "fixture", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ["expected-binary", "expected-fixture"]:
        parser.add_argument("--" + name, required=True)
    result = check(**vars(parser.parse_args()))
    print(json.dumps({k: result[k] for k in ["status", "qualified_backend", "elapsed_seconds"]}))
