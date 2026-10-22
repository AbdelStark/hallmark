"""Fresh synthetic common-input proofs on the Mac; no hardware or policy acceptance."""

import argparse
import json
import platform
import subprocess
import time
from pathlib import Path

import common_input as common
from check_gnark_encoder import assignment as encoder_assignment

from hallmark import _gnark_probe as worker
from hallmark._gnark_probe import (
    PinnedArtifact,
    RunBudget,
    digest,
    json_new,
    read_regular,
    write_new,
)
from hallmark.openings import TranscriptOpening
from hallmark.policy import RequestExpectation

MAX_FILE = 256 * 1024**2


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def run(binary, binary_pin, verifier_python, output):
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise ValueError("this controller requires the approved Mac host")
    if digest(read_regular(binary, 32 * 1024**2)) != binary_pin:
        raise ValueError("binary enrollment mismatch")
    prefix = Path(
        subprocess.check_output(
            [str(verifier_python), "-I", "-c", "import sys;print(sys.base_prefix)"],
            timeout=10,
            env={"PATH": "/usr/bin:/bin"},
            text=True,
        ).strip()
    )
    output.mkdir(mode=0o700)
    output = output.resolve()
    started = time.monotonic()
    budget = RunBudget(output, started + 7200, 600, 120, 2400, 4, 8 * 1024**3, 4 * 1024**3)
    sources = [
        Path(__file__),
        common.ROOT / "scripts/common_input.py",
        common.ROOT / "research/probes/py_ecc/verify.py",
        common.ROOT / "research/probes/py_ecc/verify_set.py",
        common.ROOT / "research/probes/py_ecc/check.py",
    ]
    json_new(
        output / "protocol.json",
        dict(
            schema_id="hallmark.common-input-run/1",
            cases=common.CASES,
            circuits=common.CIRCUITS,
            binary_sha256=binary_pin,
            verifier_python=str(verifier_python),
            verifier_python_sha256=digest(verifier_python.resolve().read_bytes()),
            sources={str(p.relative_to(common.ROOT)): digest(p.read_bytes()) for p in sources},
            seconds=7200,
            threads=4,
            max_rss_bytes=budget.max_rss_bytes,
            max_output_bytes=budget.max_output_bytes,
            worker_sha256=digest(Path(worker.__file__).read_bytes()),
            qualified_backend=False,
            hardware_claim="not-accepted",
        ),
    )
    costs = []

    def invoke(name, executable, args, inputs, produced, *, python=False):
        return worker.run_case(
            executable,
            output / name,
            args,
            inputs,
            produced,
            budget=budget,
            max_file=MAX_FILE,
            costs=costs,
            read_paths=(verifier_python.parent.parent, prefix, common.ROOT) if python else (),
        )

    def args(kind, action):
        return ["encoder-" + action, "8"] if kind == "encoder" else [kind + "-program-" + action]

    try:
        setups, keys = {}, {}
        for kind in common.KINDS:
            cost, _ = invoke(
                "setup-" + kind,
                binary,
                args(kind, "setup"),
                {},
                ("circuit.r1cs", "pk.bin", "vk.bin"),
            )
            if cost["files"]["circuit.r1cs"]["sha256"] != common.CIRCUITS[kind]:
                raise ValueError("compiled relation mismatch")
            setups[kind] = cost["files"]
            keys[kind] = read_regular(output / ("setup-" + kind) / "vk.bin", 65536)
        enrollment_raw = encoded(common.enroll(keys))
        enrollment_pin = digest(enrollment_raw)
        write_new(output / "enrollment.json", enrollment_raw)
        # The enrollment record exists before any proof; subsequent code uses this external pin.
        json_new(output / "enrollment-pin.json", dict(sha256=enrollment_pin, before_proving=True))
        records, policy = common.resolve(enrollment_raw, enrollment_pin)
        expectations, openings, bundles, results = {}, {}, {}, []
        grouped = {kind: dict(key_hex=keys[kind].hex(), records=[]) for kind in common.KINDS}
        for index, (name, prompt) in enumerate(common.CASES.items()):
            expected = RequestExpectation(
                schema_id="hallmark/request-expectation/1",
                audience="local-common-input",
                nonce=bytes([index + 1]) * 32,
                interaction_id=bytes([index + 10]) * 32,
                model=b"m" * 32,
                policy=policy.identity(),
                continuity=None,
            )
            opening = TranscriptOpening(
                schema_id="hallmark/transcript-opening/1",
                system_ref=b"s" * 32,
                prompt=prompt,
                response="Synthetic response; no inference claim.",
                salt=bytes([index + 20]) * 32,
            )
            expectations[name], openings[name] = expected, opening
            rows = common.evaluate(records, policy, opening, expected)
            json_new(
                output / (name + "-request.json"),
                dict(
                    expected_cbor_hex=expected.encode().hex(),
                    opening_cbor_hex=opening.encode().hex(),
                    native_rows=rows,
                ),
            )
            proofs = []
            for kind, row in zip(common.KINDS, rows, strict=True):
                if kind == "encoder":
                    assignment = encoder_assignment(row, True)
                else:
                    values = row["public"] + row["salt"] + row["units"]
                    values += [v + 2**31 for v in row.get("trace", [])]
                    assignment = "".join(f"{v}\n" for v in values).encode("ascii")
                inputs = {"assignment.txt": assignment}
                for filename in ("circuit.r1cs", "pk.bin"):
                    pin = setups[kind][filename]
                    inputs[filename] = PinnedArtifact(
                        output / ("setup-" + kind) / filename, pin["sha256"], pin["bytes"]
                    )
                invoke(name + "-" + kind, binary, args(kind, "prove"), inputs, ("proof.bin",))
                proofs.append(read_regular(output / (name + "-" + kind) / "proof.bin", 292))
            value = common.bundle(records, policy, opening, expected, rows, proofs)
            bundles[name] = value
            raw = encoded(value)
            write_new(output / (name + "-bundle.json"), raw)
            jobs = common.check_bundle(enrollment_raw, enrollment_pin, opening, expected, raw)
            for kind, job in zip(common.KINDS, jobs, strict=True):
                grouped[kind]["records"].append(
                    dict(name=name, proof_hex=job["proof_hex"], public=job["public"])
                )
            job_raw = encoded(jobs)
            _, report = invoke(
                name + "-separate-verifier",
                verifier_python,
                [
                    "-I",
                    "-B",
                    str(common.ROOT / "research/probes/py_ecc/verify_set.py"),
                    "--jobs",
                    "jobs.json",
                    "--expected-jobs",
                    digest(job_raw),
                ],
                {"jobs.json": job_raw},
                (),
                python=True,
            )
            results.append(
                dict(
                    name=name,
                    proofs_verified=report["proofs_verified"],
                    release=value["release"],
                    verdicts=[row["public"][99] for row in rows],
                )
            )
            print(json.dumps(results[-1]), flush=True)
        rejected = []
        for target in common.CASES:
            for source in common.CASES:
                if target == source:
                    continue
                for family in range(3):
                    changed = dict(bundles[target], proofs=bundles[target]["proofs"].copy())
                    changed["proofs"][family] = bundles[source]["proofs"][family]
                    try:
                        common.check_bundle(
                            enrollment_raw,
                            enrollment_pin,
                            openings[target],
                            expectations[target],
                            encoded(changed),
                        )
                    except ValueError:
                        rejected.append([target, source, family])
                    else:
                        raise AssertionError("cross-request proof accepted")
        negative_reports = {}
        for kind, fixture in grouped.items():
            raw = encoded(fixture)
            _, report = invoke(
                "arithmetic-negatives-" + kind,
                verifier_python,
                [
                    "-I",
                    "-B",
                    str(common.ROOT / "research/probes/py_ecc/check.py"),
                    "--fixture",
                    "fixture.json",
                    "--expected-fixture",
                    digest(raw),
                    "--expected-key",
                    digest(keys[kind]),
                ],
                {"fixture.json": raw},
                (),
                python=True,
            )
            negative_reports[kind] = len(report["cases"])
        result = dict(
            status="passed",
            qualified_backend=False,
            hardware_claim="not-accepted",
            enrollment_sha256=enrollment_pin,
            cases=results,
            cross_request_rejections=rejected,
            arithmetic_cases=negative_reports,
            elapsed_seconds=time.monotonic() - started,
            retained_bytes=budget.inspect(),
            peak_worker_rss_bytes=max(c["max_rss_bytes"] for c in costs),
        )
        json_new(output / "result.json", result)
        return result
    except BaseException as error:
        json_new(
            output / "failure.json",
            dict(
                status="failed",
                error_type=type(error).__name__,
                qualified_backend=False,
                completed_workers=len(costs),
            ),
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--expected-binary", required=True)
    parser.add_argument("--verifier-python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.binary.absolute(),
                args.expected_binary,
                args.verifier_python.absolute(),
                args.output,
            )
        )
    )
