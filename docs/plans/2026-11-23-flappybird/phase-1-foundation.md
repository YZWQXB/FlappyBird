# Phase 1: 骨架、配置与资源层

**Goal:** 建立可复现的环境与工程骨架，完成 `config` / `assets` / `audio` 三个基础模块及其单测，产出素材体检脚本。
**Prerequisites:** 无（首个阶段）。
**Deliverables:** `.venv`、`requirements.txt`、`.gitignore`、`src/config.py`、`src/assets.py`、`src/audio.py`、`scripts/check_assets.py`、`tests/conftest.py`、`tests/test_config.py`、`tests/test_assets.py`、`tests/test_audio.py`。

**Interface Decisions Implemented:** 无（本阶段不产出可见界面）。本阶段确立的常量直接承载 Spec §9.2 的布局坐标（`SCORE_Y=44`、`HINT_Y=460`、`LAND_Y=400`）。

---

## Task 1: 环境与工程骨架

**Goal:** 让 `pytest` 与 `import pygame` 在项目内可跑，建立目录结构与无头测试基座。

**Files:**
- Create: `requirements.txt`、`.gitignore`、`src/__init__.py`、`src/states/__init__.py`、`tests/conftest.py`、`scripts/`（目录）

**Steps:**
- [x] 写 `requirements.txt`：

```text
pygame>=2.5,<3
pytest>=8
```

- [x] 写 `.gitignore`：

```text
.venv/
__pycache__/
*.pyc
save/
build/
.pytest_cache/
```

- [x] 建空包文件 `src/__init__.py`、`src/states/__init__.py`（内容为空）。

- [x] 写 `tests/conftest.py`（**必须在任何 `import pygame` 之前设置环境变量**，pytest 会先导入 conftest）：

```python
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _display():
    """提供一个 288x512 的 dummy 显示，供需要 convert_alpha 的测试使用。"""
    import pygame

    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.display.set_mode((288, 512))
    yield pygame.display.get_surface()
    pygame.quit()
```

- [x] 创建 venv 并安装依赖：

```powershell
uv venv .venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```
  - Expected: 输出 `Installed 2 packages`（pygame==2.6.1、pytest==8.x），退出码 0。

- [x] 验证导入：

```powershell
.venv\Scripts\python.exe -c "import pygame, pytest; print(pygame.version.ver, pytest.__version__)"
```
  - Expected: `2.6.1 8.x.x`（可能先打印 pygame 欢迎语与版本行）。

- [x] 验证无头测试基座：

```powershell
.venv\Scripts\python.exe -m pytest -q
```
  - Expected: `no tests ran`，退出码 5（pytest 无测试的固定退出码）。**这是本任务唯一可接受的非 0 退出码**。

**Security/Boundary Notes:** `.venv` 与 `save/` 已在 `.gitignore`，运行时只向 `save/` 写数据。

---

## Task 2: `config.py` 常量与派生量

**Goal:** 把 Spec §8.3 的常量全部落地，并显式派生 `HOP`、`HITBOX_W/H`、路径常量，禁止魔法数扩散。

**Files:**
- Create: `src/config.py`
- Test: `tests/test_config.py`

**Steps:**
- [x] 先写 `tests/test_config.py`：

```python
from pathlib import Path

from src import config as c


def test_logical_size_and_fps():
    assert (c.LOGICAL_W, c.LOGICAL_H) == (288, 512)
    assert c.FPS == 60
    assert abs(c.FIXED_DT - 1 / 60) < 1e-12


def test_paths_are_absolute_and_repo_relative():
    assert c.PROJECT_ROOT.is_absolute()
    assert c.PROJECT_ROOT.name == "FlappyBird"
    assert c.RES_DIR == c.PROJECT_ROOT / "res"
    assert c.RES_DIR.is_dir()
    assert c.SAVE_FILE == c.PROJECT_ROOT / "save" / "highscore.json"


def test_derived_hop_matches_physics_formula():
    expected = c.FLAP_VELOCITY ** 2 / (2 * c.GRAVITY)
    assert abs(c.HOP - expected) < 1e-9
    assert 45.0 < c.HOP < 52.0  # 约 48.1


def test_hitbox_derived_from_sprite_and_inset():
    assert (c.BIRD_W, c.BIRD_H, c.BIRD_INSET) == (34, 24, 3)
    assert (c.HITBOX_W, c.HITBOX_H) == (28, 18)


def test_difficulty_endpoints():
    assert c.LEVEL_EVERY == 5 and c.MAX_LEVEL == 6
    assert (c.BASE_GAP, c.GAP_STEP, c.MIN_GAP) == (110, 5, 80)
    assert abs(c.BASE_SPEED - 120.0) < 1e-9
    assert abs(c.SPEED_STEP - 0.08) < 1e-9


def test_layout_bands_fit_inside_logical_screen():
    assert c.LAND_Y == 400
    assert c.SCORE_Y < c.LAND_Y
    assert c.HINT_Y <= c.LOGICAL_H - 40
    assert c.PIPE_MARGIN + c.MAX_GAP_HALF <= c.LAND_Y
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_config.py -q`
  - Expected: 全部 FAIL，报 `ModuleNotFoundError: No module named 'src.config'`（红）。

- [x] 写 `src/config.py`：

```python
"""FlappyBird 全局配置：唯一的常量与可调参数来源。"""

from __future__ import annotations

from pathlib import Path

# ---------- 路径 ----------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RES_DIR = PROJECT_ROOT / "res"
IMAGES_DIR = RES_DIR / "images"
AUDIOS_DIR = RES_DIR / "audios"
SAVE_DIR = PROJECT_ROOT / "save"
SAVE_FILE = SAVE_DIR / "highscore.json"

# ---------- 画面与循环 ----------
LOGICAL_W, LOGICAL_H = 288, 512
SCALE = 2                      # 首选窗口倍率；实际取 fit_scale() 的返回值
FORCE_SCALE = 0                # >0 时强制使用该倍率（调试/演示用）
TITLEBAR_RESERVE = 48          # 估算标题栏+任务栏预留（逻辑像素）
FPS = 60
FIXED_DT = 1 / 60
MAX_STEPS_PER_FRAME = 5
MAX_FRAME_DT = 0.25
TITLE = "FlappyBird"

# ---------- 物理 ----------
GRAVITY = 1500.0               # px/s^2
FLAP_VELOCITY = -380.0         # px/s
MAX_FALL_SPEED = 640.0         # px/s
HOP = FLAP_VELOCITY ** 2 / (2 * GRAVITY)   # 派生：单跳升高 ≈ 48.1 px

BIRD_X = 64
BIRD_Y0 = 256
BIRD_W, BIRD_H = 34, 24
BIRD_INSET = 3
HITBOX_W = BIRD_W - 2 * BIRD_INSET          # 28
HITBOX_H = BIRD_H - 2 * BIRD_INSET          # 18
BIRD_FLOAT_AMP = 5.0
BIRD_FLOAT_W = 2.4            # rad/s，待机浮动角速度
FLAP_FRAME_TIME = 0.1         # 翅膀帧切换间隔 s
ROTATE_SPRITE = True
ROTATE_MIN_DEG = -25.0
ROTATE_MAX_DEG = 90.0
ROTATE_VY_FULL = 400.0        # vy >= 该值时角度 = ROTATE_MAX_DEG
ROTATE_CACHE_MAX = 160        # 旋转帧缓存上限（防内存增长）

# ---------- 难度 ----------
BASE_SPEED = 120.0            # px/s
LEVEL_EVERY = 5               # 每 5 分升一级
MAX_LEVEL = 6
SPEED_STEP = 0.08             # 每级 +8% 速度
BASE_GAP = 110                # 0 级缝隙高度
GAP_STEP = 5                  # 每级 -5px
MIN_GAP = 80                  # 最窄缝隙

# ---------- 管道与地面 ----------
PIPE_W = 52
PIPE_CAP_H = 25
PIPE_BODY_W = 48
PIPE_BODY_X = 2               # body 相对图片的左偏移
PIPE_SPACING = 150            # 按距离生成，px
PIPE_MARGIN = 48              # 缝隙中心离顶部/地面的最小距离
MAX_CENTER_DELTA = 120        # 相邻缝隙中心最大落差
PIPE_SPAWN_X = LOGICAL_W + 10
MAX_GAP_HALF = (BASE_GAP / 2) + 1   # 供布局断言用

LAND_Y = 400
LAND_H = 112
LAND_TILE_W = 336             # 地面素材宽度，平铺周期（独立于 PIPE_W）
GROUND_SPEED = BASE_SPEED

# ---------- 主题（昼夜/鸟色） ----------
THEME_EVERY = 10              # 每 10 分换一次 stage
PALETTE_ORDER = ("yellow", "blue", "red")

# ---------- HUD ----------
SCORE_Y = 44
DIGIT_GAP = 1
HINT_Y = 460
GAMEOVER_IMG_Y = 140
SCORE_PANEL_Y = 220
BEST_PANEL_Y = 280
OVERLAY_ALPHA = 120
FONT_SMALL = 16
FONT_LARGE = 20
INK = (0x54, 0x38, 0x47)
PAPER = (255, 255, 255)
MUTE_BADGE_SECONDS = 1.5

# ---------- 音频 ----------
AUDIO_CHANNELS = 8
SFX_NAMES = ("wing", "point", "hit", "die", "swoosh")
SFX_PRIORITY_GAP_MS = 200     # hit 与 die 最小间隔

# ---------- 行为开关 ----------
ROTATE_SPRITE = True
PAUSE_ON_FOCUS_LOST = True

# ---------- 退出码 ----------
EXIT_OK = 0
EXIT_ASSET_ERROR = 2
EXIT_DISPLAY_ERROR = 3
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_config.py -q`
  - Expected: `6 passed`。

**Security/Boundary Notes:** `config` 不得 import `pygame`（保证纯逻辑模块与测试可无头运行）；`PROJECT_ROOT` 由 `__file__` 推导，不依赖 CWD。

---

## Task 3: `assets.py` 资源清单与加载

**Goal:** 建立“逻辑键 → 文件 → 尺寸”的唯一权威表，实现一次性预加载、派生帧缓存、音效路径解析，缺失图片抛 `AssetError`。

**Files:**
- Create: `src/assets.py`、`scripts/check_assets.py`
- Test: `tests/test_assets.py`

**Steps:**
- [x] 先写 `tests/test_assets.py`（关键部分）：

```python
from pathlib import Path

import pytest

from src import config as c
from src.assets import AssetError, AssetManager, IMAGE_SPECS, resolve_sound_path


def test_every_spec_exists_and_matches_size():
    for spec in IMAGE_SPECS:
        path = c.IMAGES_DIR / spec.relative
        assert path.is_file(), f"缺少素材 {path}"
        if spec.size:
            import pygame
            surf = pygame.image.load(str(path))
            assert surf.get_size() == spec.size, f"{spec.key} 尺寸不符"


def test_macosx_is_never_referenced():
    for spec in IMAGE_SPECS:
        assert "__MACOSX" not in spec.relative


def test_sound_prefers_wav(tmp_path):
    (tmp_path / "wing.wav").write_bytes(b"")
    (tmp_path / "wing.ogg").write_bytes(b"")
    assert resolve_sound_path(tmp_path, "wing").name == "wing.wav"


def test_sound_falls_back_to_ogg(tmp_path):
    (tmp_path / "wing.ogg").write_bytes(b"")
    assert resolve_sound_path(tmp_path, "wing").name == "wing.ogg"


def test_sound_missing_returns_none(tmp_path):
    assert resolve_sound_path(tmp_path, "wing") is None


def test_manager_loads_all_images():
    assets = AssetManager(c.RES_DIR)
    assert "bg_day" in assets.images and "bg_night" in assets.images
    assert assets.digit(0).get_height() == 36
    assert assets.digit(1).get_width() == 16
    assert assets.pipe_cap(True).get_size() == (52, 25)
    assert assets.pipe_body(100, True).get_size() == (48, 100)
    for palette in range(3):
        for flap in range(3):
            assert assets.bird_frame(palette, flap).get_size() == (34, 24)


def test_missing_image_raises_with_filename(tmp_path):
    broken = tmp_path / "res"
    (broken / "images").mkdir(parents=True)
    (broken / "audios").mkdir(parents=True)
    with pytest.raises(AssetError) as ei:
        AssetManager(broken)
    assert "background-day.png" in str(ei.value)
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_assets.py -q`
  - Expected: FAIL（模块不存在）。

- [x] 写 `src/assets.py`，结构固定如下：

```python
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
        candidate = audios_dir / f"{name}{ext}"
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
                "缺少或以损坏的图片资源（res/images）：\n  - "
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
```

> 命名约定（全项目一致，勿改）：`flap ∈ {0,1,2}` 依次为 up / mid / down；`palette ∈ {0,1,2}` 依次为 yellow / blue / red（来自 `config.PALETTE_ORDER`）。

- [x] 写 `scripts/check_assets.py`：遍历 `IMAGE_SPECS` 校验存在性与尺寸、打印每个音效最终选用的扩展名、统计 `__MACOSX` 被忽略的文件数，最后打印 `PASS` 或 `FAIL` 并以 0/1 退出。**不 import 游戏主循环**。

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_assets.py -q`
  - Expected: `7 passed`。

- [x] Run: `.venv\Scripts\python.exe scripts/check_assets.py`
  - Expected: 结尾 `PASS`，退出码 0；每个 `sfx` 显示 `.wav`。

**Security/Boundary Notes:** 路径常量只出现在 `config` 与本模块；`AssetManager` 不读写 `save/`；`__MACOSX` 在 `_load_images` 与清单层双重排除。

**Dependencies:** Task 2（依赖 `config` 常量与路径）。

---

## Task 4: `audio.py` 音效管理与降级

**Goal:** 封装 mixr 初始化失败、音效缺失、静音三条降级路径，保证游戏无音频设备也能完整运行。

**Files:**
- Create: `src/audio.py`
- Test: `tests/test_audio.py`

**Steps:**
- [x] 先写 `tests/test_audio.py`：

```python
from pathlib import Path

from src.audio import AudioManager


def test_disabled_manager_is_safe_noop():
    am = AudioManager.disabled()
    assert am.enabled is False
    am.play("wing")          # 不抛异常
    am.toggle_mute()
    assert am.muted is True


def test_mute_blocks_play_and_toggles():
    am = AudioManager.disabled()
    am.muted = True
    am.play("point")
    am.toggle_mute()
    assert am.muted is False


def test_create_with_dummy_driver(tmp_path):
    # conftest 已把 SDL_AUDIODRIVER 设为 dummy，mixer 应能初始化
    am = AudioManager.create({})       # 空映射：所有音效为 None
    assert am.enabled is True
    for name in ("wing", "point", "hit", "die", "swoosh"):
        am.play(name)                  # 缺失音效 => 空操作，不抛
    am.quit()


def test_reserved_channels_exist():
    am = AudioManager.create({})
    assert am.enabled
    import pygame
    assert pygame.mixer.get_num_channels() >= 8
    am.quit()
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_audio.py -q`
  - Expected: FAIL（模块不存在）。

- [x] 写 `src/audio.py`：

```python
from __future__ import annotations

from pathlib import Path

import pygame

from . import config as c


class AudioManager:
    """音效门面：所有失败路径降级为空操作，绝不向调用方抛异常。"""

    RESERVED = {"hit": 0, "die": 1, "swoosh": 2}

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.muted = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._channels: list[pygame.mixer.Channel] = []

    @classmethod
    def disabled(cls) -> "AudioManager":
        return cls(enabled=False)

    @classmethod
    def create(cls, sound_paths: dict[str, Path | None]) -> "AudioManager":
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            pygame.mixer.set_num_channels(c.AUDIO_CHANNELS)
        except (pygame.error, OSError) as exc:      # 无声卡 / 驱动缺失
            print(f"[audio] 音频不可用，已降级为静音：{exc}")
            return cls.disabled()
        am = cls(enabled=True)
        am._channels = [pygame.mixer.Channel(i) for i in range(c.AUDIO_CHANNELS)]
        for name, path in sound_paths.items():
            if path is None:
                continue
            try:
                am._sounds[name] = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError) as exc:
                print(f"[audio] 音效加载失败 {name}: {exc}")
        return am

    def play(self, name: str) -> None:
        if not self.enabled or self.muted:
            return
        sound = self._sounds.get(name)
        if sound is None:
            return
        try:
            index = self.RESERVED.get(name)
            if index is None:
                sound.play()
            else:
                channel = self._channels[index]
                channel.stop()
                channel.play(sound)
        except pygame.error:
            self.enabled = False      # 通道异常后彻底降级，避免刷屏

    def toggle_mute(self) -> None:
        self.muted = not self.muted

    def stop_all(self) -> None:
        if self.enabled:
            pygame.mixer.stop()

    def quit(self) -> None:
        if self.enabled and pygame.mixer.get_init():
            pygame.mixer.quit()
        self.enabled = False
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_audio.py -q`
  - Expected: `4 passed`。

- [x] 补充验证“无设备”路径（手工，一次即可）：

```powershell
$env:SDL_AUDIODRIVER='definitely-not-a-driver'; .venv\Scripts\python.exe -c "import os,sys; sys.path.insert(0,'.'); import pygame; pygame.init(); from src.audio import AudioManager; am=AudioManager.create({'wing': None}); print('enabled=', am.enabled); am.play('wing'); print('ok')"
```
  - Expected: 打印 `[audio] 音频不可用，已降级为静音：...`、`enabled= False`、`ok`，退出码 0；**不得抛异常**。

**Security/Boundary Notes:** `AudioManager` 不读取路径、不决定播放时机；`play()` 全路径无异常外泄。

**Dependencies:** Task 2（`config.AUDIO_CHANNELS`、`SFX_NAMES`）。

---

## Phase Completion Checklist

- [x] Task 1–4 全部完成
- [x] `.venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_assets.py tests/test_audio.py -q` 全绿（≥ 17 用例）
- [x] `.venv\Scripts\python.exe scripts/check_assets.py` 输出 `PASS`
- [x] 无声卡场景实测不崩溃（Task 4 最后一步）
- [x] `src/` 下无任何模块 import `pygame` 以外的第三方库
- [x] Ready for Phase 2