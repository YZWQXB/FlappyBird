"""难度曲线：全部为纯函数，rng 可注入以便复现。"""

from __future__ import annotations

import random

from . import config as c


def level_for(score: int) -> int:
    return min(max(score, 0) // c.LEVEL_EVERY, c.MAX_LEVEL)


def speed_for(level: int) -> float:
    return c.BASE_SPEED * (1.0 + c.SPEED_STEP * min(max(level, 0), c.MAX_LEVEL))


def gap_for(level: int) -> int:
    level = min(max(level, 0), c.MAX_LEVEL)
    return max(c.BASE_GAP - c.GAP_STEP * level, c.MIN_GAP)


def gap_band(gap: float) -> tuple[float, float]:
    """缝隙中心的合法取值区间。"""
    lo = c.PIPE_MARGIN + gap / 2
    hi = c.LAND_Y - c.PIPE_MARGIN - gap / 2
    return lo, max(lo, hi)


def next_gap_center(prev_center: float, gap: float, rng: random.Random) -> float:
    lo, hi = gap_band(gap)
    target = rng.uniform(lo, hi)
    # 先按最大落差钳制，再夹回合法区间（保证两个约束同时满足）
    delta = max(-c.MAX_CENTER_DELTA, min(c.MAX_CENTER_DELTA, target - prev_center))
    return max(lo, min(hi, prev_center + delta))
