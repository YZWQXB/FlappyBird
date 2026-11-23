"""纯物理与碰撞判定：不 import pygame，全部输入输出为普通数值/元组。"""

from __future__ import annotations

import math
from typing import Sequence

from . import config as c

Box = tuple[float, float, float, float]   # x, y, w, h
PipeGeom = tuple[float, float, float]     # x, gap_center, gap_height


def gravity_for(vy: float) -> float:
    """当前速度对应的重力加速度（px/s²）。

    三段式非对称曲线，解决"下落太快、没有调整窗口"的手感问题：

    1. **方向不对称**：下降重力 = 上升重力 × GRAVITY_FALL_SCALE（更快到不了底）；
    2. **顶点滞空**：|vy| < HANG_VY_THRESHOLD 时，重力从
       HANG_GRAVITY_SCALE 线性过渡回正常值 —— 顶点附近"飘"一下再落；
    3. **阈值处连续**：过渡在 |vy| = HANG_VY_THRESHOLD 处恰好等于基准值，
       不会产生可感知的突变。

    用数值跳过了一处常见坑：把滞空做成"悬停计时器"会让手感发木，
    这里保持纯粹的速度-加速度关系，输入响应始终是连续的。
    """
    mag = abs(vy)
    # 上升段用基准重力；下降段按系数减弱
    base = c.GRAVITY if vy < 0 else c.GRAVITY * c.GRAVITY_FALL_SCALE
    if mag >= c.HANG_VY_THRESHOLD:
        return base
    # t=0 → 顶点（最弱），t=1 → 阈值处（回到 base），线性过渡保证连续
    t = mag / c.HANG_VY_THRESHOLD
    scale = c.HANG_GRAVITY_SCALE + (1.0 - c.HANG_GRAVITY_SCALE) * t
    return base * scale


def clamp_vy(vy: float) -> float:
    return max(c.FLAP_VELOCITY, min(c.MAX_FALL_SPEED, vy))


def integrate(vy: float, y: float, dt: float) -> tuple[float, float]:
    """一步半隐式欧拉积分：先按重力曲线加速，再位移，返回 (vy, y)。"""
    vy = clamp_vy(vy + gravity_for(vy) * dt)
    return vy, y + vy * dt


def hitbox(x: float, y: float) -> Box:
    """鸟中心 (x, y) → 内缩后的 AABB；先 round 再使用，避免浮点截断漂移。"""
    half_w = c.HITBOX_W / 2
    half_h = c.HITBOX_H / 2
    return (
        round(x - half_w),
        round(y - half_h),
        c.HITBOX_W,
        c.HITBOX_H,
    )


def overlaps(a: Box, b: Box) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def pipe_boxes(pipe: PipeGeom, land_y: float) -> tuple[Box, Box]:
    """上管矩形与下管矩形（缝隙以外全部是实体）。"""
    x, center, gap = pipe
    top = center - gap / 2
    bottom = center + gap / 2
    return (x, 0.0, c.PIPE_W, max(0.0, top)), (x, bottom, c.PIPE_W, max(0.0, land_y - bottom))


def is_dead(box: Box, pipes: Sequence[PipeGeom], land_y: float) -> bool:
    x, y, w, h = box
    if y + h >= land_y:        # 撞地面
        return True
    if y <= 0:                 # 越过屏幕上边界
        return True
    for pipe in pipes:
        top_box, bottom_box = pipe_boxes(pipe, land_y)
        if overlaps(box, top_box) or overlaps(box, bottom_box):
            return True
    return False


def should_score(pipe_x: float, bird_left: float) -> bool:
    """管道尾端完全越过鸟左沿的那一步计分。"""
    return pipe_x + c.PIPE_W <= bird_left


def rotation_for(vy: float) -> float:
    """vy → 精灵视觉角度（仅绘制用，不影响 hitbox）。"""
    if vy <= c.FLAP_VELOCITY:
        return c.ROTATE_MIN_DEG
    if vy >= c.ROTATE_VY_FULL:
        return c.ROTATE_MAX_DEG
    span = c.ROTATE_VY_FULL - c.FLAP_VELOCITY
    t = (vy - c.FLAP_VELOCITY) / span
    return c.ROTATE_MIN_DEG + (c.ROTATE_MAX_DEG - c.ROTATE_MIN_DEG) * t


# ---------------------------------------------------------------- 手感度量

def jump_feel_metrics(steps: int = 900) -> dict[str, float]:
    """从一次起跳开始模拟，量化手感指标（供调参与单测使用）。

    返回：
    - hop          单跳升高（px）
    - airtime      从起跳到回到起跳高度的时间（s）
    - apex_hang    |vy| < HANG_VY_THRESHOLD 的累计时长（s），即"顶点悬停感"
    - fall_60px    从顶点下落 60px 所需时间（s）
    - climb_rate   持续补跳时的平均爬升速度（px/s）
    """
    vy, y = c.FLAP_VELOCITY, 0.0
    t = 0.0
    apex = y
    hang = 0.0
    airtime: float | None = None
    fall_60: float | None = None
    fall_start: float | None = None

    for _ in range(steps):
        vy, y = integrate(vy, y, c.FIXED_DT)
        t += c.FIXED_DT
        if y < apex:
            apex = y
        if abs(vy) < c.HANG_VY_THRESHOLD:
            hang += c.FIXED_DT
        if airtime is None and t > 0.05 and y >= 0.0:
            airtime = t
            fall_start = t
        if airtime is not None and fall_60 is None and y >= 60.0:
            fall_60 = t - fall_start
            break

    # 持续爬升：vy >= -50 就补跳，跑 1 秒
    climb_vy, climb_y, climb_t = c.FLAP_VELOCITY, 0.0, 0.0
    for _ in range(steps):
        if climb_vy >= -50.0:
            climb_vy = c.FLAP_VELOCITY
        climb_vy, climb_y = integrate(climb_vy, climb_y, c.FIXED_DT)
        climb_t += c.FIXED_DT
        if climb_t >= 1.0:
            break

    return {
        "hop": -apex,
        "airtime": airtime if airtime is not None else math.inf,
        "apex_hang": hang,
        "fall_60px": fall_60 if fall_60 is not None else math.inf,
        "climb_rate": -climb_y,
    }
