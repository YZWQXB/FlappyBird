"""资源清单、加载、派生帧与音效路径解析。

这是全项目唯一出现资源文件名字符串的地方；游戏逻辑只认逻辑键。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pygame

from . import config as c


class AssetError(RuntimeError):
    """图片资源缺失或损坏：不可降级，应终止启动。"""


@dataclass(frozen=True)
class ImageSpec:
    key: str
    relative: str          # 相对 res/images
    size: tuple[int, int] | None = None   # None 表示不校验尺寸


IMAGE_SPECS: tuple[ImageSpec, ...] = (
    ImageSpec("bg_day", "background-day.png", (288, 512)),
    ImageSpec("bg_night", "background-night.png", (288, 512)),
    ImageSpec("land", "land.png", (336, 112)),
    ImageSpec("pipe_green", "pipe-green.png", (52, 320)),
    ImageSpec("pipe_red", "pipe-red.png", (52, 320)),
    ImageSpec("msg_ready", "message.png", (184, 267)),
    ImageSpec("msg_gameover", "gameover.png", (192, 42)),
    ImageSpec("icon", "flappy.ico", None),
    *(ImageSpec(f"digit_{d}", f"{d}.png", (16 if d == 1 else 24, 36)) for d in range(10)),
    *(
        ImageSpec(f"bird_{name}_{flap}", f"{name}bird-{flap}flap.png", (34, 24))
        for name in ("yellow", "blue", "red")
        for flap in ("up", "mid", "down")
    ),
)

FLAP_NAMES = ("up", "mid", "down")   # flap 索引 → 资源键后缀


def resolve_sound_path(audios_dir: Path, name: str) -> Path | None:
    """优先 .wav，其次 .ogg；都不存在返回 None（音效缺失不致命）。"""
    for ext in (".wav", ".ogg"):
        candidate = Path(audios_dir) / f"{name}{ext}"
        if candidate.is_file():
            return candidate
    return None


class AssetManager:
    def __init__(self, res_root: Path) -> None:
        self.res_root = Path(res_root)
        self.images: dict[str, pygame.Surface] = {}
        self.sound_paths: dict[str, Path | None] = {}
        self._rot_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._load_images()
        self._resolve_sounds()

    # --- 加载 ---
    def _load_images(self) -> None:
        missing: list[str] = []
        for spec in IMAGE_SPECS:
            if not spec.relative or "__MACOSX" in spec.relative:
                continue
            path = self.res_root / "images" / spec.relative
            if not path.is_file():
                missing.append(spec.relative)
                continue
            try:
                surf = pygame.image.load(str(path))
            except pygame.error:
                missing.append(spec.relative)
                continue
            self.images[spec.key] = surf.convert_alpha()
        if missing:
            raise AssetError(
                "缺少或已损坏的图片资源（res/images）：\n  - "
                + "\n  - ".join(sorted(missing))
            )

    def _resolve_sounds(self) -> None:
        for name in c.SFX_NAMES:
            self.sound_paths[name] = resolve_sound_path(self.res_root / "audios", name)

    # --- 访问 ---
    def image(self, key: str) -> pygame.Surface:
        return self.images[key]

    def digit(self, value: int) -> pygame.Surface:
        return self.images[f"digit_{value}"]

    def bird_frame(self, palette: int, flap: int) -> pygame.Surface:
        """flap: 0=up, 1=mid, 2=down（与 FLAP_NAMES 索引一致，bird.py 沿用该约定）。"""
        name = c.PALETTE_ORDER[palette % len(c.PALETTE_ORDER)]
        return self.images[f"bird_{name}_{FLAP_NAMES[flap]}"]

    def pipe_cap(self, facing_up: bool) -> pygame.Surface:
        """facing_up=True 表示管口朝上（下管），cap 在顶部。"""
        src = self.images["pipe_green"]
        cap = src.subsurface((0, 0, c.PIPE_W, c.PIPE_CAP_H)).copy()
        return cap if facing_up else pygame.transform.flip(cap, False, True)

    def pipe_body(self, height: int, facing_up: bool) -> pygame.Surface:
        height = max(1, int(height))
        src = self.images["pipe_green"]
        row = src.subsurface((c.PIPE_BODY_X, 200, c.PIPE_BODY_W, 1)).copy()
        body = pygame.transform.scale(row, (c.PIPE_BODY_W, height))
        return body if facing_up else pygame.transform.flip(body, False, True)

    def rotated_bird(self, palette: int, flap: int, degrees: float) -> pygame.Surface:
        key = (palette * 3 + flap, int(round(degrees)))
        cached = self._rot_cache.get(key)
        if cached is None:
            base = self.bird_frame(palette, flap)
            cached = pygame.transform.rotate(base, -float(key[1]))
            if len(self._rot_cache) >= c.ROTATE_CACHE_MAX:
                self._rot_cache.clear()
            self._rot_cache[key] = cached
        return cached
