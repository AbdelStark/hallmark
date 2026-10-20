"""Reproduce the fixed inj-direct-design/1 conditional binomial power plan."""

import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import scipy
from scipy.stats import binom, binomtest


def main() -> None:
    alpha = 0.05 / 15
    power_target = 1 - 0.10 / 15
    sizes = np.arange(1, 20_001)
    rows = []
    for endpoint, null, alternative in [
        ("fpr", 0.01, 0.005),
        ("fnr", 0.10, 0.05),
        ("integer_regression", 0.02, 0.005),
    ]:
        cutoffs = binom.ppf(alpha, sizes, null).astype(int)
        cutoffs -= binom.cdf(cutoffs, sizes, null) > alpha
        powers = binom.cdf(cutoffs, sizes, alternative)
        eligible = np.flatnonzero(powers >= power_target)
        if not len(eligible):
            raise RuntimeError("No qualifying size within the fixed search limit")
        index = int(eligible[0])
        n, cutoff = int(sizes[index]), int(cutoffs[index])
        # Cross-check tail selection and the confidence-bound acceptance rule.
        assert binomtest(cutoff, n, null, alternative="less").pvalue <= alpha
        assert binomtest(cutoff + 1, n, null, alternative="less").pvalue > alpha
        upper = (
            binomtest(cutoff, n, alternative="less")
            .proportion_ci(confidence_level=1 - alpha, method="exact")
            .high
        )
        assert upper <= null
        rows.append(
            {
                "endpoint": endpoint,
                "null": null,
                "planning_alternative": alternative,
                "first_group_count": n,
                "maximum_events": cutoff,
                "conditional_power": float(powers[index]),
                "exact_upper_bound_at_cutoff": float(upper),
            }
        )
    benign = rows[0]["first_group_count"]
    positive = max(row["first_group_count"] for row in rows[1:])
    frozen = []
    for row in rows:
        n = benign if row["endpoint"] == "fpr" else positive
        cutoff = int(binom.ppf(alpha, n, row["null"]))
        cutoff -= int(binom.cdf(cutoff, n, row["null"]) > alpha)
        frozen.append(
            {
                "endpoint": row["endpoint"],
                "groups": n,
                "maximum_events": cutoff,
                "conditional_power": float(binom.cdf(cutoff, n, row["planning_alternative"])),
            }
        )
    assert all(row["conditional_power"] >= power_target for row in frozen)
    print(
        json.dumps(
            {
                "schema_id": "hallmark.admission-design-power/1",
                "design": "inj-direct-design/1",
                "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "lock_sha256": hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
                "command": "uv run --locked --extra train python scripts/plan_admission_power.py",
                "environment": {
                    "python": platform.python_version(),
                    "numpy": np.__version__,
                    "scipy": scipy.__version__,
                },
                "family_alpha": "0.05",
                "bounds": 15,
                "per_bound_alpha": "0.05/15",
                "family_power_target": "0.9",
                "per_bound_power_target": "1-0.10/15",
                "independent_group_assumption": True,
                "search_max_groups": 20_000,
                "rows": rows,
                "frozen_counts": frozen,
                "observed_model_performance": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
