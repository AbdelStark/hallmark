"""Generate one fresh eight-byte encoder proof for the separate verifier's CI gate."""

import argparse
import json
import platform
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from hallmark import _gnark_linux_compile, _gnark_probe  # noqa: E402
from hallmark._gnark_probe import (  # noqa: E402
    PinnedArtifact,
    RunBudget,
    digest,
    json_new,
    read_regular,
    stream_regular,
    write_new,
)

FIXTURE_SHA256 = "14cec4e70126684e7698d74b01dd279bf637be53d18cec343e02b3d7e05f5c60"
CIRCUIT_SHA256 = "ad8bf9b2e401fdebc2e0a0077cf3dd91a8004e1b3ec9e408534087701cd0328a"
PRIVATE = ("salt", "units", "encoded", "positions", "unit_active", "encoded_active")


def generate(binary, expected_binary, fixture, output):
    host = (platform.system(), platform.machine())
    if host not in (("Darwin", "arm64"), ("Linux", "x86_64")):
        raise ValueError("unsupported fixture host")
    if digest(read_regular(binary, 32 * 1024**2)) != expected_binary:
        raise ValueError("binary enrollment mismatch")
    raw = read_regular(fixture, 1024**2)
    if digest(raw) != FIXTURE_SHA256:
        raise ValueError("unsupported source fixture")
    frozen = json.loads(raw)
    row = next(row for row in frozen["cases"] if row["name"] == "capacity")
    output.mkdir(mode=0o700)
    output = output.resolve()
    budget = RunBudget(output, time.monotonic() + 600, 300, 300, 600, 2, 2 * 1024**3, 512 * 1024**2)
    json_new(
        output / "protocol.json",
        dict(
            schema_id="hallmark.second-verifier-ci-fixture/1",
            binary_sha256=expected_binary,
            fixture_sha256=FIXTURE_SHA256,
            generator_sha256=digest(Path(__file__).read_bytes()),
            expected_public=row["public"],
            qualified_backend=False,
            operational_enrollment=False,
            seconds=600,
            threads=2,
            max_rss_bytes=2 * 1024**3,
            max_output_bytes=512 * 1024**2,
        ),
    )

    def worker(name, action, inputs):
        work = output / name
        args = ["encoder-" + action, "8"]
        if host[0] == "Linux":
            cost = _gnark_linux_compile.invoke(
                [str(binary), *args],
                work,
                seconds=300,
                max_rss=2 * 1024**3,
                cutoff=7 * 1024**3 // 4,
                budget=budget,
                max_file=256 * 1024**2,
                inputs=inputs,
            )
        else:
            work.mkdir(mode=0o700)
            for filename, value in inputs.items():
                if isinstance(value, PinnedArtifact):
                    value.copy_to(work / filename, 256 * 1024**2)
                else:
                    write_new(work / filename, value)
            cost = _gnark_probe.invoke(
                binary,
                work,
                args,
                seconds=300,
                cpu_seconds=600,
                max_file=256 * 1024**2,
                budget=budget,
            )
        if (
            cost["exit_code"] != 0
            or json.loads((work / "stdout.txt").read_text())["status"] != "passed"
        ):
            raise ValueError("fixture worker failed")
        for filename, value in inputs.items():
            expected = (
                {"bytes": value.size, "sha256": value.sha256}
                if isinstance(value, PinnedArtifact)
                else {"bytes": len(value), "sha256": digest(value)}
            )
            if cost["files"][filename] != expected:
                raise ValueError("fixture worker changed an input")
        return cost

    setup = worker("setup", "setup", {})
    if setup["files"]["circuit.r1cs"]["sha256"] != CIRCUIT_SHA256:
        raise ValueError("unexpected compiled relation")
    key = read_regular(output / "setup/vk.bin", 65536)
    key_pin = digest(key)
    json_new(output / "key-enrollment.json", dict(key_sha256=key_pin, public=row["public"]))
    values = row["public"] + [v for name in PRIVATE for v in row[name]]
    values += [v + 2**31 for v in row["trace"]]
    inputs = {"assignment.txt": "".join(f"{v}\n" for v in values).encode("ascii")}
    for name in ("circuit.r1cs", "pk.bin"):
        pin = setup["files"][name]
        inputs[name] = PinnedArtifact(output / "setup" / name, pin["sha256"], pin["bytes"])
    worker("prove", "prove", inputs)
    proof = read_regular(output / "prove/proof.bin", 1024)
    payload = dict(
        key_hex=key.hex(),
        records=[dict(name="capacity", proof_hex=proof.hex(), public=row["public"])],
    )
    json_new(output / "fixture.json", payload)
    for name, pin in setup["files"].items():
        if stream_regular(output / "setup" / name, 256 * 1024**2) != pin:
            raise ValueError("setup changed after proving")
    result = dict(
        status="generated-unverified",
        fixture_sha256=digest((output / "fixture.json").read_bytes()),
        key_sha256=key_pin,
        proof_sha256=digest(proof),
        qualified_backend=False,
    )
    json_new(output / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--expected-binary", required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            generate(args.binary.absolute(), args.expected_binary, args.fixture, args.output)
        )
    )


if __name__ == "__main__":
    main()
