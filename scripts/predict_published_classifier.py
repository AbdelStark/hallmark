"""Native inference for the two frozen Hub models; does not generate or verify proofs."""

import argparse
import hashlib
import json
from pathlib import Path

import run_contextual_proof as cnn
import run_trained_mlp as mlp
from run_e2e import EXPORTS

from hallmark._gnark_probe import read_regular
from hallmark.integer_graph import IntegerGraph
from hallmark.mlp_training import MlpQuantization


def predict(kind, quantization, prompt):
    raw = prompt.encode("utf-8")
    if len(raw) > 96:
        raise ValueError("published proof-demo models accept at most 96 UTF-8 bytes")
    paths = {"mlp": "mlp-training/seed-17", "cnn": "cnn-training/17"}
    if kind not in paths:
        raise ValueError("choose mlp or cnn")
    data = read_regular(quantization, 65536)
    if hashlib.sha256(data).hexdigest() != EXPORTS[paths[kind] + "/quantization.json"]:
        raise ValueError("quantization differs from the published seed-17 model")
    if kind == "mlp":
        q = MlpQuantization.model_validate_json(data)
        e = mlp.export(q)
        w = q.weights
        graph = IntegerGraph(
            e["arithmetic"],
            parameters=e["parameters"],
            constants={
                "w1": tuple(x for row in w.hidden_weights for x in row),
                "b1": w.hidden_bias,
                "w2": w.output_weights,
                "b2": (w.output_bias,),
            },
        )
        score = graph.evaluate({"counts": tuple(raw.count(i) for i in range(256))})["score"][0]
        threshold = 0
    else:
        e = cnn.export(json.loads(data))
        inputs = {
            "tokens": tuple(raw) + (0,) * (96 - len(raw)),
            "mask": (1,) * len(raw) + (0,) * (96 - len(raw)),
        }
        score = e["graph"].evaluate(inputs)["score"][0]
        threshold = cnn.THRESHOLD
    return dict(
        model=kind,
        score=score,
        threshold=threshold,
        block=score >= threshold,
        input_bytes=len(raw),
        evidence="native-inference-only",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("mlp", "cnn"))
    parser.add_argument("--quantization", type=Path, required=True)
    parser.add_argument("--prompt", required=True)
    args = parser.parse_args()
    print(json.dumps(predict(args.kind, args.quantization, args.prompt), sort_keys=True))
