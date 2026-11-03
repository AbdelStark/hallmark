"""Verify FlashProve proofs with a verifier built from pinned, unchanged upstream source.

`make verify-flashprove` fetches the pinned archive, builds `cp_verify` on this host, checks the
two stored upstream proofs against caller-held values and runs upstream's rejection tables.
No GPU, weights or paid compute. The stored proofs use synthetic weights: a pass shows that this
verifier and these files fit together, not anything about a served model.
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

from run_e2e import sha, write_json
from run_llm_e2e import fetch, require

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "research/probes/flashprove"
PIN = json.loads((PROBE / "source.json").read_text())


def source_tree(output):
    archive = output / "source.tar.gz"
    fetch(PIN["url"], archive, PIN["sha256"], PIN["bytes"])
    with tarfile.open(archive) as tar:
        tar.extractall(output / "src", filter="data")
    (tree,) = (output / "src").iterdir()
    return tree


def source_digest(tree):
    """Upstream verifier/build.sh's `build_word`: SHA-256 of sha256sum lines over its sources."""
    src = tree / "verifier/src"
    rows = [(p.name, p) for p in sorted(src.iterdir())]
    rows += [
        (str(p.relative_to(src, walk_up=True)), p)
        for p in sorted((tree / "prover").glob("*/plan_rounds.h"))
    ]
    rows.append(("../../prover/hiding/token_plan.h", tree / "prover/hiding/token_plan.h"))
    blocks = tree / "blocks"
    headers = sorted(
        "./" + str(p.relative_to(blocks))
        for p in blocks.rglob("*.h")
        if p.is_file() and "tests" not in p.relative_to(blocks).parts
    )
    rows += [(name, blocks / name) for name in headers]
    text = "".join(f"{sha(path)}  {name}\n" for name, path in rows)
    return hashlib.sha256(text.encode()).hexdigest()


def build_verifier(tree, output):
    digest = source_digest(tree)
    require(digest == PIN["verifier_source_digest"], "verifier source digest changed")
    out = output / "bin"
    out.mkdir(mode=0o700)
    log = output / "verifier-build.log"
    if platform.system() == "Linux":
        args = ["bash", tree / "verifier/build.sh", "-", out]
        cwd = tree
    else:
        # Upstream build.sh needs GNU coreutils and ld; compile the same unchanged source with the
        # same macros and source digest, and the closest Apple clang hardening flags.
        args = [
            "clang++",
            "-O2",
            "-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_EXTENSIVE",
            "-U_FORTIFY_SOURCE",
            "-D_FORTIFY_SOURCE=2",
            "-fstack-protector-strong",
            "-ftrivial-auto-var-init=zero",
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Wuninitialized",
            "-Werror=unused-result",
            "-Wno-misleading-indentation",
            "-pthread",
            "-I.",
            "-I../../blocks",
            "-I../../prover",
            "-DBLK_FIELD=2",
            "-DBLK_COUNT_HASH_CALLS=1",
            "-DSERVING_BUILD=1",
            "-DDIGEST_WORDS=8",
            f'-DVF_SOURCE_DIGEST="{digest}"',
            "-o",
            out / "cp_verify",
            "cp_verify.cpp",
        ]
        cwd = tree / "verifier/src"
    started = time.monotonic()
    with log.open("x") as stream:
        subprocess.run(
            [str(a) for a in args], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, timeout=900
        ).check_returncode()
    verifier = out / "cp_verify"
    return verifier, dict(
        seconds=time.monotonic() - started,
        recipe="upstream verifier/build.sh" if platform.system() == "Linux" else "apple-clang",
        compiler=subprocess.check_output([args[0] if args[0] != "bash" else "g++", "--version"])
        .decode()
        .splitlines()[0],
        source_digest=digest,
        sha256=sha(verifier),
    )


def result_fields(stdout):
    """Upstream's pass rule: exit 0 and the line before the last starts `result: outcome=...`."""
    lines = stdout.rstrip("\n").splitlines()
    if len(lines) < 2 or not lines[-2].startswith("result: "):
        return None
    return dict(field.split("=", 1) for field in lines[-2][8:].split() if "=" in field)


def accepted(code, stdout, commitment_id, checked):
    fields = result_fields(stdout)
    return bool(
        code == 0
        and fields
        and fields.get("outcome") == "verified"
        and fields.get("claim") == "exact-match"
        and fields.get("commitment_id") == commitment_id
        and fields.get("range") == checked
        and fields.get("build") == PIN["verifier_source_digest"]
    )


def check_proof(tree, verifier, case, commitment_id, checked, next_token, log):
    """Run upstream integrations/check_proof.py with every expected value held by the caller."""
    args = [
        sys.executable,
        "-I",
        tree / "integrations/check_proof.py",
        case / "example.proof",
        case / "example.req",
        "--verifier",
        verifier,
        "--public-key-dir",
        case / "ivk",
        "--parameter-file",
        case / "config/policy.txt",
        "--scales-file",
        case / "config/KL.bin",
        "--commitment-id",
        commitment_id,
        "--range",
        checked,
        "--next-token",
        str(next_token),
        "--end-token",
        "none",
    ]
    started = time.monotonic()
    done = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=300)
    log.write_text(done.stdout + "\n--- stderr ---\n" + done.stderr)
    ok = accepted(done.returncode, done.stdout, commitment_id, checked)
    return ok, dict(
        exit_code=done.returncode,
        seconds=time.monotonic() - started,
        result=done.stdout.rstrip("\n").splitlines()[-2:],
    )


def direct(verifier, case, commitment_id, log):
    """One raw cp_verify call: (exit code, last line)."""
    args = [
        verifier,
        case / "config",
        case / "ivk",
        case / "example.req",
        case / "example.y",
        case / "example.proof",
        "-id",
        commitment_id,
    ]
    done = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=300)
    log.write_text(done.stdout + "\n--- stderr ---\n" + done.stderr)
    return done.returncode, (done.stdout.strip().splitlines() or [""])[-1]


def rejection_tables(tree, verifier, output):
    rows = []
    for example, table, count in PIN["rejection_tables"]:
        args = [
            sys.executable,
            "-I",
            tree / "examples/rejected-proofs/try_altered_copies.py",
            verifier,
            output / f"altered-{Path(table).stem}",
            tree / "examples/rejected-proofs" / table,
            "--example",
            example,
        ]
        started = time.monotonic()
        done = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=1800)
        (output / f"altered-{Path(table).stem}.log").write_text(done.stdout + done.stderr)
        last = (done.stdout.strip().splitlines() or [""])[-1]
        rows.append(
            dict(
                table=table,
                example=example,
                exit_code=done.returncode,
                last_line=last,
                seconds=time.monotonic() - started,
            )
        )
        require(
            done.returncode == 0 and last == f"{count} altered sets: all rejected",
            f"upstream rejection table {table} did not reject every altered set",
        )
    return rows


def verify_stored(output):
    tree = source_tree(output)
    verifier, build = build_verifier(tree, output)
    checks = {}
    for name, case in PIN["examples"].items():
        ok, row = check_proof(
            tree,
            verifier,
            tree / "examples" / name,
            case["commitment_id"],
            case["range"],
            case["next_token"],
            output / f"check-{name}.log",
        )
        require(ok, f"stored example {name} was not accepted")
        checks[name] = row
    tables = rejection_tables(tree, verifier, output)
    return tree, verifier, dict(build=build, examples=checks, rejection_tables=tables)


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    (ROOT / "runs").mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="flashprove-verify-", dir=ROOT / "runs"))
    print("Outputs: " + str(output), flush=True)
    started = time.monotonic()
    try:
        _, _, result = verify_stored(output)
        result |= dict(
            passed=True,
            schema_id="hallmark.flashprove-verify/1",
            source=PIN,
            host=dict(system=platform.system(), machine=platform.machine()),
            rejections=sum(c for *_, c in PIN["rejection_tables"]),
            seconds=time.monotonic() - started,
            synthetic_weights_only=True,
            qualified_backend=False,
            hiding_claim=False,
        )
        write_json(output / "result.json", result)
        print(json.dumps({k: result[k] for k in ("passed", "rejections", "seconds")}))
    except BaseException as exc:
        write_json(output / "failure.json", dict(type=type(exc).__name__, message=str(exc)))
        raise


if __name__ == "__main__":
    main()
