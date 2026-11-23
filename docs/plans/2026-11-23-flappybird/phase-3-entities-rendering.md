# Phase 3: 实体与渲染层

**Goal:** 实现五个实体（小鸟、管道、地面、背景、HUD）的自更新与绘制，并提供离屏渲染脚本，在不启动游戏主循环的前提下产出可用于视觉核对的 PNG。
**Prerequisites:** Phase 1（`assets`/`audio`/`config`）、Phase 2（`physics`/`difficulty`）完成。
**Deliverables:** `src/bird.py`、`src/pipe.py`、`src/ground.py`、`src/background.py`、`src/hud.py`、`tests/test_entities.py`、`scripts/smoke_run.py`（本阶段先出实体级截图，Phase 4 再扩展为全流程）。

**Interface Decisions Implemented:**
- Spec §9.2 布局带：分数 y=44 顶部居中、提示 y=460 底部居中、地面 y=400。
- Spec §9.3 视觉系统：素材原生像素风、无渐变/圆角、白字 + 2px INK 描边；签名元素（昼夜 + 鸟色）在本阶段完成取图逻辑。
- Spec §9.4 组件状态：分数 0 分隐藏；数字精灵间距 1px；`1.png` 宽度 16 的特殊处理。

---

## Task 1: `bird.py` 与 `pipe.py`

**Goal:** 小鸟持有位置/速度/动画/配色，能按 vy 旋转绘制；管道成对提供几何矩形与无缝拼接绘制。

**Files:**
- Create: `src/bird.py`、`src/pipe.py`
- Test: `tests/test_entities.py`（与 Task 2、3 共用，先写本任务相关用例）

**Steps:**
- [x] 先写 `tests/test_entities.py` 中与小鸟/管道相关的用例：

```python
import random

import pytest

from src import config as c
from src.assets import AssetManager
from src.bird import Bird
from src.pipe import PipePair


def test_bird_flap_sets_velocity(assets):
    bird = Bird(assets)
    bird.flap()
    assert bird.vy == pytest.approx(c.FLAP_VELOCITY)


def test_bird_update_integrates(assets):
    bird = Bird(assets)
    bird.vy, bird.y = 0.0, 200.0
    bird.update(c.FIXED_DT)
    assert bird.y > 200.0
    assert bird.vy > 0.0


def test_bird_frame_cycles(assets):
    bird = Bird(assets)
    seen = set()
    for _ in range(40):
        bird.update(c.FIXED_DT)
        seen.add(bird.flap_index)
    assert seen == {0, 1, 2}


def test_bird_palette_follows_stage(assets):
    bird = Bird(assets)
    for stage, expected in ((0, 0), (1, 1), (2, 2), (3, 0), (6, 0)):
        bird.set_stage(stage)
        assert bird.palette == expected


def test_pipe_pair_geometry():
    pair = PipePair(x=200.0, center=250.0, gap=110, speed=120.0)
    top, bottom = pair.boxes()
    assert top == (200.0, 0.0, c.PIPE_W, 195.0)
    assert bottom[1] == pytest.approx(305.0)
    assert bottom[1] + bottom[3] == pytest.approx(c.LAND_Y)


def test_pipe_pair_moves_and_scores_once():
    pair = PipePair(x=100.0, center=250.0, gap=110, speed=120.0)
    pair.update(0.5)
    assert pair.x == pytest.approx(100.0 - 60.0)
    assert pair.scored is False
    left = pair.x + c.PIPE_W
    assert pair.try_score(bird_left=left + 1.0) is True
    assert pair.try_score(bird_left=left + 1.0) is False    # 只计一次


def test_pipe_pair_off_screen():
    pair = PipePair(x=-c.PIPE_W - 1, center=250.0, gap=110, speed=120.0)
    assert pair.is_off_screen() is True
```

- [x] 在 `tests/conftest.py` 追加 `assets` fixture：

```python
@pytest.fixture(scope="session")
def assets(_display):
    from src import config as c
    from src.assets import AssetManager
    return AssetManager(c.RES_DIR)
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_entities.py -q`
  - Expected: FAIL（`src.bird` 不存在）。

- [x] 写 `src/bird.py`：

```python
from __future__ import annotations

import math

import pygame

from . import config as c
from .assets import AssetManager
from .physics import hitbox, rotation_for

# 翅膀帧循环：mid → up → mid → down
FLAP_CYCLE = (1, 2, 1, 0)


class Bird:
    def __init__(self, assets: AssetManager) -> None:
        self.assets = assets
        self.x = float(c.BIRD_X)
        self.y = float(c.BIRD_Y0)
        self.vy = 0.0
        self.palette = 0
        self.flap_index = FLAP_CYCLE[0]   # 0=up 1=mid 2=down
        self._anim_t = 0.0
        self._cycle_pos = 0

    def reset(self) -> None:
        self.x = float(c.BIRD_X)
        self.y = float(c.BIRD_Y0)
        self.vy = 0.0
        self.palette = 0
        self.flap_index = FLAP_CYCLE[0]
        self._anim_t = 0.0
        self._cycle_pos = 0

    def flap(self) -> None:
        self.vy = c.FLAP_VELOCITY

    def set_stage(self, stage: int) -> None:
        self.palette = stage % len(c.PALETTE_ORDER)

    def update(self, dt: float) -> None:
        from .physics import integrate
        self.vy, self.y = integrate(self.vy, self.y, dt)
        self._anim_t += dt
        if self._anim_t >= c.FLAP_FRAME_TIME:
            self._anim_t -= c.FLAP_FRAME_TIME
            self._cycle_pos = (self._cycle_pos + 1) % len(FLAP_CYCLE)
            self.flap_index = FLAP_CYCLE[self._cycle_pos]

    def float_motion(self, elapsed: float) -> None:
        """READY 待机：正弦上下浮动，不参与物理。"""
        self.y = c.BIRD_Y0 + math.sin(elapsed * c.BIRD_FLOAT_W) * c.BIRD_FLOAT_AMP

    @property
    def box(self):
        return hitbox(self.x, self.y)

    def draw(self, surface: pygame.Surface) -> None:
        frame = self.assets.bird_frame(self.palette, self.flap_index)
        if c.ROTATE_SPRITE:
            frame = self.assets.rotated_bird(
                self.palette, self.flap_index, rotation_for(self.vy)
            )
        rect = frame.get_rect(center=(round(self.x), round(self.y)))
        surface.blit(frame, rect)
```

- [x] 写 `src/pipe.py`：

```python
from __future__ import annotations

import pygame

from . import config as c
from .assets import AssetManager
from .physics import Box, should_score


class PipePair:
    """一对上下管道。几何以缝隙中心描述，绘制时上下各拼接 cap + body。"""

    def __init__(self, x: float, center: float, gap: float, speed: float) -> None:
        self.x = float(x)
        self.center = float(center)
        self.gap = float(gap)
        self.speed = float(speed)
        self.scored = False

    def update(self, dt: float) -> None:
        self.x -= self.speed * dt

    def boxes(self) -> tuple[Box, Box]:
        from .physics import pipe_boxes
        return pipe_boxes((self.x, self.center, self.gap), c.LAND_Y)

    def is_off_screen(self) -> bool:
        return self.x + c.PIPE_W <= 0

    def try_score(self, bird_left: float) -> bool:
        if self.scored or not should_score(self.x, bird_left):
            return False
        self.scored = True
        return True

    def draw(self, surface: pygame.Surface, assets: AssetManager) -> None:
        x = round(self.x)
        top_h = int(max(0, round(self.center - self.gap / 2)))
        bottom_y = round(self.center + self.gap / 2)
        bottom_h = int(max(0, c.LAND_Y - bottom_y))

        # 上管：cap 贴着缝隙，body 向上延伸
        if top_h >= c.PIPE_CAP_H:
            surface.blit(assets.pipe_cap(False), (x, top_h - c.PIPE_CAP_H))
            surface.blit(assets.pipe_body(top_h - c.PIPE_CAP_H, False), (x + c.PIPE_BODY_X, 0))
        elif top_h > 0:
            surface.blit(assets.pipe_cap(False), (x, 0))

        # 下管：cap 贴着缝隙，body 向下延伸到地面
        if bottom_h >= c.PIPE_CAP_H:
            surface.blit(assets.pipe_cap(True), (x, bottom_y))
            surface.blit(
                assets.pipe_body(bottom_h - c.PIPE_CAP_H, True),
                (x + c.PIPE_BODY_X, bottom_y + c.PIPE_CAP_H),
            )
        elif bottom_h > 0:
            surface.blit(assets.pipe_cap(True), (x, bottom_y))
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_entities.py -q`
  - Expected: 本任务 7 个用例全绿。

**Security/Boundary Notes:** 实体不处理输入、不切状态；`PipePair` 不自行生成（生成节奏属 `playing` 状态）。

**Dependencies:** Phase 1 Task 3（`assets`）、Phase 2 Task 1（`physics`）。

---

## Task 2: `ground.py` 与 `background.py`

**Goal:** 地面无缝循环滚动（接缝无抖动）；背景按 stage 切换 day/night。

**Files:**
- Create: `src/ground.py`、`src/background.py`
- Test: `tests/test_entities.py`（追加用例）

**Steps:**
- [x] 追加测试：

```python
from src.background import Background
from src.ground import Ground


def test_ground_offset_wraps_without_gap(assets):
    ground = Ground(assets)
    for _ in range(1000):
        ground.update(c.FIXED_DT, c.BASE_SPEED)
        assert -c.LAND_TILE_W <= ground.offset <= 0


def test_ground_keeps_subpixel_accumulator(assets):
    """offset 必须保留亚像素，否则 129.6px/s 这类速度会被逐帧取整拖慢。"""
    ground = Ground(assets)
    ground.update(c.FIXED_DT, 129.6)          # 每步 2.16px
    ground.update(c.FIXED_DT, 129.6)
    assert abs(ground.offset + 4.32) < 1e-9   # 累计 4.32，而不是 4


def test_ground_draw_position_is_quantized(assets):
    """只在绘制时取整，保证接缝不抖动。"""
    ground = Ground(assets)
    ground.offset = -2.16
    assert ground.draw_x() == -2


def test_ground_covers_screen_after_wrap(assets):
    ground = Ground(assets)
    ground.offset = -1000.0
    ground.update(0.0, c.BASE_SPEED)
    assert -c.LAND_TILE_W <= ground.offset <= 0


def test_background_selects_by_stage(assets):
    bg = Background(assets)
    assert bg.key_for_stage(0) == "bg_day"
    assert bg.key_for_stage(1) == "bg_night"
    assert bg.key_for_stage(2) == "bg_day"
```

- [x] 确认 `config.LAND_TILE_W == 336` 已存在（Phase 1 Task 2 已定义）；仅当缺失时才补。

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_entities.py -q`
  - Expected: 新增 3 个用例 FAIL。

- [x] 写 `src/ground.py`：

```python
from __future__ import annotations

import pygame

from . import config as c
from .assets import AssetManager


class Ground:
    """地面平铺滚动。

    offset 保持浮点亚像素（否则低速/提速后地面与管道速度会不一致），
    仅在 draw 时取整，避免接缝出现 1px 抖动。
    """

    def __init__(self, assets: AssetManager) -> None:
        self.assets = assets
        self.offset = 0.0

    def reset(self) -> None:
        self.offset = 0.0

    def update(self, dt: float, speed: float) -> None:
        tile = c.LAND_TILE_W
        self.offset = (self.offset - speed * dt) % tile
        # Python 的 % 对负数返回非负结果，需要再折回 [-tile, 0)
        if self.offset > 0:
            self.offset -= tile

    def draw_x(self) -> int:
        """绘制起点（整像素）。"""
        return round(self.offset)

    def draw(self, surface: pygame.Surface) -> None:
        tile = self.assets.image("land")
        x = self.draw_x() - c.LAND_TILE_W
        while x < c.LOGICAL_W:
            surface.blit(tile, (x, c.LAND_Y))
            x += c.LAND_TILE_W
```

- [x] 写 `src/background.py`：

```python
from __future__ import annotations

import pygame

from . import config as c
from .assets import AssetManager


class Background:
    def __init__(self, assets: AssetManager) -> None:
        self.assets = assets
        self.key = "bg_day"

    def set_stage(self, stage: int) -> None:
        self.key = self.key_for_stage(stage)

    @staticmethod
    def key_for_stage(stage: int) -> str:
        return "bg_day" if stage % 2 == 0 else "bg_night"

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.assets.image(self.key), (0, 0))
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_entities.py -q`
  - Expected: 全部 12 个用例绿（Task 1 的 7 个 + 本次 5 个）。

**界面验收（本任务）:** 地面在 1× 与 2× 倍率下滚动时不得出现可见缝隙或 1px 抖动；背景切换瞬时无闪烁。

**Dependencies:** Task 1。

---

## Task 3: `hud.py` 数字精灵、描边文字、遮罩

**Goal:** 提供分数数字渲染（0 分隐藏）、带 INK 描边的文字（字体失败自动回退）、半透明遮罩，供所有状态复用。

**Files:**
- Create: `src/hud.py`
- Test: `tests/test_entities.py`（追加用例）

**Steps:**
- [x] 追加测试：

```python
from src.hud import Hud, number_width


def test_number_width_accounts_for_narrow_one(assets):
    hud = Hud(assets)
    assert number_width(hud, 0) == 0                     # 0 分不占宽度
    assert number_width(hud, 1) == 16                    # 1.png 特殊窄字形
    assert number_width(hud, 10) == 16 + c.DIGIT_GAP + 24
    assert number_width(hud, 11) == 16 + c.DIGIT_GAP + 16
    assert number_width(hud, 123) == 16 + c.DIGIT_GAP + 24 + c.DIGIT_GAP + 24


def test_hud_draws_zero_as_nothing(assets):
    import pygame
    hud = Hud(assets)
    surf = pygame.Surface((c.LOGICAL_W, c.LOGICAL_H))
    surf.fill((0, 0, 0))
    before = surf.get_at((c.LOGICAL_W // 2, c.SCORE_Y))
    hud.draw_score(surf, 0)
    assert surf.get_at((c.LOGICAL_W // 2, c.SCORE_Y)) == before


def test_font_falls_back_when_sysfont_fails(assets, monkeypatch):
    import pygame
    hud = Hud(assets)

    def boom(*args, **kwargs):
        raise TypeError("simulated pygame 2.6.1 sysfont bug")

    monkeypatch.setattr(pygame.font, "SysFont", boom)
    font = hud.get_font(c.FONT_SMALL)      # 不得抛异常
    assert font is not None
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_entities.py -q`
  - Expected: 新增用例 FAIL。

- [x] 写 `src/hud.py`：

```python
from __future__ import annotations

import pygame

from . import config as c
from .assets import AssetManager


def number_width(hud: "Hud", value: int) -> int:
    if value <= 0:
        return 0
    widths = [hud.assets.digit(int(ch)).get_width() for ch in str(value)]
    return sum(widths) + c.DIGIT_GAP * (len(widths) - 1)


class Hud:
    def __init__(self, assets: AssetManager) -> None:
        self.assets = assets
        self._font_cache: dict[tuple[int, bool], pygame.font.Font] = {}
        self._outline_cache: dict[tuple[str, int, tuple], pygame.Surface] = {}

    # --- 字体（必须容忍 pygame 2.6.1 的 SysFont 缺陷）---
    def get_font(self, size: int, bold: bool = True) -> pygame.font.Font:
        key = (size, bold)
        font = self._font_cache.get(key)
        if font is None:
            try:
                font = pygame.font.SysFont(("consolas", "couriernew", "monospace"), size, bold=bold)
            except (TypeError, OSError, AttributeError, pygame.error):
                font = pygame.font.Font(None, size)
            self._font_cache[key] = font
        return font

    def text_surface(self, text: str, size: int, color: tuple = c.PAPER) -> pygame.Surface:
        key = (text, size, tuple(color))
        surf = self._outline_cache.get(key)
        if surf is None:
            font = self.get_font(size)
            glyph = font.render(text, True, color)
            surf = pygame.Surface((glyph.get_width() + 2, glyph.get_height() + 2), pygame.SRCALPHA)
            dark = font.render(text, True, c.INK)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                surf.blit(dark, (1 + dx, 1 + dy))
            surf.blit(glyph, (1, 1))
            self._outline_cache[key] = surf
        return surf

    def draw_text(self, surface, text, size, y, x_center: int | None = None) -> pygame.Rect:
        surf = self.text_surface(text, size)
        rect = surf.get_rect()
        rect.top = y
        rect.centerx = x_center if x_center is not None else c.LOGICAL_W // 2
        surface.blit(surf, rect)
        return rect

    # --- 数字 ---
    def draw_number(self, surface, value: int, y: int, x_center: int | None = None) -> None:
        if value <= 0:
            return
        digits = str(value)
        total = number_width(self, value)
        x = (x_center if x_center is not None else c.LOGICAL_W // 2) - total // 2
        for ch in digits:
            glyph = self.assets.digit(int(ch))
            surface.blit(glyph, (x, y))
            x += glyph.get_width() + c.DIGIT_GAP

    def draw_score(self, surface, score: int) -> None:
        self.draw_number(surface, score, c.SCORE_Y)

    # --- 遮罩 ---
    def overlay(self, surface, alpha: int = c.OVERLAY_ALPHA) -> None:
        shade = pygame.Surface((c.LOGICAL_W, c.LOGICAL_H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, alpha))
        surface.blit(shade, (0, 0))
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_entities.py -q`
  - Expected: 15 passed。

- [x] 扩展 `scripts/smoke_run.py`（本阶段先实现实体级渲染）：离屏渲染一张“白天 + 1 根管道 + 黄鸟 + 分数 12”的图到 `build/screens/entities_day.png`；一张“黑夜 + 蓝鸟 + 分数 25”到 `build/screens/entities_night.png`。

- [x] Run: `.venv\Scripts\python.exe scripts/smoke_run.py --mode entities`
  - Expected: 生成两张 PNG，退出码 0；人工打开确认管道 cap 朝缝隙、无穿帮（cap 与 body 无缝）。

**界面验收（本任务）:**
- 分数 0：屏幕顶部中央无数字（与 `entities_day.png` 对照）。
- 分数 12：数字居中，`1.png` 窄字形不额外留白，字间距 1px。
- 文字在 `#4EC0CA`（白天）与 `#008793`（黑夜）背景上均有描边，肉眼可读。
- 本机 SysFont 必然失败，回退到 freesansbold；文字仍为等宽感良好的大写英文。

**Security/Boundary Notes:** `hud` 不持分数真值，只接收传入值；描边缓存以 `(text,size,is_paper)` 为键，无无限增长（文案集合有限）。

**Dependencies:** Task 1、Task 2。

---

## Phase Completion Checklist

- [x] Task 1–3 全部完成
- [x] `.venv\Scripts\python.exe -m pytest tests/test_entities.py -q` 全绿（15 用例 = 鸟/管道 7 + 地面/背景 5 + HUD 3）
- [x] `scripts/smoke_run.py --mode entities` 产出两张 PNG，人工确认管道拼接无穿帮、地面无接缝
- [x] 屏幕顶部 0 分时确实无数字
- [x] `hud.get_font` 在 SysFont 抛 TypeError 时不崩溃（单测覆盖）
- [x] Ready for Phase 4