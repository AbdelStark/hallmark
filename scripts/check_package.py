"""Check distribution contents and install/run the wheel in a fresh environment."""

import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def install(
    root: Path, wheel: Path, env: Path, *, train: bool = False, guard: bool = False
) -> Path:
    subprocess.run(
        ["uv", "venv", "--no-config", "--python", sys.executable, str(env)], check=True, timeout=30
    )
    python = env / "bin/python"
    requirements = env.parent / (env.name + "-requirements.txt")
    subprocess.run(
        [
            "uv",
            "export",
            "--locked",
            "--no-default-groups",
            "--no-emit-project",
            "--no-header",
            "--no-annotate",
            "--no-config",
            "--format",
            "requirements-txt",
            "--output-file",
            str(requirements),
            *(["--extra", "train"] if train else []),
            *(["--extra", "guard"] if guard else []),
        ],
        cwd=root,
        stdout=subprocess.DEVNULL,
        check=True,
        timeout=30,
    )
    with requirements.open("a") as handle:
        handle.write(
            f"hallmark-research @ {wheel.as_uri()} "
            f"--hash=sha256:{hashlib.sha256(wheel.read_bytes()).hexdigest()}\n"
        )
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--no-config",
            "--python",
            str(python),
            "--no-deps",
            "--require-hashes",
            "--only-binary",
            ":all:",
            "-r",
            str(requirements),
        ],
        check=True,
        timeout=55,
    )
    subprocess.run(
        ["uv", "pip", "check", "--python", str(python), "--no-config"], check=True, timeout=15
    )
    return python


def installed_inventory(root: Path, python: Path, wheel: Path, directory: str) -> dict:
    result = subprocess.run(
        [
            str(python),
            str(root / "scripts/package_inventory.py"),
            "--lock",
            str(root / "uv.lock"),
            "--project-wheel",
            str(wheel),
        ],
        cwd=directory,
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--guard", action="store_true")
    args = parser.parse_args()
    root = args.source.resolve()
    subprocess.run(
        [sys.executable, str(root / "scripts/check_spec.py")], cwd=root, check=True, timeout=10
    )
    wheels = list(args.dist.glob("*.whl"))
    sdists = list(args.dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit("expected exactly one wheel and sdist; inspect dist before rebuilding")
    with zipfile.ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
        assert "hallmark/py.typed" in names
        assert "hallmark/cli.py" in names
        assert "hallmark/manifests.py" in names
        assert "hallmark/classifier_manifest.py" in names
        assert "hallmark/policy.py" in names
        assert "hallmark/openings.py" in names
        assert "hallmark/receipts.py" in names
        assert "hallmark/enrollment.py" in names
        assert "hallmark/registry_store.py" in names
        assert "hallmark/registry.py" in names
        assert "hallmark/registry_history.py" in names
        assert "hallmark/registry_cli.py" in names
        assert "hallmark/bundles.py" in names
        assert "hallmark/conformance.py" in names
        assert "hallmark/conformance_checks.py" in names
        assert "hallmark/integer_mlp.py" in names
        assert "hallmark/mlp_export.py" in names
        assert "hallmark/mlp_training.py" in names
        assert "hallmark/guard.py" in names
        assert "hallmark/comparison_run.py" in names
        assert "hallmark/baselines.py" in names
        assert "hallmark/selection.py" in names
        assert "hallmark/comparison.py" in names
        assert "hallmark/group_evaluation.py" in names
        assert "hallmark/rule.py" in names
        assert "hallmark/events.py" in names
        assert "hallmark/admission.py" in names
        assert "hallmark/data_admission.py" in names
        assert "hallmark/backend.py" in names
        for module in ("qualification", "_gnark_probe", "_gnark_graph_probe", "_gnark_block_probe"):
            assert f"hallmark/{module}.py" in names
        assert not any("fixtures/" in name or "runs/" in name for name in names)
    with tarfile.open(sdists[0]) as archive:
        names = {"/".join(name.split("/")[1:]) for name in archive.getnames()}
        for required in (
            "uv.lock",
            "docs/SPEC.md",
            "SPEC.md",
            "docs/spec/11-requirements.md",
            "docs/rfcs/RFC-0001-wire.md",
            "docs/roadmap/work-items.json",
            "docs/roadmap/IMPLEMENTATION.md",
            "scripts/check_docs.py",
            "scripts/check_spec.py",
            "docs/roadmap/coverage.json",
            "scripts/build_conformance.py",
            "scripts/check_conformance.py",
            "scripts/build_mlp_training_fixture.py",
            "scripts/check_mlp_training.py",
            "tests/test_mlp_training.py",
            "fixtures/mlp-training.json",
            "fixtures/mlp-training.sha256",
            "docs/schemas/mlp-fit-config-v1.json",
            "docs/schemas/mlp-checkpoint-v1.json",
            "docs/schemas/mlp-quantization-v1.json",
            "scripts/build_selection_fixture.py",
            "scripts/check_selection.py",
            "tests/test_selection.py",
            "fixtures/grouped-selection.json",
            "fixtures/grouped-selection.sha256",
            "docs/schemas/ngram-fit-config-v1.json",
            "docs/schemas/ngram-model-v1.json",
            "docs/schemas/ngram-fit-v1.json",
            "docs/schemas/grouped-selection-plan-v1.json",
            "docs/schemas/comparison-calibration-v1.json",
            "docs/schemas/group-report-plan-v1.json",
            "docs/schemas/report-observation-v1.json",
            "docs/schemas/report-unavailable-v1.json",
            "scripts/check_group_evaluation.py",
            "scripts/report_groups.py",
            "tests/test_group_evaluation.py",
            "scripts/build_mlp_fixture.py",
            "scripts/check_mlp_vectors.py",
            "scripts/build_encoder_fixture.py",
            "scripts/check_encoder_vectors.py",
            "tests/test_integer_encoder.py",
            "tests/test_integer_graph.py",
            "scripts/contextual_cnn.py",
            "scripts/run_contextual_cnn.py",
            "tests/test_contextual_cnn.py",
            "fixtures/contextual-protocol.json",
            "fixtures/contextual-protocol-v2.json",
            "fixtures/contextual-source.json",
            "fixtures/contextual-source-v2.json",
            "fixtures/contextual-scope.jsonl",
            "fixtures/contextual-scope-v2.jsonl",
            "fixtures/wire/integer-encoder-v1.json",
            "fixtures/wire/integer-encoder-v1.sha256",
            "docs/schemas/encoder-program-v1.json",
            "docs/schemas/encoder-constants-v1.json",
            "docs/schemas/encoder-result-v1.json",
            "scripts/build_rule_fixture.py",
            "scripts/check_rule_vectors.py",
            "tests/test_rule.py",
            "fixtures/wire/rule-v1.json",
            "docs/schemas/rule-program-v1.json",
            "docs/schemas/rule-result-v1.json",
            "scripts/check_event_storage.py",
            "scripts/build_admission_fixture.py",
            "scripts/check_admission.py",
            "tests/test_admission.py",
            "fixtures/wire/admission-v1.json",
            "docs/schemas/study-policy-v1.json",
            "docs/schemas/admission-v1.json",
            "docs/schemas/admission-review-v1.json",
            "scripts/build_data_fixture.py",
            "scripts/check_data_import.py",
            "tests/test_data_admission.py",
            "fixtures/wire/data-import-v1.json",
            "docs/schemas/source-row-v1.json",
            "docs/schemas/source-manifest-v1.json",
            "docs/schemas/near-duplicate-review-v1.json",
            "docs/schemas/data-import-plan-v1.json",
            "docs/schemas/lineage-v1.json",
            "docs/schemas/split-manifest-v1.json",
            "docs/schemas/dataset-manifest-v1.json",
            "scripts/build_qualification_fixture.py",
            "scripts/check_qualification_fixture.py",
            "tests/test_qualification.py",
            "fixtures/wire/qualification-protocol-v1.json",
            "docs/schemas/qualification-protocol-v1.json",
            "scripts/build_backend_fixture.py",
            "scripts/check_backend_fixture.py",
            "tests/test_backend.py",
            "fixtures/wire/backend-v1.json",
            "docs/schemas/backend-v1.json",
            "research/proposals/inj-direct-v1/README.md",
            "research/proposals/inj-direct-v1/proposal.json",
            "tests/test_events.py",
            "docs/schemas/event-v1.json",
            "docs/schemas/event-attempt-v1.json",
            "docs/schemas/event-summary-v1.json",
            "tests/test_integer_mlp.py",
            "fixtures/wire/integer-mlp-v1.json",
            "docs/schemas/mlp-program-v1.json",
            "docs/schemas/mlp-weights-v1.json",
            "docs/schemas/mlp-result-v1.json",
            "tests/test_conformance.py",
            "tests/vectors/v1/corpus.json",
            "tests/vectors/v1/corpus.id",
            "docs/schemas/conformance-case-v1.json",
            "docs/schemas/conformance-corpus-v1.json",
            "docs/schemas/conformance-report-v1.json",
            "scripts/check_opening_vectors.mjs",
            "scripts/check_registry_vectors.py",
            "tests/test_reference.py",
            "tests/test_wire.py",
            "tests/test_manifests.py",
            "tests/test_classifier_manifest.py",
            "tests/test_policy.py",
            "tests/test_openings.py",
            "tests/test_receipt_contracts.py",
            "tests/test_enrollment.py",
            "tests/test_registry.py",
            "fixtures/wire/registry-rotation-v1.json",
            "docs/schemas/registry-transition-v1.json",
            "docs/schemas/signed-transition-v1.json",
            "tests/test_bundles.py",
            "fixtures/wire/bundles-v1.json",
            "docs/schemas/bundle-v1.json",
            "docs/schemas/response-envelope-v1.json",
            "docs/schemas/bundle-status-v1.json",
            "docs/schemas/verification-result-v1.json",
            "fixtures/wire/enrollment-v1.json",
            "docs/schemas/trust-v1.json",
            "docs/schemas/registry-v1.json",
            "docs/schemas/signed-registry-v1.json",
            "docs/schemas/registry-state-v1.json",
            "research/evidence/w08-dependency-review-2026-10-20.json",
            "fixtures/wire/model-manifest-v1.json",
            "fixtures/wire/classifier-v1.json",
            "fixtures/wire/policy-request-v1.json",
            "fixtures/wire/openings-v1.json",
            "fixtures/wire/receipts-v1.json",
            "docs/schemas/model-manifest-v1.json",
            "docs/schemas/classifier-v1.json",
            "docs/schemas/input-profile-v1.json",
            "docs/schemas/arithmetic-v1.json",
            "docs/schemas/operator-parameters-v1.json",
            "docs/schemas/policy-v1.json",
            "docs/schemas/request-expectation-v1.json",
            "docs/schemas/request-v1.json",
            "docs/schemas/transcript-opening-v1.json",
            "docs/schemas/proof-inputs-v1.json",
            "docs/schemas/proof-input-layout-v1.json",
            "docs/schemas/epoch-v1.json",
            "docs/schemas/receipt-v1.json",
            "docs/schemas/signed-receipt-v1.json",
            "docs/schemas/proof-artifact-v1.json",
        ):
            assert required in names, required
        assert not any(name.startswith(("runs/", "data/", ".env")) for name in names)
        for path in (root / "tests/vectors/v1").rglob("*"):
            if path.is_file():
                assert path.relative_to(ROOT).as_posix() in names
    directory = tempfile.mkdtemp(
        prefix="hallmark-wheel-", dir=args.report.parent if args.report else None
    )
    env = Path(directory) / "core-env"
    python = install(root, wheels[0], env)
    subprocess.run(
        [
            str(python),
            "-c",
            "import hallmark, importlib.util, sys; from pathlib import Path; "
            "assert Path(hallmark.__file__).is_relative_to(Path(sys.prefix)); "
            "assert importlib.util.find_spec('sklearn') is None",
        ],
        cwd=directory,
        check=True,
    )
    subprocess.run([str(env / "bin/hallmark"), "--help"], cwd=directory, check=True)
    subprocess.run(
        [
            str(python),
            "-c",
            "from hallmark.wire import encode, decode, H; "
            "assert encode({'a': 1}) == bytes.fromhex('a1616101'); "
            "assert decode(bytes.fromhex('a1616101')) == {'a': 1}; "
            "assert len(H('policy', {'a': 1})) == 32",
        ],
        cwd=directory,
        check=True,
    )
    subprocess.run(
        [
            str(python),
            "-c",
            "import json, sys; from pathlib import Path; "
            "from hallmark.manifests import ModelManifest, verify_model_files; "
            "v = json.loads(Path(sys.argv[1]).read_text()); "
            "m = ModelManifest.decode(bytes.fromhex(v['cbor_hex'])); "
            "assert m.identity().hex() == v['identity_hex']; "
            "assert m.encode().hex() == v['cbor_hex']; "
            "Path('weights.bin').write_bytes(v['content_utf8'].encode('utf-8')); "
            "verify_model_files(m, Path('.'), max_bytes=3)",
            str(root / "fixtures/wire/model-manifest-v1.json"),
        ],
        cwd=directory,
        check=True,
    )
    subprocess.run(
        [
            str(python),
            "-c",
            "import json, sys; from pathlib import Path; "
            "from hallmark.classifier_manifest import "
            "InputProfile, ArithmeticProfile, ClassifierManifest; "
            "v = json.loads(Path(sys.argv[1]).read_text()); "
            "i = InputProfile.decode(bytes.fromhex(v['input_profile']['cbor_hex'])); "
            "a = ArithmeticProfile.decode(bytes.fromhex(v['arithmetic']['cbor_hex'])); "
            "c = ClassifierManifest.decode(bytes.fromhex(v['classifier']['cbor_hex'])); "
            "p = {key: bytes.fromhex(raw) for key, raw in v['parameters'].items()}; "
            "c.validate_profiles(i, a, parameters=p); "
            "assert c.identity().hex() == v['classifier']['identity_hex']",
            str(root / "fixtures/wire/classifier-v1.json"),
        ],
        cwd=directory,
        check=True,
    )
    subprocess.run(
        [
            str(python),
            "-c",
            "import json, sys; from pathlib import Path; "
            "from hallmark.classifier_manifest import ClassifierManifest; "
            "from hallmark.manifests import ModelManifest; "
            "from hallmark.policy import Policy, RequestExpectation, Request; "
            "v = json.loads(Path(sys.argv[1]).read_text()); "
            "m = ModelManifest.decode(bytes.fromhex(v['model_cbor_hex'])); "
            "c = tuple(ClassifierManifest.decode(bytes.fromhex(raw)) "
            "for raw in v['classifiers_cbor_hex']); "
            "p = Policy.decode(bytes.fromhex(v['policy']['cbor_hex'])); "
            "e = RequestExpectation.decode(bytes.fromhex(v['expectation']['cbor_hex'])); "
            "r = Request.decode(bytes.fromhex(v['request']['cbor_hex'])); "
            "assert p.identity().hex() == v['policy']['identity_hex']; "
            "r.validate_against(e, model=m, policy=p, classifiers=c)",
            str(root / "fixtures/wire/policy-request-v1.json"),
        ],
        cwd=directory,
        check=True,
    )
    subprocess.run(
        [
            str(python),
            "-c",
            "import json, sys; from pathlib import Path; "
            "from hallmark.classifier_manifest import ClassifierManifest, InputProfile; "
            "from hallmark.openings import TranscriptOpening, input_commitment; "
            "from hallmark.policy import RequestExpectation; "
            "v = json.loads(Path(sys.argv[1]).read_text()); case = v['cases'][1]; "
            "o = TranscriptOpening.decode(bytes.fromhex(case['opening']['cbor_hex'])); "
            "e = RequestExpectation.decode(bytes.fromhex(v['expected']['cbor_hex'])); "
            "o.verify_commitment(bytes.fromhex(case['transcript_hex'])); "
            "assert o.context(e).hex() == case['context_hex']; "
            "c = ClassifierManifest.decode("
            "bytes.fromhex(v['classifiers']['mlp']['cbor_hex'])); "
            "p = InputProfile.decode(bytes.fromhex(v['profiles']['bytes']['cbor_hex'])); "
            "assert input_commitment(o, c, p).hex() == case['inputs'][1]['digest_hex']",
            str(root / "fixtures/wire/openings-v1.json"),
        ],
        cwd=directory,
        check=True,
    )
    subprocess.run(
        [
            str(python),
            "-c",
            "import json, sys; from pathlib import Path; "
            "from hallmark.classifier_manifest import ClassifierManifest, InputProfile; "
            "from hallmark.policy import Policy, RequestExpectation; "
            "from hallmark.receipts import EpochRecord, ReceiptBody, SignedReceipt, "
            "ProofInputs, ProofArtifact; "
            "v = json.loads(Path(sys.argv[1]).read_text()); "
            "e = EpochRecord.decode(bytes.fromhex(v['epoch']['cbor_hex'])); "
            "s = SignedReceipt.decode(bytes.fromhex(v['signed_receipt']['cbor_hex'])); "
            "r = ReceiptBody.decode(bytes.fromhex(v['receipt']['cbor_hex'])); "
            "x = RequestExpectation.decode(bytes.fromhex(v['expected']['cbor_hex'])); "
            "p = Policy.decode(bytes.fromhex(v['policy']['cbor_hex'])); "
            "c = tuple(ClassifierManifest.decode(bytes.fromhex("
            "v['classifiers'][kind]['cbor_hex'])) for kind in ('rule','mlp','encoder')); "
            "i = tuple(InputProfile.decode(bytes.fromhex(v['profiles'][name]['cbor_hex'])) "
            "for name in ('bytes','bytes','tokens')); "
            "r.validate_expectation(x, now=v['now']); r.validate_policy(p, c, i); "
            "s.validate_epoch(e, now=v['now']); "
            "assert r.identity().hex() == v['receipt']['identity_hex']; "
            "assert r.signing_bytes().hex() == v['receipt']['signing_bytes_hex']; "
            "assert e.challenge().hex() == v['epoch']['challenge_hex']; "
            "a = ProofArtifact.decode(bytes.fromhex(v['proofs'][1]['cbor_hex'])); "
            "a.validate_inputs(r.inputs[1], c[1], i[1], max_proof_bytes=1024); "
            "assert ProofInputs.from_fields(tuple(v['packing_only'][0]['fields']))"
            ".threshold == -(2**31)",
            str(root / "fixtures/wire/receipts-v1.json"),
        ],
        cwd=directory,
        check=True,
    )
    subprocess.run(
        [
            str(python),
            "-c",
            "import json, sys; from pathlib import Path; "
            "from hallmark.enrollment import SignedRegistry, TrustPolicy, RegistryState; "
            "from hallmark.registry_store import "
            "provision_state, read_state, enroll_and_store; "
            "v = json.loads(Path(sys.argv[1]).read_text()); "
            "s = SignedRegistry.decode(bytes.fromhex(v['signed-registry']['cbor_hex'])); "
            "t = TrustPolicy.decode(bytes.fromhex(v['trust']['cbor_hex'])); "
            "c = RegistryState.decode(bytes.fromhex(v['registry-state']['cbor_hex'])); "
            "p = Path('checkpoint.sqlite'); provision_state(p, c); "
            "r = enroll_and_store(p, s, t, read_state(p), v['now']); "
            "assert read_state(p) == r.state == c; "
            "assert r.registry.hex() == v['registry']['identity_hex']; "
            "assert r.trust.hex() == v['trust']['identity_hex']; "
            "r.require_entry('model', t.accepted_models[0], issued_at=100)",
            str(root / "fixtures/wire/enrollment-v1.json"),
        ],
        cwd=directory,
        check=True,
    )
    subprocess.run(
        [
            str(python),
            "-c",
            "import json, sys; from pathlib import Path; "
            "from hallmark.enrollment import TrustPolicy; "
            "from hallmark.bundles import Bundle, BundleStatus, ResponseEnvelope, "
            "VerificationResult, decode_bundle; "
            "v = json.loads(Path(sys.argv[1]).read_text()); "
            "t = TrustPolicy.decode(bytes.fromhex(v['external_trust_cbor_hex'])); "
            "types = {'bundle': Bundle, 'bundle-status': BundleStatus, "
            "'response-envelope': ResponseEnvelope, "
            "'verification-result': VerificationResult}; "
            "records = [types[r['kind']].decode(bytes.fromhex(r['cbor_hex'])) "
            "for r in v['records']]; "
            "assert all(obj.encode().hex() == r['cbor_hex'] "
            "for obj, r in zip(records, v['records'], strict=True)); "
            "b = decode_bundle(records[0].encode(), limits=t.limits); "
            "assert len(b.proofs) == 3 and not hasattr(b, 'accepted')",
            str(root / "fixtures/wire/bundles-v1.json"),
        ],
        cwd=directory,
        check=True,
    )
    subprocess.run(
        [
            str(python),
            str(root / "scripts/check_registry_vectors.py"),
            str(root / "fixtures/wire/registry-rotation-v1.json"),
        ],
        cwd=directory,
        check=True,
    )
    subprocess.run(
        [str(env / "bin/hallmark"), "validate-data", str(root / "fixtures/smoke.jsonl")],
        cwd=directory,
        check=True,
    )
    subprocess.run(
        [str(python), str(root / "scripts/check_event_storage.py")],
        cwd=directory,
        check=True,
        timeout=15,
    )
    subprocess.run(
        [
            str(python),
            str(root / "scripts/check_qualification_fixture.py"),
            str(root / "fixtures/wire/qualification-protocol-v1.json"),
        ],
        cwd=directory,
        check=True,
        timeout=15,
    )
    training_fixture = root / "fixtures/mlp-training.json"
    training_pin = (root / "fixtures/mlp-training.sha256").read_text().strip()
    subprocess.run(
        [
            str(python),
            str(root / "scripts/check_mlp_training.py"),
            str(training_fixture),
            "--expected-fixture",
            training_pin,
        ],
        cwd=directory,
        check=True,
        timeout=15,
    )
    selection_fixture = root / "fixtures/grouped-selection.json"
    selection_pin = (root / "fixtures/grouped-selection.sha256").read_text().strip()
    subprocess.run(
        [
            str(python),
            str(root / "scripts/check_selection.py"),
            str(selection_fixture),
            "--expected-fixture",
            selection_pin,
        ],
        cwd=directory,
        check=True,
        timeout=15,
    )
    subprocess.run(
        [str(python), str(root / "scripts/check_group_evaluation.py")],
        cwd=directory,
        check=True,
        timeout=15,
    )
    corpus = root / "tests/vectors/v1"
    subprocess.run(
        [
            str(python),
            str(root / "scripts/check_backend_fixture.py"),
            str(root / "fixtures/wire/backend-v1.json"),
        ],
        cwd=directory,
        check=True,
        timeout=15,
    )
    subprocess.run(
        [
            str(python),
            str(root / "scripts/check_rule_vectors.py"),
            str(root / "fixtures/wire/rule-v1.json"),
        ],
        cwd=directory,
        check=True,
        timeout=15,
    )
    subprocess.run(
        [str(python), str(root / "scripts/check_admission.py")],
        cwd=directory,
        check=True,
        timeout=15,
    )
    subprocess.run(
        [
            str(python),
            str(root / "scripts/check_data_import.py"),
            str(root / "fixtures/wire/data-import-v1.json"),
        ],
        cwd=directory,
        check=True,
        timeout=15,
    )
    subprocess.run(
        [
            str(python),
            str(root / "scripts/check_mlp_vectors.py"),
            str(root / "fixtures/wire/integer-mlp-v1.json"),
        ],
        cwd=directory,
        check=True,
        timeout=15,
    )
    subprocess.run(
        [
            str(python),
            str(root / "scripts/check_encoder_vectors.py"),
            str(root / "fixtures/wire/integer-encoder-v1.json"),
            "--expected-fixture",
            (root / "fixtures/wire/integer-encoder-v1.sha256").read_text().strip(),
        ],
        cwd=directory,
        check=True,
        timeout=15,
    )
    for extra, expected_exit in ((["--software-only"], 0), ([], 3)):
        conformance = subprocess.run(
            [
                str(python),
                str(root / "scripts/check_conformance.py"),
                "--corpus",
                str(corpus / "corpus.json"),
                "--expected-corpus",
                (corpus / "corpus.id").read_text().strip(),
                "--self-test",
                *extra,
            ],
            cwd=directory,
            text=True,
            capture_output=True,
            timeout=15,
        )
        assert conformance.returncode == expected_exit and not conformance.stderr
        report = json.loads(conformance.stdout)
        assert report["matched"] == 156 and report["mismatched"] == 0
        assert len(report["unavailable"]) == 32 and report["self_tested"]
        assert not report["all_required_executed"] and report["independent"] is None
    failed = subprocess.run(
        [str(env / "bin/hallmark"), "schema", "PRIVATE_ERROR_SENTINEL"],
        cwd=directory,
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode == 2 and not failed.stdout
    assert "PRIVATE_ERROR_SENTINEL" not in failed.stderr
    assert json.loads(failed.stderr)["code"] == "INPUT_INVALID"
    inventories = {"core": installed_inventory(root, python, wheels[0], directory)}
    if args.train:
        train_env = Path(directory) / "train-env"
        train_python = install(root, wheels[0], train_env, train=True)
        subprocess.run(
            [
                str(train_python),
                str(root / "scripts/check_installed_train.py"),
                str(root),
                str(Path(directory) / "training-fixture"),
            ],
            cwd=directory,
            check=True,
            timeout=45,
        )
        subprocess.run(
            [
                str(train_python),
                str(root / "scripts/check_mlp_training.py"),
                str(training_fixture),
                "--expected-fixture",
                training_pin,
                "--output",
                str(Path(directory) / "mlp-training-fixture"),
            ],
            cwd=directory,
            check=True,
            timeout=45,
        )
        subprocess.run(
            [
                str(train_python),
                str(root / "scripts/check_selection.py"),
                str(selection_fixture),
                "--expected-fixture",
                selection_pin,
                "--output",
                str(Path(directory) / "grouped-selection-fixture"),
            ],
            cwd=directory,
            check=True,
            timeout=45,
        )
        subprocess.run(
            [
                str(train_python),
                "-I",
                "-c",
                "import sys; from pathlib import Path; "
                "root=Path(sys.argv[1]); sys.path.insert(0,str(root/'scripts')); "
                "import contextual_cnn as c; from hallmark.data import load_records; "
                "rows=load_records(root/'fixtures/contextual-scope.jsonl')[:2]; "
                "p=c.train(rows,17,channels=32,stop=1); q=c.quantize(p['parameters']); "
                "e=c.export(q); prompts=['','é','A'*96]; "
                "assert c.graph_scores(e,prompts)==c.integer_scores(q,prompts)",
                str(root),
            ],
            cwd=directory,
            check=True,
            timeout=45,
        )
        inventories["train"] = installed_inventory(root, train_python, wheels[0], directory)
    if args.guard:
        guard_python = install(
            root, wheels[0], Path(directory) / "guard-env", guard=True, train=args.train
        )
        subprocess.run(
            [str(guard_python), str(root / "scripts/check_guard.py")],
            cwd=directory,
            check=True,
            timeout=45,
        )
        inventories["guard"] = installed_inventory(root, guard_python, wheels[0], directory)
        if args.train:
            subprocess.run(
                [str(guard_python), str(root / "scripts/check_comparison_run.py")],
                cwd=directory,
                check=True,
                timeout=55,
            )
    if args.report:
        args.report.write_text(
            json.dumps(
                {"schema_id": "hallmark/package-install-check/1", "environments": inventories},
                sort_keys=True,
            )
            + "\n"
        )
    print("Wheel/sdist contents and isolated installed CLI passed.")


if __name__ == "__main__":
    main()
