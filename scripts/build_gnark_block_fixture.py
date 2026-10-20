"""Freeze an exhaustive integer attention block oracle, not an encoder classifier."""

import hashlib
import itertools
import json
from fractions import Fraction

EMBEDDING = [[0, 0], [1, -1], [-1, 1], [1, 1]]
QUERY = [[1, 0], [0, 1]]
KEY = [[0, 1], [1, 0]]
VALUE = [[1, 0], [0, -1]]
HIDDEN = [[1, 1], [1, -1], [-1, 0]]
OUTPUT = [[1, -1, 2], [-1, 1, 1]]
LOGITS = [[2, -1], [-1, 2]]
EXPONENTIAL = [1, 2, 4, 8, 16]
INVERSE = [0, *(round(Fraction(256, n)) for n in range(1, 33))]


def affine(rows, weights, bias):
    return [
        [
            sum(x * w for x, w in zip(row, column, strict=True)) + b
            for column, b in zip(weights, bias, strict=True)
        ]
        for row in rows
    ]


def multiply(a, b):
    return [
        [sum(x * y for x, y in zip(row, column, strict=True)) for column in zip(*b, strict=True)]
        for row in a
    ]


def evaluate(tokens, masks):
    layers = {}

    def record(name, values):
        layers[name] = values
        return values

    embeddings = record("embedding", [EMBEDDING[token] for token in tokens])
    query = record("query", affine(embeddings, QUERY, [0, 0]))
    key = record("key", affine(embeddings, KEY, [0, 0]))
    value = record("value", affine(embeddings, VALUE, [0, 0]))
    transposed = record("key_transpose", [list(row) for row in zip(*key, strict=True)])
    scores = record("scores", multiply(query, transposed))
    assert all(-2 <= score <= 2 for row in scores for score in row)
    exponentials = record(
        "exponential", [[EXPONENTIAL[score + 2] for score in row] for row in scores]
    )
    masked = record(
        "masked", [[n * mask for n, mask in zip(row, masks, strict=True)] for row in exponentials]
    )
    denominators = record("denominator", [[sum(row)] for row in masked])
    inverse = record("inverse", [[INVERSE[row[0]]] for row in denominators])
    normalized = record(
        "normalized",
        [[n * scale[0] for n in row] for row, scale in zip(masked, inverse, strict=True)],
    )
    attention = record(
        "attention", [[round(Fraction(n, 256)) for n in row] for row in multiply(normalized, value)]
    )
    residual = record(
        "residual",
        [
            [a + b for a, b in zip(row, emb, strict=True)]
            for row, emb in zip(attention, embeddings, strict=True)
        ],
    )
    hidden_acc = record("hidden_accumulator", affine(residual, HIDDEN, [1, -1, 0]))
    hidden = record("hidden", [[round(Fraction(n, 2)) for n in row] for row in hidden_acc])
    activated = record("activated", [[max(0, n) for n in row] for row in hidden])
    output_acc = record("output_accumulator", affine(activated, OUTPUT, [-1, 1]))
    output = record("output", [[round(Fraction(n, 2)) for n in row] for row in output_acc])
    block = record(
        "block_output",
        [
            [a + b for a, b in zip(row, res, strict=True)]
            for row, res in zip(output, residual, strict=True)
        ],
    )
    sums = record(
        "pool_sum",
        [[sum(row[j] for row, mask in zip(block, masks, strict=True) if mask) for j in range(2)]],
    )
    maxima = record(
        "pool_max",
        [
            [
                max((row[j] for row, mask in zip(block, masks, strict=True) if mask), default=0)
                for j in range(2)
            ]
        ],
    )
    pooled = record("pooled", [[a + b for a, b in zip(sums[0], maxima[0], strict=True)]])
    logit_acc = record("logit_accumulator", affine(pooled, LOGITS, [1, -1]))
    logits = record("logits", [[round(Fraction(n, 2)) for n in row] for row in logit_acc])
    score = logits[0][1] - logits[0][0]
    record("score", [[score]])
    trace = [n for tensor in layers.values() for row in tensor for n in row]
    assert len(trace) == 89 and all(type(n) is int and -(2**31) <= n < 2**31 for n in trace)
    return layers, trace, score


def build():
    cases = []
    for a, b, mask_a, mask_b in itertools.product(range(4), range(4), range(2), range(2)):
        layers, trace, score = evaluate([a, b], [mask_a, mask_b])
        for index, mask in enumerate((mask_a, mask_b)):
            if not mask:
                for replacement in range(4):
                    altered = [a, b]
                    altered[index] = replacement
                    assert evaluate(altered, [mask_a, mask_b])[2] == score
        cases.append(
            {
                "name": f"tokens-{a}-{b}-mask-{mask_a}-{mask_b}",
                "public": [a, b, mask_a, mask_b, score + 2**31],
                "trace": trace,
                "layers": layers,
                "score": score,
            }
        )
    graph = {
        "embedding": EMBEDDING,
        "query": QUERY,
        "key": KEY,
        "value": VALUE,
        "hidden": HIDDEN,
        "hidden_bias": [1, -1, 0],
        "output": OUTPUT,
        "output_bias": [-1, 1],
        "logits": LOGITS,
        "logit_bias": [1, -1],
        "exponential": EXPONENTIAL,
        "inverse": INVERSE,
        "attention_fractional_bits": 8,
        "affine_rescale_divisor": 2,
        "rounding": "nearest-ties-even",
        "pooling_empty_value": 0,
        "trace_order": list(cases[0]["layers"]),
    }
    raw = json.dumps(graph, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return {
        "schema_id": "hallmark.gnark-block-fixture/1",
        "qualified_backend": False,
        "warning": (
            "Synthetic operator block, not an encoder, tokenizer or Hallmark proof statement."
        ),
        "graph": graph,
        "graph_sha256": hashlib.sha256(raw).hexdigest(),
        "public_fields": ["token-0", "token-1", "mask-0", "mask-1", "score-offset-int32"],
        "cases": cases,
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
