from __future__ import annotations

import pygame

from .. import config as c
from ..bird import Bird
from ..difficulty import gap_for, level_for, next_gap_center, speed_for
from ..physics import is_dead
from ..pipe import PipePair
from .base import State, StateName


class PlayingState(State):
    name = StateName.PLAYING

    def __init__(self, game) -> None:
        super().__init__(game)
        self.bird = Bird(game.assets)
        self.background = game.background
        self.ground = game.ground
        self.pipes = game.pipes          # 同一个 list 对象（别名，不是拷贝）
        self.stage = 0
        self.dist_since_spawn = 0.0
        self.prev_center = c.LAND_Y / 2

    def enter(self) -> None:
        self.pipes.clear()
        self.dist_since_spawn = 0.0
        self.prev_center = c.LAND_Y / 2
        self.stage = self.game.score // c.THEME_EVERY
        self.background.set_stage(self.stage)
        self.bird.reset()
        self.bird.set_stage(self.stage)
        self.ground.reset()

    def handle_key(self, key: int) -> None:
        if key == pygame.K_SPACE:
            self.bird.flap()
            self.game.audio.play("wing")
        elif key == pygame.K_p:
            from .paused import PausedState

            self.game.set_state(StateName.PAUSED, PausedState(self.game, self))

    def update(self, dt: float) -> None:
        level = level_for(self.game.score)
        speed = speed_for(level)
        gap = gap_for(level)

        self.bird.update(dt)

        for pipe in self.pipes:
            pipe.update(dt)
        self.pipes[:] = [p for p in self.pipes if not p.is_off_screen()]

        self.dist_since_spawn += speed * dt
        while self.dist_since_spawn >= c.PIPE_SPACING:
            self.dist_since_spawn -= c.PIPE_SPACING
            center = next_gap_center(self.prev_center, gap, self.game.rng)
            self.pipes.append(PipePair(c.PIPE_SPAWN_X, center, gap, speed))
            self.prev_center = center

        self.ground.update(dt, speed)

        new_stage = self.game.score // c.THEME_EVERY
        if new_stage != self.stage:
            self.stage = new_stage
            self.background.set_stage(self.stage)
            self.bird.set_stage(self.stage)

        bird_left = self.bird.box[0]
        for pipe in self.pipes:
            if pipe.try_score(bird_left):
                self.game.score += 1
                self.game.audio.play("point")

        geoms = [(p.x, p.center, p.gap) for p in self.pipes]
        if is_dead(self.bird.box, geoms, c.LAND_Y):
            from .dying import DyingState

            self.game.audio.play("hit")
            self.game.set_state(
                StateName.DYING, DyingState(self.game, self.bird, self.pipes, self.ground)
            )

    def draw(self, surface: pygame.Surface) -> None:
        self.background.draw(surface)
        for pipe in self.pipes:
            pipe.draw(surface, self.game.assets)
        self.bird.draw(surface)
        self.ground.draw(surface)
        self.game.hud.draw_score(surface, self.game.score)
