import math

import pytest

from src import config as c
from src.physics import clamp_vy, hitbox, integrate, rotation_for


def test_clamp_respects_both_bounds():
    assert clamp_vy(-9999) == c.FLAP_VELOCITY
    assert clamp_vy(9999) == c.MAX_FALL_SPEED
    assert clamp_vy(0.0) == 0.0


def test_flap_sets_exact_velocity():
    vy, y = integrate(c.FLAP_VELOCITY, 256.0, c.FIXED_DT)
    assert vy > c.FLAP_VELOCITY            # 下一步就开始被重力拉回
    assert vy < c.FLAP_VELOCITY + c.GRAVITY * c.FIXED_DT + 1e-9
    assert y < 256.0


def test_free_fall_is_deterministic():
    vy, y = 0.0, 0.0
    for _ in range(600):                              # 10 秒
        vy, y = integrate(vy, y, c.FIXED_DT)
    assert vy == pytest.approx(c.MAX_FALL_SPEED)      # 早已触顶并被钳制
    assert y > 0


def test_hop_matches_config_formula():
    """上升段升高与解析 HOP 的关系。

    注：自 v1.1 起采用非对称重力，顶点附近重力减弱（HANG_GRAVITY_SCALE），
    上升段因此多 1~2 步、升高略高于旧版（旧版 44.67 → 现约 45.9）。
    这里只锁"离散结果不偏离解析值太多"的宽松契约，精确手感由 test_feel.py 负责。
    """
    vy, y = c.FLAP_VELOCITY, 0.0
    start = y
    steps = 0
    while vy < 0:
        vy, y = integrate(vy, y, c.FIXED_DT)
        steps += 1
    rise = start - y
    assert 16 <= steps <= 20
    assert c.HOP - 5.0 < rise <= c.HOP + 1.0
    assert rise == pytest.approx(45.9, abs=1.0)


def test_repeated_flap_does_not_accumulate():
    vy = c.FLAP_VELOCITY
    for _ in range(30):
        vy = c.FLAP_VELOCITY          # 模拟连续按空格：每次都直接赋值
        vy, _ = integrate(vy, 100.0, c.FIXED_DT)
    assert vy >= c.FLAP_VELOCITY


def test_hitbox_is_centered_and_inset():
    x, y, w, h = hitbox(100.0, 200.0)
    assert (w, h) == (c.HITBOX_W, c.HITBOX_H)
    assert x == pytest.approx(100.0 - c.HITBOX_W / 2)
    assert y == pytest.approx(200.0 - c.HITBOX_H / 2)


def test_hitbox_rounds_floats_before_rect():
    # pygame.Rect 向零截断，-0.6 会变成 0；先 round 保证对称
    x, y, _, _ = hitbox(100.6, 200.6)
    assert (x, y) == (87, 192)


def test_rotation_endpoints_and_interpolation():
    assert rotation_for(c.FLAP_VELOCITY) == c.ROTATE_MIN_DEG
    assert rotation_for(c.ROTATE_VY_FULL) == c.ROTATE_MAX_DEG
    assert rotation_for(9999.0) == c.ROTATE_MAX_DEG
    mid = rotation_for(10.0)
    assert c.ROTATE_MIN_DEG < mid < c.ROTATE_MAX_DEG
