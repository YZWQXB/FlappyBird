from __future__ import annotations

import random

import pygame

from . import config as c
from .assets import AssetManager
from .audio import AudioManager
from .display import init_window
from .hud import Hud
from .score_store import HighScoreStore
from .states.base import State, StateName
from .states.dying import DyingState
from .states.gameover import GameOverState
from .states.paused import PausedState
from .states.playing import PlayingState
from .states.ready import ReadyState


class Game:
    def __init__(self, rng_seed: int | None = None, scale: int | None = None) -> None:
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        if scale is None:
            self.screen, self.scale = init_window()
        else:
            self.screen = pygame.display.set_mode(
                (c.LOGICAL_W * scale, c.LOGICAL_H * scale)
            )
            pygame.display.set_caption(c.TITLE)
            self.scale = scale
        self.canvas = pygame.Surface((c.LOGICAL_W, c.LOGICAL_H))
        self.assets = AssetManager(c.RES_DIR)
        try:
            pygame.display.set_icon(self.assets.image("icon"))
        except pygame.error:
            pass
        self.audio = AudioManager.create(self.assets.sound_paths)
        self.store = HighScoreStore(c.SAVE_FILE)
        self.best = self.store.best
        self.hud = Hud(self.assets)
        self.rng = random.Random(rng_seed)
        self.clock = pygame.time.Clock()
        self.score = 0
        self.stage = 0
        self.pipes: list = []
        self.mute_badge_t = 0.0
        from .background import Background
        from .ground import Ground

        self.background = Background(self.assets)
        self.ground = Ground(self.assets)
        self.state_name: StateName = StateName.READY
        self.state: State = ReadyState(self)
        self.state.enter()

    # --- 状态切换（唯一入口）---
    def set_state(self, name: StateName, state: State | None = None) -> None:
        """挂载新状态。

        传入既有实例（暂停恢复）时只挂载、不调用 enter()，否则会重置该状态的
        内部进度（PlayingState.enter 会清空管道并重置鸟的位置）。
        """
        previous = getattr(self, "state", None)
        if state is None:
            state = self._build_state(name)
            self.state_name = name
            self.state = state
            if previous is not None and previous is not state:
                previous.exit()          # 让基类的 exit() 契约真正生效
            state.enter()
        else:
            self.state_name = name
            self.state = state

    def _build_state(self, name: StateName) -> State:
        builders = {
            StateName.READY: ReadyState,
            StateName.PLAYING: PlayingState,
            StateName.GAMEOVER: GameOverState,
        }
        if name not in builders:
            raise ValueError(f"{name} 需要携带上下文实例，不能单独构建")
        return builders[name](self)

    def reset_round(self) -> None:
        self.score = 0
        self.stage = 0
        self.pipes.clear()
        self.background.set_stage(0)
        self.ground.reset()
        self.mute_badge_t = 0.0        # UI 计时器随新一局归零（静音偏好本身保留）

    # --- 主循环 ---
    def run(self, max_frames: int | None = None) -> int:
        """主循环。max_frames 非空时跑满指定帧数后自动退出（无头冒烟用）。"""
        accumulator = 0.0
        running = True
        frame_count = 0
        while running:
            if max_frames is not None and frame_count >= max_frames:
                break
            frame_count += 1
            frame_dt = self.clock.tick(c.FPS) / 1000.0
            running = self.handle_events()
            accumulator += min(frame_dt, c.MAX_FRAME_DT)
            steps = 0
            while accumulator >= c.FIXED_DT and steps < c.MAX_STEPS_PER_FRAME:
                self.state.update(c.FIXED_DT)
                accumulator -= c.FIXED_DT
                steps += 1
            if steps >= c.MAX_STEPS_PER_FRAME:
                accumulator = 0.0
            self.draw_frame(frame_dt)
            pygame.display.flip()
        self.audio.quit()
        pygame.quit()
        return c.EXIT_OK

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_m:
                    # 全局键：静音在任何状态下都应生效（Spec FR-INPUT）
                    self.audio.toggle_mute()
                    self.mute_badge_t = c.MUTE_BADGE_SECONDS
                    continue
                self.state.handle_key(event.key)
            elif (
                event.type == getattr(pygame, "WINDOWFOCUSLOST", -1)
                and c.PAUSE_ON_FOCUS_LOST
                and getattr(self, "state_name", None) == StateName.PLAYING
            ):
                self.set_state(StateName.PAUSED, PausedState(self, self.state))
        return True

    def update_mute_badge(self, frame_dt: float) -> None:
        if self.mute_badge_t <= 0:
            return
        self.mute_badge_t = max(0.0, self.mute_badge_t - frame_dt)

    def draw_mute_badge(self) -> None:
        """静音角标：仅静音时显示，固定在屏幕右上角（Spec FR-INPUT 行 81）。"""
        if self.mute_badge_t <= 0 or not self.audio.muted:
            return
        self.hud.draw_text(
            self.canvas, "MUTE", c.FONT_SMALL, c.MUTE_BADGE_Y, x_center=c.MUTE_BADGE_X
        )

    def draw_frame(self, frame_dt: float = 0.0) -> None:
        self.state.draw(self.canvas)
        self.update_mute_badge(frame_dt)
        self.draw_mute_badge()
        pygame.transform.scale(self.canvas, self.screen.get_size(), self.screen)


