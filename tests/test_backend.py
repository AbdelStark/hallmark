"""Backend records bind claims and bytes; these tests never qualify a proof backend."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from hallmark.backend import BackendQualification, validate_backend_files
from hallmark.errors import HallmarkError
from hallmark.manifests import ArtifactDigest
from hallmark.wire import WireError, WireLimits, decode, encode

ROOT = Path(__file__).resolve().parents[1]
VECTOR = ROOT / "fixtures/wire/backend-v1.json"
DIGEST_FIELDS = (
    "source",
    "build",
    "setup",
    "verifier",
    "license_review",
    "security_review",
    "conformance",
    "costs",
)


@pytest.fixture
def backend():
    fixture = json.loads(VECTOR.read_text())
    return BackendQualification.decode(bytes.fromhex(fixture["cbor_hex"]))


def arguments(backend):
    fixture = json.loads(VECTOR.read_text())
    files = {path: bytes.fromhex(raw) for path, raw in fixture["files"].items()}
    return dict(
        expected_backend=backend.identity(),
        required_programs=backend.supported_programs,
        require_zero_knowledge=False,
        files=files,
        max_bytes=sum(map(len, files.values())),
    )


def test_fixed_vector_schema_and_independent_domain_hash(backend):
    vector = json.loads(VECTOR.read_text())
    assert backend.encode().hex() == vector["cbor_hex"]
    assert backend.identity().hex() == vector["identity_hex"]
    tag = b"hallmark/v1/backend"
    assert hashlib.sha256(len(tag).to_bytes(4, "big") + tag + backend.encode()).digest() == (
        backend.identity()
    )
    assert BackendQualification.model_validate_json(backend.model_dump_json()) == backend
    assert BackendQualification.model_json_schema() == json.loads(
        (ROOT / "docs/schemas/backend-v1.json").read_text()
    )
    assert validate_backend_files(backend, **arguments(backend)) is None
    assert backend.zero_knowledge is False
    assert not hasattr(backend, "qualified_backend")
    with pytest.raises(WireError):
        BackendQualification.decode(encode(json.loads(backend.model_dump_json())))


def test_fixture_reproduces_and_checker_runs(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_backend_fixture.py")],
        capture_output=True,
        check=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert result.stdout == VECTOR.read_bytes()
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_backend_fixture.py"), str(VECTOR)],
        capture_output=True,
        check=True,
        timeout=10,
        cwd=tmp_path,
    )
    report = json.loads(result.stdout)
    assert report["negative_checks"] == 5 and report["qualified_backend"] is False


@pytest.mark.parametrize("field", DIGEST_FIELDS)
def test_all_identity_fields_bound_to_external_pin(backend, field):
    value = decode(backend.encode())
    value[field] = b"\xff" * 32
    altered = BackendQualification.decode(encode(value))
    assert altered.identity() != backend.identity()
    with pytest.raises(HallmarkError) as error:
        validate_backend_files(altered, **arguments(backend))
    assert (error.value.code, error.value.stage) == ("TRUST_MISSING", "enroll")


@pytest.mark.parametrize("field", ["security_parameters", "public_input_layout"])
@pytest.mark.parametrize("part", ["path", "size", "sha256"])
def test_metadata_identity_fields_bound(backend, field, part):
    value = decode(backend.encode())
    value[field][part] = {"path": "changed.json", "size": 1, "sha256": b"\xff" * 32}[part]
    assert BackendQualification.decode(encode(value)).identity() != backend.identity()


@pytest.mark.parametrize("part", ["path", "size", "sha256"])
def test_dependency_fields_bound(backend, part):
    value = decode(backend.encode())
    value["dependencies"][0][part] = {
        "path": "changed.bin",
        "size": 1,
        "sha256": b"\xff" * 32,
    }[part]
    assert BackendQualification.decode(encode(value)).identity() != backend.identity()


@pytest.mark.parametrize(
    "field,new",
    [
        ("proof_system", "another-proof-system"),
        ("zero_knowledge", True),
        ("supported_programs", [b"\xff" * 32]),
    ],
)
def test_other_declared_claims_change_identity(backend, field, new):
    value = decode(backend.encode())
    value[field] = new
    altered = BackendQualification.decode(encode(value))
    assert altered.identity() != backend.identity()
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        validate_backend_files(altered, **arguments(backend))


@pytest.mark.parametrize("bad", [False, 1, "00" * 32, b"", b"a" * 31, b"a" * 33, bytearray(32)])
def test_digest_values_are_strict(backend, bad):
    with pytest.raises(ValidationError):
        BackendQualification.model_validate(backend.model_dump() | {"source": bad})


@pytest.mark.parametrize("bad", [1, 0, "true", "false", None])
def test_zero_knowledge_claim_is_strict_boolean(backend, bad):
    with pytest.raises(ValidationError):
        BackendQualification.model_validate(backend.model_dump() | {"zero_knowledge": bad})


@pytest.mark.parametrize(
    "fault",
    [
        "no-dependencies",
        "many-dependencies",
        "duplicate-dependency",
        "unordered-dependencies",
        "metadata-collision",
        "dependency-metadata-collision",
        "no-programs",
        "many-programs",
        "duplicate-program",
        "unordered-programs",
        "empty-security",
        "large-security",
        "empty-layout",
        "large-layout",
        "version",
        "extra",
    ],
)
def test_noncanonical_or_unbounded_records_reject(backend, fault):
    value = decode(backend.encode())
    if fault == "no-dependencies":
        value["dependencies"] = []
    elif fault == "many-dependencies":
        value["dependencies"] = [value["dependencies"][0]] * 1025
    elif fault == "duplicate-dependency":
        value["dependencies"] *= 2
    elif fault == "unordered-dependencies":
        value["dependencies"].append({**value["dependencies"][0], "path": "a"})
    elif fault == "metadata-collision":
        value["public_input_layout"] = value["security_parameters"]
    elif fault == "dependency-metadata-collision":
        value["dependencies"] = [value["security_parameters"]]
    elif fault == "no-programs":
        value["supported_programs"] = []
    elif fault == "many-programs":
        value["supported_programs"] *= 2049
    elif fault == "duplicate-program":
        value["supported_programs"] = [value["supported_programs"][0]] * 2
    elif fault == "unordered-programs":
        value["supported_programs"].reverse()
    elif fault in ("empty-security", "large-security", "empty-layout", "large-layout"):
        field = "security_parameters" if "security" in fault else "public_input_layout"
        value[field]["size"] = 0 if fault.startswith("empty") else 1024 * 1024 + 1
    elif fault == "version":
        value["schema_id"] = "hallmark/backend/2"
    else:
        value["qualified_backend"] = True
    with pytest.raises(WireError):
        BackendQualification.decode(encode(value))


def test_bypassed_validation_and_wire_bounds_reject(backend):
    broken = backend.model_copy(update={"zero_knowledge": "true"})
    for action in (
        broken.encode,
        broken.identity,
        lambda: validate_backend_files(broken, **arguments(backend)),
        lambda: BackendQualification.decode(backend.encode() + b"\0"),
        lambda: BackendQualification.decode(
            backend.encode(), limits=WireLimits(max_bytes=len(backend.encode()) - 1)
        ),
    ):
        with pytest.raises(WireError):
            action()
    with pytest.raises(WireError):
        validate_backend_files(backend.model_dump(), **arguments(backend))


@pytest.mark.parametrize("pin", [None, "", b"", b"\xff" * 32, bytearray(32)])
def test_missing_or_wrong_enrollment_rejects(backend, pin):
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        validate_backend_files(backend, **(arguments(backend) | {"expected_backend": pin}))


@pytest.mark.parametrize(
    "required", [(), [], (b"",), (bytearray(32),), (1,), (b"a" * 32, b"a" * 32)]
)
def test_required_programs_are_exact_bounded_values(backend, required):
    with pytest.raises(WireError):
        validate_backend_files(backend, **(arguments(backend) | {"required_programs": required}))


def test_program_coverage_and_hiding_claim_requirements(backend):
    args = arguments(backend)
    validate_backend_files(
        backend, **(args | {"required_programs": backend.supported_programs[:1]})
    )
    with pytest.raises(HallmarkError, match="REQUEST_MISMATCH"):
        validate_backend_files(backend, **(args | {"required_programs": (b"\xff" * 32,)}))
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        validate_backend_files(backend, **(args | {"require_zero_knowledge": True}))
    with pytest.raises(WireError):
        validate_backend_files(backend, **(args | {"require_zero_knowledge": 1}))
    # A separately pinned true declaration passes this binding check; it proves no hiding.
    declared = BackendQualification.model_validate(backend.model_dump() | {"zero_knowledge": True})
    validate_backend_files(
        declared,
        **(arguments(declared) | {"require_zero_knowledge": True}),
    )


@pytest.mark.parametrize("fault", ["missing", "extra", "changed", "type", "mapping-type", "length"])
def test_exact_file_inventory_rejects(backend, fault):
    args = arguments(backend)
    files = args["files"]
    key = backend.dependencies[0].path
    if fault == "missing":
        del files[key]
    elif fault == "extra":
        files["extra"] = b""
    elif fault == "changed":
        files[key] = b"!" + files[key][1:]
    elif fault == "type":
        files[key] = bytearray(files[key])
    elif fault == "mapping-type":
        args["files"] = list(files.items())
    else:
        files[key] = files[key][:-1]
    with pytest.raises(WireError):
        validate_backend_files(backend, **args)


def test_rehashed_file_change_does_not_replace_enrolled_record(backend):
    args = arguments(backend)
    key = backend.dependencies[0].path
    args["files"][key] = b"!" + args["files"][key][1:]
    value = decode(backend.encode())
    value["dependencies"][0]["sha256"] = hashlib.sha256(args["files"][key]).digest()
    altered = BackendQualification.decode(encode(value))
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        validate_backend_files(altered, **args)


@pytest.mark.parametrize("limit", [-1, 2**64, True, 1.0, "1"])
def test_byte_budget_type_bounds(backend, limit):
    with pytest.raises(WireError):
        validate_backend_files(backend, **(arguments(backend) | {"max_bytes": limit}))


def test_declared_and_actual_byte_budgets_precede_hashing(backend, monkeypatch):
    args = arguments(backend)

    def forbidden(_raw):
        raise AssertionError("oversized evidence must not be hashed")

    monkeypatch.setattr("hallmark.backend.hashlib.sha256", forbidden)
    # Pin computation itself uses hashlib through the wire module, so retain its original result.
    monkeypatch.setattr(BackendQualification, "identity", lambda _: args["expected_backend"])
    with pytest.raises(HallmarkError, match="LIMIT_EXCEEDED"):
        validate_backend_files(backend, **(args | {"max_bytes": args["max_bytes"] - 1}))
    args["files"][backend.dependencies[0].path] += b"x"
    with pytest.raises(HallmarkError, match="LIMIT_EXCEEDED"):
        validate_backend_files(backend, **args)


def test_public_metadata_boundaries(backend):
    value = backend.model_dump()
    for field in ("security_parameters", "public_input_layout"):
        value[field]["size"] = 1024 * 1024
    assert BackendQualification.model_validate(value).security_parameters.size == 1024 * 1024
    assert isinstance(backend.identity(), bytes)
    assert ArtifactDigest(backend.identity()) == backend.identity()
