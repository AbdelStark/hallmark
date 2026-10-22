"""Bounded byte CNN research candidate; exports the existing exact integer DAG.

shortcut: one frozen 96-byte profile, no chunk-boundary context; qualify another
profile before admitting longer inputs. This module does not enroll a backend.
"""

import hashlib
import importlib
import json
import os
import platform
import sys
from pathlib import Path

from hallmark.classifier_manifest import (
    ArithmeticProfile,
    ClassifierManifest,
    InputProfile,
    NodeSpec,
    TensorSpec,
)
from hallmark.contracts import Record
from hallmark.integer_encoder import BYTE_TOKENIZER, EncoderConstants, EncoderProgram
from hallmark.integer_graph import IntegerGraph
from hallmark.manifests import FileRef
from hallmark.wire import encode

CAPACITY, KERNEL, EMBEDDING = 96, 24, 4
FIT = {"epochs": 200, "learning_rate": 0.025, "beta1": 0.9, "beta2": 0.999, "epsilon": 1e-8}


def shapes(channels):
    if type(channels) is not int or channels not in (8, 32):
        raise ValueError("unadmitted CNN width")
    return {
        "embedding": (256, 4),
        "kernel": (channels, 96),
        "bias": (channels,),
        "head": (1, channels),
        "out": (1,),
    }


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def runtime():
    import numpy as np

    extension = Path(importlib.import_module("numpy._core._multiarray_umath").__file__)
    return dict(
        python=sys.version,
        numpy=np.__version__,
        platform=platform.platform(),
        numpy_extension_sha256=hashlib.sha256(extension.read_bytes()).hexdigest(),
        threads={
            k: os.environ.get(k)
            for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
        },
        device="cpu",
        dtype="float64",
    )


def arrays(parameters):
    import numpy as np

    if type(parameters) is not dict or parameters.keys() != shapes(8).keys():
        raise ValueError("invalid CNN parameter inventory")
    expected = shapes(len(parameters["bias"]))
    result = {k: np.asarray(v, dtype=np.float64) for k, v in parameters.items()}
    if any(v.shape != expected[k] or not np.isfinite(v).all() for k, v in result.items()):
        raise ValueError("invalid CNN parameter shape or value")
    return result


def inputs(prompts):
    import numpy as np

    if not 1 <= len(prompts) <= 512:
        raise ValueError("invalid CNN batch size")
    tokens = np.zeros((len(prompts), CAPACITY), dtype=np.int64)
    mask = np.zeros_like(tokens)
    for i, prompt in enumerate(prompts):
        if type(prompt) is not str:
            raise ValueError("invalid CNN text")
        raw = prompt.encode("utf-8")
        if len(raw) > CAPACITY:
            raise ValueError("CNN input exceeds admitted byte capacity")
        tokens[i, : len(raw)] = list(raw)
        mask[i, : len(raw)] = 1
    return tokens, mask


def windows():
    import numpy as np

    positions = np.arange(CAPACITY)[:, None] - np.arange(KERNEL - 1, -1, -1)
    return positions.clip(0), (positions >= 0).astype(np.int64)


def forward(p, tokens, mask):
    import numpy as np

    index, causal = windows()
    embedded = p["embedding"][tokens] * mask[:, :, None]
    x = (embedded[:, index] * causal[None, :, :, None]).reshape(len(tokens), CAPACITY, -1)
    z = x @ p["kernel"].T + p["bias"]
    h = np.maximum(z, 0) * mask[:, :, None]
    argmax = h.argmax(axis=1)
    pooled = h.max(axis=1)
    score = (pooled @ p["head"].T + p["out"])[:, 0]
    return score, (x, z, pooled, argmax)


def gradient(p, tokens, mask, labels):
    import numpy as np

    channels = len(p["bias"])
    scores, (x, z, pooled, argmax) = forward(p, tokens, mask)
    loss = float(np.mean(np.logaddexp(0, scores) - labels * scores))
    delta = (1 / (1 + np.exp(-np.clip(scores, -700, 700))) - labels) / len(tokens)
    dpool = delta[:, None] * p["head"]
    dz = np.zeros_like(z)
    dz[np.arange(len(tokens))[:, None], argmax, np.arange(channels)] = dpool
    dz *= (z > 0) * mask[:, :, None]
    g = {"head": delta[None, :] @ pooled, "out": np.array([delta.sum()])}
    g["kernel"] = dz.reshape(-1, channels).T @ x.reshape(-1, KERNEL * EMBEDDING)
    g["bias"] = dz.sum(axis=(0, 1))
    dx = (dz @ p["kernel"]).reshape(len(tokens), CAPACITY, KERNEL, EMBEDDING)
    index, causal = windows()
    de = np.zeros((len(tokens), CAPACITY, EMBEDDING))
    for k in range(KERNEL):
        np.add.at(
            de,
            (np.arange(len(tokens))[:, None], index[:, k]),
            dx[:, :, k] * causal[None, :, k, None],
        )
    de *= mask[:, :, None]
    g["embedding"] = np.zeros_like(p["embedding"])
    np.add.at(g["embedding"], tokens.reshape(-1), de.reshape(-1, EMBEDDING))
    return loss, g


def train(rows, seed, *, channels=8, stop=200, checkpoint=None):
    """Train-only full-batch Adam; exact same-environment resume, no test access."""
    import numpy as np

    if (
        type(seed) is not int
        or seed not in (17, 29, 43)
        or type(stop) is not int
        or not 0 <= stop <= 200
    ):
        raise ValueError("unadmitted training configuration")
    shape_map = shapes(channels)
    if not 2 <= len(rows) <= 512 or any(type(r) is not Record for r in rows):
        raise ValueError("invalid training records")
    rows = tuple(sorted(rows, key=lambda r: r.record_id))
    if (
        any(
            r.split != "train" or r.response or r.policy_id != "synthetic-run-quote-scope-v1"
            for r in rows
        )
        or len({r.record_id for r in rows}) != len(rows)
        or {r.label for r in rows} != {0, 1}
    ):
        raise ValueError("training split, policy or record identity mismatch")
    tokens, mask = inputs([r.prompt for r in rows])
    labels = np.asarray([r.label for r in rows], dtype=np.float64)
    identity = digest(
        dict(
            rows=[r.model_dump() for r in rows],
            seed=seed,
            channels=channels,
            fit=FIT,
            source=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            runtime=runtime(),
        )
    )
    rng = np.random.default_rng(seed)
    p = {
        k: rng.normal(0, 0.15, shape) if k in ("embedding", "kernel", "head") else np.zeros(shape)
        for k, shape in shape_map.items()
    }
    m, v = ({k: np.zeros(shape) for k, shape in shape_map.items()} for _ in range(2))
    epoch, history = 0, []
    if checkpoint is not None:
        if (
            checkpoint.keys()
            != {"schema_id", "identity", "epoch", "parameters", "m", "v", "history"}
            or checkpoint["schema_id"] != "hallmark.contextual-checkpoint/1"
            or checkpoint["identity"] != identity
        ):
            raise ValueError("resume identity mismatch")
        epoch = checkpoint["epoch"]
        if type(epoch) is not int or not 0 <= epoch <= stop:
            raise ValueError("invalid resume epoch")
        p, m, v = (arrays(checkpoint[k]) for k in ("parameters", "m", "v"))
        if any(x["bias"].shape != (channels,) for x in (p, m, v)):
            raise ValueError("resume architecture mismatch")
        history = list(checkpoint["history"])
        if (
            len(history) != epoch
            or any(type(x) is not float or not np.isfinite(x) or x < 0 for x in history)
            or any((x < 0).any() for x in v.values())
        ):
            raise ValueError("invalid resume optimizer state")
    start = epoch + 1
    for epoch in range(start, stop + 1):
        loss, grads = gradient(p, tokens, mask, labels)
        history.append(loss)
        for k, g in grads.items():
            m[k] = 0.9 * m[k] + 0.1 * g
            v[k] = 0.999 * v[k] + 0.001 * g * g
            p[k] -= 0.025 * (m[k] / (1 - 0.9**epoch)) / (np.sqrt(v[k] / (1 - 0.999**epoch)) + 1e-8)
        if not all(np.isfinite(x).all() for x in (*p.values(), *m.values(), *v.values())):
            raise ValueError("nonfinite training state")
    return dict(
        schema_id="hallmark.contextual-checkpoint/1",
        identity=identity,
        epoch=stop,
        parameters={k: x.tolist() for k, x in p.items()},
        m={k: x.tolist() for k, x in m.items()},
        v={k: x.tolist() for k, x in v.items()},
        history=history,
    )


def quantize(parameters):
    import numpy as np

    p = arrays(parameters)
    values, fractions = {}, {}
    for name in ("embedding", "kernel", "head"):
        allowed = [f for f in range(17) if np.max(np.abs(np.rint(p[name] * 2**f))) <= 127]
        if not allowed:
            raise ValueError("CNN weight cannot fit int8 without clipping")
        fractions[name] = max(allowed)
        values[name] = np.rint(p[name] * 2 ** fractions[name]).astype(np.int64).tolist()
    for name, fraction in (
        ("bias", fractions["embedding"] + fractions["kernel"]),
        ("out", 8 + fractions["head"]),
    ):
        value = np.rint(p[name] * 2**fraction)
        if np.max(np.abs(value)) >= 2**31:
            raise ValueError("CNN bias cannot fit int32")
        values[name] = value.astype(np.int64).tolist()
    return dict(schema_id="hallmark.contextual-quantization/1", values=values, fractions=fractions)


def integer_scores(q, prompts):
    """Vectorized integer oracle, separate from the existing scalar DAG executor."""
    import numpy as np

    p = {k: np.asarray(v, dtype=np.int64) for k, v in q["values"].items()}
    fractions = q["fractions"]
    tokens, mask = inputs(prompts)
    index, causal = windows()
    embedded = p["embedding"][tokens] * mask[:, :, None]
    x = (embedded[:, index] * causal[None, :, :, None]).reshape(len(tokens), CAPACITY, -1)

    def rounded(a, shift):
        if shift <= 0:
            return a * 2 ** (-shift)
        divisor = 2**shift
        quotient, remainder = np.divmod(a, divisor)
        return quotient + (
            (2 * remainder > divisor) | ((2 * remainder == divisor) & (quotient % 2 == 1))
        )

    z = rounded(x @ p["kernel"].T + p["bias"], fractions["embedding"] + fractions["kernel"] - 8)
    pooled = (np.maximum(z, 0) * mask[:, :, None]).max(axis=1)
    return rounded(pooled @ p["head"].T + p["out"], fractions["head"])[:, 0].tolist()


def export(q, *, threshold=0):
    """Lower the complete fixed profile to already supported, range-checked operators."""
    import numpy as np

    p = arrays(q["values"])
    if (
        q.keys() != {"schema_id", "values", "fractions"}
        or q["schema_id"] != "hallmark.contextual-quantization/1"
        or q["fractions"].keys() != {"embedding", "kernel", "head"}
    ):
        raise ValueError("invalid quantization inventory")
    if any(type(f) is not int or not 0 <= f <= 16 for f in q["fractions"].values()) or any(
        (x != np.rint(x)).any() or np.abs(x).max() > (127 if k in q["fractions"] else 2**31 - 1)
        for k, x in p.items()
    ):
        raise ValueError("invalid quantization range")
    tensors, nodes, constants, parameters = {}, [], {}, {}

    def ref(path, raw):
        return FileRef(path=path, size=len(raw), sha256=hashlib.sha256(raw).digest())

    def tensor(name, shape, low, high, fraction=0):
        tensors[name] = TensorSpec(
            name=name,
            shape=shape,
            minimum=int(low),
            maximum=int(high),
            signed_bits=32,
            fractional_bits=fraction,
        )
        return tensors[name]

    def constant(name, value, fraction=0):
        value = np.asarray(value, dtype=np.int64)
        constants[name] = tuple(int(x) for x in value.reshape(-1))
        return tensor(name, value.shape, value.min(), value.max(), fraction)

    def node(name, op, sources, shape, low, high, fraction=0, **options):
        raw = encode(dict(schema_id="hallmark/operator-parameters/1", op=op, **options))
        path = f"params/{hashlib.sha256(raw).hexdigest()}.cbor"
        parameters[path] = raw
        nodes.append(
            NodeSpec(id=name, op=op, inputs=sources, output=name, parameters=ref(path, raw))
        )
        return tensor(name, shape, low, high, fraction)

    def affine(name, source, weight, bias, wf, out_fraction=8):
        a, w, b = (
            tensors[source],
            constant(name + "-w", weight, wf),
            constant(name + "-b", bias, tensors[source].fractional_bits + wf),
        )
        products = [i * j for i in (a.minimum, a.maximum) for j in (w.minimum, w.maximum)]
        low, high = min(products) * a.shape[-1] + b.minimum, max(products) * a.shape[-1] + b.maximum
        from fractions import Fraction

        scale = Fraction(2**out_fraction, 2 ** (a.fractional_bits + wf))
        return node(
            name,
            "affine",
            (source, w.name, b.name),
            a.shape[:-1] + (w.shape[0],),
            round(low * scale),
            round(high * scale),
            out_fraction,
        )

    tensor("tokens", (CAPACITY,), 0, 255)
    tensor("mask", (CAPACITY,), 0, 1)
    e = constant("embedding", p["embedding"], q["fractions"]["embedding"])
    node(
        "embedded",
        "gather",
        ("embedding", "tokens"),
        (CAPACITY, EMBEDDING),
        e.minimum,
        e.maximum,
        e.fractional_bits,
        axis=0,
    )
    node("row-mask", "reshape", ("mask",), (CAPACITY, 1), 0, 1)
    low, high = min(0, e.minimum), max(0, e.maximum)
    node(
        "active",
        "multiply",
        ("embedded", "row-mask"),
        (CAPACITY, EMBEDDING),
        low,
        high,
        e.fractional_bits,
        mode="elementwise",
    )
    index, causal = windows()
    constant("window-index", index)
    constant("causal-mask", causal[:, :, None])
    node(
        "window-values",
        "gather",
        ("active", "window-index"),
        (CAPACITY, KERNEL, EMBEDDING),
        low,
        high,
        e.fractional_bits,
        axis=0,
    )
    node(
        "causal-values",
        "multiply",
        ("window-values", "causal-mask"),
        (CAPACITY, KERNEL, EMBEDDING),
        low,
        high,
        e.fractional_bits,
        mode="elementwise",
    )
    node(
        "flat",
        "reshape",
        ("causal-values",),
        (CAPACITY, KERNEL * EMBEDDING),
        low,
        high,
        e.fractional_bits,
    )
    z = affine("convolution", "flat", p["kernel"], p["bias"], q["fractions"]["kernel"])
    node("relu", "relu", ("convolution",), z.shape, max(0, z.minimum), max(0, z.maximum), 8)
    node(
        "pooled",
        "masked-reduce",
        ("relu", "row-mask"),
        (len(p["bias"]),),
        0,
        max(0, z.maximum),
        8,
        axes=[0],
        keep_dims=False,
        reduction="max",
        empty_value=0,
    )
    # Expose score units as integers, as required by the classifier contract.
    affine("score", "pooled", p["head"] * 256, p["out"] * 256, q["fractions"]["head"], 0)
    arithmetic = ArithmeticProfile(
        schema_id="hallmark/arithmetic/1",
        tensors=tuple(tensors.values()),
        nodes=tuple(nodes),
        output="score",
    )
    graph = IntegerGraph(arithmetic, parameters=parameters, constants=constants)
    tokenizer = ref("tokenizer/bytes.json", BYTE_TOKENIZER)
    profile = InputProfile(
        schema_id="hallmark/input-profile/1",
        encoding="token-ids",
        tokenizer_files=(tokenizer,),
        prefix_tokens=(),
        suffix_tokens=(),
        chunk_size=CAPACITY,
        overlap=0,
        max_units=CAPACITY,
        padding_id=0,
        padding_side="right",
    )
    weights = EncoderConstants(schema_id="hallmark/encoder-constants/1", tensors=constants).encode()
    program = EncoderProgram(
        schema_id="hallmark/encoder-program/1",
        input_profile=profile.identity(),
        arithmetic=arithmetic.identity(),
        weights=ref("weights/encoder.cbor", weights),
        tokenizer=tokenizer,
        token_input="tokens",
        mask_input="mask",
    )
    # No actual key or backend enrollment is implied by this software-only manifest.
    classifier = ClassifierManifest(
        schema_id="hallmark/classifier/1",
        kind="encoder",
        program=program.identity(),
        weights=program.weights.sha256,
        tokenizer=tokenizer.sha256,
        input_profile=profile.identity(),
        arithmetic=arithmetic.identity(),
        threshold=threshold,
        scope="prompt",
        labels=("synthetic-inert", "synthetic-run-forbidden"),
        backend=bytes(32),
        verifier_key=bytes(32),
        setup=bytes(32),
    )
    return dict(
        classifier=classifier,
        program=program,
        profile=profile,
        arithmetic=arithmetic,
        weights=weights,
        tokenizer=BYTE_TOKENIZER,
        parameters=parameters,
        graph=graph,
    )


def graph_scores(exported, prompts):
    tokens, masks = inputs(prompts)
    return [
        exported["graph"].evaluate({"tokens": tuple(map(int, t)), "mask": tuple(map(int, m))})[
            "score"
        ][0]
        for t, m in zip(tokens, masks, strict=True)
    ]
