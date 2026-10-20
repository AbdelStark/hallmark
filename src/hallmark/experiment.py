"""Bounded experiment execution and caller-pinned replay of research artifacts."""

import importlib.metadata
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from hallmark.contracts import ArtifactName, Experiment, LinearArtifact, Record, RunManifest
from hallmark.data import dataset_summary, load_records
from hallmark.evaluation import calibrate_threshold, metrics
from hallmark.integrity import (
    commitment,
    digest_bytes,
    load_contract,
    parse_json,
    read_bytes,
    write_json_new,
)
from hallmark.reference import score
from hallmark.training import train_linear

ARTIFACTS: tuple[ArtifactName, ...] = (
    "config.json",
    "model.json",
    "results.json",
    "predictions.json",
    "source.json",
)


def admit(config: Experiment, dataset: Path) -> tuple[Record, ...]:
    if digest_bytes(read_bytes(dataset)) != config.dataset_sha256:
        raise ValueError("dataset SHA-256 differs from frozen experiment")
    rows = load_records(dataset)
    if {row.split for row in rows} != {"train", "calibration", "test"}:
        raise ValueError("train, calibration and test splits are all required")
    if any(row.policy_id != config.policy_id for row in rows):
        raise ValueError("one pinned policy per baseline experiment")
    if any(
        row.license_id not in config.approved_licenses
        or row.source_id not in config.approved_sources
        for row in rows
    ):
        raise ValueError("dataset source or licence lacks configured review approval")
    return rows


def evaluate(
    rows: tuple[Record, ...], artifact: LinearArtifact, config: Experiment
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if (artifact.policy_id, artifact.scope, artifact.chunk_bytes) != (
        config.policy_id,
        config.scope,
        config.chunk_bytes,
    ):
        raise ValueError("classifier and frozen experiment differ")
    predictions = [
        {
            "record_id": row.record_id,
            "split": row.split,
            "label": row.label,
            "score": score(artifact, getattr(row, artifact.scope)),
        }
        for row in rows
    ]
    by_split = {}
    for split in ("train", "calibration", "test"):
        selected = [row for row in rows if row.split == split]
        by_split[split] = metrics(
            tuple(row.label for row in selected),
            tuple(score(artifact, getattr(row, artifact.scope)) for row in selected),
            artifact.threshold,
            config.alpha,
        )
    test = by_split["test"]
    upper = test["zero_fp_one_sided_upper"]
    status = (
        "supported-zero-fp-bound"
        if upper is not None and upper <= config.target_fpr
        else "insufficient-evidence"
    )
    return {
        "schema_id": "hallmark.baseline-result/1",
        "evidence_class": config.evidence_class,
        "classifier_commitment": commitment("integer-classifier", artifact.model_dump(mode="json")),
        "dataset_sha256": config.dataset_sha256,
        "threshold": artifact.threshold,
        "target_fpr": config.target_fpr,
        "fpr_evidence_status": status,
        "split_counts": dataset_summary(rows),
        "metrics": by_split,
        "claim_a": "not-implemented",
        "zk_proof": "not-implemented",
        "scope": (
            "software research baseline; replay is not a cryptographic proof or safety guarantee"
        ),
    }, predictions


def source_record(config_path: Path) -> dict[str, Any]:
    def git(*args: str) -> str | None:
        result = subprocess.run(
            ["git", *args], cwd=config_path.parent, capture_output=True, text=True, check=False
        )
        return result.stdout.strip() if result.returncode == 0 else None

    versions: dict[str, str | None] = {}
    for name in ("hallmark-research", "numpy", "scikit-learn", "pydantic", "cbor2"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    package = Path(__file__).parent
    lock = config_path.parent.parent / "uv.lock"
    return {
        "git_revision": git("rev-parse", "HEAD"),
        "git_status": git("status", "--porcelain=v1", "--untracked-files=all"),
        "tracked_diff": git("diff", "HEAD"),
        "source_snapshot": {
            p.name: read_bytes(p).decode("utf-8") for p in sorted(package.glob("*.py"))
        },
        "python": sys.version,
        "platform": platform.platform(),
        "packages": versions,
        "lock_sha256": digest_bytes(read_bytes(lock)) if lock.is_file() else None,
        "execution": "local CPU baseline; no network, GPU, model download or hosted tracker",
    }


def run_experiment(config_path: Path, output: Path) -> str:
    config = load_contract(config_path, Experiment)
    dataset = (config_path.parent / config.dataset).resolve()
    rows = admit(config, dataset)
    output.mkdir(parents=True, exist_ok=False)
    try:
        artifact, training = train_linear(rows, config)
        calibration = [row for row in rows if row.split == "calibration"]
        threshold = calibrate_threshold(
            tuple(score(artifact, getattr(row, artifact.scope)) for row in calibration),
            tuple(row.label for row in calibration),
            config.target_fpr,
        )
        artifact = artifact.model_copy(update={"threshold": threshold})
        result, predictions = evaluate(rows, artifact, config)
        source = source_record(config_path)
        source["training"] = training
        write_json_new(output / "config.json", config.model_dump(mode="json"))
        write_json_new(output / "model.json", artifact.model_dump(mode="json"))
        write_json_new(output / "results.json", result)
        write_json_new(output / "predictions.json", predictions)
        write_json_new(output / "source.json", source)
        manifest = {
            "schema_id": "hallmark.run-manifest/1",
            "status": "complete",
            "artifacts": {name: digest_bytes(read_bytes(output / name)) for name in ARTIFACTS},
        }
        write_json_new(output / "manifest.json", manifest)
        return digest_bytes(read_bytes(output / "manifest.json"))
    except Exception:
        write_json_new(output / "failure.json", {"status": "failed", "artifacts_complete": False})
        raise


def audit_run(output: Path, dataset: Path, expected_manifest: str) -> dict[str, str]:
    raw_manifest = read_bytes(output / "manifest.json")
    if digest_bytes(raw_manifest) != expected_manifest:
        raise ValueError("manifest differs from caller-enrolled SHA-256")
    parse_json(raw_manifest.decode("utf-8"))
    manifest = RunManifest.model_validate_json(raw_manifest)
    for name in ARTIFACTS:
        if digest_bytes(read_bytes(output / name)) != manifest.artifacts[name]:
            raise ValueError(f"artifact hash mismatch: {name}")
    config = load_contract(output / "config.json", Experiment)
    artifact = load_contract(output / "model.json", LinearArtifact)
    rows = admit(config, dataset)
    calibration = [row for row in rows if row.split == "calibration"]
    expected_threshold = calibrate_threshold(
        tuple(score(artifact, getattr(row, artifact.scope)) for row in calibration),
        tuple(row.label for row in calibration),
        config.target_fpr,
    )
    if artifact.threshold != expected_threshold:
        raise ValueError("threshold was not selected from frozen calibration data")
    result, predictions = evaluate(rows, artifact, config)
    for name, expected in (("results.json", result), ("predictions.json", predictions)):
        observed = parse_json(read_bytes(output / name).decode("utf-8"))
        if commitment("replay-comparison", observed) != commitment("replay-comparison", expected):
            raise ValueError("reported results differ from software replay")
    return {"status": "research-replay-matched", "manifest_sha256": expected_manifest}
