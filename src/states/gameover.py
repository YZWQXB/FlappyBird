from __future__ import annotations

import pygame

from .. import config as c
from .base import State, StateName


class GameOverState(State):
    name = StateName.GAMEOVER

    def __init__(self, game) -> None:
        super().__init__(game)
        self.final_score = 0
        self.best = 0

    def enter(self) -> None:
        # Spec FR-AUDIO: 进入 GAMEOVER 播 swoosh
        self.game.audio.play("swoosh")
        self.final_score = self.game.score
        self.best = self.game.best

    def handle_key(self, key: int) -> None:
        if key in (pygame.K_SPACE, pygame.K_r):
            self.game.reset_round()
            self.game.set_state(StateName.READY)   # ReadyState.enter 会播 swoosh

    def update(self, dt: float) -> None:
        pass

    @staticmethod
    def _draw_panel(surface: pygame.Surface) -> None:
        """像素风实心面板：填充 + 深色边框（无圆角、无渐变）。"""
        rect = pygame.Rect(c.PANEL_X, c.PANEL_Y, c.PANEL_W, c.PANEL_H)
        pygame.draw.rect(surface, c.INK, rect)
        inner = rect.inflate(-2 * c.PANEL_BORDER, -2 * c.PANEL_BORDER)
        pygame.draw.rect(surface, c.PANEL_FILL, inner)

    def draw(self, surface: pygame.Surface) -> None:
        self.game.background.draw(surface)
        # 保留管道现场：与 DYING 画面一致，避免结算瞬间画面突变
        for pipe in self.game.pipes:
            pipe.draw(surface, self.game.assets)
        self.game.ground.draw(surface)
        hud = self.game.hud
        # 压暗背景 + 实心结算底板：保证文字在管道纹理之上清晰可读
        hud.overlay(surface, alpha=c.GAMEOVER_OVERLAY_ALPHA)
        self._draw_panel(surface)
        msg = self.game.assets.image("msg_gameover")
        surface.blit(msg, ((c.LOGICAL_W - msg.get_width()) // 2, c.GAMEOVER_IMG_Y))
        hud.draw_number(surface, self.final_score, c.SCORE_PANEL_Y, allow_zero=True)
        hud.draw_text(
            surface, "BEST", c.FONT_SMALL, c.BEST_PANEL_Y - c.BEST_LABEL_OFFSET
        )
        hud.draw_number(surface, self.best, c.BEST_PANEL_Y, allow_zero=True)
        hud.draw_text(surface, "PRESS SPACE TO RESTART", c.FONT_SMALL, c.HINT_Y)
