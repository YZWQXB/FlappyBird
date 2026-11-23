from __future__ import annotations

import pygame

from . import config as c
from .assets import AssetManager


class Ground:
    """地面平铺滚动。

    offset 保持浮点亚像素（否则低速/提速后地面与管道速度会不一致），
    仅在 draw 时取整，避免接缝出现 1px 抖动。
    """

    def __init__(self, assets: AssetManager) -> None:
        self.assets = assets
        self.offset = 0.0

    def reset(self) -> None:
        self.offset = 0.0

    def update(self, dt: float, speed: float) -> None:
        tile = c.LAND_TILE_W
        self.offset = (self.offset - speed * dt) % tile
        # Python 的 % 对负数返回非负结果，需要再折回 [-tile, 0)
        if self.offset > 0:
            self.offset -= tile

    def draw_x(self) -> int:
        """绘制起点（整像素）。"""
        return round(self.offset)

    def draw(self, surface: pygame.Surface) -> None:
        tile = self.assets.image("land")
        x = self.draw_x() - c.LAND_TILE_W
        while x < c.LOGICAL_W:
            surface.blit(tile, (x, c.LAND_Y))
            x += c.LAND_TILE_W
