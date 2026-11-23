"""缺陷回归测试：每个用例对应 docs/testing/缺陷报告.md 中的一个 ID。

修复前这些用例全部为 RED，修复后应全绿并长期守护。
"""

import os
import random

import pygame
import pytest

from src import config as c
from src.states.base import StateName


# ---------------------------------------------------------------- helpers

def _make_game(seed: int = 0):
    from src.game import Game

    return Game(rng_seed=seed, scale=1)


def _enter_playing(game):
    game.state.handle_key(pygame.K_SPACE)
    assert game.state_name == StateName.PLAYING
    return game.state


def _kill_to_gameover(game):
    """让当前局以撞地方式结束，返回 GAMEOVER 状态对象。"""
    st = game.state
    st.pipes.clear()
    st.bird.y = c.LAND_Y
    st.update(c.FIXED_DT)
    assert game.state_name == StateName.DYING
    for _ in range(300):
        game.state.update(c.FIXED_DT)
        if game.state_name == StateName.GAMEOVER:
            break
    assert game.state_name == StateName.GAMEOVER
    return game.state


def _render(state_obj) -> pygame.Surface:
    surf = pygame.Surface((c.LOGICAL_W, c.LOGICAL_H))
    surf.fill((255, 0, 255))          # 品红底：任何绘制都会覆盖它
    state_obj.draw(surf)
    return surf


def _count_in_rect(surf, rect, colors) -> int:
    x0, y0, x1, y1 = rect
    return sum(
        1
        for y in range(y0, y1)
        for x in range(x0, x1)
        if surf.get_at((x, y))[:3] in colors
    )


# ================================================================ D-01
# M 静音键必须在 5 个状态下都生效（Spec FR-INPUT「任意状态生效」）

def _press_m_via_events(game, key=pygame.K_m):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
    game.handle_events()


@pytest.mark.parametrize("target_state", ["READY", "PLAYING", "PAUSED", "DYING", "GAMEOVER"])
def test_D01_mute_key_works_in_every_state(target_state):
    game = _make_game()
    if target_state != "READY":
        _enter_playing(game)

    if target_state == "PAUSED":
        game.state.handle_key(pygame.K_p)
    elif target_state == "DYING":
        game.state.pipes.clear()
        game.state.bird.y = c.LAND_Y
        game.state.update(c.FIXED_DT)
    elif target_state == "GAMEOVER":
        _kill_to_gameover(game)

    assert game.state_name.name == target_state, game.state_name.name

    before = game.audio.muted
    _press_m_via_events(game)
    assert game.audio.muted is not before, f"{target_state} 下 M 键未生效"
    assert game.mute_badge_t == pytest.approx(c.MUTE_BADGE_SECONDS)


def test_D01_mute_is_not_double_toggled():
    """M 键若同时被 Game 与 PlayingState 处理，会切两次等于没变。"""
    game = _make_game()
    _enter_playing(game)
    before = game.audio.muted
    _press_m_via_events(game)
    assert game.audio.muted is not before


def test_D01_mute_does_not_reach_esc_behaviour():
    """M 键被 Game 拦截后，不应该再把事件下发给状态造成副作用。"""
    game = _make_game()
    st = _enter_playing(game)
    bird_vy = st.bird.vy
    _press_m_via_events(game)
    assert st.bird.vy == bird_vy


# ================================================================ D-02
# 重开后 MUTE 角标计时器必须归零；静音偏好本身应保留

def test_D02_mute_badge_reset_on_restart():
    game = _make_game()
    _enter_playing(game)
    _press_m_via_events(game)              # M 键由 Game 层全局处理
    assert game.mute_badge_t > 0

    _kill_to_gameover(game)
    game.state.handle_key(pygame.K_r)
    assert game.state_name == StateName.READY
    assert game.mute_badge_t == 0.0, "重开后角标计时器应归零"
    assert game.audio.muted is True, "静音是用户偏好，跨局应保留"


# ================================================================ D-03
# 存档写入侧必须与读取侧对称校验 0 <= best < 10^6

def test_D03_save_rejects_out_of_range_score(tmp_path):
    from src.score_store import HighScoreStore

    path = tmp_path / "highscore.json"
    store = HighScoreStore(path)
    assert store.save_if_better(10**6) == 0
    assert not path.exists(), "超范围分数不应落盘"
    assert HighScoreStore(path).load() == 0


def test_D03_save_rejects_negative_score(tmp_path):
    from src.score_store import HighScoreStore

    store = HighScoreStore(tmp_path / "h.json")
    assert store.save_if_better(-5) == 0
    assert store.best == 0


def test_D03_save_accepts_max_valid_score(tmp_path):
    from src.score_store import HighScoreStore

    path = tmp_path / "h.json"
    store = HighScoreStore(path)
    assert store.save_if_better(10**6 - 1) == 10**6 - 1
    assert HighScoreStore(path).load() == 10**6 - 1


# ================================================================ D-04
# GAMEOVER 必须保留管道现场（与 DYING 画面一致）

def test_D04_gameover_draws_pipes():
    from src.pipe import PipePair

    game = _make_game()
    st = _enter_playing(game)
    st.pipes.clear()
    st.pipes.append(PipePair(x=200.0, center=250.0, gap=c.BASE_GAP, speed=0.0))
    st.bird.y = 256
    with_pipe = _render(st)

    st.pipes.clear()
    without_pipe = _render(st)

    diff = sum(
        1
        for y in range(c.LAND_Y)
        for x in range(c.LOGICAL_W)
        if with_pipe.get_at((x, y)) != without_pipe.get_at((x, y))
    )
    assert diff > 0, "PLAYING 画面应绘制管道（对照基线）"

    # GAMEOVER 也应绘制 game.pipes
    game.pipes.append(PipePair(x=200.0, center=250.0, gap=c.BASE_GAP, speed=0.0))
    game.pipes.append(PipePair(x=80.0, center=180.0, gap=c.BASE_GAP, speed=0.0))
    game.score = 3
    game.set_state(StateName.GAMEOVER)
    go_with = _render(game.state)
    game.pipes.clear()
    go_without = _render(game.state)
    go_diff = sum(
        1
        for y in range(c.LAND_Y)
        for x in range(c.LOGICAL_W)
        if go_with.get_at((x, y)) != go_without.get_at((x, y))
    )
    assert go_diff > 0, "GAMEOVER 画面未绘制管道（D-04 未修复）"


# ================================================================ D-06
# 结束面板必须显示 0 分（首次游玩 best=0 是常态）

def _paper_pixels(state_obj, y0: int, h: int = 36) -> int:
    """数字精灵的主色是 PAPER 白，统计条带内的白色像素数即可判断"画了没"。"""
    surf = _render(state_obj)
    return sum(
        1
        for y in range(y0, y0 + h)
        for x in range(c.LOGICAL_W)
        if surf.get_at((x, y))[:3] == c.PAPER
    )


def test_D06_gameover_shows_zero_best():
    """best=0 时 BEST 区必须出现数字像素（实测 8 分时为 532，0 分时为 0）。"""
    game = _make_game()
    game.score = 0
    game.best = 0
    game.set_state(StateName.GAMEOVER)

    assert _paper_pixels(game.state, c.BEST_PANEL_Y) > 0, (
        "GAMEOVER 的 BEST=0 没有渲染数字（像素数为 0）→ D-06 未修复"
    )


def test_D06_gameover_shows_zero_final_score():
    game = _make_game()
    game.score = 0
    game.best = 0
    game.set_state(StateName.GAMEOVER)

    assert _paper_pixels(game.state, c.SCORE_PANEL_Y) > 0, (
        "GAMEOVER 的本局 0 分没有渲染数字（像素数为 0）→ D-06 未修复"
    )


def test_D04_gameover_dim_overlay_keeps_text_readable():
    """保留管道现场后，必须压暗背景，否则文字与管道颜色互相干扰。"""
    game = _make_game()
    game.score = 5
    game.best = 9
    game.pipes.clear()
    game.set_state(StateName.GAMEOVER)
    surf = _render(game.state)

    # 取一个必定被背景覆盖的点（左上角），比较它与原始背景色
    raw = game.assets.image("bg_day").get_at((5, 5))[:3]
    now = surf.get_at((5, 5))[:3]
    assert now != raw, "GAMEOVER 背景未被压暗，结算文字可读性无保障"
    assert sum(now) < sum(raw), "GAMEOVER 遮罩应当压暗而非提亮"


def test_D04_gameover_has_solid_score_panel():
    """结算面板需要实心底板，否则分数/ BEST 文字压在管道纹理上难以辨认。"""
    game = _make_game()
    game.score = 5
    game.best = 9
    game.set_state(StateName.GAMEOVER)
    surf = _render(game.state)

    # 判据 1：面板四个内角必须是同一种底色（管道纹理无法满足）
    inset = c.PANEL_BORDER + 2
    corners = [
        surf.get_at((c.PANEL_X + inset, c.PANEL_Y + inset))[:3],
        surf.get_at((c.PANEL_X + c.PANEL_W - inset, c.PANEL_Y + inset))[:3],
        surf.get_at((c.PANEL_X + inset, c.PANEL_Y + c.PANEL_H - inset))[:3],
        surf.get_at((c.PANEL_X + c.PANEL_W - inset, c.PANEL_Y + c.PANEL_H - inset))[:3],
    ]
    assert len(set(corners)) == 1, f"面板四角颜色不一致 {corners}，未覆盖实心底板"
    assert corners[0] == c.PANEL_FILL, f"面板底色 {corners[0]} 应为 {c.PANEL_FILL}"

    # 判据 2：面板底色不能等于天空色或地面色，否则等于没画
    assert corners[0] not in ((78, 192, 202),), "面板底色不应等于天空色"


def test_D04_panel_border_is_ink():
    game = _make_game()
    game.set_state(StateName.GAMEOVER)
    surf = _render(game.state)
    border_px = surf.get_at((c.PANEL_X + 1, c.PANEL_Y + c.PANEL_H // 2))[:3]
    assert border_px == c.INK, f"面板边框应为 INK {c.INK}，实际 {border_px}"


def test_D06_nonzero_still_renders():
    """对照：非 0 值本来就能画（防止修复时把正常路径改坏）。"""
    game = _make_game()
    game.score = 7
    game.best = 8
    game.set_state(StateName.GAMEOVER)
    assert _paper_pixels(game.state, c.BEST_PANEL_Y) > 0
    assert _paper_pixels(game.state, c.SCORE_PANEL_Y) > 0


def test_D06_zero_is_still_hidden_in_playing_hud():
    """回归：'PLAYING 时 0 分不显示'的规则不能被 allow_zero 破坏。"""
    game = _make_game()
    blank = pygame.Surface((c.LOGICAL_W, c.LOGICAL_H))
    blank.fill((0, 0, 255))
    game.hud.draw_score(blank, 0)
    lit = sum(
        1
        for y in range(c.SCORE_Y, c.SCORE_Y + 36)
        for x in range(c.LOGICAL_W)
        if blank.get_at((x, y))[:3] != (0, 0, 255)
    )
    assert lit == 0, "PLAYING 的 0 分仍应不显示"


# ================================================================ D-09
# Game 必须在实例上显式初始化 state_name，不依赖类属性兜底

def test_D09_state_name_initialised_on_instance():
    game = _make_game()
    assert "state_name" in game.__dict__, "state_name 未在实例上初始化"


# ================================================================ D-11
# 音效最小间隔规则（Spec FR-AUDIO-4）必须有可测的实现

def test_D11_sfx_gap_rule_is_enforced():
    from src.audio import sfx_gap_ok

    # 同一音效、间隔不足 -> 不允许
    assert sfx_gap_ok("hit", now_ms=1000, last_ms=1000) is False
    assert sfx_gap_ok("hit", now_ms=1100, last_ms=1000) is False
    # 间隔足够 -> 允许
    assert sfx_gap_ok("hit", now_ms=1201, last_ms=1000) is True
    # 从未播放过 -> 允许
    assert sfx_gap_ok("hit", now_ms=0, last_ms=None) is True
    # 不受限制的音效总是允许
    assert sfx_gap_ok("wing", now_ms=1000, last_ms=1000) is True


def test_D11_dead_config_constants_removed():
    """GROUND_SPEED / MAX_GAP_HALF 是死代码，不应再出现在 config 中。"""
    from src import config as cfg

    assert not hasattr(cfg, "GROUND_SPEED")
    assert not hasattr(cfg, "MAX_GAP_HALF")
    # SFX_PRIORITY_GAP_MS 保留，因为它已真正实现
    assert hasattr(cfg, "SFX_PRIORITY_GAP_MS")

def test_mute_key_not_handled_in_state_layer():
    """架构约束：M 是全局键，只应在 Game.handle_events 处理。

    若有人在状态里再加一遍 K_m 分支，会与 Game 层形成双次切换（切了两次=没切）。
    本用例扫描源码防止回归。
    """
    from pathlib import Path

    import src

    states_dir = Path(src.__file__).parent / "states"
    offenders = []
    for py in sorted(states_dir.glob("*.py")):
        text = py.read_text(encoding="utf-8")
        if "K_m" in text:
            offenders.append(py.name)
    assert not offenders, f"M 键不应出现在状态层，但发现：{offenders}"
