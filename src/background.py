from __future__ import annotations

import pygame

from .assets import AssetManager


class Background:
    def __init__(self, assets: AssetManager) -> None:
        self.assets = assets
        self.key = "bg_day"

    def set_stage(self, stage: int) -> None:
        self.key = self.key_for_stage(stage)

    @staticmethod
    def key_for_stage(stage: int) -> str:
        return "bg_day" if stage % 2 == 0 else "bg_night"

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.assets.image(self.key), (0, 0))
