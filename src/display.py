from __future__ import annotations

from . import config as c


def fit_scale(
    avail_w: int,
    avail_h: int,
    preferred: int = c.SCALE,
    force: int = c.FORCE_SCALE,
) -> int:
    """取能放下逻辑画面的最大整数倍率；force>0 时直接返回 force。"""
    if force > 0:
        return force
    usable_h = max(1, avail_h - c.TITLEBAR_RESERVE)
    by_h = usable_h // c.LOGICAL_H
    by_w = max(1, avail_w) // c.LOGICAL_W
    best = max(1, min(by_h, by_w))
    return max(1, min(best, max(1, preferred)))


def query_desktop_size() -> tuple[int, int]:
    """返回主显示器尺寸（失败时回退到 2 倍能放下的大小）。"""
    try:
        import pygame

        sizes = pygame.display.get_desktop_sizes()
        if sizes:
            return sizes[0]
    except Exception:      # display 未初始化 / 无显示器
        pass
    return c.LOGICAL_W * c.SCALE, c.LOGICAL_H * c.SCALE


def init_window(screen_size: tuple[int, int] | None = None):
    import pygame

    if screen_size is None:
        avail_w, avail_h = query_desktop_size()
        scale = fit_scale(avail_w, avail_h)
    else:
        scale = max(1, screen_size[0] // c.LOGICAL_W)
    size = (c.LOGICAL_W * scale, c.LOGICAL_H * scale)
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption(c.TITLE)
    return screen, scale
