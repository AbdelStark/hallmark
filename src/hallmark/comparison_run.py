"""Run reviewed baseline comparisons; admission is caller-enrolled, never self-approved."""

import hashlib
import importlib.metadata
import json
import platform
import time
from pathlib import Path
from typing import Any, Literal

from hallmark._worker import write_new
from hallmark.admission import (
    CANDIDATES,
    AdmissionProtocol,
    AdmissionReview,
    StudyPolicy,
    validate_reviewed_admission,
)
from hallmark.comparison import calibrate_fitted, evaluate_fitted
from hallmark.contracts import Digest, Record
from hallmark.data import validate_splits
from hallmark.data_admission import (
    MAX_OUTPUT_BYTES,
    MAX_RAW_BYTES,
    DataImportPlan,
    DatasetManifest,
    SourceManifest,
    verify_dataset,
)
from hallmark.errors import HallmarkError, sanitize_exception
from hallmark.evaluation import metrics
from hallmark.guard import GuardSpec, LocalGuard, _pinned_bytes
from hallmark.integrity import parse_json, read_bytes
from hallmark.manifests import ArtifactDigest, FileRef, FileSHA256
from hallmark.mlp_training import _TrainingRecord
from hallmark.selection import (
    Fitted,
    SelectionPlan,
    bind_guard,
    fit_candidate,
    grouped_selection,
    representatives,
)
from hallmark.wire import WireError


class ComparisonRunPlan(_TrainingRecord):
    schema_id: Literal["hallmark/comparison-run-plan/1"]
    fixture_only: bool
    dataset: Digest
    import_plan: Digest
    selection: SelectionPlan
    guard: GuardSpec
    guard_runtime: Digest


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def execution_inventory() -> bytes:
    """Review the complete installed Python implementation and selected package versions."""
    packages: dict[str, str | None] = {}
    for name in (
        "cbor2",
        "pydantic",
        "cryptography",
        "numpy",
        "scipy",
        "scikit-learn",
        "onnx",
        "onnxruntime",
        "tokenizers",
        "protobuf",
    ):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return json_bytes(
        {
            "schema_id": "hallmark/comparison-executable-inventory/1",
            "python": platform.python_version(),
            "packages": packages,
            "files": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(Path(__file__).parent.glob("*.py"))
            },
        }
    )


def _read_refs(root: Path, refs: tuple[FileRef, ...], cap: int) -> dict[str, bytes]:
    if len({r.path for r in refs}) != len(refs) or sum(r.size for r in refs) > cap:
        raise WireError("LIMIT_EXCEEDED")
    # Roots and their parent directories are caller-owned, as for LocalGuard.
    return {r.path: _pinned_bytes(root / r.path, r.size, r.sha256.hex()) for r in refs}


def _admit(
    dossier: Path, expected_review: ArtifactDigest, *, fixture_only: bool
) -> tuple[ComparisonRunPlan, AdmissionProtocol, tuple[Record, ...]]:
    policy = StudyPolicy.decode(read_bytes(dossier / "policy.cbor"))
    protocol = AdmissionProtocol.decode(read_bytes(dossier / "protocol.cbor"))
    review = AdmissionReview.decode(read_bytes(dossier / "review.cbor"))
    if review.identity() != expected_review:
        raise HallmarkError("TRUST_MISSING", "enroll")
    documents = _read_refs(dossier / "documents", review.evidence, 8 * 1024 * 1024)
    validate_reviewed_admission(
        protocol, policy, review, expected_review=expected_review, files=documents
    )
    raw_plan = read_bytes(dossier / "comparison.json")
    parse_json(raw_plan.decode())
    plan = ComparisonRunPlan.model_validate_json(raw_plan)
    imported = DataImportPlan.decode(read_bytes(dossier / "import.cbor"))
    manifest = DatasetManifest.decode(read_bytes(dossier / "dataset.cbor"))
    code = hashlib.sha256(execution_inventory()).digest()
    config = hashlib.sha256(raw_plan).digest()
    if (
        type(fixture_only) is not bool
        or not plan.fixture_only == manifest.fixture_only == imported.fixture_only == fixture_only
        or plan.dataset != manifest.identity().hex()
        or plan.import_plan != imported.identity().hex()
        or protocol.sources != imported.sources
        or protocol.split_manifest != manifest.splits.sha256
        or manifest.policy != policy.identity()
        or protocol.evaluator != code
        or any(c.code != code or c.config != config for c in protocol.candidate_roster[:-1])
        or plan.selection.bounds.policy_id != policy.policy_id
        or plan.selection.seeds != protocol.seeds
        or plan.selection.target_fpr != protocol.target_fpr
        or (protocol.target_fpr, protocol.alpha, protocol.min_tpr, protocol.max_quality_loss)
        != ("0.01", "0.05", "0.9", "0.02")
        or not policy.max_prompt_bytes
        == plan.selection.bounds.max_prompt_bytes
        == plan.guard.max_prompt_bytes
        or protocol.budget.jobs != 1
        or protocol.budget.max_disk_bytes < 4096
        or plan.guard.threads > protocol.budget.threads
        or protocol.budget.max_cost_minor != 0
    ):
        raise HallmarkError("REQUEST_MISMATCH", "bind")
    guard_files = tuple(
        FileRef(path=name, size=size, sha256=FileSHA256(bytes.fromhex(pin)))
        for name, size, pin in (
            ("model.onnx", plan.guard.model_bytes, plan.guard.model_sha256),
            ("tokenizer.json", plan.guard.tokenizer_bytes, plan.guard.tokenizer_sha256),
        )
    )
    if protocol.candidate_roster[4].base_files != guard_files:
        raise HallmarkError("REQUEST_MISMATCH", "bind")
    import_docs = _read_refs(dossier / "documents", imported.evidence, 8 * 1024 * 1024)
    by_hash = {hashlib.sha256(raw).digest(): raw for raw in import_docs.values()}
    if any(s.revision not in by_hash for s in imported.sources):
        raise WireError("INPUT_INVALID")
    sources = [SourceManifest.decode(by_hash[s.revision]) for s in imported.sources]
    raw_files = _read_refs(
        dossier / "sources",
        tuple(ref for source in sources for ref in source.raw_files),
        MAX_RAW_BYTES,
    )
    files = _read_refs(
        dossier / "dataset", (manifest.records, manifest.lineage, manifest.splits), MAX_OUTPUT_BYTES
    )
    verify_dataset(
        manifest,
        files,
        imported,
        policy,
        expected_dataset=ArtifactDigest(bytes.fromhex(plan.dataset)),
        expected_plan=ArtifactDigest(bytes.fromhex(plan.import_plan)),
        documents=import_docs,
        raw_files=raw_files,
    )
    rows = tuple(
        Record.model_validate_json(line) for line in files[manifest.records.path].splitlines()
    )
    validate_splits(rows)
    if {r.split for r in rows} != {"train", "calibration", "test"}:
        raise WireError("INPUT_INVALID")
    return plan, protocol, rows


def run_comparisons(
    dossier: Path,
    guard_root: Path,
    output: Path,
    *,
    expected_review: ArtifactDigest,
    fixture_only: bool = False,
) -> dict[str, Any]:
    """One fresh run; caller authenticates the review and controls resources and test reuse."""
    started = time.monotonic()
    plan, protocol, rows = _admit(dossier, expected_review, fixture_only=fixture_only)
    output.mkdir(mode=0o700)
    deadline = started + protocol.budget.max_wall_seconds

    def put(path: Path, value: Any) -> None:
        if time.monotonic() >= deadline:
            raise HallmarkError("RESOURCE_EXHAUSTED", "execute")
        total = sum(p.stat().st_size for p in output.iterdir())
        if total + len(json_bytes(value)) + 4096 > protocol.budget.max_disk_bytes:
            raise HallmarkError("RESOURCE_EXHAUSTED", "store")
        write_new(path, json_bytes(value))

    try:
        put(output / "plan.json", plan.model_dump(mode="json"))
        put(
            output / "admission.json",
            {
                "review": expected_review.hex(),
                "protocol": protocol.identity().hex(),
                "fixture_only": fixture_only,
            },
        )
        put(output / "source.json", parse_json(execution_inventory().decode()))
        training = tuple(r for r in rows if r.split == "train")
        calibration_rows = tuple(r for r in rows if r.split == "calibration")
        test = tuple(r for r in rows if r.split == "test")
        guard = LocalGuard(guard_root, plan.guard, expected_spec=plan.guard.identity())
        guard_fit = bind_guard(guard, plan.selection.bounds, expected_runtime=plan.guard_runtime)
        put(output / "guard-runtime.json", guard.record)
        selection = grouped_selection(training, plan.selection)
        put(output / "selection.json", selection)
        fitted: dict[str, Fitted] = {"task-guard": guard_fit}
        missing: list[dict[str, Any]] = [{"kind": "compact-encoder", "reason": "W16-not-executed"}]
        candidates = {c.id: c for c in plan.selection.candidates}
        for winner in selection["selected"]:
            name = f"{winner['kind']}-{winner['seed']}"
            if winner["candidate"] is None:
                missing.append({**winner, "reason": "no-eligible-train-only-candidate"})
                continue
            model = fit_candidate(
                training, candidates[winner["candidate"]], plan.selection, winner["seed"]
            )
            put(output / (name + "-fit.json"), model.record)
            if not model.record["converged"]:
                missing.append({**winner, "reason": "final-refit-nonconverged"})
                continue
            fitted[name] = model
        put(output / "task-guard-fit.json", guard_fit.record)
        thresholds = {}
        for name, model in fitted.items():
            threshold = calibrate_fitted(
                model,
                calibration_rows,
                expected_fit=model.record["identity"],
                target_fpr=plan.selection.target_fpr,
            )
            put(output / (name + "-calibration.json"), threshold.model_dump(mode="json"))
            thresholds[name] = threshold
        # Every fit and threshold is frozen before the first test-scoring call.
        put(
            output / "frozen.json",
            {
                name: {"fit": fitted[name].record["identity"], "calibration": cut.identity()}
                for name, cut in thresholds.items()
            },
        )
        evaluations = []
        for name, model in fitted.items():
            result = evaluate_fitted(
                model,
                thresholds[name],
                test,
                expected_fit=model.record["identity"],
                expected_calibration=thresholds[name].identity(),
            )
            put(output / (name + "-evaluation.json"), result)
            evaluations.append(
                {"name": name, "primary": result["primary"], "all_rows": result["all_rows"]}
            )
        primary = representatives(test)
        controls = {
            name: {
                "primary": metrics(tuple(r.label for r in primary), (block,) * len(primary), 1),
                "all_rows": metrics(tuple(r.label for r in test), (block,) * len(test), 1),
            }
            for name, block in (("pass-all", 0), ("block-all", 1))
        }
        put(output / "controls.json", controls)
        result = {
            "schema_id": "hallmark/comparison-run-result/1",
            "fixture_only": fixture_only,
            "review": expected_review.hex(),
            "dataset": plan.dataset,
            "roster": list(CANDIDATES),
            "evaluated": evaluations,
            "controls": controls,
            "unavailable": missing,
            "baseline_complete": len(missing) == 1,
            "full_study_complete": False,
            "quality_claim": False,
            "independent_verification": False,
        }
        put(output / "result.json", result)
        return result
    except BaseException as exc:
        error = (
            sanitize_exception(exc, stage="execute")
            if isinstance(exc, Exception)
            else HallmarkError("RESOURCE_EXHAUSTED", "execute")
        )
        write_new(output / "failure.json", json_bytes(error.as_dict()))
        raise
