"""Pinned local ONNX guard inference; no downloads, labels, fitting or proof claims."""

import hashlib
import importlib
import importlib.metadata
import math
import os
import platform
import stat
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field

from hallmark.contracts import Digest
from hallmark.integrity import commitment
from hallmark.mlp_training import _TrainingRecord
from hallmark.wire import WireError


class GuardSpec(_TrainingRecord):
    schema_id: Literal["hallmark/guard-spec/1"]
    model_sha256: Digest
    model_bytes: Annotated[int, Field(ge=1, le=800 * 1024 * 1024)]
    tokenizer_sha256: Digest
    tokenizer_bytes: Annotated[int, Field(ge=1, le=16 * 1024 * 1024)]
    max_prompt_bytes: Annotated[int, Field(ge=1, le=32768)]
    sequence_tokens: Annotated[int, Field(ge=3, le=512)]
    vocabulary_size: Annotated[int, Field(ge=4, le=128100)]
    threads: Annotated[int, Field(ge=1, le=4)]


def _pinned_bytes(path: Path, size: int, expected: str) -> bytes:
    # The root is caller-owned; never reopen a verified pathname in a model loader.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != size:
            raise WireError("INPUT_INVALID")
        raw = handle.read(size + 1)
        after = os.fstat(handle.fileno())
    if (
        len(raw) != size
        or hashlib.sha256(raw).hexdigest() != expected
        or (before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_nlink)
        != (after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_nlink)
    ):
        raise WireError("INPUT_INVALID")
    return raw


def _inspect_graph(raw: bytes, onnx: Any) -> dict[str, Any]:
    model = onnx.load_model_from_string(raw)
    if model.functions or model.training_info or any(o.domain for o in model.opset_import):
        raise WireError("INPUT_INVALID")
    stack = [model.graph]
    nodes = 0
    while stack:
        message = stack.pop()
        kind = message.DESCRIPTOR.full_name
        if kind == "onnx.TensorProto" and (message.external_data or message.data_location == 1):
            raise WireError("INPUT_INVALID")
        if kind == "onnx.NodeProto":
            nodes += 1
            if message.domain or nodes > 20000:
                raise WireError("INPUT_INVALID")
        for field, value in message.ListFields():
            if field.message_type is not None:
                stack.extend(value if field.is_repeated else [value])
    onnx.checker.check_model(model)
    return {"nodes": nodes, "opsets": [o.version for o in model.opset_import]}


class LocalGuard:
    """One trusted-process session loaded from caller-pinned bytes, never a pickle."""

    def __init__(self, root: Path, spec: GuardSpec, *, expected_spec: str) -> None:
        if type(spec) is not GuardSpec or type(expected_spec) is not str:
            raise WireError("INPUT_INVALID")
        self.spec = spec._validated()
        if self.spec.identity() != expected_spec:
            raise WireError("INPUT_INVALID")
        model = _pinned_bytes(root / "model.onnx", spec.model_bytes, spec.model_sha256)
        tokenizer = _pinned_bytes(
            root / "tokenizer.json", spec.tokenizer_bytes, spec.tokenizer_sha256
        )
        onnx = importlib.import_module("onnx")
        ort = importlib.import_module("onnxruntime")
        tokens = importlib.import_module("tokenizers")
        self._np = importlib.import_module("numpy")
        graph = _inspect_graph(model, onnx)
        self._tokenizer = tokens.Tokenizer.from_str(tokenizer.decode("utf-8"))
        self._tokenizer.no_truncation()
        self._tokenizer.no_padding()
        if (
            any(
                self._tokenizer.token_to_id(name) != index
                for name, index in (("[PAD]", 0), ("[CLS]", 1), ("[SEP]", 2))
            )
            or self._tokenizer.get_vocab_size() > spec.vocabulary_size
        ):
            raise WireError("INPUT_INVALID")
        ort.disable_telemetry_events()
        options = ort.SessionOptions()
        options.intra_op_num_threads = spec.threads
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        options.add_session_config_entry("session.intra_op.allow_spinning", "0")
        options.add_session_config_entry("session.inter_op.allow_spinning", "0")
        self._session = ort.InferenceSession(
            model, sess_options=options, providers=["CPUExecutionProvider"]
        )
        inputs, outputs = self._session.get_inputs(), self._session.get_outputs()
        if (
            {i.name for i in inputs} != {"input_ids", "attention_mask"}
            or any(i.type != "tensor(int64)" or len(i.shape) != 2 for i in inputs)
            or len(outputs) != 1
            or outputs[0].name != "logits"
            or outputs[0].type != "tensor(float)"
            or len(outputs[0].shape) != 2
            or outputs[0].shape[1] != 2
        ):
            raise WireError("INPUT_INVALID")
        self.record = {
            "schema_id": "hallmark/guard-runtime/1",
            "spec": expected_spec,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "packages": {
                name: importlib.metadata.version(name)
                for name in ("onnx", "onnxruntime", "tokenizers", "numpy", "protobuf")
            },
            "binaries": {
                name: {
                    str(file): hashlib.sha256(
                        Path(str(dist.locate_file(file))).read_bytes()
                    ).hexdigest()
                    for file in dist.files or ()
                    if str(file).endswith((".so", ".dylib", ".pyd", ".dll"))
                }
                for name in ("onnx", "onnxruntime", "tokenizers", "numpy", "protobuf")
                for dist in (importlib.metadata.distribution(name),)
            },
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "providers": self._session.get_providers(),
            "graph": graph,
            "precision": "float32 logits, float64 margin",
            "aggregation": "max-over-all-contiguous-content-chunks",
            "normalization": "pinned-tokenizer; lossy; no truncation or padding",
            "optimizer": "none-frozen-pretrained",
            "resume": "not-applicable",
            "pretraining_contamination_reviewed": False,
        }
        self.identity = commitment("guard-runtime", self.record)

    def tokens(self, prompt: str) -> tuple[int, ...]:
        if type(prompt) is not str:
            raise WireError("INPUT_INVALID")
        try:
            raw = prompt.encode("utf-8")
        except UnicodeError:
            raise WireError("INPUT_INVALID") from None
        if len(raw) > self.spec.max_prompt_bytes:
            raise WireError("LIMIT_EXCEEDED")
        encoded = self._tokenizer.encode(prompt, add_special_tokens=False)
        ids = tuple(encoded.ids)
        if encoded.overflowing or len(ids) > 131072:
            raise WireError("LIMIT_EXCEEDED")
        if any(type(i) is not int or not 0 <= i < self.spec.vocabulary_size for i in ids):
            raise WireError("INPUT_INVALID")
        return ids

    def score(self, prompt: str) -> dict[str, Any]:
        ids = self.tokens(prompt)
        width = self.spec.sequence_tokens - 2
        count = max(1, (len(ids) + width - 1) // width)
        if count > 1024:
            raise WireError("LIMIT_EXCEEDED")
        samples: list[dict[str, Any]] = []
        for start in range(0, max(1, len(ids)), width):
            content = ids[start : start + width]
            batch = self._np.asarray([[1, *content, 2]], dtype=self._np.int64)
            values = self._session.run(
                ["logits"], {"input_ids": batch, "attention_mask": self._np.ones_like(batch)}
            )[0]
            if values.shape != (1, 2) or values.dtype != self._np.float32:
                raise WireError("INPUT_INVALID")
            logits = [float(v) for v in values[0]]
            margin = logits[1] - logits[0]
            if not all(math.isfinite(v) for v in (*logits, margin)):
                raise WireError("INPUT_INVALID")
            samples.append({"start": start, "stop": start + len(content), "logits": logits})
        return {
            "schema_id": "hallmark/guard-score/1",
            "runtime": self.identity,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "prompt_bytes": len(prompt.encode()),
            "token_count": len(ids),
            "tokens": commitment("guard-content-tokens", ids),
            "chunks": samples,
            "score": max(s["logits"][1] - s["logits"][0] for s in samples),
            "quality_claim": False,
        }
