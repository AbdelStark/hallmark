"""Build authored marker inputs and fixed training configs; no real policy dataset."""

import hashlib
import json

from hallmark.contracts import Record
from hallmark.mlp_training import MlpFitConfig


def build():
    texts = (
        "",
        "A",
        "A" * 512,
        "A" * 1024,
        "éAA",
        "AX" * 256,
        "B",
        "B" * 512,
        "A" * 512 + "B" * 512,
        "B" * 512 + "\x00",
        "A" * 1024 + "B" * 512,
        "B" * 1024,
    )
    configs = [
        MlpFitConfig(
            schema_id="hallmark/mlp-fit-config/1",
            policy_id="fixture.mlp-training",
            seed=seed,
            hidden_width=4,
            chunk_bytes=512,
            max_prompt_bytes=32768,
            max_rows=32,
            max_feature_values=32768,
            epochs=80,
            learning_rate=0.05,
            momentum=0.8,
            l2=0.001,
            tolerance=0.0,
        ).model_dump(mode="json")
        for seed in (17, 29, 43)
    ]
    records = [
        Record(
            schema_id="hallmark.dataset-record/1",
            record_id=f"r-{i:02d}",
            group_id=f"g-{i:02d}",
            family_id="fixture",
            source_id="authored-markers",
            source_revision=hashlib.sha256(b"hallmark authored MLP markers v1").hexdigest(),
            license_id="fixture-only",
            policy_id="fixture.mlp-training",
            split="train",
            language="en",
            prompt=text,
            response="",
            label=int("B" in text),
        ).model_dump(mode="json")
        for i, text in enumerate(texts)
    ]
    return {
        "schema_id": "hallmark.mlp-training-fixture/1",
        "fixture_only": True,
        "purpose": "Authored marker software checks; no policy-quality, admission or proof claim.",
        "configs": configs,
        "records": records,
        "numeric_error_bound": 0.1,
        "probes": [
            {"name": name, "prompt": text}
            for name, text in (
                ("empty", ""),
                ("near-chunk", "A" * 511),
                ("chunk-boundary", "A" * 512),
                ("two-chunks", "A" * 512 + "B" * 512),
                ("last-byte", "A" * 32767 + "B"),
                ("maximum", "A" * 32768),
                ("unicode", "é😀" * 80),
            )
        ],
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True, ensure_ascii=False))
