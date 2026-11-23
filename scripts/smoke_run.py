"""无头截图脚本：不打开真实窗口也能产出验收用的 PNG。

用法：
    python scripts/smoke_run.py --mode entities   # Phase 3 实体级渲染
    python scripts/smoke_run.py --frames 900      # Phase 4 全流程六张图
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame  # noqa: E402

from src import config as c  # noqa: E402
from src.assets import AssetManager  # noqa: E402
from src.background import Background  # noqa: E402
from src.bird import Bird  # noqa: E402
from src.display import fit_scale, query_desktop_size  # noqa: E402
from src.ground import Ground  # noqa: E402
from src.hud import Hud  # noqa: E402
from src.pipe import PipePair  # noqa: E402

OUT_DIR = c.PROJECT_ROOT / "build" / "screens"


def _init() -> tuple[AssetManager, Hud]:
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.display.set_mode((c.LOGICAL_W, c.LOGICAL_H))
    assets = AssetManager(c.RES_DIR)
    return assets, Hud(assets)


def _compose(
    assets: AssetManager,
    bg_key: str,
    palette: int,
    score: int,
    with_pipes: bool = True,
    dy: float = 0.0,
) -> pygame.Surface:
    canvas = pygame.Surface((c.LOGICAL_W, c.LOGICAL_H))
    canvas.blit(assets.image(bg_key), (0, 0))
    if with_pipes:
        for x, center in ((200.0, 250.0), (60.0, 300.0)):
            PipePair(x=x, center=center, gap=c.BASE_GAP, speed=0.0).draw(canvas, assets)
    bird = Bird(assets)
    bird.set_stage(0)
    bird.palette = palette
    bird.y = c.BIRD_Y0 + dy
    bird.flap_index = 1
    bird.draw(canvas)
    ground = Ground(assets)
    ground.draw(canvas)
    hud = Hud(assets)
    hud.draw_score(canvas, score)
    return canvas


def _save(canvas: pygame.Surface, name: str, scale: int) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    size = (canvas.get_width() * scale, canvas.get_height() * scale)
    scaled = pygame.transform.scale(canvas, size)
    path = OUT_DIR / name
    pygame.image.save(scaled, str(path))
    return path


def run_entities() -> int:
    assets, _ = _init()
    scale = fit_scale(*query_desktop_size())
    a = _compose(assets, "bg_day", palette=0, score=12)
    b = _compose(assets, "bg_night", palette=1, score=25)
    c0 = _compose(assets, "bg_day", palette=0, score=0, with_pipes=False, dy=-5.0)
    p1 = _save(a, "entities_day.png", scale)
    p2 = _save(b, "entities_night.png", scale)
    p3 = _save(c0, "entities_zero.png", scale)
    print(f"scale={scale}")
    for p in (p1, p2, p3):
        print("saved:", p.relative_to(c.PROJECT_ROOT))
    pygame.quit()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("entities", "full"), default="full")
    parser.add_argument("--frames", type=int, default=900)
    args = parser.parse_args()
    if args.mode == "entities":
        return run_entities()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _smoke_impl import run_full

    return run_full(args.frames)


if __name__ == "__main__":
    raise SystemExit(main())
