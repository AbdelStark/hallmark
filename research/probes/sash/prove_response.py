"""Prove every fixed TinyLlama segment against independently enrolled roots."""

import hashlib
import json
import os
import resource
import shlex
import shutil
import subprocess
import tarfile
import time
from pathlib import Path

from check_response import TAGS, bundle, read_json, require

ROOT = Path("/persist")
WORK = Path("/work")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def closed(point):
    require(point["accepts"] is True and point["binding"]["all_bound"] is True, "segment rejected")
    require(point["binding"]["unbound"] == [], "open binding")
    verdict = point["verdict"]
    require(verdict["shape_root_ok"] is True and verdict["error"] is None, "wrong shape")
    require(verdict["rq_scale_open"] == [] and verdict["deq_out_open"] == [], "open scale")
    require(verdict["nn_open"] is False and verdict["ao_q_open"] is False, "open arithmetic")
    for key, value in verdict.items():
        if key.endswith("_ok"):
            require(value is True or (type(value) is list and all(x is True for x in value)), key)
    require(verdict["sums_cancel"] is True, "claimed sums do not cancel")


def main():
    out = ROOT / "output"
    out.mkdir(exist_ok=False)
    job = read_json(ROOT / "protocol.json")
    resource.setrlimit(resource.RLIMIT_AS, (job["max_address_space_bytes"],) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (job["max_single_file_bytes"],) * 2)
    os.environ["RAYON_NUM_THREADS"] = str(job["threads"])
    started = time.monotonic()
    commands = []

    def run(name, args):
        require(time.monotonic() - started < 2900, "proving deadline exceeded")
        print("Starting " + name, flush=True)
        before = time.monotonic()
        with (
            (out / (name + ".stdout")).open("xb") as stdout,
            (out / (name + ".stderr")).open("xb") as stderr,
        ):
            process = subprocess.run(args, cwd=WORK, stdout=stdout, stderr=stderr, timeout=600)
        row = dict(
            name=name,
            args=args,
            exit_code=process.returncode,
            seconds=time.monotonic() - before,
            peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        )
        commands.append(row)
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        require(process.returncode == 0, name + " failed")
        print(json.dumps(row), flush=True)

    try:
        for name, pin in job["inputs"].items():
            require(digest(ROOT / name) == pin, "changed job input: " + name)
        WORK.mkdir(exist_ok=False)
        shutil.copy2(ROOT / "zk-prover", WORK / "zk-prover")
        (WORK / "zk-prover").chmod(0o700)
        inventory = read_json(ROOT / "inventory.json")
        seen = set()
        with tarfile.open(ROOT / "inputs.tar.gz", "r|gz") as tar:
            for member in tar:
                require(
                    member.isfile() and member.name in inventory and member.name not in seen,
                    "invalid archive member",
                )
                relative = Path(member.name)
                require(
                    not relative.is_absolute() and ".." not in relative.parts, "unsafe archive path"
                )
                seen.add(member.name)
                path = WORK / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as src, path.open("xb") as dst:
                    shutil.copyfileobj(src, dst)
                pin = inventory[member.name]
                require(
                    path.stat().st_size == pin["bytes"] and digest(path) == pin["sha256"],
                    "changed witness file",
                )
        require(seen == inventory.keys(), "incomplete archive")
        expected = read_json(ROOT / "expected.json")
        case = read_json(ROOT / "response-case.json")
        plan = [
            shlex.split(line)
            for line in (WORK / "plan.txt").read_text().splitlines()
            if line.strip()
        ]
        tags = [args[args.index("--ser-tag") + 1] for args in plan]
        require(tags == TAGS, "wrong proving coverage")
        head = read_json(WORK / "head_B0/manifest.json")
        require(
            head["residual_stream"] == {} and head["head"]["final_norm"] is True,
            "wrong output-head family",
        )
        binary = str(WORK / "zk-prover")
        flags = case["shared_flags"]
        run(
            "roots",
            [
                binary,
                "model-roots",
                "--plan",
                "plan.txt",
                "--pins",
                shlex.join(flags),
                "--out",
                str(out / "model-roots.json"),
            ],
        )
        roots = read_json(out / "model-roots.json")
        require(roots == expected["roots"], "model or calibration differs from caller enrollment")
        report = read_json(out / "roots.stdout")
        require(
            report["provenance"]["unsound_skips"] == [] and report["result"]["rejections"] == [],
            "root derivation rejected",
        )
        for tag, args in zip(TAGS, plan, strict=True):
            run(
                "prove-" + tag,
                [
                    binary,
                    "compose",
                    *flags,
                    *args,
                    "--verify-calibration",
                    str(ROOT / "expected-roots.json"),
                    "--ser-dir",
                    str(out / "proof"),
                ],
            )
            report = read_json(out / ("prove-" + tag + ".stdout"))
            closed(report["result"]["point"])
            provenance = report["provenance"]
            require(
                provenance["unsound_skips"] == []
                and provenance["commit"] == case["source"]["revision"]
                and provenance["dirty"] is False,
                "unexpected prover source",
            )
        bundle(out / "proof", expected)
        (out / "result.json").write_text(
            json.dumps(
                dict(
                    proofs_produced=23,
                    seconds=time.monotonic() - started,
                    full_response_verified=False,
                    next="fresh proof-only worker",
                ),
                indent=2,
            )
            + "\n"
        )
    except BaseException as exc:
        (out / "failure.json").write_text(
            json.dumps(
                dict(type=type(exc).__name__, message=str(exc), seconds=time.monotonic() - started),
                indent=2,
            )
            + "\n"
        )
        raise


if __name__ == "__main__":
    main()
