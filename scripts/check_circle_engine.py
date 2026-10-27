"""Real small gate-AIR proof and fresh-worker negatives; not a classifier proof."""

import argparse
import json
import tempfile
import time
from pathlib import Path

from hallmark._gnark_probe import RunBudget, digest, invoke, json_new, read_regular, write_new

ROOT = Path(__file__).resolve().parents[1]
P = 2**31 - 1


def encode(value):
    return json.dumps(value, separators=(",", ":")).encode()


def fixture():
    return (
        dict(
            schema="hallmark.gate-program/1",
            external=5,
            gates=[
                dict(mode=1, a=2, b=3, qa=1, qb=1, qm=0, qk=0),
                dict(mode=2, a=5, b=4, qa=1, qb=P - 1, qm=0, qk=0),
            ],
        ),
        [0, 1, 3, 4, 7],
        [0, 1, 3, 4, 7, 7, 0],
    )


def run(
    prover, expected_prover, verifier, expected_verifier, output, program, public, witness, scope
):
    if (
        digest(read_regular(prover, 128 * 1024**2)) != expected_prover
        or digest(read_regular(verifier, 128 * 1024**2)) != expected_verifier
    ):
        raise ValueError("caller binary pin mismatch")
    output.mkdir(mode=0o700)
    output = output.resolve()
    started = time.monotonic()
    budget = RunBudget(output, started + 600, 600, 180, 600, 4, 16 * 1024**3, 4 * 1024**3)
    json_new(
        output / "protocol.json",
        dict(
            schema_id="hallmark.circle-api-fixture-plan/1",
            prover_sha256=expected_prover,
            verifier_sha256=expected_verifier,
            script_sha256=digest(Path(__file__).read_bytes()),
            seconds=600,
            threads=4,
            max_rss_bytes=budget.max_rss_bytes,
            scope=scope,
            sources={
                str(p.relative_to(ROOT)): digest(p.read_bytes())
                for p in sorted((ROOT / "research/probes/circle").glob("src/**/*.rs"))
            },
            program_sha256=digest(encode(program)),
            public_sha256=digest(encode(public)),
            witness_sha256=digest(encode(witness)),
            automatic_retries=0,
        ),
    )
    costs = []

    def attempt(name, binary, args, inputs, *, accept=True):
        work = output / name
        work.mkdir()
        for name, value in inputs.items():
            write_new(work / name, value)
        cost = invoke(binary, work, args, budget=budget, cpu_seconds=600, max_file=256 * 1024**2)
        costs.append(dict(name=work.name, **cost))
        budget.inspect(cost)
        if (cost["exit_code"] == 0) is not accept:
            raise ValueError("unexpected worker outcome: " + work.name)
        return work

    try:
        raw = encode(program)
        setup = attempt(
            "enroll", prover, ["enroll", "program.json", "enrollment.json"], {"program.json": raw}
        )
        enrollment = read_regular(setup / "enrollment.json", 65536)
        pin = digest(enrollment)
        json_new(
            output / "caller-enrollment.json",
            dict(sha256=pin, before_proving=True, program_sha256=digest(raw)),
        )
        proofdir = attempt(
            "prove",
            prover,
            [
                "prove",
                "program.json",
                "enrollment.json",
                "public.json",
                "witness.json",
                "proof.json",
            ],
            {
                "program.json": raw,
                "enrollment.json": enrollment,
                "public.json": encode(public),
                "witness.json": encode(witness),
            },
        )
        proof = read_regular(proofdir / "proof.json", 64 * 1024**2)
        args = ["enrollment.json", pin, "public.json", "proof.json"]
        inputs = {"enrollment.json": enrollment, "public.json": encode(public), "proof.json": proof}
        checked = attempt("verify", verifier, args, inputs)
        if json.loads((checked / "stdout.txt").read_text()) != {
            "status": "passed",
            "cryptographic_verification": True,
            "qualified_backend": False,
        }:
            raise ValueError("unexpected proof-only verifier report")
        negatives = {}
        changed = list(public)
        changed[4] += 1
        negatives["changed-public"] = dict(inputs, **{"public.json": encode(changed)})
        negatives["truncated-proof"] = dict(inputs, **{"proof.json": proof[:-1]})
        value = json.loads(proof)
        # Keep a valid canonical engine structure, but break a committed OODS sample.
        scalar = value["sampled_values"][0][0][0]
        scalar[0][0] = (scalar[0][0] + 1) % P
        negatives["changed-oods"] = dict(inputs, **{"proof.json": encode(value)})
        value = json.loads(proof)
        value["sampled_values"][0][0][0][0][0] = P
        negatives["noncanonical-m31"] = dict(inputs, **{"proof.json": encode(value)})
        value = json.loads(proof)
        value["config"]["pow_bits"] = 0
        negatives["weaker-parameters"] = dict(inputs, **{"proof.json": encode(value)})
        value = json.loads(enrollment)
        value["program_sha256"] = "0" * 64
        negatives["changed-enrollment"] = dict(inputs, **{"enrollment.json": encode(value)})
        for name, files in negatives.items():
            attempt(name, verifier, args, files, accept=False)
        result = dict(
            schema_id="hallmark.circle-api-fixture/1",
            status="passed",
            serialized_proof_bytes=len(proof),
            proof_sha256=digest(proof),
            fresh_honest_verifications=1,
            mutations_rejected=list(negatives),
            costs=costs,
            elapsed_seconds=time.monotonic() - started,
            classifier_support=False,
            qualified_backend=False,
        )
        json_new(output / "result.json", result)
        return result
    except BaseException as error:
        json_new(
            output / "failure.json",
            dict(
                error=str(error),
                error_type=type(error).__name__,
                costs=costs,
                elapsed_seconds=time.monotonic() - started,
            ),
        )
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prover", type=Path, required=True)
    parser.add_argument("--expected-prover", required=True)
    parser.add_argument("--verifier", type=Path, required=True)
    parser.add_argument("--expected-verifier", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output is None:
        (ROOT / "runs").mkdir(exist_ok=True)
        args.output = Path(tempfile.mkdtemp(prefix="circle-api-", dir=ROOT / "runs"))
        args.output.rmdir()
    print("Evidence: " + str(args.output.resolve()), flush=True)
    result = run(
        args.prover.resolve(),
        args.expected_prover,
        args.verifier.resolve(),
        args.expected_verifier,
        args.output,
        *fixture(),
        "Gate AIR API fixture only; no classifier or SHA-256 relation claim",
    )
    print(json.dumps({k: v for k, v in result.items() if k != "costs"}), flush=True)


if __name__ == "__main__":
    main()
