"""Audit retained campaign bytes and recompute the frozen statistics without proving."""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path, PurePosixPath

from benchmark_classifiers import summarize
from classifier_comparison import encoded, sha
from run_llm_e2e import require

PREFIX = "runs/campaign/"


def audit(archive, expected_archive, expected_commit, output):
    with archive.open("rb") as stream:
        require(
            hashlib.file_digest(stream, "sha256").hexdigest() == expected_archive,
            "archive pin mismatch",
        )
    output.mkdir(mode=0o700)
    hashes, documents = {}, {}
    total = 0
    with tarfile.open(archive, "r|gz") as source:
        for count, member in enumerate(source, 1):
            name = PurePosixPath(member.name)
            total += member.size
            require(count <= 20000 and total <= 16 * 1024**3, "archive inventory exceeds bound")
            require(
                member.isfile()
                and not name.is_absolute()
                and ".." not in name.parts
                and member.name not in hashes,
                "unsafe archive inventory",
            )
            content = source.extractfile(member)
            require(content is not None, "missing regular archive content")
            selected = member.name in (
                PREFIX + "protocol.json",
                PREFIX + "result.json",
            ) or member.name.endswith("/sample.json")
            retained = member.name in (
                PREFIX + "fresh-00-circle/caller-enrollment.json",
                PREFIX + "composition-00-circle/llm-response-bundle.json",
            )
            require(
                not (selected or retained) or member.size <= 32 * 1024**2, "oversized report input"
            )
            digest = hashlib.sha256()
            chunks = []
            size = 0
            while chunk := content.read(1024**2):
                digest.update(chunk)
                size += len(chunk)
                if selected or retained:
                    chunks.append(chunk)
            require(size == member.size, "truncated archive member")
            hashes[member.name] = dict(bytes=size, sha256=digest.hexdigest())
            if selected:
                documents[member.name] = json.loads(b"".join(chunks))
            if retained:
                destination = output / "campaign" / member.name.removeprefix(PREFIX)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(b"".join(chunks))
    protocol = documents[PREFIX + "protocol.json"]
    result = documents[PREFIX + "result.json"]
    require(
        protocol["protocol_commit"] == expected_commit, "campaign commit differs from caller freeze"
    )
    require(
        protocol["benchmark_sample"] is True and result["status"] == "passed",
        "not a passed matched campaign",
    )
    for name, pin in protocol["sources"].items():
        require(hashes[PREFIX + "source/" + name]["sha256"] == pin, "changed captured source")
    require(sha(encoded(protocol["sources"])) == protocol["source_sha256"], "source inventory pin")
    require(
        sha(encoded(protocol["environment"])) == protocol["environment_sha256"], "environment pin"
    )
    for name, pin in protocol["frozen_input_pins"].items():
        require(hashes[PREFIX + "inputs/" + name]["sha256"] == pin, "changed frozen input")
    samples = [
        doc
        for name, doc in documents.items()
        if name.endswith("/sample.json") and doc["phase"] in ("fresh", "warm")
    ]
    summary = summarize(samples, protocol["plan"])
    require(
        result["samples"] == len(samples) == 16
        and result["fresh_proofs"] == 144
        and result["fresh_verifications"] == 144
        and result["summary"] == summary,
        "reported matrix differs from raw samples",
    )
    proofs = 0
    for sample in samples:
        for case in sample["cases"]:
            for proof in case["proofs"]:
                kind = proof["kind"]
                filename = "proof.json" if sample["backend"] == "circle" else "proof.bin"
                name = (
                    PREFIX
                    + sample["sample_id"]
                    + "/"
                    + case["case_id"]
                    + "-prove-"
                    + kind
                    + "/"
                    + filename
                )
                require(
                    hashes[name] == dict(bytes=proof["proof_bytes"], sha256=proof["proof_sha256"]),
                    "serialized proof differs from sample",
                )
                require(
                    proof["prover_cost"]["files"][filename] == hashes[name],
                    "prover cost proof pin differs",
                )
                require(
                    proof["prover_cost"]["exit_code"] == proof["verifier_cost"]["exit_code"] == 0,
                    "failed proof worker admitted as a passed sample",
                )
                proofs += 1
    require(proofs == 144, "incomplete proof inventory")
    report = dict(
        schema_id="hallmark.classifier-campaign-byte-audit/1",
        status="passed",
        archive_sha256=expected_archive,
        source_commit=expected_commit,
        protocol=protocol,
        campaign=result,
        raw_samples=samples,
        measured_proofs=proofs,
        artifact_inventory=hashes,
        byte_audit_only=True,
        independently_reverified_here=False,
        qualified_backend=False,
    )
    (output / "report.json").write_bytes(encoded(report))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--expected-archive", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.archive, args.expected_archive, args.expected_commit, args.output)
    print(
        json.dumps(
            dict(
                status=report["status"],
                measured_proofs=report["measured_proofs"],
                byte_audit_only=True,
                output=str(args.output),
            )
        )
    )
