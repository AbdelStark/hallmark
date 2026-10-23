"""Fresh proof-only worker for the fixed TinyLlama response and mutation suite."""

import argparse
import copy
import hashlib
import json
import os
import platform
import re
import resource
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

from check_response import TAGS, bundle, read_json

if not __debug__:
    raise RuntimeError("Run research workers without Python optimization")

NATIVE_BOUNDARY_CASES = [
    ("claim-head-alias", "head.claims.json", ["head_tok", 0, 0], "alias", "OodsNotMatching"),
    ("claim-embedding-alias", "B0L0.claims.json", ["embed_tok", 0, 0], "alias", "OodsNotMatching"),
    ("sample-alias", "B0L0.proof.json", ["sampled_values", 0, 0, 0, 0, 0], "alias", "Merkle("),
    ("query-alias", "B0L0.proof.json", ["queried_values", 0, 0], "alias", "Merkle("),
    (
        "column-alias",
        "B0L0.proof.json",
        ["decommitments", 0, "column_witness", 0],
        "alias",
        "Merkle(",
    ),
    (
        "fri-polynomial-alias",
        "B0L0.proof.json",
        ["fri_proof", "last_layer_poly", "coeffs", 0, 0, 0],
        "alias",
        "Merkle(",
    ),
    ("empty-commitments", "B0L0.proof.json", ["commitments"], "empty", "proof tree count mismatch"),
    ("empty-samples", "B0L0.proof.json", ["sampled_values"], "empty", "proof tree count mismatch"),
    (
        "empty-decommitments",
        "B0L0.proof.json",
        ["decommitments"],
        "empty",
        "proof tree count mismatch",
    ),
    ("empty-queries", "B0L0.proof.json", ["queried_values"], "empty", "proof tree count mismatch"),
    (
        "empty-fri-layers",
        "B0L0.proof.json",
        ["fri_proof", "inner_layers"],
        "empty",
        "Fri(InvalidNumFriLayers)",
    ),
    (
        "empty-fri-witness",
        "B0L0.proof.json",
        ["fri_proof", "first_layer", "fri_witness"],
        "empty",
        "Fri(FirstLayerEvaluationsInvalid)",
    ),
    (
        "config-queries",
        "B0L0.proof.json",
        ["config", "fri_config", "n_queries"],
        "zero",
        "proof configuration mismatch",
    ),
    (
        "config-blowup",
        "B0L0.proof.json",
        ["config", "fri_config", "log_blowup_factor"],
        "zero",
        "proof configuration mismatch",
    ),
    (
        "config-pow",
        "B0L0.proof.json",
        ["config", "pow_bits"],
        "increment",
        "proof configuration mismatch",
    ),
    ("empty-gkr", "B0L0.claims.json", ["gkr"], "empty", "unparseable GKR proof"),
    (
        "input-token-field-alias",
        "B0L0.fixed.json",
        ["tok_in", 0],
        "alias",
        "token ID outside enrolled vocabulary",
    ),
    (
        "output-token-field-alias",
        "head.fixed.json",
        ["tok_out", 31],
        "alias",
        "token ID outside enrolled vocabulary",
    ),
    ("empty-fixed-sizes", "B0L0.fixed.json", ["sizes"], "empty", "claims shape mismatch"),
    (
        "empty-fixed-column-sizes",
        "B0L0.fixed.json",
        ["sizes", 0],
        "empty",
        "proof column shape mismatch",
    ),
]


def write_mutated(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, separators=(",", ":")))
    tmp.replace(path)


def mutate_native(path, keys, operation):
    document = read_json(path, 128 * 1024**2)
    value = document
    for key in keys[:-1]:
        value = value[key]
    key = keys[-1]
    if operation == "alias":
        value[key] += 2**31 - 1
    elif operation == "empty":
        value[key] = []
    elif operation == "zero":
        value[key] = 0
    elif operation == "increment":
        value[key] += 1
    else:
        raise ValueError("unknown native mutation")
    write_mutated(path, document)


def check_inventory(inventory):
    wanted = {f"proof/{tag}.{kind}.json" for tag in TAGS for kind in ("fixed", "claims", "proof")}
    assert set(inventory) == wanted, "incomplete proof inventory"
    for row in inventory.values():
        assert set(row) == {"bytes", "sha256"}, "invalid inventory row"
        assert type(row["bytes"]) is int and 0 < row["bytes"] <= 128 * 1024**2, "invalid size"
        assert isinstance(row["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
    assert sum(row["bytes"] for row in inventory.values()) <= 1024**3, "oversized proof bundle"


def check_provenance(provenance, job):
    assert provenance["unsound_skips"] == [], "unsound verifier mode"
    assert provenance["commit"] == job["source_commit"], "wrong verifier source"
    assert type(job.get("source_dirty", False)) is bool, "invalid source status"
    assert provenance["dirty"] is job.get("source_dirty", False), "unexpected source changes"
    assert provenance.get("shape_root_source") == job.get("shape_root_source"), "wrong root basis"


def main(root, work):
    out = root / "output"
    out.mkdir(exist_ok=False)
    started = time.monotonic()
    job = read_json(root / "protocol.json")
    commands = []
    cases = []
    if sys.platform != "darwin":
        resource.setrlimit(resource.RLIMIT_AS, (job["max_address_space_bytes"],) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (job["max_single_file_bytes"],) * 2)
    os.environ["RAYON_NUM_THREADS"] = "4"

    def run(name, directory, expected, accept, native_failure=None):
        t = time.monotonic()
        print("Starting " + name, flush=True)
        try:
            assert native_failure is None or not accept, "native bypass is negative-only"
            if native_failure is None:
                bundle(directory, expected)
        except (AssertionError, ValueError, KeyError) as e:
            assert not accept, name
            row = {
                "name": name,
                "accepted": False,
                "stage": "caller statement checks",
                "reason": str(e) or type(e).__name__,
                "seconds": time.monotonic() - t,
            }
            cases.append(row)
            print(json.dumps(row), flush=True)
            return
        pp = out / (name + "-prompt.json")
        pp.write_text(json.dumps(expected["prompt_ids"]))
        rr = out / (name + "-roots.json")
        rr.write_text(json.dumps(expected["roots"]))
        args = [
            str(work / "zk-prover"),
            "boundary-grid",
            "--dir",
            str(directory),
            "--tags",
            ",".join(TAGS),
            "--verify",
            "--prompt",
            str(pp),
            "--verify-calibration",
            str(rr),
            "--expect-model-roots",
            str(rr),
            "--expect-pre-roots",
            str(rr),
            "--expect-layer-links",
            "22",
            "--expect-token-links",
            "0",
        ]
        with (
            (out / (name + ".stdout")).open("wb") as so,
            (out / (name + ".stderr")).open("wb") as se,
        ):
            p = subprocess.run(args, stdout=so, stderr=se, timeout=600)
        row = {
            "name": name,
            "args": args,
            "exit_code": p.returncode,
            "seconds": time.monotonic() - t,
            "peak_child_rss_bytes": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
            * (1 if sys.platform == "darwin" else 1024),
        }
        commands.append(row)
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        doc = read_json(out / (name + ".stdout"), 8 * 1024**2)
        v = doc["result"]
        check_provenance(doc["provenance"], job)
        accepted = (
            p.returncode == 0
            and v["all_chain"] is True
            and v["verified"]["accepted"] == 23
            and v["shape_roots"]["matched"] == 23
            and v["gaps"] == []
            and v["failures"] == []
            and v["tokens"]["all"] is True
            and v["tokens"]["prompt_positions"] == 25
            and v["tokens"]["generated_positions"] == 7
            and v["links_passed"] == 22
        )
        assert accepted == accept, name
        if not accept:
            assert (
                p.returncode != 0
                and v["all_chain"] is False
                and v["verified"]["accepted"] < 23
                and v["failures"]
            ), name
        if native_failure is not None:
            assert any(native_failure in failure for failure in v["failures"]), name
        result = {
            "caller_checks": native_failure is None,
            "name": name,
            "accepted": accepted,
            "stage": "real verifier",
            "seconds": row["seconds"],
            "failures": v["failures"],
        }
        cases.append(result)
        print(json.dumps(result), flush=True)

    def mutate(name, edit, native_failure=None):
        d = work / name
        shutil.copytree(work / "proof", d, copy_function=os.link)
        expected = copy.deepcopy(enrolled)
        edit(d, expected)
        run(name, d, expected, False, native_failure)
        (out / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")

    try:
        for name, digest in job["inputs"].items():
            with (root / name).open("rb") as f:
                assert hashlib.file_digest(f, "sha256").hexdigest() == digest, name
        work.mkdir(exist_ok=True)
        shutil.copy2(root / "zk-prover", work / "zk-prover")
        (work / "zk-prover").chmod(0o700)
        inventory = read_json(root / "proof-inventory.json")
        check_inventory(inventory)
        seen = set()
        with tarfile.open(root / "proofs.tar.gz", "r|gz") as tar:
            for member in tar:
                assert member.isfile() and member.name in inventory and member.name not in seen
                assert member.size == inventory[member.name]["bytes"], "archive size mismatch"
                rel = Path(member.name)
                assert not rel.is_absolute() and ".." not in rel.parts
                seen.add(member.name)
                p = work / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as src, p.open("xb") as dst:
                    shutil.copyfileobj(src, dst)
                assert p.stat().st_size == inventory[member.name]["bytes"]
                with p.open("rb") as f:
                    assert (
                        hashlib.file_digest(f, "sha256").hexdigest()
                        == inventory[member.name]["sha256"]
                    )
        assert seen == inventory.keys()
        enrolled = read_json(root / "expected.json")
        assert (
            hashlib.sha256((root / "expected.json").read_bytes()).hexdigest()
            == job["expected_sha256"]
        )
        run("honest-0", work / "proof", enrolled, True)
        run("honest-1", work / "proof", enrolled, True)
        mutate("changed-prompt", lambda d, e: e["prompt_ids"].__setitem__(0, 530))
        mutate("changed-answer", lambda d, e: e["answer_ids"].__setitem__(0, 1577))
        mutate("changed-model", lambda d, e: e["roots"][0].__setitem__("model_root", "0" * 64))
        mutate(
            "changed-calibration",
            lambda d, e: e["roots"][0]["frac_per_head"].__setitem__(
                0, e["roots"][0]["frac_per_head"][0] + 1
            ),
        )
        mutate("missing-layer", lambda d, e: (d / "B0L10.proof.json").unlink())

        def fixed_edit(d, tag, edit):
            p = d / (tag + ".fixed.json")
            v = read_json(p)
            edit(v)
            write_mutated(p, v)

        mutate(
            "wrong-layer-coordinate",
            lambda d, e: fixed_edit(d, "B0L1", lambda f: f.__setitem__("layer", 2)),
        )
        mutate(
            "changed-final-output",
            lambda d, e: fixed_edit(d, "head", lambda f: f["tok_out"].__setitem__(31, 3)),
        )
        mutate(
            "token-alias",
            lambda d, e: fixed_edit(d, "B0L0", lambda f: f["tok_in"].__setitem__(0, 2**32 + 529)),
        )
        mutate(
            "boolean-token",
            lambda d, e: fixed_edit(d, "B0L0", lambda f: f["tok_in"].__setitem__(0, True)),
        )
        mutate(
            "open-scale-profile",
            lambda d, e: fixed_edit(
                d, "B0L0", lambda f: f["params"]["mats"][2].__setitem__("variant", "fold")
            ),
        )
        mutate(
            "weaker-security",
            lambda d, e: fixed_edit(d, "B0L0", lambda f: f.__setitem__("n_queries", 1)),
        )

        def proof_edit(d, tag, tree):
            p = d / (tag + ".proof.json")
            v = read_json(p, 128 * 1024**2)
            v["commitments"][tree][0] ^= 1
            write_mutated(p, v)

        mutate("altered-proof", lambda d, e: proof_edit(d, "B0L0", 0))
        mutate("altered-residual-boundary", lambda d, e: proof_edit(d, "B0L10", 4))

        def claim_edit(d, e):
            p = d / "head.claims.json"
            v = read_json(p, 8 * 1024**2)
            v["head_tok"][0][0] ^= 1
            write_mutated(p, v)

        mutate("altered-output-claim", claim_edit)
        native = job.get("shape_root_source") == "compiled-enrollment"
        if native:
            mutate(
                "native-unknown-shape",
                lambda d, e: fixed_edit(
                    d, "B0L0", lambda f: f["params"].__setitem__("round", "away")
                ),
                native_failure="unenrolled shape",
            )
            mutate(
                "native-changed-calibration",
                lambda d, e: e["roots"][0]["frac_per_head"].__setitem__(
                    0, e["roots"][0]["frac_per_head"][0] + 1
                ),
                native_failure="unenrolled shape",
            )
            for name, filename, keys, operation, failure in NATIVE_BOUNDARY_CASES:
                mutate(
                    name,
                    lambda d, e, f=filename, k=keys, op=operation: mutate_native(d / f, k, op),
                    native_failure=failure,
                )
        for name, row in inventory.items():
            with (work / name).open("rb") as f:
                assert hashlib.file_digest(f, "sha256").hexdigest() == row["sha256"], (
                    "control proof changed during mutations"
                )
        assert len(cases) == (38 if native else 16) and sum(x["accepted"] for x in cases) == 2
        (out / "result.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "seconds": time.monotonic() - started,
                    "cases": cases,
                    "weights_present": False,
                    "witness_present": False,
                    "worker": (
                        f"fresh proof-only {platform.system()} CPU process; "
                        "same pinned upstream verifier implementation"
                    ),
                    "shape_root_source": job.get("shape_root_source", "runtime-derivation"),
                    "source_dirty": job.get("source_dirty", False),
                    "security_review": False,
                },
                indent=2,
            )
            + "\n"
        )
    except BaseException as e:
        (out / "failure.json").write_text(
            json.dumps(
                {
                    "type": type(e).__name__,
                    "message": str(e),
                    "seconds": time.monotonic() - started,
                },
                indent=2,
            )
            + "\n"
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/persist"))
    parser.add_argument("--work", type=Path, default=Path("/work"))
    args = parser.parse_args()
    main(args.root.resolve(), args.work.resolve())
