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


# 期望尺寸一律从 config 取，避免"改窗口/改鸟尺寸要同步改两处"（审查 Shotgun Surgery #1）
_BG_SIZE = (c.LOGICAL_W, c.LOGICAL_H)
_BIRD_SIZE = (c.BIRD_W, c.BIRD_H)
_PIPE_SIZE = (c.PIPE_W, c.PIPE_H)
_LAND_SIZE = (c.LAND_TILE_W, c.LAND_H)

IMAGE_SPECS: tuple[ImageSpec, ...] = (
    ImageSpec("bg_day", "background-day.png", _BG_SIZE),
    ImageSpec("bg_night", "background-night.png", _BG_SIZE),
    ImageSpec("land", "land.png", _LAND_SIZE),
    ImageSpec("pipe_green", "pipe-green.png", _PIPE_SIZE),
    ImageSpec("pipe_red", "pipe-red.png", _PIPE_SIZE),
    ImageSpec("msg_ready", "message.png", c.MSG_READY_SIZE),
    ImageSpec("msg_gameover", "gameover.png", c.MSG_GAMEOVER_SIZE),
    *(
        ImageSpec(
            f"digit_{d}",
            f"{d}.png",
            (c.DIGIT_NARROW_W if d == 1 else c.DIGIT_W, c.DIGIT_H),
        )
        for d in range(10)
    ),
    *(
        ImageSpec(f"bird_{name}_{flap}", f"{name}bird-{flap}flap.png", _BIRD_SIZE)
        for name in ("yellow", "blue", "red")
        for flap in ("up", "mid", "down")
    ),
)

# 可选资源：缺失或损坏都不致命（Spec FR-WIN-3：图标失败时用默认图标，不崩溃）
OPTIONAL_SPECS: tuple[ImageSpec, ...] = (
    ImageSpec("icon", "flappy.ico", None),
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
        self._pipe_cap_cache: dict[bool, pygame.Surface] = {}
        self._pipe_body_cache: dict[tuple[int, bool], pygame.Surface] = {}
        self._load_images()
        self._resolve_sounds()

    # --- 加载 ---
    def _load_images(self) -> None:
        missing: list[str] = []
        for spec in IMAGE_SPECS:
            if not spec.relative or "__MACOSX" in spec.relative:
                continue
            surf = self._try_load(spec)
            if surf is None:
                missing.append(spec.relative)
            else:
                self.images[spec.key] = surf
        if missing:
            raise AssetError(
                "缺少或已损坏的图片资源（res/images）：\n  - "
                + "\n  - ".join(sorted(missing))
            )
        # 可选资源：失败只跳过，不抛异常
        for spec in OPTIONAL_SPECS:
            surf = self._try_load(spec)
            if surf is None:
                print(f"[assets] 可选资源缺失，已忽略：{spec.relative}")
            else:
                self.images[spec.key] = surf

    def _try_load(self, spec: ImageSpec) -> pygame.Surface | None:
        """加载单张图片并校验尺寸；失败返回 None（不抛异常，由调用方决定严重性）。"""
        path = self.res_root / "images" / spec.relative
        if not path.is_file():
            return None
        try:
            surf = pygame.image.load(str(path)).convert_alpha()
        except pygame.error:
            return None
        # Spec §7.4：尺寸与清单不符时打印一次警告（不致命，按实际尺寸绘制）
        if spec.size and surf.get_size() != spec.size:
            print(
                f"[assets] 尺寸不符：{spec.relative} 实际 {surf.get_size()} "
                f"清单 {spec.size}（按实际尺寸绘制）"
            )
        return surf

    def _resolve_sounds(self) -> None:
        for name in c.SFX_NAMES:
            self.sound_paths[name] = resolve_sound_path(self.res_root / "audios", name)

    # --- 访问 ---
    def image(self, key: str) -> pygame.Surface:
        return self.images[key]

    def optional_image(self, key: str) -> pygame.Surface | None:
        """取可选资源（如 icon）；不存在时返回 None。"""
        return self.images.get(key)

    def digit(self, value: int) -> pygame.Surface:
        return self.images[f"digit_{value}"]

    def bird_frame(self, palette: int, flap: int) -> pygame.Surface:
        """flap: 0=up, 1=mid, 2=down（与 FLAP_NAMES 索引一致，bird.py 沿用该约定）。"""
        name = c.PALETTE_ORDER[palette % len(c.PALETTE_ORDER)]
        return self.images[f"bird_{name}_{FLAP_NAMES[flap]}"]

    def pipe_cap(self, facing_up: bool) -> pygame.Surface:
        """facing_up=True 表示管口朝上（下管），cap 在顶部。结果缓存（Spec FR-ASSET-5）。"""
        cached = self._pipe_cap_cache.get(facing_up)
        if cached is None:
            src = self.images["pipe_green"]
            cap = src.subsurface((0, 0, c.PIPE_W, c.PIPE_CAP_H)).copy()
            cached = cap if facing_up else pygame.transform.flip(cap, False, True)
            self._pipe_cap_cache[facing_up] = cached
        return cached

    def pipe_body(self, height: int, facing_up: bool) -> pygame.Surface:
        """按 (高度, 朝向) 缓存拉伸结果，避免每帧每管重复 scale（Spec FR-ASSET-5）。"""
        height = max(1, int(height))
        key = (height, facing_up)
        cached = self._pipe_body_cache.get(key)
        if cached is None:
            src = self.images["pipe_green"]
            row = src.subsurface((c.PIPE_BODY_X, 200, c.PIPE_BODY_W, 1)).copy()
            body = pygame.transform.scale(row, (c.PIPE_BODY_W, height))
            cached = body if facing_up else pygame.transform.flip(body, False, True)
            # 高度组合有限（每帧最多几根管），上限保护防异常输入导致膨胀
            if len(self._pipe_body_cache) >= 256:
                self._pipe_body_cache.clear()
            self._pipe_body_cache[key] = cached
        return cached

    def rotated_bird(self, palette: int, flap: int, degrees: float) -> pygame.Surface:
        # 用 len(FLAP_NAMES) 而非硬编码 3：新增 flap 帧时键不会与既有组合静默碰撞
        key = (palette * len(FLAP_NAMES) + flap, int(round(degrees)))
        cached = self._rot_cache.get(key)
        if cached is None:
            base = self.bird_frame(palette, flap)
            cached = pygame.transform.rotate(base, -float(key[1]))
            if len(self._rot_cache) >= c.ROTATE_CACHE_MAX:
                self._rot_cache.clear()
            self._rot_cache[key] = cached
        return cached
