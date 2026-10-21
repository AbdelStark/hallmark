"""Archive, source-selection and reproducibility negative fixtures without network."""

import base64
import csv
import hashlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# These are maintainer scripts, deliberately absent from the runtime wheel.
spec = importlib.util.spec_from_file_location(
    "package_inventory", ROOT / "scripts/package_inventory.py"
)
inv = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = inv
spec.loader.exec_module(inv)
spec = importlib.util.spec_from_file_location(
    "reproduce_package", ROOT / "scripts/reproduce_package.py"
)
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


@pytest.mark.parametrize(
    "name",
    [
        "../x",
        "/x",
        "a/../b",
        "a//b",
        "a/./b",
        "a\\b",
        "a:b",
        "a\nx",
        "runs/a",
        "data/a",
        "checkpoints/a",
        ".env",
        "docs/.env.local",
        "docs/private/a",
        "docs/credentials.json",
        "a.pem",
        "a.key",
        "a.safetensors",
        "a.pkl",
        "a.npy",
        "a.pyc",
        ".agents/harness/goal.md",
    ],
)
def test_unsafe_source_names(name):
    with pytest.raises(ValueError):
        inv.safe_name(name)


@pytest.mark.parametrize(
    "secret",
    [
        b"-----BEGIN " + b"PRIVATE KEY-----",
        b"ghp_" + b"A" * 36,
        b"AKIA" + b"A" * 16,
        b"hf_" + b"a" * 30,
    ],
)
def test_credentials_reject_without_disclosing_content(secret):
    with pytest.raises(ValueError) as error:
        inv.file_inventory({"docs/note.txt": secret})
    assert secret.decode() not in str(error.value)


def test_inventory_hashes_and_bounds(monkeypatch):
    assert inv.file_inventory({"a.txt": b"abc"}) == [
        {"path": "a.txt", "size": 3, "sha256": hashlib.sha256(b"abc").hexdigest()}
    ]
    with pytest.raises(ValueError):
        inv.file_inventory({"a.txt": b"a", "A.txt": b"b"})
    monkeypatch.setattr(inv, "MAX_FILE", 2)
    with pytest.raises(ValueError):
        inv.file_inventory({"a.txt": b"abc"})
    monkeypatch.setattr(inv, "MAX_TOTAL", 3)
    with pytest.raises(ValueError):
        inv.file_inventory({"a": b"ab", "b": b"cd"})
    monkeypatch.setattr(inv, "MAX_FILES", 1)
    with pytest.raises(ValueError):
        inv.file_inventory({"a": b"a", "b": b"b"})


@pytest.mark.parametrize(
    "kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.DIRTYPE]
)
def test_tar_nonregular_members_reject(tmp_path, kind):
    path = tmp_path / "sample.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("sample/a")
        info.type = kind
        info.linkname = "outside"
        archive.addfile(info)
    with pytest.raises(ValueError):
        inv.archive_files(path)


@pytest.mark.parametrize("mutation", ["duplicate", "traversal", "symlink", "oversize"])
def test_zip_bad_members_reject(tmp_path, monkeypatch, mutation):
    path = tmp_path / "sample.whl"
    with zipfile.ZipFile(path, "w") as archive:
        if mutation == "duplicate":
            archive.writestr("a", b"a")
            with pytest.warns(UserWarning):
                archive.writestr("a", b"b")
        elif mutation == "traversal":
            archive.writestr("../a", b"a")
        elif mutation == "symlink":
            info = zipfile.ZipInfo("a")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, b"outside")
        else:
            monkeypatch.setattr(inv, "MAX_FILE", 2)
            archive.writestr("a", b"abc")
    with pytest.raises(ValueError):
        inv.archive_files(path)


def artifacts(tmp_path, *, extra=None, missing=None, changed=False, bad_record=False):
    source = {
        "src/hallmark/__init__.py": b"",
        "src/hallmark/py.typed": b"",
        "LICENSE.md": b"fixture",
    }
    name = "sample-0.1"
    info = name + ".dist-info/"
    wheel_files = {
        "hallmark/__init__.py": b"",
        "hallmark/py.typed": b"",
        info + "licenses/LICENSE.md": b"fixture",
        info + "METADATA": b"metadata",
        info + "WHEEL": b"wheel",
        info + "entry_points.txt": b"entry",
    }
    record = io.StringIO()
    writer = csv.writer(record, lineterminator="\n")
    for file, raw in wheel_files.items():
        hashed = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=")
        writer.writerow((file, "sha256=" + hashed, len(raw)))
    writer.writerow((info + "RECORD", "", ""))
    wheel_files[info + "RECORD"] = b"wrong" if bad_record else record.getvalue().encode()
    if extra:
        wheel_files[extra] = b"unreviewed"
    if missing:
        del wheel_files[missing]
    if changed:
        wheel_files["hallmark/__init__.py"] = b"changed"
    wheel = tmp_path / "sample.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for file, raw in wheel_files.items():
            archive.writestr(file, raw)
    sdist = tmp_path / "sample.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        for file, raw in source.items() | {"PKG-INFO": b"metadata"}.items():
            entry = tarfile.TarInfo(name + "/" + file)
            entry.size = len(raw)
            archive.addfile(entry, io.BytesIO(raw))
    return wheel, sdist, source, name


def test_exact_archives_and_wheel_record(tmp_path):
    result = inv.check_archives(*artifacts(tmp_path))
    assert len(result) == 2
    assert len(result["sample.whl"]["files"]) == 7


@pytest.mark.parametrize(
    "kwargs",
    [
        {"extra": "hallmark/unreviewed.py"},
        {"missing": "hallmark/py.typed"},
        {"changed": True},
        {"bad_record": True},
    ],
)
def test_archive_inventory_and_hash_mismatches_reject(tmp_path, kwargs):
    with pytest.raises(ValueError):
        inv.check_archives(*artifacts(tmp_path, **kwargs))


def test_sdist_unreviewed_file_rejects(tmp_path):
    wheel, sdist, source, name = artifacts(tmp_path)
    with tarfile.open(sdist, "w:gz") as archive:
        for file, raw in (source | {"PKG-INFO": b"metadata", ".gitignore": b"*"}).items():
            entry = tarfile.TarInfo(name + "/" + file)
            entry.size = len(raw)
            archive.addfile(entry, io.BytesIO(raw))
    with pytest.raises(ValueError):
        inv.check_archives(wheel, sdist, source, name)


def init_source(root):
    (root / "src").mkdir()
    (root / "src/a.py").write_text("value = 1\n")
    (root / "pyproject.toml").write_text(
        '[tool.hatch.build.targets.sdist]\ninclude=["src","pyproject.toml"]\n'
    )
    subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)
    subprocess.run(["git", "add", "src/a.py", "pyproject.toml"], cwd=root, check=True)


def test_only_reviewed_paths_with_actual_working_bytes(tmp_path):
    init_source(tmp_path)
    (tmp_path / "src/unreviewed.py").write_text("private material")
    (tmp_path / "src/a.py").write_text("value = 2\n")
    files, inventory = build.reviewed_source(tmp_path)
    assert "src/unreviewed.py" not in files
    assert files["src/a.py"] == b"value = 2\n"
    destination = tmp_path / "snapshot"
    build.copy_source(destination, files, inventory)
    assert (destination / ".git").is_dir()
    assert not (destination / "src/unreviewed.py").exists()
    assert int((destination / "src/a.py").stat().st_mtime) == int(build.BUILD_EPOCH)


@pytest.mark.parametrize("kind", ["symlink", "parent_symlink", "hardlink", "missing"])
def test_source_aliases_and_missing_files_reject(tmp_path, kind):
    init_source(tmp_path)
    file = tmp_path / "src/a.py"
    if kind == "parent_symlink":
        (tmp_path / "src").rename(tmp_path / "other")
        (tmp_path / "src").symlink_to(tmp_path / "other", target_is_directory=True)
    elif kind == "hardlink":
        os.link(file, tmp_path / "alias")
    else:
        file.unlink()
        if kind == "symlink":
            file.symlink_to(tmp_path / "pyproject.toml")
    with pytest.raises((ValueError, FileNotFoundError)):
        build.reviewed_source(tmp_path)


def test_unequal_builds_fail(tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    first.mkdir()
    second.mkdir()
    for root in (first, second):
        (root / "a.whl").write_bytes(b"wheel")
        (root / "a.tar.gz").write_bytes(b"source")
    assert len(build.require_same(first, second)) == 2
    (second / "a.whl").write_bytes(b"changed")
    with pytest.raises(ValueError):
        build.require_same(first, second)
    (second / "a.whl").unlink()
    with pytest.raises(ValueError):
        build.require_same(first, second)


def test_build_environment_drops_unrecorded_python_and_uv_settings(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", "private")
    monkeypatch.setenv("UV_INDEX", "private")
    monkeypatch.setenv("HATCH_BUILD_LOCATION", "private")
    env = build.build_environment()
    assert all(key not in env for key in ("PYTHONPATH", "UV_INDEX", "HATCH_BUILD_LOCATION"))
    assert env["OMP_NUM_THREADS"] == env["OPENBLAS_NUM_THREADS"] == env["MKL_NUM_THREADS"] == "1"


def test_compressed_wheel_tag_matching():
    assert inv.wheel_tags("example-1.0-py2.py3-none-any.whl") == {"py2-none-any", "py3-none-any"}


@pytest.mark.parametrize("mutation", [None, "build", "review", "licence", "duplicate"])
def test_build_pins_and_metadata_review_cannot_drift(mutation):
    files = {
        name: (ROOT / name).read_bytes()
        for name in (
            "pyproject.toml",
            "uv.lock",
            "research/evidence/w15-guard-dependencies-2026-10-20.json",
        )
    }
    if mutation == "build":
        files["pyproject.toml"] = files["pyproject.toml"].replace(
            b"hatchling==1.32.4", b"hatchling>=1", 1
        )
    elif mutation:
        name = "research/evidence/w15-guard-dependencies-2026-10-20.json"
        review = json.loads(files[name])
        if mutation == "review":
            review["packages"][0]["version"] = "0.0.0"
        elif mutation == "duplicate":
            review["packages"].append(review["packages"][0])
        else:
            for key in (
                "license_expression",
                "legacy_license_label",
                "license_classifiers",
                "license_notices_when_metadata_missing",
            ):
                review["packages"][0][key] = None
        files[name] = json.dumps(review).encode()
    if mutation:
        with pytest.raises(ValueError):
            build.validate_build_inputs(files)
    else:
        assert len(build.validate_build_inputs(files)) == 6


def test_reviewed_fixture_keys_are_not_recognizable_credentials():
    files, inventory = build.reviewed_source(ROOT)
    assert len(files) == len(inventory)
    assert "fixtures/wire/registry-rotation-v1.json" in files
    assert ".agents/harness/goal.md" not in files and ".gitignore" not in files


@pytest.mark.parametrize("kind", ["extra", "oversize", "symlink"])
def test_build_comparison_checks_outputs_before_hashing(tmp_path, monkeypatch, kind):
    first, second = tmp_path / "one", tmp_path / "two"
    first.mkdir()
    second.mkdir()
    for root in (first, second):
        (root / "a.whl").write_bytes(b"wheel")
        (root / "a.tar.gz").write_bytes(b"source")
    if kind == "extra":
        (first / "unexpected.zip").write_bytes(b"extra")
    elif kind == "oversize":
        monkeypatch.setattr(build, "MAX_TOTAL", 3)
    else:
        (first / "a.whl").unlink()
        (first / "a.whl").symlink_to(second / "a.whl")
    with pytest.raises(ValueError):
        build.require_same(first, second)


@pytest.mark.parametrize(
    "field",
    [
        "st_atime_ns",
        "st_mtime_ns",
        "st_ctime_ns",
        "st_size",
        "st_ino",
        "st_nlink",
        "st_mode",
        "st_uid",
    ],
)
def test_snapshot_ignores_access_time_but_rejects_other_changes(tmp_path, monkeypatch, field):
    from types import SimpleNamespace

    init_source(tmp_path)
    target = tmp_path / "src/a.py"
    original = Path.stat

    def changed_stat(path, *, follow_symlinks=True):
        info = original(path, follow_symlinks=follow_symlinks)
        if path != target or not follow_symlinks:
            return info
        changed = {name: getattr(info, name) for name in dir(info) if name.startswith("st_")}
        changed[field] += 1
        return SimpleNamespace(**changed)

    monkeypatch.setattr(Path, "stat", changed_stat)
    if field == "st_atime_ns":
        files, _ = build.reviewed_source(tmp_path)
        assert files["src/a.py"] == b"value = 1\n"
    else:
        with pytest.raises(ValueError, match="source changed"):
            build.reviewed_source(tmp_path)
