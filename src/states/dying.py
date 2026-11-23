from __future__ import annotations

import pygame

from .. import config as c
from .base import State, StateName


class DyingState(State):
    """撞击后的坠落阶段：只推进小鸟，管道与地面静止；落地后进入 GAMEOVER。

    注意音效归属：
    - `hit`（撞击瞬间）由 PlayingState 在迁移到本状态**之前**播放；
    - `die`（坠落触地）由本状态的 update 在落地那一刻播放。
    这样划分是因为 hit 属于"碰撞发生"这一事件，而碰撞检测在 PlayingState。
    """

    name = StateName.DYING

    def __init__(self, game, bird, pipes, ground) -> None:
        super().__init__(game)
        self.bird = bird
        self.pipes = pipes
        self.ground = ground
        self.landed = False

    def enter(self) -> None:
        self.landed = False

    def handle_key(self, key: int) -> None:
        """DYING 期间忽略 SPACE/P（不可空中暂停），仅 ESC 由 Game 处理。"""

    def update(self, dt: float) -> None:
        if self.landed:
            return
        from ..physics import integrate

        self.bird.vy, self.bird.y = integrate(self.bird.vy, self.bird.y, dt)
        box = self.bird.box
        if box[1] + box[3] >= c.LAND_Y:
            self.landed = True
            self.game.best = self.game.store.save_if_better(self.game.score)
            self.game.audio.play("die")
            # 不传实例：交给 Game 构建并执行 enter()，以捕获本局分数与 best
            self.game.set_state(StateName.GAMEOVER)

    def draw(self, surface: pygame.Surface) -> None:
        self.game.background.draw(surface)
        for pipe in self.pipes:
            pipe.draw(surface, self.game.assets)
        self.bird.draw(surface)
        self.ground.draw(surface)
        self.game.hud.draw_score(surface, self.game.score)
