from pathlib import Path

from src import config as c


def test_logical_size_and_fps():
    assert (c.LOGICAL_W, c.LOGICAL_H) == (288, 512)
    assert c.FPS == 60
    assert abs(c.FIXED_DT - 1 / 60) < 1e-12


def test_paths_are_absolute_and_repo_relative():
    assert c.PROJECT_ROOT.is_absolute()
    assert c.PROJECT_ROOT.name == "FlappyBird"
    assert c.RES_DIR == c.PROJECT_ROOT / "res"
    assert c.RES_DIR.is_dir()
    assert c.SAVE_FILE == c.PROJECT_ROOT / "save" / "highscore.json"


def test_derived_hop_matches_physics_formula():
    expected = c.FLAP_VELOCITY ** 2 / (2 * c.GRAVITY)
    assert abs(c.HOP - expected) < 1e-9
    assert 45.0 < c.HOP < 52.0  # 约 48.1


def test_hitbox_derived_from_sprite_and_inset():
    assert (c.BIRD_W, c.BIRD_H, c.BIRD_INSET) == (34, 24, 3)
    assert (c.HITBOX_W, c.HITBOX_H) == (28, 18)


def test_difficulty_endpoints():
    assert c.LEVEL_EVERY == 5 and c.MAX_LEVEL == 6
    assert (c.BASE_GAP, c.GAP_STEP, c.MIN_GAP) == (110, 5, 80)
    assert abs(c.BASE_SPEED - 120.0) < 1e-9
    assert abs(c.SPEED_STEP - 0.08) < 1e-9


def test_layout_bands_fit_inside_logical_screen():
    assert c.LAND_Y == 400
    assert c.SCORE_Y < c.LAND_Y
    assert c.HINT_Y <= c.LOGICAL_H - 40
    # 最窄缝隙下，缝隙中心的最低位置仍在地面之上（用派生量而非已删除的配置项）
    assert c.PIPE_MARGIN + c.MIN_GAP / 2 < c.LAND_Y
    assert c.LAND_Y - c.PIPE_MARGIN - c.MIN_GAP / 2 > c.PIPE_MARGIN + c.MIN_GAP / 2
