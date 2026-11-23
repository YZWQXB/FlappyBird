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
        # 待机时翅膀也要扇动（Spec 行 203：0.1s/帧循环）
        self.bird.update_animation(dt)
        self.bird.float_motion(self.elapsed)
        self.game.ground.update(dt, c.BASE_SPEED)

    def handle_key(self, key: int) -> None:
        if key == pygame.K_SPACE:
            # Spec FR-STATE 行 92：READY -> PLAYING 应"播 wing，鸟获得起跳初速"
            self.game.audio.play("wing")
            self.game.set_state(StateName.PLAYING)
            # enter() 把鸟 reset 到 vy=0，初速必须在 enter 之后施加。
            # 用 getattr 兜底：测试替身可能没有真实 state 对象。
            begin = getattr(self.game.state, "begin_takeoff", None)
            if begin is not None:
                begin()

    def draw(self, surface: pygame.Surface) -> None:
        # 提示图夹在背景与小鸟之间（保持 v1.0 的视觉层次）
        self.game.background.draw(surface)
        msg = self.game.assets.image("msg_ready")
        surface.blit(msg, ((c.LOGICAL_W - msg.get_width()) // 2, c.READY_MSG_Y))
        self.bird.draw(surface)
        self.game.ground.draw(surface)
        self.game.hud.draw_score(surface, self.game.score)
