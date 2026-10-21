"""Execute a tiny authored ONNX graph through the optional installed guard runtime."""

import hashlib
import json
import tempfile
from pathlib import Path

from hallmark.guard import GuardSpec, LocalGuard


def fixture(root):
    from onnx import TensorProto, helper
    from tokenizers import Tokenizer, models, pre_tokenizers

    root.mkdir()
    tokenizer = Tokenizer(
        models.WordLevel(
            {"[PAD]": 0, "[CLS]": 1, "[SEP]": 2, "[UNK]": 3, "hello": 4, "ALERT": 5, "é": 6},
            unk_token="[UNK]",
        )
    )
    tokenizer.pre_tokenizer = pre_tokenizers.WhitespaceSplit()
    # Deliberately unsafe defaults: the adapter must disable both before encoding.
    tokenizer.enable_truncation(max_length=8)
    tokenizer.enable_padding(length=16, pad_id=0, pad_token="[PAD]")
    raw_tokenizer = tokenizer.to_str().encode()
    (root / "tokenizer.json").write_bytes(raw_tokenizer)
    nodes = [
        helper.make_node("Equal", ["input_ids", "marker"], ["matched"]),
        helper.make_node("Cast", ["matched"], ["float_match"], to=TensorProto.FLOAT),
        helper.make_node("Cast", ["attention_mask"], ["float_mask"], to=TensorProto.FLOAT),
        helper.make_node("Mul", ["float_match", "float_mask"], ["masked"]),
        helper.make_node("ReduceSum", ["masked"], ["positive"], axes=[1], keepdims=1),
        helper.make_node("Neg", ["positive"], ["negative"]),
        helper.make_node("Concat", ["negative", "positive"], ["logits"], axis=1),
    ]
    graph = helper.make_graph(
        nodes,
        "authored-marker-only",
        [
            helper.make_tensor_value_info(name, TensorProto.INT64, ["batch", "sequence"])
            for name in ("input_ids", "attention_mask")
        ],
        [helper.make_tensor_value_info("logits", TensorProto.FLOAT, ["batch", 2])],
        [helper.make_tensor("marker", TensorProto.INT64, [1], [5])],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 12)], ir_version=7)
    raw_model = model.SerializeToString()
    (root / "model.onnx").write_bytes(raw_model)
    return GuardSpec(
        schema_id="hallmark/guard-spec/1",
        model_sha256=hashlib.sha256(raw_model).hexdigest(),
        model_bytes=len(raw_model),
        tokenizer_sha256=hashlib.sha256(raw_tokenizer).hexdigest(),
        tokenizer_bytes=len(raw_tokenizer),
        max_prompt_bytes=32768,
        sequence_tokens=512,
        vocabulary_size=7,
        threads=1,
    )


def check(directory):
    root = directory / "assets"
    spec = fixture(root)
    guard = LocalGuard(root, spec, expected_spec=spec.identity())
    prompts = ("", "é hello", "hello " * 510 + "ALERT", "hello " * 5460 + "ALERT!!!")
    results = [guard.score(p) for p in prompts]
    assert [r["score"] for r in results[:3]] == [0.0, 0.0, 2.0]
    assert [len(r["chunks"]) for r in results[:3]] == [1, 1, 2]
    assert results[2]["chunks"][1]["logits"] == [-1.0, 1.0]
    assert results[3]["prompt_bytes"] == 32768
    assert all(r["chunks"][-1]["stop"] == r["token_count"] for r in results)
    assert results == [guard.score(p) for p in prompts]
    return {"schema_id": "hallmark/guard-fixture-result/1", "passed": True, "quality_claim": False}


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="hallmark-guard-fixture-") as directory:
        print(json.dumps(check(Path(directory))))
