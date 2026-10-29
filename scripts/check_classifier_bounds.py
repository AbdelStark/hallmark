"""Conservative integer bounds for the frozen model domain; no data selection."""

import argparse
import sys
from fractions import Fraction
from pathlib import Path

import circle_inputs
import classifier_comparison as comparison


def mlp_bounds(model, capacity):
    if type(capacity) is not int or not 0 <= capacity <= 96:
        raise ValueError("unsupported bound domain")
    hidden = []
    for weights, bias in zip(model["hidden_weights"], model["hidden_bias"], strict=True):
        low = bias + capacity * min(0, min(weights))
        high = bias + capacity * max(0, max(weights))
        rounded = [round(Fraction(value, 2 ** model["first_fraction"])) for value in (low, high)]
        hidden.append(
            dict(accumulator=[low, high], rounded=rounded, relu=[max(0, v) for v in rounded])
        )
    low = high = model["output_bias"]
    for row, weight in zip(hidden, model["output_weights"], strict=True):
        products = [weight * v for v in row["relu"]]
        low += min(products)
        high += max(products)
    score = [round(Fraction(value, 2 ** model["last_fraction"])) for value in (low, high)]
    return dict(
        capacity_bytes=capacity,
        domain=(
            "all 256 byte values; nonnegative counts sum to at most capacity; includes UTF-8 inputs"
        ),
        method="independent interval relaxation; exact monotone ties-to-even rescaling",
        hidden=hidden,
        output_accumulator=[low, high],
        score=score,
        tight_bound=False,
        held_out_evaluation=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classifier-run", type=Path, required=True)
    parser.add_argument("--expected-preparation", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    exported, records, _ = circle_inputs.admit(args.classifier_run, args.expected_preparation)
    report = mlp_bounds(exported["mlp"]["model"], 96)
    threshold = records[1]["classifier"].threshold
    report |= dict(
        schema_id="hallmark.classifier-interval-certificate/1",
        purpose="fixed-domain conformance; no fitting, model selection or test-set evaluation",
        license="MIT; original released synthetic classifier",
        authority="standing bounded local research approval and publication decision 0080",
        source_model="abdelstark/hallmark-byte-mlp@05b2bdef120d3aea9133af042d15ed1a3a621aa9",
        python=sys.version,
        threshold=threshold,
        always_allow=report["score"][1] < threshold,
        quantization_sha256=comparison.sha(
            (args.classifier_run / "mlp-training/seed-17/quantization.json").read_bytes()
        ),
        source_sha256=comparison.sha(Path(__file__).read_bytes()),
        canonical_model_sha256=comparison.sha(comparison.encoded(exported["mlp"]["model"])),
        native_program=records[1]["program"].identity().hex(),
        analysis_sources={
            name: comparison.sha((comparison.ROOT / name).read_bytes())
            for name in (
                "scripts/classifier_comparison.py",
                "scripts/trained_mlp.py",
                "src/hallmark/mlp_export.py",
                "src/hallmark/classifier_manifest.py",
            )
        },
        benchmark_sample=False,
        proof=False,
    )
    with args.output.open("xb") as stream:
        stream.write(comparison.encoded(report))
    print(comparison.encoded(report).decode(), end="")
