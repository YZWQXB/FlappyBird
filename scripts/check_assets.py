"""资源体检：不启动游戏即可校验 res/ 与清单是否一致。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame  # noqa: E402

from src import config as c  # noqa: E402
from src.assets import IMAGE_SPECS, resolve_sound_path  # noqa: E402


def main() -> int:
    pygame.init()
    pygame.display.set_mode((c.LOGICAL_W, c.LOGICAL_H))
    failures: list[str] = []

    print(f"== 图片清单（{len(IMAGE_SPECS)} 项）==")
    for spec in IMAGE_SPECS:
        path = c.IMAGES_DIR / spec.relative
        if not path.is_file():
            failures.append(f"缺失 {spec.relative}")
            print(f"  [MISS] {spec.key:14s} {spec.relative}")
            continue
        try:
            surf = pygame.image.load(str(path))
        except pygame.error as exc:
            failures.append(f"损坏 {spec.relative}: {exc}")
            print(f"  [BAD ] {spec.key:14s} {spec.relative}")
            continue
        size = surf.get_size()
        if spec.size and size != spec.size:
            failures.append(f"尺寸不符 {spec.relative}: {size} != {spec.size}")
            print(f"  [SIZE] {spec.key:14s} {spec.relative} {size} != {spec.size}")
        else:
            print(f"  [ OK ] {spec.key:14s} {spec.relative} {size[0]}x{size[1]}")

    print("== 音效（wav 优先，缺失回退 ogg）==")
    for name in c.SFX_NAMES:
        picked = resolve_sound_path(c.AUDIOS_DIR, name)
        if picked is None:
            failures.append(f"音效缺失 {name}")
            print(f"  [MISS] {name}")
        else:
            print(f"  [ OK ] {name:8s} -> {picked.suffix}")

    ignored = 0
    macosx = c.RES_DIR / "__MACOSX"
    if macosx.is_dir():
        ignored = sum(1 for _ in macosx.rglob("*") if _.is_file())
    print(f"== 忽略 __MACOSX 下 {ignored} 个文件 ==")

    pygame.quit()
    if failures:
        print("FAIL")
        for item in failures:
            print("  -", item)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
