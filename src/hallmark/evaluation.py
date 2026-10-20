"""Fixed-threshold decisions and uncertainty with explicit empty-denominator semantics."""

import math
from statistics import NormalDist
from typing import Any


def calibrate_threshold(scores: tuple[int, ...], labels: tuple[int, ...], target_fpr: float) -> int:
    if (
        len(scores) != len(labels)
        or not scores
        or any(type(s) is not int or not -(2**31) <= s < 2**31 for s in scores)
        or any(type(y) is not int or y not in (0, 1) for y in labels)
    ):
        raise ValueError("calibration needs aligned nonempty scores and binary labels")
    if not 0 < target_fpr < 1 or not math.isfinite(target_fpr):
        raise ValueError("target_fpr must be finite and in (0,1)")
    benign = [s for s, y in zip(scores, labels, strict=True) if y == 0]
    if not benign:
        raise ValueError("calibration requires benign examples")
    allowed = math.floor(target_fpr * len(benign))
    threshold = sorted(benign, reverse=True)[allowed] + 1
    if not -(2**31) <= threshold < 2**31:
        raise ValueError("calibrated threshold does not fit int32")
    return threshold


def wilson_interval(successes: int, total: int, alpha: float = 0.05) -> list[float] | None:
    if not 0 <= successes <= total or not 0 < alpha < 1:
        raise ValueError("invalid binomial counts or alpha")
    if not total:
        return None
    z = NormalDist().inv_cdf(1 - alpha / 2)
    rate = successes / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    half = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def metrics(
    labels: tuple[int, ...], scores: tuple[int, ...], threshold: int, alpha: float = 0.05
) -> dict[str, Any]:
    if (
        len(labels) != len(scores)
        or not labels
        or any(type(s) is not int or not -(2**31) <= s < 2**31 for s in scores)
        or type(threshold) is not int
        or not -(2**31) <= threshold < 2**31
        or any(type(y) is not int or y not in (0, 1) for y in labels)
    ):
        raise ValueError("metrics need aligned nonempty scores and binary labels")
    tp = fp = tn = fn = 0
    for y, s in zip(labels, scores, strict=True):
        if y:
            tp += int(s >= threshold)
            fn += int(s < threshold)
        else:
            fp += int(s >= threshold)
            tn += int(s < threshold)
    negatives, positives = fp + tn, tp + fn
    return {
        "n": len(labels),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "tpr": tp / positives if positives else None,
        "fpr": fp / negatives if negatives else None,
        "tpr_wilson_interval": wilson_interval(tp, positives, alpha),
        "fpr_wilson_interval": wilson_interval(fp, negatives, alpha),
        "zero_fp_one_sided_upper": 1 - alpha ** (1 / negatives) if negatives and fp == 0 else None,
        "confidence_level": 1 - alpha,
    }
