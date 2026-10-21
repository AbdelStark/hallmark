"""Author a grouped comparison software fixture; no policy-quality dataset."""

import hashlib
import json

from hallmark.baselines import NgramConfig, TrainingBounds
from hallmark.contracts import Record
from hallmark.mlp_training import MlpFitConfig
from hallmark.selection import FitCandidate, SelectionPlan


def build():
    bounds = TrainingBounds(
        policy_id="fixture.selection",
        max_rows=128,
        max_prompt_bytes=128,
        max_total_bytes=16384,
    )
    ngram = NgramConfig(
        schema_id="hallmark/ngram-fit-config/1",
        min_n=1,
        max_n=3,
        max_features=128,
        max_events=32768,
        c=1.0,
        tolerance=0.0001,
        max_iter=100,
    )
    mlp = MlpFitConfig(
        schema_id="hallmark/mlp-fit-config/1",
        policy_id=bounds.policy_id,
        seed=17,
        hidden_width=2,
        chunk_bytes=32,
        max_prompt_bytes=128,
        max_rows=128,
        max_feature_values=65536,
        epochs=4,
        learning_rate=0.05,
        momentum=0.8,
        l2=0.001,
        tolerance=1.0,
    )
    plan = SelectionPlan(
        schema_id="hallmark/grouped-selection-plan/1",
        bounds=bounds,
        chunk_bytes=32,
        seeds=(17, 29, 43),
        folds=5,
        target_fpr="0.01",
        candidates=(
            FitCandidate(id="floor", kind="byte-logistic", ngram=None, mlp=None),
            FitCandidate(id="char-a", kind="char-ngram", ngram=ngram, mlp=None),
            FitCandidate(id="char-z", kind="char-ngram", ngram=ngram, mlp=None),
            FitCandidate(id="mlp", kind="byte-mlp", ngram=None, mlp=mlp),
            FitCandidate(
                id="mlp-nonconverged",
                kind="byte-mlp",
                ngram=None,
                mlp=mlp.model_copy(update={"tolerance": 0.0}),
            ),
        ),
    )
    rows = tuple(
        Record(
            schema_id="hallmark.dataset-record/1",
            record_id=f"r-{group:02d}-{variant}",
            group_id=f"group-{group:02d}",
            family_id="authored-markers",
            source_id="authored-grouped-markers",
            source_revision=hashlib.sha256(b"hallmark grouped comparison markers v1").hexdigest(),
            license_id="fixture-only",
            policy_id=bounds.policy_id,
            split="train",
            language="en",
            prompt=("AAAA" if group % 2 == 0 else "BBBB") + f" {group:02d} {variant}",
            response="",
            label=group % 2,
        )
        for group in range(50)
        for variant in range(2)
    )
    return {
        "schema_id": "hallmark/grouped-selection-fixture/1",
        "fixture_only": True,
        "purpose": "Group/label isolation, fixed ties and failure retention; no quality claim.",
        "note": (
            "The loose MLP tolerance exercises successful selection; the second config "
            "exercises nonconvergence. Neither is a study candidate."
        ),
        "plan": plan.model_dump(mode="json"),
        "records": [row.model_dump(mode="json") for row in rows],
        **{
            f"{split}_records": [
                row.model_copy(
                    update={
                        "record_id": f"{split}-{row.record_id}",
                        "group_id": f"{split}-{row.group_id}",
                        "split": split,
                        "prompt": row.prompt + " " + split,
                    }
                ).model_dump(mode="json")
                for row in rows[:20]
            ]
            for split in ("calibration", "test")
        },
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True, ensure_ascii=False))
