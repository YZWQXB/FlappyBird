from __future__ import annotations

import pygame

from . import config as c
from .assets import AssetManager
from .physics import Box, pipe_boxes, should_score


class PipePair:
    """一对上下管道。几何以缝隙中心描述，绘制时上下各拼接 cap + body。"""

    def __init__(self, x: float, center: float, gap: float, speed: float) -> None:
        self.x = float(x)
        self.center = float(center)
        self.gap = float(gap)
        self.speed = float(speed)
        self.scored = False

    def update(self, dt: float) -> None:
        self.x -= self.speed * dt

    def boxes(self) -> tuple[Box, Box]:
        return pipe_boxes((self.x, self.center, self.gap), c.LAND_Y)

    def is_off_screen(self) -> bool:
        return self.x + c.PIPE_W <= 0

    def try_score(self, bird_left: float) -> bool:
        if self.scored or not should_score(self.x, bird_left):
            return False
        self.scored = True
        return True

    def draw(self, surface: pygame.Surface, assets: AssetManager) -> None:
        x = round(self.x)
        top_h = int(max(0, round(self.center - self.gap / 2)))
        bottom_y = round(self.center + self.gap / 2)
        bottom_h = int(max(0, round(c.LAND_Y - bottom_y)))

        # 上管：cap 贴着缝隙（倒置），body 从 cap 上方向顶部延伸
        if top_h >= c.PIPE_CAP_H:
            surface.blit(assets.pipe_cap(False), (x, top_h - c.PIPE_CAP_H))
            body_h = top_h - c.PIPE_CAP_H
            surface.blit(assets.pipe_body(body_h, False), (x + c.PIPE_BODY_X, 0))
        elif top_h > 0:
            surface.blit(assets.pipe_cap(False), (x, 0))

        # 下管：cap 贴着缝隙（正置），body 从 cap 下方延伸到地面
        if bottom_h >= c.PIPE_CAP_H:
            surface.blit(assets.pipe_cap(True), (x, bottom_y))
            body_h = bottom_h - c.PIPE_CAP_H
            surface.blit(
                assets.pipe_body(body_h, True),
                (x + c.PIPE_BODY_X, bottom_y + c.PIPE_CAP_H),
            )
        elif bottom_h > 0:
            surface.blit(assets.pipe_cap(True), (x, bottom_y))
