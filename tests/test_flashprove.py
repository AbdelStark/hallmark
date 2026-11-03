"""Caller-side FlashProve checks on fake outputs; no verifier is built and no proof is checked."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import flashprove as fp
import run_flashprove_gpu as gpu

ID = "ab" * 32
BUILD = fp.PIN["verifier_source_digest"]


def output(**fields):
    line = " ".join(f"{k}={v}" for k, v in fields.items())
    return f"cp_verify: notes\nresult: {line}\ncheck_proof: verified: exact match\n"


GOOD = dict(outcome="verified", commitment_id=ID, range="15:64", claim="exact-match", build=BUILD)


def test_accepts_only_the_callers_exact_match_claim():
    assert fp.accepted(0, output(**GOOD), ID, "15:64")
    assert not fp.accepted(1, output(**GOOD), ID, "15:64")
    assert not fp.accepted(0, output(**GOOD), "cd" * 32, "15:64")
    assert not fp.accepted(0, output(**GOOD), ID, "14:64")
    for field, value in [
        ("outcome", "within-limits"),
        ("claim", "next-token"),
        ("build", "0" * 64),
    ]:
        assert not fp.accepted(0, output(**GOOD | {field: value}), ID, "15:64")
    # Exit 0 without the result line (as after --help) is not a pass.
    assert not fp.accepted(0, "usage: check_proof.py\n", ID, "15:64")
    assert not fp.accepted(0, output(**GOOD) + "trailing\n", ID, "15:64")


@pytest.fixture
def kit_and_case(tmp_path):
    tree = tmp_path / "tree"
    kit = tree / "prover/examples" / fp.PIN["gpu_kit"]["name"]
    kit.mkdir(parents=True)
    case = tmp_path / "case"
    (case / "config").mkdir(parents=True)
    for name in ("policy.txt", "KL.bin", "layout.txt"):
        (kit / name).write_bytes(name.encode())
        (case / "config" / name).write_bytes(name.encode())
    (kit / "own_choices.req").write_bytes(b"request")
    (case / "example.req").write_bytes(b"request")
    (case / "example.y").write_bytes((199).to_bytes(4, "little"))
    log = tmp_path / "cp_commit.log"
    log.write_text(f"x\ncommitment ID: {ID}\n")
    return tree, case, log


def test_caller_case_reads_own_commitment_and_reply(kit_and_case):
    assert gpu.caller_case(*kit_and_case) == (ID, 199)


@pytest.mark.parametrize(
    "change",
    [
        lambda case, log: (case / "config/KL.bin").write_bytes(b"other scales"),
        lambda case, log: (case / "example.req").write_bytes(b"other request"),
        lambda case, log: (case / "example.y").write_bytes(b"\0" * 8),
        lambda case, log: log.write_text("no identifier\n"),
        lambda case, log: log.write_text(f"commitment ID: {ID}\ncommitment ID: {'cd' * 32}\n"),
        lambda case, log: log.write_text("commitment ID: " + "zz" * 32 + "\n"),
    ],
)
def test_caller_case_rejects_worker_substitutions(kit_and_case, change):
    tree, case, log = kit_and_case
    change(case, log)
    with pytest.raises(ValueError):
        gpu.caller_case(tree, case, log)


def test_source_digest_follows_upstream_file_list(tmp_path):
    tree = tmp_path
    for name in ("verifier/src/a.cpp", "verifier/src/b.h", "prover/attn/plan_rounds.h"):
        (tree / name).parent.mkdir(parents=True, exist_ok=True)
        (tree / name).write_text(name)
    (tree / "prover/hiding").mkdir()
    (tree / "prover/hiding/token_plan.h").write_text("plan")
    (tree / "blocks/frame").mkdir(parents=True)
    (tree / "blocks/frame/heads.h").write_text("h")
    (tree / "blocks/tests").mkdir()
    (tree / "blocks/tests/t.h").write_text("excluded")
    first = fp.source_digest(tree)
    (tree / "blocks/tests/t.h").write_text("changed test header")
    assert fp.source_digest(tree) == first
    (tree / "blocks/frame/heads.h").write_text("changed")
    assert fp.source_digest(tree) != first
