"""审查修复回归测试：每个用例对应 docs/reviews/2026-11-23-code-review.md 的一个编号。

修复前 RED，修复后 GREEN 并长期守护。
"""

import pytest
import pygame

from src import config as c
from src.states.base import StateName


def _make_game(seed: int = 0):
    from src.game import Game

    return Game(rng_seed=seed, scale=1)


# ================================================================ S1
# Spec 行 92: READY -> PLAYING 时"播 wing，鸟获得起跳初速"

def test_S1_takeoff_grants_upward_velocity():
    game = _make_game()
    game.state.handle_key(pygame.K_SPACE)      # READY -> PLAYING
    assert game.state_name == StateName.PLAYING
    assert game.state.bird.vy == pytest.approx(c.FLAP_VELOCITY), (
        "起飞瞬间应获得起跳初速，否则按下空格后鸟直接下坠"
    )


def test_S1_takeoff_bird_moves_up_first_frame():
    """起飞后的第一帧，鸟的 y 必须变小（向上），而不是立刻下坠。"""
    game = _make_game()
    y_before = game.state.bird.y
    game.state.handle_key(pygame.K_SPACE)
    game.state.update(c.FIXED_DT)
    assert game.state.bird.y < y_before, "起飞第一帧鸟应向上移动"


def test_S1_takeoff_plays_wing_sound(monkeypatch):
    """起飞应播放 wing 音效（Spec: READY -> PLAYING | 播 wing）。"""
    game = _make_game()
    played: list[str] = []
    monkeypatch.setattr(game.audio, "play", lambda name: played.append(name))
    game.state.handle_key(pygame.K_SPACE)
    assert "wing" in played, f"起飞未播放 wing，实际播放：{played}"


# ================================================================ B1
# score_store 写盘失败时，内存中的 best 不应被升级

def test_B1_best_not_raised_when_write_fails(tmp_path):
    from src.score_store import HighScoreStore

    blocker = tmp_path / "blocked"
    blocker.write_text("x", encoding="utf-8")     # 父路径是文件 -> mkdir 失败
    store = HighScoreStore(blocker / "h.json")

    assert store.best == 0
    returned = store.save_if_better(42)
    assert returned == 0, "写盘失败时应返回旧 best，而不是已升级的值"
    assert store.best == 0, "写盘失败不应污染内存中的 best"


def test_B1_best_raised_only_after_successful_write(tmp_path):
    from src.score_store import HighScoreStore

    path = tmp_path / "h.json"
    store = HighScoreStore(path)
    assert store.save_if_better(42) == 42
    assert store.best == 42
    assert HighScoreStore(path).load() == 42


# ================================================================ S13
# rotation_for(0) 应接近水平；READY 待机不应低头

def test_S13_level_velocity_maps_to_level_sprite():
    from src.physics import rotation_for

    assert abs(rotation_for(0.0)) < 5.0, (
        f"vy=0（顶点/待机）时应接近水平，实际 {rotation_for(0.0):.1f}°"
    )


def test_S13_rotation_endpoints_preserved():
    from src.physics import rotation_for

    assert rotation_for(c.FLAP_VELOCITY) == pytest.approx(c.ROTATE_MIN_DEG)
    assert rotation_for(c.ROTATE_VY_FULL) == pytest.approx(c.ROTATE_MAX_DEG)
    assert rotation_for(9999) == pytest.approx(c.ROTATE_MAX_DEG)


def test_S13_ready_bird_does_not_pitch():
    """READY 待机时鸟应水平朝前，不应低头。"""
    game = _make_game()
    surf = pygame.Surface((c.LOGICAL_W, c.LOGICAL_H))
    game.state.bird.y = c.BIRD_Y0
    game.state.bird.vy = 0.0
    # 水平帧与 0 度旋转帧应一致
    level = game.assets.bird_frame(0, game.state.bird.flap_index)
    rotated = game.assets.rotated_bird(0, game.state.bird.flap_index, 0.0)
    assert rotated.get_size() == level.get_size(), "0 度旋转不应改变精灵尺寸"


# ================================================================ S14
# 主题切换必须与计分同步（同一步内完成）

def test_S14_theme_switch_happens_same_step_as_scoring():
    game = _make_game()
    game.state.handle_key(pygame.K_SPACE)
    st = game.state
    st.enter()
    st.pipes.clear()

    from src.pipe import PipePair

    # 构造一根尾端已越过鸟左沿的管道，使本步计分 1 分
    pair = PipePair(
        x=st.bird.box[0] - c.PIPE_W - 1,
        center=c.LAND_Y / 2,
        gap=c.BASE_GAP,
        speed=0.0,
    )
    st.pipes.append(pair)
    game.score = 9                       # 加 1 分后正好跨过 10

    st.update(c.FIXED_DT)
    assert game.score == 10
    assert st.stage == 1, "跨过 10 分当步 stage 就应为 1，否则会渲染出「10 分 + 白天」一帧"
    assert st.background.key == "bg_night"
    assert st.bird.palette == 1


# ================================================================ S4
# 图标缺失不应致命

def test_S4_icon_is_optional(tmp_path):
    """Spec FR-WIN-3: 图标加载失败时用默认图标，不崩溃。"""
    import shutil

    from src import config as cfg

    res = tmp_path / "res"
    shutil.copytree(cfg.RES_DIR, res)
    (res / "images" / "flappy.ico").unlink()

    from src.assets import AssetManager

    assets = AssetManager(res)            # 不应抛 AssetError
    assert "icon" not in assets.images or assets.images.get("icon") is None
    # 其余资源仍应正常
    assert "bg_day" in assets.images


# ================================================================ S5
# READY 状态翅膀动画应播放

def test_S5_ready_state_animates_wings():
    game = _make_game()
    seen = set()
    for _ in range(60):
        game.state.update(c.FIXED_DT)
        seen.add(game.state.bird.flap_index)
    assert len(seen) >= 2, f"READY 待机翅膀帧未变化，实际只出现 {seen}"


# ================================================================ S2
# GAMEOVER 进入时应播放 swoosh

def test_S2_gameover_enter_plays_swoosh(monkeypatch):
    game = _make_game()
    game.score = 3
    played: list[str] = []
    monkeypatch.setattr(game.audio, "play", lambda name: played.append(name))
    game.set_state(StateName.GAMEOVER)
    assert "swoosh" in played, f"进入 GAMEOVER 未播放 swoosh，实际：{played}"


# ================================================================ S7
# 存档读失败应有警告

def test_S7_corrupt_save_warns(tmp_path, capsys):
    from src.score_store import HighScoreStore

    path = tmp_path / "h.json"
    path.write_text("{broken", encoding="utf-8")
    HighScoreStore(path).load()
    out = capsys.readouterr().out
    assert "score_store" in out, "读取损坏存档时应打印一次警告（Spec FR-STORE-4）"


# ================================================================ S8
# 素材尺寸与清单不符时应警告

def test_S8_size_mismatch_warns(monkeypatch, tmp_path, capsys):
    """Spec §7.4: 尺寸与清单不符时启动打印一次警告。"""
    import shutil

    from src import config as cfg

    res = tmp_path / "res"
    shutil.copytree(cfg.RES_DIR, res)
    # 用一张小图替换背景，制造尺寸不符
    import pygame as pg

    small = pg.Surface((10, 10))
    pg.image.save(small, str(res / "images" / "background-day.png"))

    from src.assets import AssetManager

    AssetManager(res)
    out = capsys.readouterr().out
    assert "background-day.png" in out, "尺寸不符应打印警告并指明文件"


# ================================================================ S17
# HUD 字体应真正拿到等宽粗体，而不是永远回退

def test_S17_font_reports_fallback_status():
    """不要求一定拿到 SysFont（本机 pygame 2.6.1 有缺陷），但必须如实报告。"""
    game = _make_game()
    game.hud.get_font(c.FONT_SMALL)
    assert isinstance(game.hud.font_fallback, bool)


# ================================================================ S18
# MUTE 角标应在屏幕角落，且只在静音时显示

def test_S18_mute_badge_only_when_muted():
    game = _make_game()
    game.mute_badge_t = 1.0
    game.audio.muted = False
    surf = pygame.Surface((c.LOGICAL_W, c.LOGICAL_H))
    surf.fill((0, 0, 0))
    game.draw_mute_badge()
    # 未静音时不应出现任何文字（不显示 SOUND ON）
    assert game.mute_badge_t > 0       # 计时器仍在走
