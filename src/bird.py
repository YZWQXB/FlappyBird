from __future__ import annotations

import math

import pygame

from . import config as c
from .assets import AssetManager
from .physics import hitbox, integrate, rotation_for

# 翅膀帧循环：mid → up → mid → down（索引 0=up 1=mid 2=down）
FLAP_CYCLE = (1, 2, 1, 0)


class Bird:
    def __init__(self, assets: AssetManager) -> None:
        self.assets = assets
        self.x = float(c.BIRD_X)
        self.y = float(c.BIRD_Y0)
        self.vy = 0.0
        self.palette = 0
        self.flap_index = FLAP_CYCLE[0]
        self._anim_t = 0.0
        self._cycle_pos = 0

    def reset(self) -> None:
        self.x = float(c.BIRD_X)
        self.y = float(c.BIRD_Y0)
        self.vy = 0.0
        self.palette = 0
        self.flap_index = FLAP_CYCLE[0]
        self._anim_t = 0.0
        self._cycle_pos = 0

    def flap(self) -> None:
        self.vy = c.FLAP_VELOCITY

    def set_stage(self, stage: int) -> None:
        self.palette = stage % len(c.PALETTE_ORDER)

    def update(self, dt: float) -> None:
        self.vy, self.y = integrate(self.vy, self.y, dt)
        self._anim_t += dt
        while self._anim_t >= c.FLAP_FRAME_TIME:
            self._anim_t -= c.FLAP_FRAME_TIME
            self._cycle_pos = (self._cycle_pos + 1) % len(FLAP_CYCLE)
            self.flap_index = FLAP_CYCLE[self._cycle_pos]

    def float_motion(self, elapsed: float) -> None:
        """READY 待机：正弦上下浮动，不参与物理。"""
        self.y = c.BIRD_Y0 + math.sin(elapsed * c.BIRD_FLOAT_W) * c.BIRD_FLOAT_AMP

    @property
    def box(self):
        return hitbox(self.x, self.y)

    def draw(self, surface: pygame.Surface) -> None:
        frame = self.assets.bird_frame(self.palette, self.flap_index)
        if c.ROTATE_SPRITE:
            frame = self.assets.rotated_bird(
                self.palette, self.flap_index, rotation_for(self.vy)
            )
        rect = frame.get_rect(center=(round(self.x), round(self.y)))
        surface.blit(frame, rect)
