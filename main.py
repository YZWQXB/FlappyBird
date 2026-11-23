"""FlappyBird 入口。

启动顺序：先确保运行环境（自动切换到项目 .venv），再初始化游戏。
这样用户直接 `python main.py` 即可运行，无需手动管理虚拟环境。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 抑制 pygame 的欢迎 banner，避免干扰错误信息（必须在 import pygame 之前）
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import config as c


def main() -> int:
    # 1) 环境准备：缺 pygame 时自动切换到项目 .venv（或创建它）
    from src.launcher import ensure_environment, project_root

    handled = ensure_environment(project_root(), sys.argv[1:])
    if handled is not None:
        return handled

    # 2) 导入游戏（此时保证有 pygame）
    try:
        from src.game import Game
    except ImportError as exc:
        from src.launcher import manual_instructions

        print(f"依赖缺失：{exc}\n")
        print(manual_instructions(project_root()))
        return c.EXIT_ASSET_ERROR

    # 3) 初始化并运行
    try:
        game = Game()
    except Exception as exc:                      # AssetError / 显示失败
        from src.assets import AssetError

        if isinstance(exc, AssetError):
            print(f"资源错误：\n{exc}")
            return c.EXIT_ASSET_ERROR
        print(f"启动失败：{exc}")
        return c.EXIT_DISPLAY_ERROR

    smoke_frames = os.environ.get("FLAPPYBIRD_SMOKE_FRAMES")
    max_frames = int(smoke_frames) if smoke_frames and smoke_frames.isdigit() else None
    return game.run(max_frames=max_frames)


if __name__ == "__main__":
    raise SystemExit(main())
