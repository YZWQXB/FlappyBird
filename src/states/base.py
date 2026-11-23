from __future__ import annotations

from enum import Enum, auto


class StateName(Enum):
    READY = auto()
    PLAYING = auto()
    PAUSED = auto()
    DYING = auto()
    GAMEOVER = auto()


class State:
    """五态共同契约：enter/exit 生命周期，handle_key/update/draw 每帧三件套。"""

    name: StateName = StateName.READY

    def __init__(self, game) -> None:
        self.game = game

    # --- 生命周期 ---
    def enter(self) -> None: ...
    def exit(self) -> None: ...

    # --- 每帧 ---
    def handle_key(self, key: int) -> None:
        """只接收 KEYDOWN 的 keycode；ESC 由 Game 统一处理。"""

    def update(self, dt: float) -> None: ...
    def draw(self, surface) -> None: ...

    # --- 共享渲染（消除各状态重复的"背景→管道→地面"序列）---
    def draw_world(
        self, surface, *, pipes=(), bird=None, with_score: bool = False
    ) -> None:
        """绘制游戏世界：背景 → 管道 → 小鸟 → 地面 →（可选）分数。

        各状态的差异只在"画什么"，不在"怎么画"，因此统一在这里。
        """
        self.game.background.draw(surface)
        for pipe in pipes:
            pipe.draw(surface, self.game.assets)
        if bird is not None:
            bird.draw(surface)
        self.game.ground.draw(surface)
        if with_score:
            self.game.hud.draw_score(surface, self.game.score)
