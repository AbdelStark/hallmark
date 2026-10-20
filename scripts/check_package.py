"""Check distribution contents and install/run the wheel in a fresh environment."""

import json
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    wheels = list((ROOT / "dist").glob("*.whl"))
    sdists = list((ROOT / "dist").glob("*.tar.gz"))
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
            "scripts/build_conformance.py",
            "scripts/check_conformance.py",
            "scripts/build_mlp_fixture.py",
            "scripts/check_mlp_vectors.py",
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
        for path in (ROOT / "tests/vectors/v1").rglob("*"):
            if path.is_file():
                assert path.relative_to(ROOT).as_posix() in names
    with tempfile.TemporaryDirectory(prefix="hallmark-wheel-") as directory:
        env = Path(directory) / "venv"
        subprocess.run(["uv", "venv", "--python", sys.executable, str(env)], check=True)
        python = env / "bin/python"
        requirements = Path(directory) / "requirements.txt"
        subprocess.run(
            [
                "uv",
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--format",
                "requirements-txt",
                "--output-file",
                str(requirements),
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            check=True,
        )
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                "--requirements",
                str(requirements),
                str(wheels[0]),
            ],
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
                str(ROOT / "fixtures/wire/model-manifest-v1.json"),
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
                str(ROOT / "fixtures/wire/classifier-v1.json"),
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
                str(ROOT / "fixtures/wire/policy-request-v1.json"),
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
                str(ROOT / "fixtures/wire/openings-v1.json"),
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
                str(ROOT / "fixtures/wire/receipts-v1.json"),
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
                str(ROOT / "fixtures/wire/enrollment-v1.json"),
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
                str(ROOT / "fixtures/wire/bundles-v1.json"),
            ],
            cwd=directory,
            check=True,
        )
        subprocess.run(
            [
                str(python),
                str(ROOT / "scripts/check_registry_vectors.py"),
                str(ROOT / "fixtures/wire/registry-rotation-v1.json"),
            ],
            cwd=directory,
            check=True,
        )
        subprocess.run(
            [str(env / "bin/hallmark"), "validate-data", str(ROOT / "fixtures/smoke.jsonl")],
            cwd=directory,
            check=True,
        )
        corpus = ROOT / "tests/vectors/v1"
        subprocess.run(
            [
                str(python),
                str(ROOT / "scripts/check_mlp_vectors.py"),
                str(ROOT / "fixtures/wire/integer-mlp-v1.json"),
            ],
            cwd=directory,
            check=True,
            timeout=15,
        )
        for extra, expected_exit in ((["--software-only"], 0), ([], 3)):
            conformance = subprocess.run(
                [
                    str(python),
                    str(ROOT / "scripts/check_conformance.py"),
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
    print("Wheel/sdist contents and isolated installed CLI passed.")


if __name__ == "__main__":
    main()
