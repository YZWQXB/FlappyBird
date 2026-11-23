from __future__ import annotations

import pygame

from .. import config as c
from .base import State, StateName


class PausedState(State):
    name = StateName.PAUSED

    def __init__(self, game, snapshot) -> None:
        super().__init__(game)
        self.snapshot = snapshot      # 被暂停的 PlayingState 实例

    def enter(self) -> None:
        pass

    def handle_key(self, key: int) -> None:
        if key == pygame.K_p:
            # 直接挂载原 PlayingState 实例，不重复 enter（否则会清空管道、丢失速度）
            self.game.set_state(StateName.PLAYING, self.snapshot)

    def update(self, dt: float) -> None:
        """空实现：不推进任何实体（含地面），否则"暂停"时背景还在动。"""

    def draw(self, surface: pygame.Surface) -> None:
        self.snapshot.draw(surface)
        self.game.hud.overlay(surface)
        self.game.hud.draw_text(surface, "PAUSED", c.FONT_LARGE, 220)
        self.game.hud.draw_text(surface, "PRESS P TO RESUME", c.FONT_SMALL, 256)
