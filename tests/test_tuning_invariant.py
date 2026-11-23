import math

import pytest

from src import config as c
from src.difficulty import gap_for, level_for, speed_for


def test_min_gap_leaves_enough_clearance():
    clear = c.MIN_GAP - c.HITBOX_H
    assert clear >= 1.25 * c.HOP, f"最窄净空 {clear} < 1.25×hop({1.25 * c.HOP})"


def test_dwell_beats_crossing_time():
    clear = c.MIN_GAP - c.HITBOX_H
    dwell = 2 * math.sqrt(2 * clear / c.GRAVITY)
    cross = (c.PIPE_W + c.HITBOX_W) / speed_for(c.MAX_LEVEL)
    assert dwell / cross >= 1.25, f"DWELL/CROSS={dwell / cross:.2f} < 1.25"


def test_gap_ordering():
    assert c.BASE_GAP > c.MIN_GAP
    assert gap_for(0) > gap_for(c.MAX_LEVEL)


def test_speed_is_not_absurdly_fast():
    assert speed_for(c.MAX_LEVEL) <= 1.6 * c.BASE_SPEED


def test_level_progression_reaches_cap():
    assert level_for(c.LEVEL_EVERY * c.MAX_LEVEL) == c.MAX_LEVEL
