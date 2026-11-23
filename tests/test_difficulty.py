import random

import pytest

from src import config as c
from src.difficulty import gap_band, gap_for, level_for, next_gap_center, speed_for


@pytest.mark.parametrize(
    "score,expected",
    [(0, 0), (4, 0), (5, 1), (9, 1), (10, 2), (29, 5), (30, 6), (31, 6), (999, 6)],
)
def test_level_for(score, expected):
    assert level_for(score) == expected


def test_speed_is_monotonic_and_capped():
    speeds = [speed_for(lv) for lv in range(c.MAX_LEVEL + 1)]
    assert speeds == sorted(speeds)
    assert speeds[0] == pytest.approx(120.0)
    assert speeds[-1] == pytest.approx(120.0 * (1 + 0.08 * 6))
    assert speed_for(99) == speed_for(c.MAX_LEVEL)
    assert speed_for(-5) == speed_for(0)


def test_gap_is_monotonic_and_capped():
    gaps = [gap_for(lv) for lv in range(c.MAX_LEVEL + 1)]
    assert gaps == sorted(gaps, reverse=True)
    assert gaps[0] == c.BASE_GAP
    assert gaps[-1] == c.MIN_GAP
    assert gap_for(99) == c.MIN_GAP


def test_gap_band_matches_expected_values():
    lo, hi = gap_band(c.MIN_GAP)
    assert lo == pytest.approx(88.0)
    assert hi == pytest.approx(312.0)


def test_center_within_legal_band():
    rng = random.Random(0)
    prev = 250.0
    for _ in range(500):
        gap = gap_for(level_for(rng.randrange(0, 60)))
        center = next_gap_center(prev, gap, rng)
        lo, hi = gap_band(gap)
        assert lo <= center <= hi + 1e-9
        prev = center


def test_center_delta_is_smooth_when_prev_is_extreme():
    for prev in (60.0, 250.0, 340.0):
        rng = random.Random(1)
        center = next_gap_center(prev, c.MIN_GAP, rng)
        assert abs(center - prev) <= c.MAX_CENTER_DELTA + 1e-9


def test_center_is_deterministic_with_same_seed():
    a = next_gap_center(250.0, 100.0, random.Random(7))
    b = next_gap_center(250.0, 100.0, random.Random(7))
    assert a == b
