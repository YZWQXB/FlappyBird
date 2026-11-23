from __future__ import annotations

import pygame

from .. import config as c
from .base import State, StateName


class ReadyState(State):
    name = StateName.READY

    def __init__(self, game) -> None:
        super().__init__(game)
        self.elapsed = 0.0
        from ..bird import Bird

        self.bird = Bird(game.assets)
        self.bird.set_stage(0)

    def enter(self) -> None:
        self.game.audio.play("swoosh")
        self.game.reset_round()
        self.elapsed = 0.0
        self.bird.reset()

    def update(self, dt: float) -> None:
        self.elapsed += dt
        self.bird.float_motion(self.elapsed)
        self.game.ground.update(dt, c.BASE_SPEED)

    def handle_key(self, key: int) -> None:
        if key == pygame.K_SPACE:
            self.game.set_state(StateName.PLAYING)

    def draw(self, surface: pygame.Surface) -> None:
        self.game.background.draw(surface)
        msg = self.game.assets.image("msg_ready")
        surface.blit(msg, ((c.LOGICAL_W - msg.get_width()) // 2, 96))
        self.bird.draw(surface)
        self.game.ground.draw(surface)
        self.game.hud.draw_score(surface, self.game.score)
