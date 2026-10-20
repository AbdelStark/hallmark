import math

import pytest

from hallmark.evaluation import calibrate_threshold, metrics


def test_threshold_ties_and_empirical_fpr() -> None:
    scores, labels = (5, 5, 8, 1), (0, 0, 1, 1)
    threshold = calibrate_threshold(scores, labels, 0.01)
    assert threshold == 6
    report = metrics(labels, scores, threshold)
    assert report["fp"] == 0
    assert report["tpr"] == 0.5
    assert report["zero_fp_one_sided_upper"] == pytest.approx(1 - math.sqrt(0.05))


def test_small_fixture_cannot_establish_one_percent_fpr() -> None:
    report = metrics((0,) * 8, (-1,) * 8, 0)
    assert report["fpr"] == 0
    assert report["zero_fp_one_sided_upper"] > 0.01
    assert report["tpr"] is None
    assert report["tpr_wilson_interval"] is None


@pytest.mark.parametrize("scores,labels", [((1,), ()), ((1,), (True,)), ((1,), (1,)), ((), ())])
def test_invalid_calibration_is_not_a_result(
    scores: tuple[int, ...], labels: tuple[int, ...]
) -> None:
    with pytest.raises(ValueError):
        calibrate_threshold(scores, labels, 0.01)


def test_noninteger_scores_rejected() -> None:
    with pytest.raises(ValueError):
        calibrate_threshold((True,), (0,), 0.01)
    with pytest.raises(ValueError):
        metrics((0,), (2**31,), 0)
    with pytest.raises(ValueError):
        metrics((0,), (0,), True)
