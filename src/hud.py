from __future__ import annotations

import pygame

from . import config as c
from .assets import AssetManager


def number_width(hud: "Hud", value: int) -> int:
    if value <= 0:
        return 0
    widths = [hud.assets.digit(int(ch)).get_width() for ch in str(value)]
    return sum(widths) + c.DIGIT_GAP * (len(widths) - 1)


class Hud:
    def __init__(self, assets: AssetManager) -> None:
        self.assets = assets
        self._font_cache: dict[tuple[int, bool], pygame.font.Font] = {}
        self._outline_cache: dict[tuple[str, int, tuple], pygame.Surface] = {}

    # --- 字体（必须容忍 pygame 2.6.1 的 SysFont 缺陷）---
    def get_font(self, size: int, bold: bool = True) -> pygame.font.Font:
        key = (size, bold)
        font = self._font_cache.get(key)
        if font is None:
            try:
                font = pygame.font.SysFont(
                    ("consolas", "couriernew", "monospace"), size, bold=bold
                )
            except (TypeError, OSError, AttributeError, pygame.error):
                font = pygame.font.Font(None, size)
            self._font_cache[key] = font
        return font

    def text_surface(self, text: str, size: int, color: tuple = c.PAPER) -> pygame.Surface:
        key = (text, size, tuple(color))
        surf = self._outline_cache.get(key)
        if surf is None:
            font = self.get_font(size)
            glyph = font.render(text, True, color)
            surf = pygame.Surface(
                (glyph.get_width() + 2, glyph.get_height() + 2), pygame.SRCALPHA
            )
            dark = font.render(text, True, c.INK)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                surf.blit(dark, (1 + dx, 1 + dy))
            surf.blit(glyph, (1, 1))
            self._outline_cache[key] = surf
        return surf

    def draw_text(
        self, surface: pygame.Surface, text: str, size: int, y: int, x_center: int | None = None
    ) -> pygame.Rect:
        surf = self.text_surface(text, size)
        rect = surf.get_rect()
        rect.top = y
        rect.centerx = x_center if x_center is not None else c.LOGICAL_W // 2
        surface.blit(surf, rect)
        return rect

    # --- 数字 ---
    def draw_number(
        self,
        surface: pygame.Surface,
        value: int,
        y: int,
        x_center: int | None = None,
        allow_zero: bool = False,
    ) -> None:
        """绘制数字精灵。

        默认 0 不绘制（PLAYING 时 0 分不显示，Spec FR-SCORE-2）；
        GAMEOVER 面板需要显示 0 分，调用方传 allow_zero=True。
        """
        if value <= 0 and not allow_zero:
            return
        value = max(0, value)
        digits = str(value)
        total = number_width(self, value)
        x = (x_center if x_center is not None else c.LOGICAL_W // 2) - total // 2
        for ch in digits:
            glyph = self.assets.digit(int(ch))
            surface.blit(glyph, (x, y))
            x += glyph.get_width() + c.DIGIT_GAP

    def draw_score(self, surface: pygame.Surface, score: int) -> None:
        self.draw_number(surface, score, c.SCORE_Y)

    # --- 遮罩 ---
    def overlay(self, surface: pygame.Surface, alpha: int = c.OVERLAY_ALPHA) -> None:
        shade = pygame.Surface((c.LOGICAL_W, c.LOGICAL_H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, alpha))
        surface.blit(shade, (0, 0))
