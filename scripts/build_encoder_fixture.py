"""Freeze an owned synthetic complete encoder and independent rational/Decimal traces."""

import argparse
import hashlib
import json
import math
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

from hallmark.classifier_manifest import (
    ArithmeticProfile,
    ClassifierManifest,
    InputProfile,
    NodeSpec,
    TensorSpec,
)
from hallmark.integer_encoder import BYTE_TOKENIZER, EncoderConstants, EncoderProgram
from hallmark.manifests import FileRef
from hallmark.openings import TranscriptOpening
from hallmark.wire import encode

EMBEDDING = ((0, 0), (1, -1), (-1, 1), (1, 1))
QUERY = ((1, 0), (0, 1))
KEY = ((0, 1), (1, 0))
VALUE = ((1, 0), (0, -1))
HIDDEN = ((1, 1), (1, -1), (-1, 0))
OUTPUT = ((1, -1, 2), (-1, 1, 1))
HEAD = ((2, -1), (-1, 2))
EXPONENTIAL = tuple(1 if n < 0 else 2 ** (n // 8) for n in range(-16, 33))
INVERSE = (0, *(round(Fraction(256, n)) for n in range(1, 33)))


def file_ref(path, raw):
    return FileRef(path=path, size=len(raw), sha256=hashlib.sha256(raw).digest())


def inverse_sqrt(n):
    """Nearest integer to 256/sqrt(n), using only exact integer comparisons."""
    value = math.isqrt(65536 // n)
    twice = n * (2 * value + 1) ** 2
    return value + (4 * 65536 > twice or (4 * 65536 == twice and value % 2 == 1))


def normalization(a, b):
    mean = round(Fraction(a + b, 2))
    a, b = a - mean, b - mean
    variance = round(Fraction(a * a + b * b, 2))
    inverse = inverse_sqrt(variance + 1)
    return a * inverse + 256, -2 * b * inverse - 256


def export(*, padding=0, prefix=(), suffix=()):
    """Compile exactly this two-token graph, with no fit, checkpoint or enrollment."""
    tensors, nodes, constants, parameters = {}, [], {}, {}

    def tensor(name, shape, low, high, fraction=0):
        value = TensorSpec(
            name=name,
            shape=shape,
            signed_bits=32,
            fractional_bits=fraction,
            minimum=low,
            maximum=high,
        )
        tensors[name] = value
        return value

    def constant(name, shape, values, fraction=0):
        values = tuple(values)
        constants[name] = values
        return tensor(name, shape, min(values), max(values), fraction)

    def node(name, op, inputs, shape, low, high, fraction=0, **options):
        raw = encode(
            {
                "schema_id": "hallmark/operator-parameters/1",
                "op": op,
                **{k: list(v) if isinstance(v, tuple) else v for k, v in options.items()},
            }
        )
        path = f"params/{hashlib.sha256(raw).hexdigest()}.cbor"
        parameters[path] = raw
        nodes.append(
            NodeSpec(id=name, op=op, inputs=inputs, output=name, parameters=file_ref(path, raw))
        )
        return tensor(name, shape, low, high, fraction)

    def affine(name, source, weights, bias, weight_fraction=0, out_fraction=0):
        a = tensors[source]
        width = len(weights)
        w = constant(
            name + "-weights",
            (width, a.shape[-1]),
            (x for row in weights for x in row),
            weight_fraction,
        )
        b = constant(name + "-bias", (width,), bias, a.fractional_bits + weight_fraction)
        products = [x * y for x in (a.minimum, a.maximum) for y in (w.minimum, w.maximum)]
        low, high = min(products) * a.shape[-1] + b.minimum, max(products) * a.shape[-1] + b.maximum
        scale = Fraction(2**out_fraction, 2 ** (a.fractional_bits + weight_fraction))
        return node(
            name,
            "affine",
            (source, w.name, b.name),
            a.shape[:-1] + (width,),
            round(low * scale),
            round(high * scale),
            out_fraction,
        )

    def norm(name, source):
        # shortcut: pair tables cover two features; qualify a new lowering for wider graphs.
        a = tensors[source]
        assert a.fractional_bits == 0
        low, high = a.minimum, a.maximum
        width = high - low + 1
        pairs = [normalization(x, y) for x in range(low, high + 1) for y in range(low, high + 1)]
        table = constant(
            name + "-table", (2 * width * width,), (p[i] for i in range(2) for p in pairs), 8
        )
        constant(name + "-left-index", (1,), (0,))
        constant(name + "-right-index", (1,), (1,))
        node(name + "-left", "gather", (source, name + "-left-index"), (2, 1), low, high, axis=1)
        node(name + "-right", "gather", (source, name + "-right-index"), (2, 1), low, high, axis=1)
        constant(name + "-width", (1,), (width,))
        constant(name + "-offset", (1,), (-low * (width + 1),))
        constant(name + "-feature-offset", (1, 2), (0, width * width))
        node(
            name + "-scaled-left",
            "multiply",
            (name + "-left", name + "-width"),
            (2, 1),
            low * width,
            high * width,
            mode="elementwise",
        )
        node(
            name + "-pair",
            "add",
            (name + "-scaled-left", name + "-right"),
            (2, 1),
            low * (width + 1),
            high * (width + 1),
        )
        node(
            name + "-index", "add", (name + "-pair", name + "-offset"), (2, 1), 0, width * width - 1
        )
        node(
            name + "-indices",
            "add",
            (name + "-index", name + "-feature-offset"),
            (2, 2),
            0,
            2 * width * width - 1,
        )
        return node(
            name,
            "lookup",
            (table.name, name + "-indices"),
            (2, 2),
            table.minimum,
            table.maximum,
            8,
            offset=0,
        )

    tensor("tokens", (2,), 0, 255)
    tensor("mask", (2,), 0, 1)
    constant("embedding-table", (256, 2), (x for b in range(256) for x in EMBEDDING[b % 4]))
    constant("positions", (2, 2), (0, 0, 1, 0))
    node("token-embedding", "gather", ("embedding-table", "tokens"), (2, 2), -1, 1, axis=0)
    node("embedding", "add", ("token-embedding", "positions"), (2, 2), -1, 2)
    affine("query", "embedding", QUERY, (0, 0))
    affine("key", "embedding", KEY, (0, 0))
    affine("value", "embedding", VALUE, (0, 0))
    node("key-transpose", "transpose", ("key",), (2, 2), -2, 4, permutation=(1, 0))
    node("scores", "multiply", ("query", "key-transpose"), (2, 2), -16, 32, mode="matmul")
    constant("exponential-table", (49,), EXPONENTIAL)
    node("exponential", "lookup", ("exponential-table", "scores"), (2, 2), 1, 16, offset=16)
    node("key-mask", "reshape", ("mask",), (1, 2), 0, 1)
    node("masked", "multiply", ("exponential", "key-mask"), (2, 2), 0, 16, mode="elementwise")
    constant("ones", (1,), (1,))
    node(
        "denominator",
        "masked-reduce",
        ("masked", "ones"),
        (2, 1),
        0,
        32,
        axes=(1,),
        keep_dims=True,
        reduction="sum",
        empty_value=0,
    )
    constant("inverse-table", (33,), INVERSE, 8)
    node("inverse", "lookup", ("inverse-table", "denominator"), (2, 1), 0, 256, 8, offset=0)
    node("normalized", "multiply", ("masked", "inverse"), (2, 2), 0, 4096, 8, mode="elementwise")
    node("attention", "multiply", ("normalized", "value"), (2, 2), -128, 128, mode="matmul")
    node("residual", "add", ("attention", "embedding"), (2, 2), -129, 130)
    n1 = norm("norm1", "residual")
    h = affine("hidden", n1.name, HIDDEN, (1, -1, 0), 1)
    node("activated", "relu", ("hidden",), (2, 3), max(0, h.minimum), max(0, h.maximum))
    out = affine("output", "activated", OUTPUT, (-1, 1), 1)
    node(
        "residual2",
        "add",
        ("norm1", "output"),
        (2, 2),
        round(Fraction(n1.minimum, 256) + out.minimum),
        round(Fraction(n1.maximum, 256) + out.maximum),
    )
    n2 = norm("norm2", "residual2")
    node("pool-mask", "reshape", ("mask",), (2, 1), 0, 1)
    node(
        "pool-sum",
        "masked-reduce",
        ("norm2", "pool-mask"),
        (2,),
        min(0, n2.minimum) * 2,
        max(0, n2.maximum) * 2,
        8,
        axes=(0,),
        keep_dims=False,
        reduction="sum",
        empty_value=0,
    )
    node(
        "pool-max",
        "masked-reduce",
        ("norm2", "pool-mask"),
        (2,),
        min(0, n2.minimum),
        max(0, n2.maximum),
        8,
        axes=(0,),
        keep_dims=False,
        reduction="max",
        empty_value=0,
    )
    node(
        "pooled",
        "add",
        ("pool-sum", "pool-max"),
        (2,),
        min(0, n2.minimum) * 3,
        max(0, n2.maximum) * 3,
        8,
    )
    affine("logits", "pooled", HEAD, (1, -1), 1)
    affine("score", "logits", ((-1, 1),), (0,))
    arithmetic = ArithmeticProfile(
        schema_id="hallmark/arithmetic/1",
        tensors=tuple(tensors.values()),
        nodes=tuple(nodes),
        output="score",
    )
    arithmetic.validate_parameters(parameters)
    tokenizer_ref = file_ref("tokenizer/bytes.json", BYTE_TOKENIZER)
    inputs = InputProfile(
        schema_id="hallmark/input-profile/1",
        encoding="token-ids",
        tokenizer_files=(tokenizer_ref,),
        prefix_tokens=prefix,
        suffix_tokens=suffix,
        chunk_size=2,
        overlap=0,
        max_units=32768,
        padding_id=padding,
        padding_side="right",
    )
    raw = EncoderConstants(schema_id="hallmark/encoder-constants/1", tensors=constants).encode()
    program = EncoderProgram(
        schema_id="hallmark/encoder-program/1",
        input_profile=inputs.identity(),
        arithmetic=arithmetic.identity(),
        weights=file_ref("weights/encoder.cbor", raw),
        tokenizer=tokenizer_ref,
        token_input="tokens",
        mask_input="mask",
    )
    classifier = ClassifierManifest(
        schema_id="hallmark/classifier/1",
        kind="encoder",
        program=program.identity(),
        weights=program.weights.sha256,
        tokenizer=tokenizer_ref.sha256,
        input_profile=inputs.identity(),
        arithmetic=arithmetic.identity(),
        threshold=2,
        scope="prompt",
        labels=("fixture-benign", "fixture-marker"),
        backend=b"b" * 32,
        verifier_key=b"k" * 32,
        setup=b"s" * 32,
    )
    return classifier, program, inputs, arithmetic, raw, BYTE_TOKENIZER, parameters


def oracle(tokens, masks, arithmetic):
    """Direct formulas; no graph executor, rescale helper or normalization table is used."""
    result = {}
    specs = {t.name: t for t in arithmetic.tensors}

    def record(name, rows):
        result[name] = tuple(x for row in rows for x in row)
        return rows

    def affine(rows, weights, bias, divisor=1):
        return [
            [
                round(Fraction(sum(x * w for x, w in zip(row, w, strict=True)) + b, divisor))
                for w, b in zip(weights, bias, strict=True)
            ]
            for row in rows
        ]

    def multiply(a, b):
        return [
            [sum(x * y for x, y in zip(row, col, strict=True)) for col in zip(*b, strict=True)]
            for row in a
        ]

    def norm(name, source, rows):
        low, high = specs[source].minimum, specs[source].maximum
        width = high - low + 1
        left = record(name + "-left", [[a] for a, b in rows])
        right = record(name + "-right", [[b] for a, b in rows])
        scaled = record(name + "-scaled-left", [[a[0] * width] for a in left])
        pair = record(name + "-pair", [[a[0] + b[0]] for a, b in zip(scaled, right, strict=True)])
        index = record(name + "-index", [[p[0] - low * (width + 1)] for p in pair])
        record(name + "-indices", [[p[0], p[0] + width * width] for p in index])
        out = []
        with localcontext() as ctx:
            ctx.prec = 80
            for a, b in rows:
                mean = int(((Decimal(a) + Decimal(b)) / 2).to_integral_value())
                a, b = a - mean, b - mean
                var = int((Decimal(a * a + b * b) / 2).to_integral_value())
                inv = int((Decimal(256) / Decimal(var + 1).sqrt()).to_integral_value())
                out.append([a * inv + 256, -2 * b * inv - 256])
        return record(name, out)

    emb = record("token-embedding", [list(EMBEDDING[t % 4]) for t in tokens])
    emb = record("embedding", [[a + (i == 1), b] for i, (a, b) in enumerate(emb)])
    q = record("query", affine(emb, QUERY, (0, 0)))
    k = record("key", affine(emb, KEY, (0, 0)))
    v = record("value", affine(emb, VALUE, (0, 0)))
    kt = record("key-transpose", [list(row) for row in zip(*k, strict=True)])
    scores = record("scores", multiply(q, kt))
    exp = record("exponential", [[1 if n < 0 else 2 ** (n // 8) for n in row] for row in scores])
    record("key-mask", [list(masks)])
    masked = record("masked", [[n * m for n, m in zip(row, masks, strict=True)] for row in exp])
    denom = record("denominator", [[sum(row)] for row in masked])
    inv = record("inverse", [[round(Fraction(256, row[0])) if row[0] else 0] for row in denom])
    normalized = record(
        "normalized", [[n * i[0] for n in row] for row, i in zip(masked, inv, strict=True)]
    )
    attention = record(
        "attention", [[round(Fraction(n, 256)) for n in row] for row in multiply(normalized, v)]
    )
    residual = record(
        "residual",
        [
            [a + b for a, b in zip(row, e, strict=True)]
            for row, e in zip(attention, emb, strict=True)
        ],
    )
    n1 = norm("norm1", "residual", residual)
    hidden = record("hidden", affine(n1, HIDDEN, (1, -1, 0), 512))
    activated = record("activated", [[max(0, n) for n in row] for row in hidden])
    output = record("output", affine(activated, OUTPUT, (-1, 1), 2))
    residual2 = record(
        "residual2",
        [
            [round(Fraction(a, 256) + b) for a, b in zip(row, o, strict=True)]
            for row, o in zip(n1, output, strict=True)
        ],
    )
    n2 = norm("norm2", "residual2", residual2)
    record("pool-mask", [[m] for m in masks])
    sums = record(
        "pool-sum", [[sum(row[j] for row, m in zip(n2, masks, strict=True) if m) for j in range(2)]]
    )
    maxima = record(
        "pool-max",
        [
            [
                max((row[j] for row, m in zip(n2, masks, strict=True) if m), default=0)
                for j in range(2)
            ]
        ],
    )
    pooled = record("pooled", [[a + b for a, b in zip(sums[0], maxima[0], strict=True)]])
    logits = record("logits", affine(pooled, HEAD, (1, -1), 512))
    record("score", [[logits[0][1] - logits[0][0]]])
    assert set(result) == {n.output for n in arithmetic.nodes}
    return result


def opening(text):
    return TranscriptOpening(
        schema_id="hallmark/transcript-opening/1",
        system_ref=b"r" * 32,
        prompt=text,
        response="Harmless unused fixture response.",
        salt=b"t" * 32,
    )


def build():
    classifier, program, inputs, arithmetic, weights, tokenizer, parameters = export()
    cases = []
    for name, text in (
        ("empty", ""),
        ("one", "A"),
        ("exact", "AB"),
        ("tail", "ABx"),
        ("multichunk", "xxAA"),
        ("unicode", "é🙂"),
        ("nul", "\x00A\x00"),
        ("newline", "A\r\nB"),
    ):
        units = text.encode()
        chunks = []
        for i, start in enumerate(range(0, max(1, len(units)), 2)):
            content = units[start : start + 2]
            tokens = tuple(content) + (0,) * (2 - len(content))
            mask = (1,) * len(content) + (0,) * (2 - len(content))
            trace = oracle(tokens, mask, arithmetic)
            chunks.append(
                dict(
                    index=i,
                    unit_count=len(content),
                    tokens=tokens,
                    mask=mask,
                    tensors=trace,
                    score=trace["score"][0],
                )
            )
        score = max(c["score"] for c in chunks)
        cases.append(
            dict(
                name=name,
                opening_cbor_hex=opening(text).encode().hex(),
                chunks=chunks,
                score=score,
                verdict=score < classifier.threshold,
            )
        )
    return dict(
        schema_id="hallmark/encoder-fixture/1",
        evidence_class="public-synthetic-software-vectors",
        qualified_backend=False,
        provenance="Owned authored integer constants; no trained checkpoint or private data.",
        licence="Existing repository licence; no additional grant.",
        warning=(
            "Two-token, two-feature synthetic architecture. "
            "No pretrained-model equivalence, quality, proof, or admission."
        ),
        records={
            name: dict(cbor_hex=obj.encode().hex(), identity_hex=obj.identity().hex())
            for name, obj in (
                ("classifier", classifier),
                ("program", program),
                ("input_profile", inputs),
                ("arithmetic", arithmetic),
            )
        },
        weights_cbor_hex=weights.hex(),
        tokenizer_hex=tokenizer.hex(),
        parameters={p: r.hex() for p, r in parameters.items()},
        cases=cases,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.output.open("x") as stream:
        json.dump(build(), stream, sort_keys=True, indent=2)
        stream.write("\n")
