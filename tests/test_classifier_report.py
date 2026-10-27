"""Synthetic archive accounting; these fixtures contain no cryptographic proofs."""

import hashlib
import io
import sys
import tarfile
from pathlib import Path

import pytest
from test_classifier_measurements import matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from benchmark_classifiers import summarize
from classifier_comparison import encoded, sha
from report_classifier_benchmark import PREFIX, audit


def retained(tmp_path):
    plan, samples = matrix()
    files = {}
    for sample in samples:
        sample["sample_id"] = f"{sample['phase']}-{sample['repetition']:02d}-{sample['backend']}"
        for case in sample["cases"]:
            for proof in case["proofs"]:
                raw = b"synthetic proof bytes"
                pin = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                proof["proof_bytes"] = len(raw)
                proof["proof_sha256"] = pin["sha256"]
                filename = "proof.json" if sample["backend"] == "circle" else "proof.bin"
                proof["prover_cost"] |= dict(exit_code=0, files={filename: pin})
                proof["verifier_cost"]["exit_code"] = 0
                files[
                    PREFIX
                    + sample["sample_id"]
                    + "/"
                    + case["case_id"]
                    + "-prove-"
                    + proof["kind"]
                    + "/"
                    + filename
                ] = raw
        files[PREFIX + sample["sample_id"] + "/sample.json"] = encoded(sample)
    files[PREFIX + "protocol.json"] = encoded(
        dict(
            protocol_commit="a" * 40,
            benchmark_sample=True,
            sources={},
            plan=plan,
            source_sha256=sha(encoded({})),
            environment={},
            environment_sha256=sha(encoded({})),
            frozen_input_pins={},
        )
    )
    files[PREFIX + "result.json"] = encoded(
        dict(
            status="passed",
            samples=16,
            fresh_proofs=144,
            fresh_verifications=144,
            summary=summarize(samples, plan),
        )
    )
    return files


def archive(tmp_path, files):
    path = tmp_path / "outputs.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        for name, raw in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            tar.addfile(info, io.BytesIO(raw))
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_statistics_recompute_from_complete_retained_proof_inventory(tmp_path):
    path, pin = archive(tmp_path, retained(tmp_path))
    result = audit(path, pin, "a" * 40, tmp_path / "audit")
    assert result["measured_proofs"] == 144 and result["byte_audit_only"] is True
    assert result["independently_reverified_here"] is False


@pytest.mark.parametrize("change", ["proof", "source-commit", "archive-pin"])
def test_byte_audit_rejects_changed_proof_or_caller_freeze(tmp_path, change):
    files = retained(tmp_path)
    if change == "proof":
        name = next(n for n in files if n.endswith("/proof.bin"))
        files[name] += b"changed"
    path, pin = archive(tmp_path, files)
    with pytest.raises(ValueError):
        audit(
            path,
            "0" * 64 if change == "archive-pin" else pin,
            "b" * 40 if change == "source-commit" else "a" * 40,
            tmp_path / "audit",
        )


def test_extraction_keeps_proof_inputs_and_excludes_private_or_execution_material():
    from report_classifier_benchmark import proof_only_file

    assert proof_only_file(PREFIX + "warm-04-circle/allow-prove-encoder/proof.json")
    assert proof_only_file(PREFIX + "fresh-00-gnark/setup-rule/vk.bin")
    assert proof_only_file(PREFIX + "fresh-00-gnark/caller-enrollment.json")
    for name in ("pk.bin", "witness.json", "model.json", "program.json", "assignment.txt"):
        assert not proof_only_file(PREFIX + "fresh-00-gnark/setup-rule/" + name)
    assert not proof_only_file(PREFIX + "../fresh-00-gnark/setup-rule/vk.bin")
