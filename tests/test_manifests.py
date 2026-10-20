"""Model identity vectors and local path/file admission failure cases."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import cbor2
import pytest
from pydantic import ValidationError

from hallmark.errors import HallmarkError
from hallmark.manifests import FileRef, GenerationConfig, ModelManifest, verify_model_files
from hallmark.wire import WireError, WireLimits, decode, encode

ROOT = Path(__file__).resolve().parents[1]
VECTOR = ROOT / "fixtures/wire/model-manifest-v1.json"


@pytest.fixture
def model() -> ModelManifest:
    return ModelManifest.model_validate_json(json.dumps(json.loads(VECTOR.read_text())["model"]))


def test_golden(model: ModelManifest) -> None:
    vector = json.loads(VECTOR.read_text())
    raw = bytes.fromhex(vector["cbor_hex"])
    assert model.encode() == raw
    assert ModelManifest.decode(raw) == model
    assert model.identity().hex() == vector["identity_hex"]
    tag = b"hallmark/v1/model"
    assert hashlib.sha256(len(tag).to_bytes(4, "big") + tag + raw).digest() == model.identity()
    assert cbor2.loads(raw) == decode(raw)
    assert cbor2.dumps(decode(raw), canonical=True) == raw
    assert hashlib.sha256(raw).digest() != model.identity()


def test_schema_snapshot_and_json_projection(model: ModelManifest) -> None:
    schema = json.loads((ROOT / "docs/schemas/model-manifest-v1.json").read_text())
    assert ModelManifest.model_json_schema() == schema
    assert ModelManifest.model_validate_json(model.model_dump_json()) == model
    assert len(json.loads(model.model_dump_json())["runtime"]) == 64
    with pytest.raises(WireError):
        ModelManifest.decode(encode(json.loads(model.model_dump_json())))


@pytest.mark.parametrize("field", ["architecture", "tokenizer", "chat_template", "runtime"])
def test_identity_pins_each_artifact(model: ModelManifest, field: str) -> None:
    value = decode(model.encode())
    value[field] = b"\xff" * 32
    assert ModelManifest.decode(encode(value)).identity() != model.identity()


@pytest.mark.parametrize(
    "field,new", [("path", "other.bin"), ("size", 4), ("sha256", b"\xff" * 32)]
)
def test_identity_pins_each_file_field(model: ModelManifest, field: str, new: Any) -> None:
    value = decode(model.encode())
    value["files"][0][field] = new
    assert ModelManifest.decode(encode(value)).identity() != model.identity()


def test_identity_pins_additional_shard_and_generation(model: ModelManifest) -> None:
    value = decode(model.encode())
    value["files"].append({**value["files"][0], "path": "z.bin"})
    assert ModelManifest.decode(encode(value)).identity() != model.identity()
    value = decode(model.encode())
    value["generation"]["max_new_tokens"] += 1
    assert ModelManifest.decode(encode(value)).identity() != model.identity()
    value = decode(model.encode())
    value["numerical_mode"] = "int8"
    assert ModelManifest.decode(encode(value)).identity() != model.identity()


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/",
        "/weights.bin",
        "//host/file",
        "a/",
        "a//b",
        ".",
        "..",
        "./a",
        "../a",
        "a/./b",
        "a/../b",
        "C:/a",
        "C:a",
        "a\\b",
        "\\\\host\\file",
        "a\x00b",
        "a\nb",
        "a\tb",
        "a\x7fb",
        "\ud800",
        "a" * 4097,
        "é" * 2049,
    ],
)
def test_invalid_paths(path: str) -> None:
    with pytest.raises(ValidationError):
        FileRef(path=path, size=0, sha256=b"\0" * 32)


@pytest.mark.parametrize(
    "path", ["weights.bin", "a/b", ".hidden", "a..b", "é", "e\u0301", "a" * 4096]
)
def test_paths_are_preserved(path: str) -> None:
    assert FileRef(path=path, size=0, sha256=b"\0" * 32).path == path


@pytest.mark.parametrize(
    "field,bad",
    [
        ("size", -1),
        ("size", 2**64),
        ("size", False),
        ("size", 0.0),
        ("size", "0"),
        ("sha256", b""),
        ("sha256", b"x" * 31),
        ("sha256", b"x" * 33),
        ("sha256", "00" * 32),
        ("sha256", bytearray(32)),
        ("path", b"weights.bin"),
    ],
)
def test_file_types(field: str, bad: Any) -> None:
    value = {"path": "a", "size": 0, "sha256": b"\0" * 32, field: bad}
    with pytest.raises(ValidationError):
        FileRef.model_validate(value)


def test_size_extremes() -> None:
    for size in (0, 2**64 - 1):
        assert FileRef(path="a", size=size, sha256=b"\0" * 32).size == size


@pytest.mark.parametrize(
    "field,bad",
    [
        ("seed", False),
        ("seed", True),
        ("seed", 1),
        ("seed", -1),
        ("seed", 0.0),
        ("seed", "0"),
        ("sampling", "sample"),
        ("sampling", b"greedy"),
        ("max_new_tokens", False),
        ("max_new_tokens", 0),
        ("max_new_tokens", 4097),
        ("max_new_tokens", 1.0),
        ("max_new_tokens", "1"),
    ],
)
def test_greedy_types(field: str, bad: Any) -> None:
    value = {"seed": 0, "sampling": "greedy", "max_new_tokens": 1, field: bad}
    with pytest.raises(ValidationError):
        GenerationConfig.model_validate(value)


def test_generation_extremes() -> None:
    for size in (1, 4096):
        assert (
            GenerationConfig(max_new_tokens=size, seed=0, sampling="greedy").max_new_tokens == size
        )


@pytest.mark.parametrize("field", list(ModelManifest.model_fields))
def test_exact_top_level_fields(model: ModelManifest, field: str) -> None:
    value = decode(model.encode())
    del value[field]
    with pytest.raises(WireError):
        ModelManifest.decode(encode(value))


@pytest.mark.parametrize("nested", [None, "files", "generation"])
def test_unknown_fields_and_version(model: ModelManifest, nested: str | None) -> None:
    value = decode(model.encode())
    target = value if nested is None else value[nested][0] if nested == "files" else value[nested]
    target["PRIVATE_SENTINEL"] = "PRIVATE_SENTINEL"
    with pytest.raises(WireError) as error:
        ModelManifest.decode(encode(value))
    assert "PRIVATE_SENTINEL" not in str(error.value)
    assert error.value.__context__ is None
    value = decode(model.encode())
    value["schema_id"] = "hallmark/model/2"
    with pytest.raises(WireError):
        ModelManifest.decode(encode(value))


@pytest.mark.parametrize("files", [[], {}, "a", None, [None]])
def test_invalid_file_collection(model: ModelManifest, files: Any) -> None:
    value = decode(model.encode())
    value["files"] = files
    with pytest.raises(WireError):
        ModelManifest.decode(encode(value))


def test_sorted_unique_bounded_files(model: ModelManifest) -> None:
    value = decode(model.encode())
    one = value["files"][0]
    for paths in (["b", "a"], ["a", "a"], [f"{i:04}" for i in range(4097)]):
        value["files"] = [{**one, "path": p} for p in paths]
        with pytest.raises(WireError):
            ModelManifest.decode(encode(value))
    value["files"] = [{**one, "path": f"{i:04}"} for i in range(4096)]
    assert len(ModelManifest.decode(encode(value)).files) == 4096


def test_unicode_is_not_normalized(model: ModelManifest) -> None:
    value = decode(model.encode())
    value["files"][0]["path"] = "é"
    composed = ModelManifest.decode(encode(value))
    value["files"][0]["path"] = "e\u0301"
    assert ModelManifest.decode(encode(value)).identity() != composed.identity()


@pytest.mark.parametrize("mode", ["", "x y", "é", "a" * 129])
def test_numerical_mode_is_id(model: ModelManifest, mode: str) -> None:
    value = decode(model.encode())
    value["numerical_mode"] = mode
    with pytest.raises(WireError):
        ModelManifest.decode(encode(value))


def test_immutable_including_nested_values(model: ModelManifest) -> None:
    original = model.identity()
    assert isinstance(model.files, tuple)
    for obj, field, new in (
        (model, "runtime", b"x" * 32),
        (model.files[0], "size", 99),
        (model.generation, "seed", 1),
    ):
        with pytest.raises(ValidationError):
            setattr(obj, field, new)
    value = decode(model.encode())
    other = ModelManifest.model_validate(value)
    value["files"][0]["path"] = "changed.bin"
    assert other.identity() == original


def test_unvalidated_copies_fail_at_boundaries(model: ModelManifest, tmp_path: Path) -> None:
    copies = [
        model.model_copy(update={"runtime": b"x"}),
        model.model_copy(update={"extra": "PRIVATE_SENTINEL"}),
        model.model_copy(
            update={"generation": model.generation.model_copy(update={"seed": False})}
        ),
        model.model_copy(update={"files": (model.files[0].model_copy(update={"path": "../a"}),)}),
        ModelManifest.model_construct(),
    ]
    for invalid in copies:
        for operation in (
            invalid.encode,
            invalid.identity,
            lambda invalid=invalid: verify_model_files(invalid, tmp_path, max_bytes=100),
        ):
            with pytest.raises(WireError):
                operation()


def test_wire_rejections_and_limits(model: ModelManifest) -> None:
    raw = model.encode()
    for bad in (raw + b"\0", b"\xa0", b"\x80", b"\xa2\x61a\x00\x61a\x00"):
        with pytest.raises(WireError):
            ModelManifest.decode(bad)
    for action in (
        lambda: model.encode(limits=WireLimits(max_bytes=len(raw) - 1)),
        lambda: ModelManifest.decode(raw, limits=WireLimits(max_bytes=len(raw) - 1)),
    ):
        with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
            action()


def test_explicit_file_checks(model: ModelManifest, tmp_path: Path) -> None:
    (tmp_path / "weights.bin").write_bytes(b"abc")
    verify_model_files(model, tmp_path, max_bytes=3)
    for data in (b"abd", b"ab", b"abcd"):
        (tmp_path / "weights.bin").write_bytes(data)
        with pytest.raises(HallmarkError, match="INPUT_INVALID"):
            verify_model_files(model, tmp_path, max_bytes=3)
    (tmp_path / "weights.bin").unlink()
    with pytest.raises(HallmarkError) as error:
        verify_model_files(model, tmp_path, max_bytes=3)
    assert str(tmp_path) not in str(error.value)
    assert error.value.__context__ is None


def test_empty_and_nested_files(model: ModelManifest, tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub/empty").touch()
    value = decode(model.encode())
    value["files"] = [{"path": "sub/empty", "size": 0, "sha256": hashlib.sha256(b"").digest()}]
    verify_model_files(ModelManifest.decode(encode(value)), tmp_path, max_bytes=0)


@pytest.mark.parametrize(
    "kind", ["file-link", "parent-link", "root-link", "hard-link", "directory", "fifo"]
)
def test_links_and_nonregular_files(model: ModelManifest, tmp_path: Path, kind: str) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "weights.bin").write_bytes(b"abc")
    target = root / "weights.bin"
    value = decode(model.encode())
    if kind == "file-link":
        target.symlink_to(outside / "weights.bin")
    elif kind == "parent-link":
        (root / "sub").symlink_to(outside, target_is_directory=True)
        value["files"][0]["path"] = "sub/weights.bin"
    elif kind == "root-link":
        root = tmp_path / "root-link"
        root.symlink_to(outside, target_is_directory=True)
    elif kind == "hard-link":
        target.hardlink_to(outside / "weights.bin")
    elif kind == "directory":
        target.mkdir()
    else:
        os.mkfifo(target)
    with pytest.raises(HallmarkError):
        verify_model_files(ModelManifest.decode(encode(value)), root, max_bytes=3)


def test_total_budget_is_checked_before_io(
    model: ModelManifest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("budget rejection must precede filesystem access")

    monkeypatch.setattr(os, "open", forbidden)
    value = decode(model.encode())
    value["files"].append({**value["files"][0], "path": "z.bin"})
    with pytest.raises(HallmarkError, match="LIMIT_EXCEEDED"):
        verify_model_files(ModelManifest.decode(encode(value)), tmp_path, max_bytes=5)
    for budget in (True, -1, 2**64, 3.0):
        with pytest.raises(HallmarkError, match="INPUT_INVALID"):
            verify_model_files(model, tmp_path, max_bytes=budget)


@pytest.mark.parametrize("data", [b"abcd", b"ab", b"abd"])
def test_file_changed_during_read(
    model: ModelManifest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data: bytes
) -> None:
    path = tmp_path / "weights.bin"
    path.write_bytes(b"abc")
    read = os.read
    changed = False

    def racing_read(fd: int, size: int) -> bytes:
        nonlocal changed
        block = read(fd, size)
        if not changed:
            changed = True
            path.write_bytes(data)
        return block

    monkeypatch.setattr(os, "read", racing_read)
    with pytest.raises(HallmarkError):
        verify_model_files(model, tmp_path, max_bytes=3)


def test_directory_swap_cannot_follow_link(
    model: ModelManifest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub/weights.bin").write_bytes(b"abc")
    value = decode(model.encode())
    value["files"][0]["path"] = "sub/weights.bin"
    dup = os.dup

    def swap(fd: int) -> int:
        (tmp_path / "sub").rename(tmp_path / "renamed")
        (tmp_path / "sub").symlink_to(tmp_path / "renamed", target_is_directory=True)
        return dup(fd)

    monkeypatch.setattr(os, "dup", swap)
    with pytest.raises(HallmarkError):
        verify_model_files(ModelManifest.decode(encode(value)), tmp_path, max_bytes=3)


def test_file_inspection_requires_safe_platform(
    model: ModelManifest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(os, "supports_dir_fd", set())
    with pytest.raises(HallmarkError):
        verify_model_files(model, tmp_path, max_bytes=3)


def test_filesystem_aliases_cannot_duplicate_a_file(
    model: ModelManifest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "weights.bin").write_bytes(b"abc")
    value = decode(model.encode())
    value["files"].insert(0, {**value["files"][0], "path": "alias.bin"})
    real_open = os.open

    def alias_open(path: Any, flags: int, **kwargs: Any) -> int:
        return real_open("weights.bin" if path == "alias.bin" else path, flags, **kwargs)

    monkeypatch.setattr(os, "open", alias_open)
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, alias_open})
    with pytest.raises(HallmarkError):
        verify_model_files(ModelManifest.decode(encode(value)), tmp_path, max_bytes=6)


def test_file_reads_respect_byte_budget(
    model: ModelManifest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "weights.bin").write_bytes(b"abc")
    read = os.read
    requested = []

    def counted_read(fd: int, size: int) -> bytes:
        requested.append(size)
        return read(fd, size)

    monkeypatch.setattr(os, "read", counted_read)
    verify_model_files(model, tmp_path, max_bytes=3)
    assert sum(requested) <= 3


@pytest.mark.parametrize("field", ["architecture", "tokenizer", "chat_template", "runtime"])
@pytest.mark.parametrize("bad", [b"x" * 31, b"x" * 33, "00" * 32, 0, False])
def test_artifact_digest_types(model: ModelManifest, field: str, bad: Any) -> None:
    value = decode(model.encode())
    value[field] = bad
    with pytest.raises(WireError):
        ModelManifest.decode(encode(value))


def test_schema_parse_never_opens_files(
    model: ModelManifest, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = model.encode()

    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("schema validation must not access the filesystem")

    monkeypatch.setattr(os, "open", forbidden)
    assert ModelManifest.decode(raw).identity() == model.identity()
