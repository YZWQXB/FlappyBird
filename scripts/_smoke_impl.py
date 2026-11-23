"""无头全流程冒烟：脚本化输入 + 关键帧截图（供视觉验收）。

本文件是 scripts/smoke_run.py 的实现细节，属于测试工具，不属于生产包。
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path

import pygame

from src import config as c
from src.display import fit_scale, query_desktop_size
from src.game import Game
from src.states.base import StateName

OUT_DIR = c.PROJECT_ROOT / "build" / "screens"


def _capture(game: Game, name: str, scale: int) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    size = (c.LOGICAL_W * scale, c.LOGICAL_H * scale)
    scaled = pygame.transform.scale(game.canvas, size)
    path = OUT_DIR / name
    pygame.image.save(scaled, str(path))
    return path


def _keep_alive(game: Game) -> None:
    """把鸟放到下一根缝隙的中心（无管道时固定在初始高度），保证脚本化流程不会撞死。"""
    state = game.state
    target = c.BIRD_Y0
    for pipe in state.pipes:
        if pipe.x + c.PIPE_W > state.bird.x - c.HITBOX_W / 2:
            target = pipe.center
            break
    state.bird.y = target
    state.bird.vy = 0.0


def run_full(frames: int = 900) -> int:
    game = Game(rng_seed=7, scale=1)
    scale = fit_scale(*query_desktop_size())
    saved: list[Path] = []
    steps = 0

    game.draw_frame(0.0)
    saved.append(_capture(game, "01_ready.png", scale))

    game.state.handle_key(pygame.K_SPACE)          # READY -> PLAYING
    for _ in range(180):
        _keep_alive(game)
        game.state.update(c.FIXED_DT)
        steps += 1
        if game.state_name != StateName.PLAYING:
            break
    game.draw_frame(0.0)
    saved.append(_capture(game, "02_playing.png", scale))

    if game.state_name == StateName.PLAYING:
        game.state.handle_key(pygame.K_p)          # PAUSED
        game.draw_frame(0.0)
        saved.append(_capture(game, "03_paused.png", scale))
        game.state.handle_key(pygame.K_p)          # 恢复原 PlayingState
        assert game.state_name == StateName.PLAYING
        game.state.update(c.FIXED_DT)

    if game.state_name == StateName.PLAYING:
        game.score = 10                            # 第 10 分：夜晚 + 蓝鸟
        game.state.update(c.FIXED_DT)
        _keep_alive(game)
        game.draw_frame(0.0)
        saved.append(_capture(game, "04_night_blue.png", scale))

    if game.state_name == StateName.PLAYING:
        # 制造撞击：把鸟挪到最近一根管道的 x 位置上方的实体区
        if game.state.pipes:
            target = min(game.state.pipes, key=lambda p: abs(p.x - game.state.bird.x))
            game.state.bird.x = target.x + c.PIPE_W / 2
            game.state.bird.y = target.center - target.gap / 2 - 30
        else:
            game.state.bird.y = c.LAND_Y
        game.state.update(c.FIXED_DT)
        assert game.state_name == StateName.DYING, game.state_name
        for _ in range(6):                          # 只坠落几帧，保持 DYING 状态
            game.state.update(c.FIXED_DT)
        assert game.state_name == StateName.DYING, "DYING 截图必须落在落地之前"
        game.draw_frame(0.0)
        saved.append(_capture(game, "05_dying.png", scale))
        for _ in range(300):
            game.state.update(c.FIXED_DT)
            if game.state_name == StateName.GAMEOVER:
                break
        if game.state_name == StateName.GAMEOVER:
            game.draw_frame(0.0)
            saved.append(_capture(game, "06_gameover.png", scale))

    for p in saved:
        print("saved:", p.relative_to(c.PROJECT_ROOT))
    print("frames simulated:", steps)
    print("state:", game.state_name.name)
    game.audio.quit()
    pygame.quit()
    return 0 if len(saved) == 6 else 1
