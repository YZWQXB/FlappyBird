import random

import pygame
import pytest

from src import config as c
from src.states.base import State, StateName


class _NullStore:
    def save_if_better(self, score):
        return max(0, int(score))


class FakeGame:
    """只实现状态机需要的接口，便于无头测试（与真实 Game 的属性名保持一致）。"""

    def __init__(self, assets, audio):
        from src.background import Background
        from src.ground import Ground
        from src.hud import Hud

        self.assets = assets
        self.audio = audio
        self.hud = Hud(assets)
        self.background = Background(assets)
        self.ground = Ground(assets)
        self.score = 0
        self.best = 0
        self.stage = 0
        self.state_name = StateName.READY
        self.state = None
        self.pipes = []
        self.rng = random.Random(0)
        self.elapsed = 0.0
        self.mute_badge_t = 0.0
        self.store = _NullStore()

    def set_state(self, name, state=None):
        """state 非 None 时直接挂载（不重复 enter），用于暂停恢复。"""
        self.state_name = name
        if state is not None:
            self.state = state

    def reset_round(self):
        self.score = 0
        self.stage = 0
        self.pipes.clear()
        self.background.set_stage(0)
        self.ground.reset()


@pytest.fixture
def fake_game(assets):
    from src.audio import AudioManager

    return FakeGame(assets, AudioManager.disabled())


@pytest.fixture
def fake_game_factory(assets):
    from src.audio import AudioManager

    def _make():
        return FakeGame(assets, AudioManager.disabled())

    return _make


# ---------- READY ----------

def test_ready_to_playing_on_space(fake_game_factory):
    """READY 按空格 → PLAYING，且起飞时给鸟初速（审查缺陷 S1）。"""
    game = fake_game_factory()
    from src.states.ready import ReadyState
    from src.states.playing import PlayingState

    # FakeGame.set_state 只记录名字；这里补一个真实 state，模拟 Game 的行为
    state = ReadyState(game)

    def fake_set_state(name, obj=None):
        game.state_name = name
        game.state = obj if obj is not None else PlayingState(game)

    game.set_state = fake_set_state
    state.handle_key(pygame.K_SPACE)
    assert game.state_name == StateName.PLAYING
    assert game.state.bird.vy == pytest.approx(c.FLAP_VELOCITY), "起飞应获得初速"


def test_ready_ignores_other_keys(fake_game_factory):
    game = fake_game_factory()
    from src.states.ready import ReadyState

    state = ReadyState(game)
    for key in (pygame.K_p, pygame.K_r, pygame.K_m):
        state.handle_key(key)
    assert game.state_name == StateName.READY


# ---------- PLAYING ----------

def test_playing_space_flaps_and_scores_on_pass(fake_game_factory):
    game = fake_game_factory()
    from src.states.playing import PlayingState

    state = PlayingState(game)
    state.enter()
    state.handle_key(pygame.K_SPACE)
    assert state.bird.vy == pytest.approx(c.FLAP_VELOCITY)

    from src.pipe import PipePair

    pair = PipePair(
        x=state.bird.x - c.HITBOX_W / 2 - c.PIPE_W - 1,
        center=250.0,
        gap=110.0,
        speed=0.0,
    )
    state.pipes.append(pair)
    state.update(c.FIXED_DT)
    assert game.score == 1
    assert pair.scored is True


def test_playing_stage_changes_at_ten(fake_game_factory):
    game = fake_game_factory()
    from src.states.playing import PlayingState

    state = PlayingState(game)
    state.enter()
    game.score = 10
    state.update(c.FIXED_DT)
    assert state.stage == 1
    assert state.background.key == "bg_night"
    assert state.bird.palette == 1


def test_playing_stage_is_derived_from_score(fake_game_factory):
    game = fake_game_factory()
    from src.states.playing import PlayingState

    state = PlayingState(game)
    state.enter()
    for score, stage in ((0, 0), (9, 0), (10, 1), (19, 1), (20, 2), (30, 3)):
        game.score = score
        state.update(c.FIXED_DT)
        assert state.stage == stage


def test_playing_spawns_pipes_by_distance(fake_game_factory):
    game = fake_game_factory()
    from src.states.playing import PlayingState

    state = PlayingState(game)
    state.enter()
    assert len(state.pipes) == 0
    for _ in range(300):            # 5 秒，足够生成多根
        state.update(c.FIXED_DT)
        if len(state.pipes) >= 3:
            break
    assert len(state.pipes) >= 3


def test_playing_pipe_speed_does_not_change_after_level_up(fake_game_factory):
    game = fake_game_factory()
    from src.states.playing import PlayingState

    state = PlayingState(game)
    state.enter()
    for _ in range(120):            # 2 秒，确保生成第一根管道
        state.update(c.FIXED_DT)
        if state.pipes:
            break
    assert state.pipes, "2 秒内应生成至少一根管道"
    first = state.pipes[0]
    old_speed = first.speed
    game.score = 30                 # 直接跳到最高等级
    state.update(c.FIXED_DT)
    assert first.speed == old_speed  # 已在屏幕上的管道速度不变


def test_playing_collision_switches_to_dying(fake_game_factory):
    game = fake_game_factory()
    from src.states.playing import PlayingState

    state = PlayingState(game)
    state.enter()
    state.bird.y = c.LAND_Y - 1.0   # 直接撞地
    state.update(c.FIXED_DT)
    assert game.state_name == StateName.DYING


def test_playing_p_pauses(fake_game_factory):
    game = fake_game_factory()
    from src.states.playing import PlayingState

    state = PlayingState(game)
    state.enter()
    state.handle_key(pygame.K_p)
    assert game.state_name == StateName.PAUSED


def test_playing_state_does_not_handle_mute(fake_game_factory):
    """M 是全局键，由 Game.handle_events 统一处理（见 test_regressions.py::D01）。

    状态层若也处理，会与 Game 层形成双次切换（等于没切）。这里锁定该契约。
    """
    game = fake_game_factory()
    from src.states.playing import PlayingState

    state = PlayingState(game)
    state.enter()
    state.handle_key(pygame.K_m)
    assert game.audio.muted is False


# ---------- PAUSED ----------

def test_paused_freezes_positions(fake_game_factory):
    game = fake_game_factory()
    from src.states.paused import PausedState
    from src.states.playing import PlayingState

    playing = PlayingState(game)
    playing.enter()
    bird_y = playing.bird.y
    paused = PausedState(game, playing)
    paused.update(1.0)
    assert playing.bird.y == bird_y


def test_paused_p_resumes_same_playing_instance(fake_game_factory):
    game = fake_game_factory()
    from src.states.paused import PausedState
    from src.states.playing import PlayingState

    playing = PlayingState(game)
    playing.enter()
    game.state = playing
    paused = PausedState(game, playing)
    paused.handle_key(pygame.K_p)
    assert game.state_name == StateName.PLAYING
    assert game.state is playing        # 恢复原实例，不丢鸟的速度


# ---------- DYING ----------

def test_dying_ignores_space_and_p(fake_game_factory):
    game = fake_game_factory()
    from src.bird import Bird
    from src.states.dying import DyingState

    dying = DyingState(game, Bird(game.assets), [], game.ground)
    game.state_name = StateName.DYING
    dying.handle_key(pygame.K_SPACE)
    dying.handle_key(pygame.K_p)
    assert game.state_name == StateName.DYING


def test_dying_falls_and_lands_then_gameover(fake_game_factory):
    game = fake_game_factory()
    from src.bird import Bird
    from src.states.dying import DyingState

    bird = Bird(game.assets)
    bird.y = c.LAND_Y - 60.0
    dying = DyingState(game, bird, [], game.ground)
    for _ in range(240):
        dying.update(c.FIXED_DT)
        if game.state_name == StateName.GAMEOVER:
            break
    assert game.state_name == StateName.GAMEOVER


# ---------- GAMEOVER ----------

def test_gameover_space_restarts_and_resets(fake_game_factory):
    game = fake_game_factory()
    game.score = 42
    game.stage = 4
    from src.states.gameover import GameOverState

    state = GameOverState(game)
    state.handle_key(pygame.K_SPACE)
    assert game.score == 0 and game.stage == 0
    assert game.state_name == StateName.READY


def test_gameover_r_also_restarts(fake_game_factory):
    game = fake_game_factory()
    from src.states.gameover import GameOverState

    GameOverState(game).handle_key(pygame.K_r)
    assert game.state_name == StateName.READY


def test_gameover_ignores_other_keys(fake_game_factory):
    game = fake_game_factory()
    game.state_name = StateName.GAMEOVER
    from src.states.gameover import GameOverState

    state = GameOverState(game)
    state.handle_key(pygame.K_p)
    assert game.state_name == StateName.GAMEOVER


# ---------- 计时器 ----------

def test_mute_badge_timer_decays():
    t = c.MUTE_BADGE_SECONDS
    frames = 0
    while t > 0:
        t -= c.FIXED_DT
        frames += 1
    assert 90 <= frames <= 91
    assert t <= 1e-9


def test_state_base_is_abstract_contract():
    class Dummy(State):
        name = StateName.READY

    d = Dummy(object())
    assert d.handle_key(pygame.K_SPACE) is None
    assert d.update(0.016) is None
    assert d.enter() is None and d.exit() is None
