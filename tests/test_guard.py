import importlib.util
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from hallmark.guard import GuardSpec, LocalGuard, _pinned_bytes
from hallmark.wire import WireError

ROOT = Path(__file__).resolve().parents[1]


def spec():
    return GuardSpec(
        schema_id="hallmark/guard-spec/1",
        model_sha256="0" * 64,
        model_bytes=1,
        tokenizer_sha256="1" * 64,
        tokenizer_bytes=1,
        max_prompt_bytes=32768,
        sequence_tokens=512,
        vocabulary_size=7,
        threads=1,
    )


@pytest.mark.parametrize(
    "key,value",
    [
        ("threads", True),
        ("threads", 5),
        ("model_bytes", 0),
        ("sequence_tokens", 513),
        ("max_prompt_bytes", 32769),
        ("model_sha256", "wrong"),
    ],
)
def test_spec_bounds(key, value):
    raw = spec().model_dump()
    raw[key] = value
    with pytest.raises(ValidationError):
        GuardSpec.model_validate(raw)


def test_pin_checked_before_assets_or_optional_imports(tmp_path):
    with pytest.raises(WireError):
        LocalGuard(tmp_path, spec(), expected_spec="wrong")


@pytest.mark.parametrize("kind", ["hash", "size", "symlink", "hardlink", "directory", "fifo"])
def test_unsafe_assets_reject(tmp_path, kind):
    import hashlib
    import os

    path = tmp_path / "asset"
    if kind == "directory":
        path.mkdir()
    elif kind == "fifo":
        os.mkfifo(path)
    else:
        path.write_bytes(b"x")
        if kind == "symlink":
            path.unlink()
            path.symlink_to(tmp_path / "target")
        elif kind == "hardlink":
            os.link(path, tmp_path / "alias")
    with pytest.raises((WireError, OSError)):
        _pinned_bytes(
            path,
            2 if kind == "size" else 1,
            "0" * 64 if kind == "hash" else hashlib.sha256(b"x").hexdigest(),
        )


@pytest.fixture
def runtime(tmp_path):
    pytest.importorskip("onnx")
    pytest.importorskip("onnxruntime")
    pytest.importorskip("tokenizers")
    module_spec = importlib.util.spec_from_file_location(
        "guard_fixture", ROOT / "scripts/check_guard.py"
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    assets = tmp_path / "assets"
    pinned = module.fixture(assets)
    return LocalGuard(assets, pinned, expected_spec=pinned.identity()), assets, module


def test_real_runtime_fixture(runtime, tmp_path):
    guard, _, module = runtime
    repeat = tmp_path / "repeat"
    repeat.mkdir()
    assert module.check(repeat)["passed"]
    assert guard.score("ALERT")["score"] == 2.0
    long = guard.score("hello " * 510 + "ALERT")
    assert long["token_count"] == 511
    assert long["chunks"][0]["logits"] == [-0.0, 0.0]
    assert long["chunks"][1]["logits"] == [-1.0, 1.0]
    assert long["score"] == 2.0
    assert guard.score("")["token_count"] == 0
    assert guard.score("é hello")["token_count"] == 2
    assert len(guard.score("hello " * 5460 + "ALERT!!!")["chunks"]) == 11


@pytest.mark.parametrize("prompt", ["x" * 32769, "é" * 16385, "\ud800", 1])
def test_invalid_prompts_reject(runtime, prompt):
    with pytest.raises(WireError):
        runtime[0].score(prompt)


@pytest.mark.parametrize("change", ["external", "custom", "function", "training"])
def test_unsafe_graphs_reject_before_runtime(runtime, change):
    import onnx

    from hallmark.guard import _inspect_graph

    _, assets, _ = runtime
    model = onnx.load(assets / "model.onnx")
    if change == "external":
        tensor = model.graph.initializer[0]
        tensor.data_location = 1
        entry = tensor.external_data.add()
        entry.key, entry.value = "location", "PRIVATE_PATH_SENTINEL"
    elif change == "custom":
        model.graph.node[0].domain = "unreviewed"
    elif change == "function":
        model.functions.add().name = "unreviewed"
    else:
        model.training_info.add()
    with pytest.raises(WireError):
        _inspect_graph(model.SerializeToString(), onnx)


@pytest.mark.parametrize("mode", ["nan", "shape", "dtype"])
def test_bad_outputs_reject(runtime, mode):
    import numpy as np

    guard = runtime[0]

    class BadSession:
        def run(self, *_):
            return [
                np.array([[float("nan"), 0]], dtype=np.float32)
                if mode == "nan"
                else np.zeros(
                    (1, 3) if mode == "shape" else (1, 2),
                    dtype=np.float64 if mode == "dtype" else np.float32,
                )
            ]

    guard._session = BadSession()
    with pytest.raises(WireError):
        guard.score("hello")


def test_core_import_has_no_optional_runtime(tmp_path):
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import hallmark.guard; "
            "assert not {'onnx', 'onnxruntime', 'tokenizers', 'numpy'} & sys.modules.keys()",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_guard_schema_is_json():
    assert GuardSpec.model_json_schema() == json.loads(
        (ROOT / "fixtures/guard-spec.schema.json").read_text()
    )


def test_guard_calibration_and_test_boundaries(runtime):
    from hallmark.baselines import TrainingBounds
    from hallmark.comparison import calibrate_fitted, evaluate_fitted
    from hallmark.contracts import Record
    from hallmark.selection import bind_guard

    guard = runtime[0]
    bounds = TrainingBounds(
        policy_id="fixture.guard", max_rows=16, max_prompt_bytes=32768, max_total_bytes=65536
    )
    fitted = bind_guard(guard, bounds, expected_runtime=guard.identity)

    def row(name, split, prompt, label):
        return Record(
            schema_id="hallmark.dataset-record/1",
            record_id=name,
            group_id=name,
            family_id="fixture",
            source_id="fixture",
            source_revision="1" * 64,
            license_id="fixture",
            policy_id=bounds.policy_id,
            split=split,
            language="en",
            prompt=prompt,
            response="",
            label=label,
        )

    calibration = (row("c0", "calibration", "hello", 0), row("c1", "calibration", "ALERT", 1))
    test = (row("t0", "test", "hello hello", 0), row("t1", "test", "ALERT hello", 1))
    pin = fitted.record["identity"]
    frozen = calibrate_fitted(fitted, calibration, expected_fit=pin, target_fpr="0.01")
    result = evaluate_fitted(
        fitted, frozen, test, expected_fit=pin, expected_calibration=frozen.identity()
    )
    assert [r["block"] for r in result["predictions"]] == [False, True]
    assert result["quality_claim"] is False
    for rows in (test, tuple(r.model_copy(update={"split": "train"}) for r in calibration)):
        with pytest.raises(WireError):
            calibrate_fitted(fitted, rows, expected_fit=pin, target_fpr="0.01")
    with pytest.raises(WireError):
        evaluate_fitted(fitted, frozen, test, expected_fit=pin, expected_calibration="0" * 64)
    with pytest.raises(WireError):
        evaluate_fitted(
            fitted,
            frozen,
            (test[0].model_copy(update={"prompt": "hello"}), test[1]),
            expected_fit=pin,
            expected_calibration=frozen.identity(),
        )
    guard.record["precision"] = "changed"
    with pytest.raises(WireError):
        calibrate_fitted(fitted, calibration, expected_fit=pin, target_fpr="0.01")


@pytest.mark.parametrize("mode", ["valid", "pin", "invalid", "existing"])
def test_probe_command_pins_inputs_and_preserves_outputs(runtime, tmp_path, mode):
    import hashlib
    import subprocess
    import sys

    guard, assets, _ = runtime
    spec_file, inputs_file, output = (
        tmp_path / "spec.json",
        tmp_path / "inputs.json",
        tmp_path / "out",
    )
    spec_file.write_text(guard.spec.model_dump_json())
    data = {
        "schema_id": "hallmark/guard-probes/1",
        "fixture_only": True,
        "prompts": ["hello", "ALERT"],
    }
    if mode == "invalid":
        data["PRIVATE_SENTINEL"] = True
    inputs_file.write_text(json.dumps(data))
    pin = hashlib.sha256(inputs_file.read_bytes()).hexdigest()
    if mode == "existing":
        output.mkdir()
        (output / "keep").write_text("unchanged")
    command = [
        sys.executable,
        str(ROOT / "scripts/run_guard.py"),
        "--assets",
        str(assets),
        "--spec",
        str(spec_file),
        "--expected-spec",
        guard.spec.identity(),
        "--inputs",
        str(inputs_file),
        "--expected-inputs",
        "0" * 64 if mode == "pin" else pin,
        "--output",
        str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=15)
    if mode == "valid":
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["passed"]
        assert json.loads((output / "score-01.json").read_text())["score"] == 2.0
        assert not (output / "failure.json").exists()
    else:
        assert result.returncode != 0 and not result.stdout
        assert "PRIVATE_SENTINEL" not in result.stderr and str(tmp_path) not in result.stderr
        assert not (output / "result.json").exists()
        if mode == "existing":
            assert (output / "keep").read_text() == "unchanged"
