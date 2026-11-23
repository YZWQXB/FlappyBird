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
