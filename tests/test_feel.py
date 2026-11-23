"""手感调优：非对称重力 + 顶点滞空。

用户反馈（原话）：
  "重力下降太快了，连续高低障碍很难飞跃调整下降速度，
   空格按下后在空中有一段短暂悬空不要立马就掉落"

量化现状（修复前实测）：
  单跳升高 45.0px，总滞空 0.500s，顶点悬停 0.000s，落 60px 仅 0.133s

本文件锁定"手感契约"，防止后续调参把浮动感改回去。
"""

import math

import pytest

from src import config as c
from src.physics import gravity_for, integrate, jump_feel_metrics


# ---------------------------------------------------------------- 重力曲线

def test_gravity_is_asymmetric():
    """下降时的重力必须小于上升时（这是"不那么容易掉"的物理来源）。"""
    rising = gravity_for(c.FLAP_VELOCITY)       # 高速上升
    falling = gravity_for(c.MAX_FALL_SPEED)     # 高速下降
    assert falling < rising, "下降重力应小于上升重力"


def test_gravity_reduced_near_apex():
    """接近顶点（|vy| 小）时重力进一步减弱 —— 产生"顶端悬停"的观感。"""
    at_apex = gravity_for(0.0)
    at_speed = gravity_for(c.HANG_VY_THRESHOLD)   # 恰好等于阈值
    fast = gravity_for(c.MAX_FALL_SPEED)
    assert at_apex < at_speed <= fast


def test_gravity_is_continuous_at_threshold():
    """阈值两侧的重力必须连续，否则会产生可感知的"卡顿"。"""
    below = gravity_for(c.HANG_VY_THRESHOLD - 1e-6)
    at = gravity_for(c.HANG_VY_THRESHOLD)
    assert abs(below - at) < 1e-3


def test_gravity_is_always_positive():
    for vy in (-1000, -380, -1, 0, 1, 100, 640, 9999):
        assert gravity_for(vy) > 0


def test_gravity_never_exceeds_rising_gravity():
    """任何速度下的重力都不应超过上升段基准重力（防止调参调出怪值）。"""
    for vy in (-2000, -500, 0, 100, 480, 2000):
        assert gravity_for(vy) <= c.GRAVITY + 1e-9


# ---------------------------------------------------------------- 跳跃手感

def test_apex_hang_time_is_perceptible():
    """顶点附近应有可感知的悬停（用户明确要求）。"""
    m = jump_feel_metrics()
    assert m["apex_hang"] >= 0.25, f"顶点悬停仅 {m['apex_hang']:.3f}s，太短"


def test_total_airtime_is_long_enough_to_adjust():
    """单跳总滞空要留出调整窗口（原 0.5s 太短）。"""
    m = jump_feel_metrics()
    assert m["airtime"] >= 0.60, f"总滞空仅 {m['airtime']:.3f}s"


def test_descent_is_not_instant():
    """从顶点下落 60px 的时间要明显长于修复前（0.133s）。"""
    m = jump_feel_metrics()
    assert m["fall_60px"] >= 0.15, f"落 60px 仅 {m['fall_60px']:.3f}s，仍太急"


def test_terminal_fall_speed_reduced():
    """终端下落速度降低，减少"直接栽下去"的观感。"""
    assert c.MAX_FALL_SPEED <= 520, f"终端速度 {c.MAX_FALL_SPEED} 仍偏高"


def test_hop_height_stays_reasonable():
    """单跳升高不能变得过大，否则微操更难。"""
    m = jump_feel_metrics()
    assert 40.0 <= m["hop"] <= 52.0, f"单跳升高 {m['hop']:.1f}px 超出合理区间"


# ---------------------------------------------------------------- 不破坏既有契约

def test_climb_rate_still_meets_recovery_window():
    """爬升能力必须仍能在两根管道之间完成 120px 的落差调整。"""
    from src import config as cfg
    from src.difficulty import speed_for

    climb = jump_feel_metrics()["climb_rate"]          # px/s（持续补跳）
    window = cfg.PIPE_SPACING / speed_for(cfg.MAX_LEVEL)
    needed = cfg.MAX_CENTER_DELTA / climb
    assert needed < window, (
        f"爬升 {climb:.0f}px/s 需要 {needed:.2f}s 才能补回 120px，"
        f"但最高难度只有 {window:.2f}s"
    )


def test_tuning_invariant_still_holds_with_new_gravity():
    """非对称重力不能打破"最窄缝隙可通过"的红线。"""
    from src import config as cfg

    hop = jump_feel_metrics()["hop"]
    clear = cfg.MIN_GAP - cfg.HITBOX_H
    assert clear >= 1.25 * hop, f"净空 {clear} < 1.25×hop({1.25*hop:.1f})"


def test_integrate_uses_asymmetric_gravity():
    """integrate 必须真正用上新重力曲线，而不只是定义了一个没人调用的函数。"""
    vy_rise, _ = integrate(c.FLAP_VELOCITY, 0.0, c.FIXED_DT)
    vy_fall, _ = integrate(c.MAX_FALL_SPEED, 0.0, c.FIXED_DT)
    rise_delta = vy_rise - c.FLAP_VELOCITY
    fall_delta = c.MAX_FALL_SPEED - vy_fall
    # 下降时速度增量更小（被减缓）
    assert fall_delta < rise_delta


def test_vertical_motion_is_deterministic():
    """同一输入序列必须复现同一轨迹。"""
    def run():
        vy, y = c.FLAP_VELOCITY, 100.0
        path = []
        for _ in range(120):
            vy, y = integrate(vy, y, c.FIXED_DT)
            path.append(round(y, 6))
        return path

    assert run() == run()
