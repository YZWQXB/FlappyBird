"""调参可行性校验（Spec 附录 A）+ 无头 bot 回归。

用法：
    python scripts/tune_sim.py          # 只做解析校验
    python scripts/tune_sim.py --bot    # 额外跑无头 bot（同种子同结果）
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config as c  # noqa: E402
from src.difficulty import gap_for, level_for, next_gap_center, speed_for  # noqa: E402
from src.physics import hitbox, integrate, is_dead, should_score  # noqa: E402


def feel_report() -> None:
    """打印手感指标（非判定项，供调参参考）。"""
    from src.physics import jump_feel_metrics

    m = jump_feel_metrics()
    print("== 手感指标（v1.1 非对称重力）==")
    print(f"  单跳升高    {m['hop']:.1f} px")
    print(f"  总滞空      {m['airtime']:.3f} s")
    print(f"  顶点悬停    {m['apex_hang']:.3f} s   (|vy| < {c.HANG_VY_THRESHOLD})")
    print(f"  落 60px 用时 {m['fall_60px']:.3f} s")
    print(f"  持续爬升    {m['climb_rate']:.0f} px/s")
    print(f"  下落系数    {c.GRAVITY_FALL_SCALE}  顶点系数 {c.HANG_GRAVITY_SCALE}")
    print(f"  终端速度    {c.MAX_FALL_SPEED} px/s")


def analytic_report() -> bool:
    clear = c.MIN_GAP - c.HITBOX_H
    dwell = 2 * math.sqrt(2 * clear / c.GRAVITY)
    max_speed = speed_for(c.MAX_LEVEL)
    cross = (c.PIPE_W + c.HITBOX_W) / max_speed
    ratio = dwell / cross
    need = 1.25 * c.HOP

    print("== Spec 附录 A.2 派生量 ==")
    print(f"HOP     = {c.HOP:.1f} px      (解析值，离散实测约 44.7)")
    print(f"CLEAR   = {clear} px           (= MIN_GAP - HITBOX_H)")
    print(f"DWELL   = {dwell:.3f} s")
    print(f"CROSS   = {cross:.3f} s        (@ max speed {max_speed:.1f} px/s)")
    print(f"RATIO   = {ratio:.3f}          (需 >= 1.25)")
    print(f"净空需求 = 1.25 * HOP = {need:.1f} px, 实际 {clear} px")

    ok = True
    if clear < need:
        print(f"FAIL: 净空 {clear} < {need:.1f}")
        ok = False
    if ratio < 1.25:
        print(f"FAIL: RATIO {ratio:.2f} < 1.25")
        ok = False
    if c.BASE_GAP <= c.MIN_GAP:
        print("FAIL: BASE_GAP <= MIN_GAP")
        ok = False
    if max_speed > 1.6 * c.BASE_SPEED:
        print("FAIL: speed_for(MAX_LEVEL) > 1.6 * BASE_SPEED")
        ok = False
    if level_for(c.LEVEL_EVERY * c.MAX_LEVEL) != c.MAX_LEVEL:
        print("FAIL: 等级未在 LEVEL_EVERY*MAX_LEVEL 处达到上限")
        ok = False
    return ok


def simulate(level: int, seed: int, frames: int = 3000) -> tuple[str, int]:
    """无头 bot：固定阈值的简单策略，仅用于确定性回归，不代表人类手感。"""
    gap = gap_for(level)
    speed = speed_for(level)
    rng = random.Random(seed)
    x, y, vy = float(c.BIRD_X), float(c.BIRD_Y0), 0.0
    pipes = []
    dist = 0.0
    prev_center = c.LAND_Y / 2
    spawn_x = c.PIPE_SPAWN_X
    for _ in range(4):
        center = next_gap_center(prev_center, gap, rng)
        pipes.append([spawn_x, center, gap, False])
        prev_center = center
        spawn_x += c.PIPE_SPACING
    for _ in range(frames):
        nxt = next((p for p in pipes if p[0] + c.PIPE_W > x - c.HITBOX_W / 2), None)
        target = nxt[1] if nxt else c.LAND_Y / 2
        if vy >= 0 and y >= target + c.HOP * 0.5 - 2:
            vy = c.FLAP_VELOCITY
        vy, y = integrate(vy, y, c.FIXED_DT)
        for p in pipes:
            p[0] -= speed * c.FIXED_DT
        pipes = [p for p in pipes if p[0] + c.PIPE_W > -10]
        dist += speed * c.FIXED_DT
        if dist >= c.PIPE_SPACING:
            dist -= c.PIPE_SPACING
            center = next_gap_center(prev_center, gap, rng)
            pipes.append([c.LOGICAL_W, center, gap, False])
            prev_center = center
        box = hitbox(x, y)
        if is_dead(box, [(p[0], p[1], p[2]) for p in pipes], c.LAND_Y):
            return "dead", sum(1 for p in pipes if p[3])
        for p in pipes:
            if not p[3] and should_score(p[0], box[0]):
                p[3] = True
    return "alive", sum(1 for p in pipes if p[3])


def bot_report() -> bool:
    print("== 无头 bot（确定性回归，非手感判据）==")
    results = []
    for level in (0, c.MAX_LEVEL):
        scores = [simulate(level, seed)[1] for seed in range(3)]
        results.append((level, scores))
        print(f"  level {level}: scores {scores}")
    a = simulate(0, 42)
    b = simulate(0, 42)
    same = a == b
    print(f"  同种子复现: {a} == {b} -> {same}")
    return same


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bot", action="store_true")
    args = parser.parse_args()
    feel_report()
    print()
    ok = analytic_report()
    if args.bot:
        ok = bot_report() and ok
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())