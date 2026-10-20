"""Exact identities and adversarial static contracts for v1 classifier artifacts."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from hallmark.classifier_manifest import (
    PARAMETERS,
    ArithmeticProfile,
    ClassifierManifest,
    InputProfile,
    NodeSpec,
    TensorSpec,
)
from hallmark.manifests import FileRef
from hallmark.wire import WireError, decode, encode

ROOT = Path(__file__).resolve().parents[1]


def tensor(
    name: str, shape: tuple[int, ...], low: int = -2, high: int = 2, frac: int = 0
) -> TensorSpec:
    return TensorSpec(
        name=name, shape=shape, minimum=low, maximum=high, signed_bits=32, fractional_bits=frac
    )


def parameters(op: str, **attrs: Any) -> tuple[FileRef, bytes]:
    raw = encode({"schema_id": "hallmark/operator-parameters/1", "op": op, **attrs})
    ref = FileRef(path=f"params/{op}.cbor", size=len(raw), sha256=hashlib.sha256(raw).digest())
    return ref, raw


def graph(
    op: str, inputs: list[TensorSpec], out: TensorSpec, **attrs: Any
) -> tuple[ArithmeticProfile, dict[str, bytes]]:
    ref, raw = parameters(op, **attrs)
    node = NodeSpec(
        id="node", op=op, inputs=tuple(t.name for t in inputs), output=out.name, parameters=ref
    )
    profile = ArithmeticProfile(
        schema_id="hallmark/arithmetic/1", tensors=(*inputs, out), nodes=(node,), output=out.name
    )
    return profile, {ref.path: raw}


def byte_profile(**changes: Any) -> InputProfile:
    fields = dict(
        schema_id="hallmark/input-profile/1",
        encoding="utf8-bytes",
        tokenizer_files=(),
        prefix_tokens=(),
        suffix_tokens=(),
        chunk_size=16,
        overlap=0,
        max_units=32768,
        padding_id=0,
        padding_side="right",
    )
    return InputProfile(**(fields | changes))


@pytest.fixture
def vector() -> dict[str, Any]:
    return json.loads((ROOT / "fixtures/wire/classifier-v1.json").read_text())


@pytest.fixture
def artifacts(
    vector: dict[str, Any],
) -> tuple[InputProfile, ArithmeticProfile, ClassifierManifest, dict[str, bytes]]:
    inputs = InputProfile.decode(bytes.fromhex(vector["input_profile"]["cbor_hex"]))
    arithmetic = ArithmeticProfile.decode(bytes.fromhex(vector["arithmetic"]["cbor_hex"]))
    classifier = ClassifierManifest.decode(bytes.fromhex(vector["classifier"]["cbor_hex"]))
    params = {path: bytes.fromhex(raw) for path, raw in vector["parameters"].items()}
    return inputs, arithmetic, classifier, params


def test_fixed_vectors_and_schema_snapshots(vector: dict[str, Any], artifacts: Any) -> None:
    for name, cls, obj in zip(
        ("input_profile", "arithmetic", "classifier"),
        (InputProfile, ArithmeticProfile, ClassifierManifest),
        artifacts[:3],
        strict=True,
    ):
        entry = vector[name]
        raw = bytes.fromhex(entry["cbor_hex"])
        tag = ("hallmark/v1/" + obj._domain).encode()
        assert obj.encode() == raw
        assert obj.identity().hex() == entry["identity_hex"]
        assert hashlib.sha256(len(tag).to_bytes(4, "big") + tag + raw).digest() == obj.identity()
        assert cls.model_validate_json(obj.model_dump_json()) == obj
        snapshot = ROOT / f"docs/schemas/{name.replace('_', '-')}-v1.json"
        assert cls.model_json_schema() == json.loads(snapshot.read_text())
    assert PARAMETERS.json_schema() == json.loads(
        (ROOT / "docs/schemas/operator-parameters-v1.json").read_text()
    )
    inputs, arithmetic, classifier, params = artifacts
    classifier.validate_profiles(inputs, arithmetic, parameters=params)


VALID_OPERATIONS = [
    (
        "gather",
        [tensor("table", (5, 3)), tensor("index", (2,), 0, 4)],
        tensor("out", (2, 3)),
        {"axis": 0},
    ),
    (
        "gather",
        [tensor("table", (3, 5)), tensor("index", (2,), 0, 4)],
        tensor("out", (3, 2)),
        {"axis": 1},
    ),
    (
        "affine",
        [tensor("x", (2, 3)), tensor("w", (4, 3)), tensor("b", (4,), -1, 1)],
        tensor("out", (2, 4), -13, 13),
        {},
    ),
    ("add", [tensor("x", (2, 1)), tensor("y", (1, 3))], tensor("out", (2, 3), -4, 4), {}),
    (
        "multiply",
        [tensor("x", (2, 1)), tensor("y", (1, 3))],
        tensor("out", (2, 3), -4, 4),
        {"mode": "elementwise"},
    ),
    (
        "multiply",
        [tensor("x", (2, 1, 3, 4)), tensor("y", (1, 5, 4, 2))],
        tensor("out", (2, 5, 3, 2), -16, 16),
        {"mode": "matmul"},
    ),
    ("reshape", [tensor("x", (2, 3))], tensor("out", (6,)), {}),
    ("transpose", [tensor("x", (2, 3, 4))], tensor("out", (4, 2, 3)), {"permutation": [2, 0, 1]}),
    (
        "masked-reduce",
        [tensor("x", (2, 3)), tensor("mask", (2, 1), 0, 1)],
        tensor("out", (3,), -4, 4),
        {"axes": [0], "keep_dims": False, "reduction": "sum", "empty_value": 0},
    ),
    (
        "masked-reduce",
        [tensor("x", (2, 3)), tensor("mask", (2, 1), 0, 1)],
        tensor("out", (1, 1), -3, 2),
        {"axes": [0, 1], "keep_dims": True, "reduction": "max", "empty_value": -3},
    ),
    ("relu", [tensor("x", (2, 3))], tensor("out", (2, 3), 0, 2), {}),
    (
        "lookup",
        [tensor("table", (5,), -8, 8, 2), tensor("index", (2, 3), -2, 2, 1)],
        tensor("out", (2, 3), -8, 8, 2),
        {"offset": 2},
    ),
]


@pytest.mark.parametrize("op,inputs,out,attrs", VALID_OPERATIONS)
def test_every_operation_checks_shapes_and_ranges(
    op: str, inputs: Any, out: TensorSpec, attrs: Any
) -> None:
    profile, files = graph(op, inputs, out, **attrs)
    profile.validate_parameters(files)
    bad = decode(profile.encode())
    bad["tensors"][-1]["shape"] = [999]
    with pytest.raises(WireError):
        ArithmeticProfile.decode(encode(bad)).validate_parameters(files)
    bad = decode(profile.encode())
    bad["tensors"][-1]["maximum"] = out.maximum - 1
    with pytest.raises(WireError):
        ArithmeticProfile.decode(encode(bad)).validate_parameters(files)


@pytest.mark.parametrize(
    "op,inputs,out,attrs",
    [
        ("gather", [tensor("a", (3,)), tensor("i", (1,), -1, 0)], tensor("z", (1,)), {"axis": 0}),
        ("gather", [tensor("a", (3,)), tensor("i", (1,), 0, 3)], tensor("z", (1,)), {"axis": 0}),
        ("gather", [tensor("a", (3,)), tensor("i", (1,), 0, 2, 1)], tensor("z", (1,)), {"axis": 0}),
        ("gather", [tensor("a", (3,)), tensor("i", (1,), 0, 2)], tensor("z", (1,)), {"axis": 1}),
        (
            "affine",
            [tensor("a", (2,)), tensor("w", (1, 3)), tensor("b", (1,))],
            tensor("z", (1,), -20, 20),
            {},
        ),
        (
            "affine",
            [tensor("a", (2,)), tensor("w", (1, 2)), tensor("b", (2,))],
            tensor("z", (1,), -20, 20),
            {},
        ),
        (
            "affine",
            [tensor("a", (2,), frac=1), tensor("w", (1, 2)), tensor("b", (1,))],
            tensor("z", (1,), -20, 20),
            {},
        ),
        ("add", [tensor("a", (2,)), tensor("b", (3,))], tensor("z", (3,), -4, 4), {}),
        (
            "multiply",
            [tensor("a", (2, 3)), tensor("b", (2, 4))],
            tensor("z", (2, 4), -20, 20),
            {"mode": "matmul"},
        ),
        (
            "multiply",
            [tensor("a", (3,)), tensor("b", (3,))],
            tensor("z", (3,), -20, 20),
            {"mode": "matmul"},
        ),
        ("transpose", [tensor("a", (2, 2))], tensor("z", (2, 2)), {"permutation": [0, 0]}),
        (
            "masked-reduce",
            [tensor("a", (2,)), tensor("m", (2,), 0, 2)],
            tensor("z", (1,), -4, 4),
            {"axes": [0], "keep_dims": False, "reduction": "sum", "empty_value": 0},
        ),
        (
            "masked-reduce",
            [tensor("a", (2,)), tensor("m", (2,), 0, 1, 1)],
            tensor("z", (1,), -4, 4),
            {"axes": [0], "keep_dims": False, "reduction": "sum", "empty_value": 0},
        ),
        (
            "masked-reduce",
            [tensor("a", (2,)), tensor("m", (3,), 0, 1)],
            tensor("z", (1,), -4, 4),
            {"axes": [0], "keep_dims": False, "reduction": "sum", "empty_value": 0},
        ),
        ("lookup", [tensor("t", (3,)), tensor("i", (1,), -2, 2)], tensor("z", (1,)), {"offset": 1}),
        (
            "lookup",
            [tensor("t", (3, 1)), tensor("i", (1,), 0, 2)],
            tensor("z", (1,)),
            {"offset": 0},
        ),
        ("reshape", [tensor("a", (1,), frac=1)], tensor("z", (1,)), {}),
    ],
)
def test_invalid_operator_contracts(op: str, inputs: Any, out: TensorSpec, attrs: Any) -> None:
    profile, files = graph(op, inputs, out, **attrs)
    with pytest.raises(WireError):
        profile.validate_parameters(files)


@pytest.mark.parametrize(
    "value,expected", [(-7, -4), (-5, -2), (-3, -2), (-1, 0), (1, 0), (3, 2), (5, 2), (7, 4)]
)
def test_signed_ties_to_even(value: int, expected: int) -> None:
    profile, files = graph(
        "add",
        [tensor("a", (1,), value, value, 1), tensor("b", (1,), 0, 0, 1)],
        tensor("z", (1,), expected, expected),
    )
    profile.validate_parameters(files)


def test_range_overflow_is_rejected() -> None:
    profile, files = graph(
        "add",
        [tensor("a", (1,), 2**31 - 1, 2**31 - 1), tensor("b", (1,), 1, 1)],
        tensor("z", (1,), -(2**31), 2**31 - 1),
    )
    with pytest.raises(WireError):
        profile.validate_parameters(files)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("shape", []),
        ("shape", [0]),
        ("shape", [-1]),
        ("shape", [True]),
        ("shape", [1.0]),
        ("shape", [1] * 5),
        ("shape", [2**64]),
        ("signed_bits", 1),
        ("signed_bits", 33),
        ("signed_bits", True),
        ("fractional_bits", -1),
        ("fractional_bits", 31),
        ("fractional_bits", False),
        ("minimum", -(2**31) - 1),
        ("maximum", 2**31),
        ("minimum", 3),
        ("maximum", False),
    ],
)
def test_tensor_type_and_range_rejection(field: str, bad: Any) -> None:
    value = tensor("a", (1,)).model_dump()
    value[field] = bad
    with pytest.raises(ValidationError):
        TensorSpec.model_validate(value)


def test_bit_width_restricts_values() -> None:
    value = tensor("a", (1,), -128, 127).model_dump() | {"signed_bits": 8}
    assert TensorSpec.model_validate(value).minimum == -128
    for changes in ({"minimum": -129}, {"maximum": 128}):
        with pytest.raises(ValidationError):
            TensorSpec.model_validate(value | changes)


@pytest.mark.parametrize(
    "case",
    [
        "duplicate-tensor",
        "duplicate-node",
        "duplicate-producer",
        "forward",
        "cycle",
        "missing-input",
        "missing-output",
        "root-output",
        "unused-tensor",
        "unused-node",
        "conflicting-file",
    ],
)
def test_topology_rejections(artifacts: Any, case: str) -> None:
    value = decode(artifacts[1].encode())
    nodes = value["nodes"]
    if case == "duplicate-tensor":
        value["tensors"].append(value["tensors"][0])
    elif case == "duplicate-node":
        nodes[1]["id"] = nodes[0]["id"]
    elif case == "duplicate-producer":
        nodes[1]["output"] = nodes[0]["output"]
    elif case == "forward":
        nodes[0], nodes[1] = nodes[1], nodes[0]
    elif case == "cycle":
        nodes[0]["inputs"][0] = nodes[-1]["output"]
    elif case == "missing-input":
        nodes[0]["inputs"][0] = "missing"
    elif case == "missing-output":
        value["output"] = "missing"
    elif case == "root-output":
        value["output"] = "x"
    elif case == "unused-tensor":
        value["tensors"].append({**value["tensors"][0], "name": "unused"})
    elif case == "unused-node":
        value["output"] = nodes[0]["output"]
    else:
        nodes[-1]["parameters"] = {**nodes[0]["parameters"], "size": 99}
    with pytest.raises(WireError):
        ArithmeticProfile.decode(encode(value))


@pytest.mark.parametrize(
    "field,bad",
    [
        ("op", "softmax"),
        ("inputs", []),
        ("inputs", ["x"]),
        ("inputs", ["x"] * 4),
        ("parameters", None),
    ],
)
def test_node_contract_rejections(artifacts: Any, field: str, bad: Any) -> None:
    value = decode(artifacts[1].encode())
    value["nodes"][0][field] = bad
    with pytest.raises(WireError):
        ArithmeticProfile.decode(encode(value))


@pytest.mark.parametrize(
    "field,bad",
    [
        ("chunk_size", 0),
        ("chunk_size", 513),
        ("chunk_size", True),
        ("overlap", 1),
        ("overlap", False),
        ("max_units", 0),
        ("max_units", 32769),
        ("max_units", "16"),
        ("padding_id", 256),
        ("padding_id", False),
        ("padding_side", "left"),
        ("prefix_tokens", [1]),
        ("suffix_tokens", [1]),
    ],
)
def test_byte_profile_rejections(field: str, bad: Any) -> None:
    with pytest.raises(ValidationError):
        byte_profile(**{field: bad})


def token_profile(**changes: Any) -> InputProfile:
    ref, _ = parameters("relu")
    return byte_profile(
        encoding="token-ids",
        tokenizer_files=(ref,),
        **({"prefix_tokens": (1,), "suffix_tokens": (2,), "padding_id": 3} | changes),
    )


def test_special_token_capacity_and_identity() -> None:
    profile = token_profile(chunk_size=3)
    assert profile.chunk_size - len(profile.prefix_tokens) - len(profile.suffix_tokens) == 1
    for change in (
        {"chunk_size": 2},
        {"prefix_tokens": (1,) * 9},
        {"suffix_tokens": (1,) * 9},
        {"prefix_tokens": (False,)},
        {"suffix_tokens": (-1,)},
        {"padding_id": 2**64},
    ):
        with pytest.raises(ValidationError):
            token_profile(**change)
    for change in (
        {"prefix_tokens": (4,)},
        {"suffix_tokens": (4,)},
        {"padding_id": 4},
        {"chunk_size": 4},
        {"max_units": 16},
    ):
        assert token_profile(**change).identity() != token_profile().identity()
    with pytest.raises(ValidationError):
        byte_profile(encoding="token-ids")
    with pytest.raises(ValidationError):
        byte_profile(tokenizer_files=profile.tokenizer_files)


def test_tokenizer_file_constraints_and_identity() -> None:
    profile = token_profile()
    ref = profile.tokenizer_files[0]
    for files in ((ref, ref), (ref.model_copy(update={"path": "z"}), ref), (ref,) * 65):
        with pytest.raises(ValidationError):
            profile.model_validate(profile.model_dump() | {"tokenizer_files": files})
    for field, new in (("path", "a"), ("size", ref.size + 1), ("sha256", b"x" * 32)):
        changed = ref.model_copy(update={field: new})
        assert (
            profile.model_validate(
                profile.model_dump() | {"tokenizer_files": (changed,)}
            ).identity()
            != profile.identity()
        )


@pytest.mark.parametrize(
    "field",
    ["program", "weights", "input_profile", "arithmetic", "backend", "setup", "verifier_key"],
)
def test_classifier_identity_fields(artifacts: Any, field: str) -> None:
    model = artifacts[2]
    value = decode(model.encode())
    value[field] = b"\xff" * 32
    assert ClassifierManifest.decode(encode(value)).identity() != model.identity()


def test_classifier_kind_threshold_labels_and_tokenizer(artifacts: Any) -> None:
    model = artifacts[2]
    for update in (
        {"threshold": 2},
        {"labels": ["allowed", "blocked"]},
        {"kind": "encoder", "tokenizer": b"\x02" * 32},
    ):
        changed = ClassifierManifest.decode(encode(decode(model.encode()) | update))
        assert changed.identity() != model.identity()
    encoder = ClassifierManifest.decode(
        encode(decode(model.encode()) | {"kind": "encoder", "tokenizer": b"\x02" * 32})
    )
    changed = ClassifierManifest.decode(
        encode(decode(encoder.encode()) | {"tokenizer": b"\x03" * 32})
    )
    assert changed.identity() != encoder.identity()
    rule = ClassifierManifest.decode(
        encode(decode(model.encode()) | {"kind": "rule", "weights": None})
    )
    assert rule.identity() != model.identity()


@pytest.mark.parametrize(
    "change",
    [
        {"threshold": True},
        {"threshold": 2**31},
        {"threshold": -(2**31) - 1},
        {"scope": "response"},
        {"labels": ["x", "x"]},
        {"labels": ["x"]},
        {"weights": None},
        {"tokenizer": b"x" * 32},
        {"kind": "encoder"},
        {"kind": "rule"},
        {"kind": "rule", "weights": None, "threshold": 0},
    ],
)
def test_classifier_rejections(artifacts: Any, change: Any) -> None:
    with pytest.raises(WireError):
        ClassifierManifest.decode(encode(decode(artifacts[2].encode()) | change))


def test_parameter_bytes_are_mandatory_and_pinned(artifacts: Any) -> None:
    _, profile, _, files = artifacts
    path = next(iter(files))
    for changed in (
        {},
        {**files, "extra": b""},
        {**files, path: files[path] + b"\0"},
        {**files, path: b"x" * len(files[path])},
        {**files, path: "text"},
    ):
        with pytest.raises(WireError):
            profile.validate_parameters(changed)


@pytest.mark.parametrize(
    "op,attrs",
    [
        ("softmax", {}),
        ("relu", {"extra": "PRIVATE_SENTINEL"}),
        ("multiply", {"mode": "float"}),
        ("gather", {"axis": True}),
        ("transpose", {"permutation": [False]}),
        (
            "masked-reduce",
            {"axes": [0, 0], "keep_dims": False, "reduction": "sum", "empty_value": 0},
        ),
        (
            "masked-reduce",
            {"axes": [1, 0], "keep_dims": False, "reduction": "sum", "empty_value": 0},
        ),
        ("masked-reduce", {"axes": [0], "keep_dims": False, "reduction": "sum", "empty_value": 1}),
        ("masked-reduce", {"axes": [0], "keep_dims": 0, "reduction": "sum", "empty_value": 0}),
    ],
)
def test_invalid_parameter_documents(op: str, attrs: Any) -> None:
    profile, files = graph("relu", [tensor("x", (1,))], tensor("out", (1,), 0, 2))
    ref, raw = parameters(op, **attrs)
    value = decode(profile.encode())
    value["nodes"][0]["parameters"] = decode(ref.encode())
    with pytest.raises(WireError) as error:
        ArithmeticProfile.decode(encode(value)).validate_parameters({ref.path: raw})
    assert "PRIVATE_SENTINEL" not in str(error.value)
    assert error.value.__context__ is None


def test_profile_binding_and_unchecked_copies(artifacts: Any) -> None:
    inputs, profile, classifier, files = artifacts
    for changed in (
        inputs.model_copy(update={"chunk_size": 17}),
        inputs.model_copy(update={"overlap": True}),
    ):
        with pytest.raises(WireError):
            classifier.validate_profiles(changed, profile, parameters=files)
    for changed in (
        profile.model_copy(update={"output": "x"}),
        profile.model_copy(update={"tensors": ()}),
    ):
        with pytest.raises(WireError):
            classifier.validate_profiles(inputs, changed, parameters=files)
    for obj, update in (
        (classifier, {"threshold": False}),
        (inputs, {"overlap": False}),
        (profile, {"nodes": (profile.nodes[0].model_copy(update={"op": "softmax"}),)}),
    ):
        bad = obj.model_copy(update=update)
        for operation in (bad.encode, bad.identity):
            with pytest.raises(WireError):
                operation()


def test_all_artifact_fields_required_and_versions_exact(artifacts: Any) -> None:
    for obj in artifacts[:3]:
        original = decode(obj.encode())
        for field in original:
            value = {key: val for key, val in original.items() if key != field}
            with pytest.raises(WireError):
                type(obj).decode(encode(value))
        for changed in (
            original | {"schema_id": "hallmark/unknown/99"},
            original | {"extra": False},
        ):
            with pytest.raises(WireError):
                type(obj).decode(encode(changed))


def test_graph_identity_covers_nested_records(artifacts: Any) -> None:
    profile = artifacts[1]
    for field, new in (
        ("minimum", -1),
        ("maximum", 17),
        ("signed_bits", 31),
        ("fractional_bits", 1),
        ("shape", [255]),
    ):
        value = decode(profile.encode())
        value["tensors"][0][field] = new
        assert ArithmeticProfile.decode(encode(value)).identity() != profile.identity()
    for field, new in (("id", "changed"), ("inputs", ["w1", "x", "b1"])):
        value = decode(profile.encode())
        value["nodes"][0][field] = new
        assert ArithmeticProfile.decode(encode(value)).identity() != profile.identity()
    for field, new in (("path", "new.cbor"), ("size", 1), ("sha256", b"x" * 32)):
        value = decode(profile.encode())
        value["nodes"][1]["parameters"][field] = new
        assert ArithmeticProfile.decode(encode(value)).identity() != profile.identity()


def test_validation_allocates_no_tensor_data_or_files(
    artifacts: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("static validation cannot open a file")

    monkeypatch.setattr(Path, "open", forbidden)
    inputs, profile, classifier, files = artifacts
    classifier.validate_profiles(inputs, profile, parameters=files)


def test_collection_bounds(artifacts: Any) -> None:
    original = decode(artifacts[1].encode())
    for field in ("nodes", "tensors"):
        for items in ([], [original[field][0]] * 4097):
            with pytest.raises(WireError):
                ArithmeticProfile.decode(encode(original | {field: items}))


def test_parameter_budget(artifacts: Any) -> None:
    profile, files = artifacts[1], artifacts[3]
    path = next(iter(files))
    with pytest.raises(WireError, match="LIMIT_EXCEEDED"):
        profile.validate_parameters(files | {path: b"\0" * (64 * 1024 * 1024 + 1)})


def test_conservative_empty_reduction_and_scalar_shape() -> None:
    for reduction, low, high, empty in (("sum", 0, 12, 0), ("max", -1, 3, -1)):
        profile, files = graph(
            "masked-reduce",
            [tensor("x", (2, 2), 2, 3), tensor("m", (1,), 0, 1)],
            tensor("out", (1,), low, high),
            axes=[0, 1],
            keep_dims=False,
            reduction=reduction,
            empty_value=empty,
        )
        profile.validate_parameters(files)
    profile, files = graph(
        "masked-reduce",
        [tensor("x", (2,), 0, 1), tensor("m", (2,), 0, 1)],
        tensor("out", (1,), 0, 2),
        axes=[1],
        keep_dims=False,
        reduction="sum",
        empty_value=0,
    )
    with pytest.raises(WireError):
        profile.validate_parameters(files)


def test_upscaling_and_mixed_scale_add() -> None:
    # 1 + 3/2 = 5/2, expressed exactly with two fractional bits.
    profile, files = graph(
        "add",
        [tensor("a", (1,), 1, 1), tensor("b", (1,), 3, 3, 1)],
        tensor("out", (1,), 10, 10, 2),
    )
    profile.validate_parameters(files)


def test_scalar_and_encoding_obligations(artifacts: Any) -> None:
    inputs, arithmetic, classifier, files = artifacts
    tokens = token_profile()
    changed = classifier.model_copy(update={"input_profile": tokens.identity()})
    with pytest.raises(WireError):
        changed.validate_profiles(tokens, arithmetic, parameters=files)
    for change in ({"shape": [2]}, {"fractional_bits": 1}):
        value = decode(arithmetic.encode())
        value["tensors"][-1].update(change)
        profile = ArithmeticProfile.decode(encode(value))
        changed = classifier.model_copy(update={"arithmetic": profile.identity()})
        with pytest.raises(WireError):
            changed.validate_profiles(inputs, profile, parameters=files)
    value = decode(arithmetic.encode())
    value["nodes"][0]["id"] = "renamed"
    with pytest.raises(WireError):
        classifier.validate_profiles(
            inputs, ArithmeticProfile.decode(encode(value)), parameters=files
        )
    rule = classifier.model_copy(update={"kind": "rule", "weights": None})
    with pytest.raises(WireError):
        rule.validate_profiles(inputs, arithmetic, parameters=files)
    profile, parameters = graph("relu", [tensor("x", (1,), 0, 1)], tensor("out", (1,), 0, 1))
    rule = rule.model_copy(update={"arithmetic": profile.identity()})
    rule.validate_profiles(inputs, profile, parameters=parameters)


@pytest.mark.parametrize("raw", [b"\xa0", b"\x00", b"\xff", b"\xa2\x61a\x00\x61a\x00"])
def test_parameter_wire_boundary(raw: bytes) -> None:
    profile, _ = graph("relu", [tensor("x", (1,))], tensor("out", (1,), 0, 2))
    ref = FileRef(path="params/invalid.cbor", size=len(raw), sha256=hashlib.sha256(raw).digest())
    value = decode(profile.encode())
    value["nodes"][0]["parameters"] = decode(ref.encode())
    with pytest.raises(WireError):
        ArithmeticProfile.decode(encode(value)).validate_parameters({ref.path: raw})


def test_nested_immutability(artifacts: Any) -> None:
    inputs, arithmetic, classifier, _ = artifacts
    for obj, name, new in (
        (inputs, "chunk_size", 1),
        (classifier, "threshold", 3),
        (arithmetic.tensors[0], "minimum", 1),
        (arithmetic.nodes[0], "output", "x"),
        (arithmetic.nodes[0].parameters, "path", "elsewhere"),
    ):
        with pytest.raises(ValidationError):
            setattr(obj, name, new)


def test_names_output_operation_and_recipe_are_bound(artifacts: Any) -> None:
    profile = artifacts[1]
    value = decode(profile.encode())
    value["tensors"][-1]["name"] = "renamed"
    value["nodes"][-1]["output"] = "renamed"
    value["output"] = "renamed"
    assert ArithmeticProfile.decode(encode(value)).identity() != profile.identity()
    value = decode(profile.encode())
    value["nodes"][1]["op"] = "reshape"
    changed = ArithmeticProfile.decode(encode(value))
    assert changed.identity() != profile.identity()
    with pytest.raises(WireError):
        changed.validate_parameters(artifacts[3])
    assert token_profile().identity() != byte_profile().identity()


def test_huge_shapes_are_metadata_only() -> None:
    profile, files = graph(
        "relu",
        [tensor("x", (2**64 - 1,) * 4, 0, 1)],
        tensor("out", (2**64 - 1,) * 4, 0, 1),
    )
    profile.validate_parameters(files)
    assert len(profile.encode()) < 1024
