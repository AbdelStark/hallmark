"""Corpus plumbing and component evidence; no independent or genuine-proof result."""

import hashlib
import json
import os
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from hallmark import conformance_checks
from hallmark.conformance import (
    CHEATS,
    MANDATORY_REQUIREMENTS,
    Case,
    ConformanceReport,
    Corpus,
    Outcome,
    _read_file,
    implementation_identity,
    load_corpus,
    run_corpus,
)
from hallmark.errors import HallmarkError
from hallmark.manifests import ArtifactDigest, FileRef

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "tests/vectors/v1"
PIN = ArtifactDigest(bytes.fromhex((VECTORS / "corpus.id").read_text().strip()))
PRIMARY = ArtifactDigest(b"p" * 32)


@pytest.fixture
def corpus() -> Corpus:
    return load_corpus(VECTORS / "corpus.json")


def run(corpus: Corpus, root: Path = VECTORS, software: bool = True) -> ConformanceReport:
    return run_corpus(
        corpus, root, expected_corpus=corpus.identity(), primary=PRIMARY, software_only=software
    )


def replace_case(corpus: Corpus, case_id: str, **changes) -> Corpus:
    return corpus.model_copy(
        update={
            "cases": tuple(
                case.model_copy(update=changes) if case.case_id == case_id else case
                for case in corpus.cases
            )
        }
    )


def test_frozen_results_and_full_gate(corpus: Corpus, monkeypatch) -> None:
    actual = conformance_checks.execute
    calls = []

    def execute(check, inputs, trust, expected_request, now):
        assert check != "unavailable"
        calls.append(check)
        return actual(check, inputs, trust, expected_request, now)

    monkeypatch.setattr(conformance_checks, "execute", execute)
    report = run(corpus)
    assert corpus.identity() == PIN
    assert len(calls) == report.matched == 156
    assert report.mismatched == 0 and len(report.unavailable) == 32
    assert report.exit_code() == 0 and report.software_passed
    assert not report.all_required_executed and report.independent is None
    assert report.model_copy(update={"scope": "all-required-evidence"}).exit_code() == 3
    assert all(
        result.observed.claim_a == result.observed.claim_b == "not-accepted"
        for result in report.cases
        if result.observed is not None
    )


def test_requirements_and_all_original_cheats_are_retained(corpus: Corpus) -> None:
    assert {item.id for item in corpus.requirements} == MANDATORY_REQUIREMENTS
    assert {case.requirement for case in corpus.cases} == MANDATORY_REQUIREMENTS
    by_id = {case.case_id: case for case in corpus.cases}
    for name in CHEATS:
        case = by_id["full.prd-" + name]
        assert case.evidence_class == "hybrid" and case.check == "unavailable"
        assert case.parent == "full.hybrid-valid" and case.mutation == name
        assert case.expected.code and not case.expected.accepted and case.unavailable
    assert by_id["full.b2-valid"].trust != by_id["full.hybrid-valid"].trust


def test_expected_result_corruption_is_a_mismatch(corpus: Corpus) -> None:
    first = corpus.cases[0]
    wrong = first.expected.model_copy(update={"integers": (123,)})
    mutant = replace_case(corpus, first.case_id, expected=wrong)
    assert mutant.identity() != PIN
    report = run(mutant)
    assert report.exit_code() == 1 and report.mismatched == 1 and report.matched == 155
    assert len(report.unavailable) == 32


def test_no_input_access_before_external_pin_agreement(corpus: Corpus, monkeypatch) -> None:
    def forbidden(*args):
        pytest.fail("read before checking external corpus identity")

    monkeypatch.setattr("hallmark.conformance._read_file", forbidden)
    with pytest.raises(HallmarkError, match="INPUT_INVALID"):
        run_corpus(corpus, VECTORS, expected_corpus=PRIMARY, primary=PRIMARY)


@pytest.mark.parametrize("kind", ["input", "source", "trust", "expectation"])
def test_pinned_file_tampering_fails(corpus: Corpus, tmp_path: Path, kind: str) -> None:
    shutil.copytree(VECTORS, tmp_path / "vectors")
    ref = {
        "input": corpus.cases[0].inputs[0],
        "source": corpus.requirements[0].source,
        "trust": corpus.trust_policies[0],
        "expectation": corpus.expectations[0],
    }[kind]
    path = tmp_path / "vectors" / ref.path
    raw = path.read_bytes()
    path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    with pytest.raises(HallmarkError, match="INPUT_INVALID"):
        run(corpus, tmp_path / "vectors")


@pytest.mark.parametrize("kind", ["symlink", "directory-link", "hardlink", "fifo", "directory"])
def test_file_reader_rejects_unsafe_files(tmp_path: Path, kind: str) -> None:
    content = b"fixture"
    target = tmp_path / "actual"
    target.write_bytes(content)
    path = tmp_path / "input"
    if kind == "symlink":
        path.symlink_to(target)
    elif kind == "directory-link":
        (tmp_path / "real").mkdir()
        (tmp_path / "real" / "input").write_bytes(content)
        (tmp_path / "link").symlink_to(tmp_path / "real", target_is_directory=True)
        path = tmp_path / "link/input"
    elif kind == "hardlink":
        os.link(target, path)
    elif kind == "fifo":
        os.mkfifo(path)
    else:
        path.mkdir()
    ref = FileRef(
        path=path.relative_to(tmp_path).as_posix(),
        size=len(content),
        sha256=hashlib.sha256(content).digest(),
    )
    with pytest.raises((OSError, HallmarkError)):
        _read_file(tmp_path, ref)


@pytest.mark.parametrize("path", ["../private", "/private", "a/../b", "a\\b", "a:b"])
def test_input_paths_cannot_escape_root(path: str) -> None:
    with pytest.raises(ValidationError):
        FileRef(path=path, size=0, sha256=b"x" * 32)


@pytest.mark.parametrize(
    "changes",
    [
        {"check": "shell"},
        {"inputs": ()},
        {"parent": "missing", "mutation": "change"},
        {"parent": "wire.valid-00", "mutation": "cycle"},
        {"parent": "wire.valid-01", "mutation": None},
        {"trust": b"x" * 31},
        {"now": True},
        {"requirement": "absent"},
        {"unavailable": ("W99",)},
        {"evidence_class": "real-proof"},
    ],
)
def test_invalid_cases_cannot_execute(corpus: Corpus, changes: dict) -> None:
    with pytest.raises(HallmarkError):
        run(replace_case(corpus, "wire.valid-00", **changes))


def test_mutation_must_change_input_and_cannot_cycle(corpus: Corpus) -> None:
    first = next(case for case in corpus.cases if case.case_id == "wire.valid-00")
    same = replace_case(
        corpus, "wire.valid-01", parent=first.case_id, mutation="unchanged", inputs=first.inputs
    )
    with pytest.raises(HallmarkError):
        same.identity()
    cycle = replace_case(corpus, "wire.valid-00", parent="wire.valid-01", mutation="cycle")
    cycle = replace_case(cycle, "wire.valid-01", parent="wire.valid-00", mutation="cycle")
    with pytest.raises(HallmarkError):
        cycle.identity()


@pytest.mark.parametrize("field", ["trust", "expected_request"])
def test_context_is_independently_required(corpus: Corpus, field: str) -> None:
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        run(replace_case(corpus, "wire.valid-00", **{field: b"x" * 32}))


def test_obligation_cannot_be_removed_or_relabelled(corpus: Corpus) -> None:
    reduced = corpus.model_copy(
        update={"cases": tuple(c for c in corpus.cases if c.case_id != "full.prd-replay")}
    )
    with pytest.raises(HallmarkError):
        reduced.identity()
    wrong = replace_case(corpus, "diagnostic.input", requirement="error.STORAGE_FAILED")
    with pytest.raises(HallmarkError):
        wrong.identity()
    duplicated = corpus.model_copy(update={"cases": (corpus.cases[0], *corpus.cases)})
    with pytest.raises(HallmarkError):
        duplicated.identity()


def test_conflicting_file_references_and_total_size_are_rejected(corpus: Corpus) -> None:
    first = next(case for case in corpus.cases if case.case_id == "wire.valid-00")
    shared = first.inputs[0].model_copy(update={"sha256": b"x" * 32})
    conflict = replace_case(corpus, "wire.valid-01", inputs=(shared,))
    with pytest.raises(HallmarkError):
        conflict.identity()
    huge = first.inputs[0].model_copy(update={"path": "huge", "size": 64 * 1024 * 1024})
    with pytest.raises(HallmarkError):
        replace_case(corpus, first.case_id, inputs=(huge,)).identity()


@pytest.mark.parametrize("payload", ['{"revision":"x","revision":"y"}', '{"schema_id":null}', "[]"])
def test_malformed_manifest_is_rejected(tmp_path: Path, payload: str) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(payload)
    with pytest.raises((HallmarkError, ValueError)):
        load_corpus(path)


def test_report_cannot_relabel_missing_evidence_as_passed(corpus: Corpus) -> None:
    report = run(corpus)
    for changes in (
        {"matched": 188},
        {"unavailable": ()},
        {"all_required_executed": True},
        {"mismatched": 1},
        {"cases": tuple(reversed(report.cases))},
        {"independent": b"i" * 32},
    ):
        with pytest.raises(HallmarkError):
            report.model_copy(update=changes).exit_code()
    missing = tuple(c for c in report.cases if c.status == "unavailable")
    empty = report.model_copy(
        update={"cases": missing, "matched": 0, "software_passed": False}
    )._validated()
    assert empty.exit_code() == 1


def test_unexpected_implementation_exception_is_not_an_expected_result(
    corpus: Corpus, monkeypatch
) -> None:
    def explode(*args):
        raise RuntimeError("SYNTHETIC_PRIVATE_SENTINEL")

    monkeypatch.setattr(conformance_checks, "_execute", explode)
    with pytest.raises(RuntimeError):
        run(corpus)


@pytest.mark.parametrize(
    "name,cls",
    [
        ("conformance-case", Case),
        ("conformance-corpus", Corpus),
        ("conformance-report", ConformanceReport),
    ],
)
def test_schema_snapshots(name, cls) -> None:
    assert (
        json.loads((ROOT / f"docs/schemas/{name}-v1.json").read_text()) == cls.model_json_schema()
    )


def test_rebuild_reproduces_frozen_bytes_and_refuses_overwrite(tmp_path: Path) -> None:
    build = runpy.run_path(str(ROOT / "scripts/build_conformance.py"))["build"]
    rebuilt = tmp_path / "fresh"
    assert build(rebuilt, VECTORS / "sources").identity() == PIN
    files = {
        path.relative_to(VECTORS): path.read_bytes()
        for path in VECTORS.rglob("*")
        if path.is_file()
    }
    assert {
        path.relative_to(rebuilt): path.read_bytes()
        for path in rebuilt.rglob("*")
        if path.is_file()
    } == files
    with pytest.raises(FileExistsError):
        build(rebuilt, VECTORS / "sources")


@pytest.mark.parametrize("software,expected_code", [(True, 0), (False, 3)])
def test_cli_gate_and_wrong_result_self_test(software: bool, expected_code: int) -> None:
    command = [
        sys.executable,
        str(ROOT / "scripts/check_conformance.py"),
        "--corpus",
        str(VECTORS / "corpus.json"),
        "--expected-corpus",
        PIN.hex(),
        "--self-test",
    ]
    if software:
        command.append("--software-only")
    completed = subprocess.run(command, text=True, capture_output=True, timeout=10)
    assert completed.returncode == expected_code and not completed.stderr
    report = ConformanceReport.model_validate_json(completed.stdout)
    assert report.self_tested and report.matched == 156 and len(report.unavailable) == 32
    assert report.primary == implementation_identity(ROOT)


def test_cli_redacts_bad_path_and_pin() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_conformance.py"),
            "--corpus",
            "/SYNTHETIC_PRIVATE_SENTINEL",
            "--expected-corpus",
            "INVALID_SENTINEL",
        ],
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert completed.returncode == 2 and not completed.stdout
    assert "SENTINEL" not in completed.stderr and "Traceback" not in completed.stderr
    assert json.loads(completed.stderr)["code"] == "INPUT_INVALID"


def test_software_vectors_cannot_claim_proof_acceptance(corpus: Corpus) -> None:
    result = Outcome(
        accepted=True,
        claim_a="accepted",
        claim_b="accepted",
        code=None,
        input_digests=(),
        integers=(),
    )
    with pytest.raises(HallmarkError):
        replace_case(corpus, "wire.valid-00", expected=result).identity()
