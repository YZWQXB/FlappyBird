import random

import pytest

from src import config as c
from src.assets import AssetManager
from src.background import Background
from src.bird import Bird
from src.ground import Ground
from src.hud import Hud, number_width
from src.pipe import PipePair


def test_bird_flap_sets_velocity(assets):
    bird = Bird(assets)
    bird.flap()
    assert bird.vy == pytest.approx(c.FLAP_VELOCITY)


def test_bird_update_integrates(assets):
    bird = Bird(assets)
    bird.vy, bird.y = 0.0, 200.0
    bird.update(c.FIXED_DT)
    assert bird.y > 200.0
    assert bird.vy > 0.0


def test_bird_frame_cycles(assets):
    bird = Bird(assets)
    seen = set()
    for _ in range(40):
        bird.update(c.FIXED_DT)
        seen.add(bird.flap_index)
    assert seen == {0, 1, 2}


def test_bird_palette_follows_stage(assets):
    bird = Bird(assets)
    for stage, expected in ((0, 0), (1, 1), (2, 2), (3, 0), (6, 0)):
        bird.set_stage(stage)
        assert bird.palette == expected


def test_bird_reset_restores_initial_state(assets):
    bird = Bird(assets)
    bird.y, bird.vy, bird.palette = 100.0, 300.0, 2
    bird.reset()
    assert bird.y == c.BIRD_Y0 and bird.vy == 0.0 and bird.palette == 0


def test_bird_float_motion_stays_within_amplitude(assets):
    import math

    bird = Bird(assets)
    for i in range(200):
        bird.float_motion(i * 0.05)
        assert abs(bird.y - c.BIRD_Y0) <= c.BIRD_FLOAT_AMP + 1e-9


def test_pipe_pair_geometry():
    pair = PipePair(x=200.0, center=250.0, gap=110.0, speed=120.0)
    top, bottom = pair.boxes()
    assert top == (200.0, 0.0, c.PIPE_W, 195.0)
    assert bottom[1] == pytest.approx(305.0)
    assert bottom[1] + bottom[3] == pytest.approx(c.LAND_Y)


def test_pipe_pair_moves_and_scores_once():
    pair = PipePair(x=100.0, center=250.0, gap=110.0, speed=120.0)
    pair.update(0.5)
    assert pair.x == pytest.approx(100.0 - 60.0)
    assert pair.scored is False
    left = pair.x + c.PIPE_W
    assert pair.try_score(bird_left=left + 1.0) is True
    assert pair.try_score(bird_left=left + 1.0) is False


def test_pipe_pair_off_screen():
    pair = PipePair(x=-c.PIPE_W - 1, center=250.0, gap=110.0, speed=120.0)
    assert pair.is_off_screen() is True
    pair2 = PipePair(x=-c.PIPE_W + 1, center=250.0, gap=110.0, speed=120.0)
    assert pair2.is_off_screen() is False


# ---------- 地面与背景 ----------

def test_ground_offset_wraps_without_gap(assets):
    ground = Ground(assets)
    for _ in range(1000):
        ground.update(c.FIXED_DT, c.BASE_SPEED)
        assert -c.LAND_TILE_W <= ground.offset <= 0


def test_ground_keeps_subpixel_accumulator(assets):
    """offset 必须保留亚像素，否则 129.6px/s 这类速度会被逐帧取整拖慢。"""
    ground = Ground(assets)
    ground.update(c.FIXED_DT, 129.6)
    ground.update(c.FIXED_DT, 129.6)
    assert abs(ground.offset + 4.32) < 1e-9


def test_ground_draw_position_is_quantized(assets):
    """只在绘制时取整，保证接缝不抖动。"""
    ground = Ground(assets)
    ground.offset = -2.16
    assert ground.draw_x() == -2


def test_ground_covers_screen_after_wrap(assets):
    ground = Ground(assets)
    ground.offset = -1000.0
    ground.update(0.0, c.BASE_SPEED)
    assert -c.LAND_TILE_W <= ground.offset <= 0


def test_ground_handles_large_dt(assets):
    ground = Ground(assets)
    ground.update(10.0, 120.0)          # 单步 1200px
    assert -c.LAND_TILE_W <= ground.offset <= 0


def test_background_selects_by_stage(assets):
    bg = Background(assets)
    assert bg.key_for_stage(0) == "bg_day"
    assert bg.key_for_stage(1) == "bg_night"
    assert bg.key_for_stage(2) == "bg_day"
    bg.set_stage(1)
    assert bg.key == "bg_night"


# ---------- HUD ----------

def test_number_width_accounts_for_narrow_one(assets):
    hud = Hud(assets)
    assert number_width(hud, 0) == 0
    assert number_width(hud, 1) == 16
    assert number_width(hud, 10) == 16 + c.DIGIT_GAP + 24
    assert number_width(hud, 11) == 16 + c.DIGIT_GAP + 16
    assert number_width(hud, 123) == 16 + c.DIGIT_GAP + 24 + c.DIGIT_GAP + 24


def test_hud_draws_zero_as_nothing(assets):
    import pygame

    hud = Hud(assets)
    surf = pygame.Surface((c.LOGICAL_W, c.LOGICAL_H))
    surf.fill((0, 0, 0))
    before = surf.get_at((c.LOGICAL_W // 2, c.SCORE_Y))
    hud.draw_score(surf, 0)
    assert surf.get_at((c.LOGICAL_W // 2, c.SCORE_Y)) == before


def test_hud_draws_number_when_positive(assets):
    import pygame

    hud = Hud(assets)
    surf = pygame.Surface((c.LOGICAL_W, c.LOGICAL_H))
    surf.fill((0, 0, 0))
    hud.draw_score(surf, 12)
    lit = sum(
        1
        for x in range(c.LOGICAL_W)
        for y in range(c.SCORE_Y, c.SCORE_Y + 36)
        if surf.get_at((x, y))[:3] != (0, 0, 0)
    )
    assert lit > 0


def test_font_falls_back_when_sysfont_fails(assets, monkeypatch):
    import pygame

    hud = Hud(assets)

    def boom(*args, **kwargs):
        raise TypeError("simulated pygame 2.6.1 sysfont bug")

    monkeypatch.setattr(pygame.font, "SysFont", boom)
    font = hud.get_font(c.FONT_SMALL)
    assert font is not None


def test_text_has_outline_and_cache(assets):
    hud = Hud(assets)
    a = hud.text_surface("PAUSED", c.FONT_LARGE)
    b = hud.text_surface("PAUSED", c.FONT_LARGE)
    assert a is b                     # 命中缓存
    c2 = hud.text_surface("BEST", c.FONT_SMALL)
    assert c2 is not a


def test_overlay_darkens_surface(assets):
    import pygame

    hud = Hud(assets)
    surf = pygame.Surface((c.LOGICAL_W, c.LOGICAL_H))
    surf.fill((255, 255, 255))
    hud.overlay(surf)
    px = surf.get_at((10, 10))
    assert px[0] < 255 and px[1] < 255 and px[2] < 255
