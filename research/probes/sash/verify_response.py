"""Fresh proof-only worker for the fixed TinyLlama response and mutation suite."""

import copy
import hashlib
import json
import os
import resource
import shutil
import subprocess
import tarfile
import time
from pathlib import Path

from check_response import TAGS, bundle, read_json

if not __debug__:
    raise RuntimeError("Run research workers without Python optimization")
root = Path("/persist")
out = root / "output"
out.mkdir(exist_ok=False)
started = time.monotonic()
job = read_json(root / "protocol.json")
commands = []
cases = []
resource.setrlimit(resource.RLIMIT_AS, (job["max_address_space_bytes"],) * 2)
resource.setrlimit(resource.RLIMIT_FSIZE, (job["max_single_file_bytes"],) * 2)
os.environ["RAYON_NUM_THREADS"] = "4"


def run(name, directory, expected, accept):
    t = time.monotonic()
    print("Starting " + name, flush=True)
    try:
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
        "/work/zk-prover",
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
    with (out / (name + ".stdout")).open("wb") as so, (out / (name + ".stderr")).open("wb") as se:
        p = subprocess.run(args, stdout=so, stderr=se, timeout=600)
    row = {
        "name": name,
        "args": args,
        "exit_code": p.returncode,
        "seconds": time.monotonic() - t,
        "peak_child_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
    }
    commands.append(row)
    (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    doc = read_json(out / (name + ".stdout"), 8 * 1024**2)
    v = doc["result"]
    assert doc["provenance"]["unsound_skips"] == [] and doc["provenance"]["dirty"] is False
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
    result = {
        "name": name,
        "accepted": accepted,
        "stage": "real verifier",
        "seconds": row["seconds"],
        "failures": v["failures"],
    }
    cases.append(result)
    print(json.dumps(result), flush=True)


def write_mutated(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, separators=(",", ":")))
    tmp.replace(path)


def mutate(name, edit):
    d = Path("/work") / name
    shutil.copytree("/work/proof", d, copy_function=os.link)
    expected = copy.deepcopy(enrolled)
    edit(d, expected)
    run(name, d, expected, False)
    (out / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")


try:
    for name, digest in job["inputs"].items():
        with (root / name).open("rb") as f:
            assert hashlib.file_digest(f, "sha256").hexdigest() == digest, name
    Path("/work").mkdir(exist_ok=True)
    shutil.copy2(root / "zk-prover", "/work/zk-prover")
    Path("/work/zk-prover").chmod(0o700)
    inventory = read_json(root / "proof-inventory.json")
    seen = set()
    with tarfile.open(root / "proofs.tar.gz", "r|gz") as tar:
        for member in tar:
            assert member.isfile() and member.name in inventory and member.name not in seen
            rel = Path(member.name)
            assert not rel.is_absolute() and ".." not in rel.parts
            seen.add(member.name)
            p = Path("/work") / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as src, p.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            assert p.stat().st_size == inventory[member.name]["bytes"]
            with p.open("rb") as f:
                assert (
                    hashlib.file_digest(f, "sha256").hexdigest() == inventory[member.name]["sha256"]
                )
    assert seen == inventory.keys()
    enrolled = read_json(root / "expected.json")
    assert (
        hashlib.sha256((root / "expected.json").read_bytes()).hexdigest() == job["expected_sha256"]
    )
    run("honest-0", Path("/work/proof"), enrolled, True)
    run("honest-1", Path("/work/proof"), enrolled, True)
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
    for name, row in inventory.items():
        with (Path("/work") / name).open("rb") as f:
            assert hashlib.file_digest(f, "sha256").hexdigest() == row["sha256"], (
                "control proof changed during mutations"
            )
    assert len(cases) == 16 and sum(x["accepted"] for x in cases) == 2
    (out / "result.json").write_text(
        json.dumps(
            {
                "passed": True,
                "seconds": time.monotonic() - started,
                "cases": cases,
                "weights_present": False,
                "witness_present": False,
                "worker": (
                    "fresh proof-only Linux CPU process; "
                    "same pinned upstream verifier implementation"
                ),
                "security_review": False,
            },
            indent=2,
        )
        + "\n"
    )
except BaseException as e:
    (out / "failure.json").write_text(
        json.dumps(
            {"type": type(e).__name__, "message": str(e), "seconds": time.monotonic() - started},
            indent=2,
        )
        + "\n"
    )
    raise
