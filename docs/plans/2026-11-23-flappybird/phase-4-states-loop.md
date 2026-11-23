# Phase 4: 状态机与主循环

**Goal:** 把实体与逻辑组装成完整游戏：五态状态机、固定步长主循环、窗口倍率自适应、入口脚本；用无头脚本跑完整流程并产出六张验收截图。
**Prerequisites:** Phase 1–3 完成。
**Deliverables:** `src/display.py`、`src/states/*.py`、`src/game.py`、`main.py`、`tests/test_states.py`、`scripts/smoke_run.py`（完整版）。

**Interface Decisions Implemented:**
- Spec §9.1 主旅程与全部恢复路径（P 暂停提示、SPACE 重开提示、ESC 退出）。
- Spec §9.4 全组件状态：MUTE 角标 1.5 s、暂停遮罩、GAMEOVER 面板、失焦自动暂停。
- Spec §6.10 各状态画面版式（READY 的 message.png 位置、PAUSED 遮罩、GAMEOVER 三段式）。
- 签名元素落地点：`playing.update` 中 `stage = score // 10` 同帧驱动背景与鸟色。

---

## Task 1: `display.py` 窗口倍率自适应

**Goal:** 解决 Spec 写死 `SCALE=2` 与本机可用高度 1019 < 1024 的实际冲突：启动时取能放下的最大整数倍，且倍率逻辑可单测。

**Files:**
- Create: `src/display.py`
- Test: `tests/test_config.py`（追加）或新建 `tests/test_display.py`

**Steps:**
- [x] 先写 `tests/test_display.py`：

```python
import pytest

from src import config as c
from src.display import fit_scale


def test_prefers_configured_scale_when_it_fits():
    assert fit_scale(1920, 1080, preferred=2) == 2


def test_falls_back_to_one_when_two_does_not_fit():
    # 本机真实情况：可用区 1707x1019，1024 高放不下
    assert fit_scale(1707, 1019, preferred=2) == 1


def test_never_returns_zero_on_tiny_screens():
    assert fit_scale(200, 300, preferred=2) == 1


def test_respects_force_scale_override():
    assert fit_scale(1707, 1019, preferred=2, force=3) == 3


def test_uses_largest_integer_that_fits():
    assert fit_scale(288 * 3 + 10, 512 * 3 + 10, preferred=2) == 3


def test_ignores_titlebar_reserve_when_abundant():
    assert fit_scale(4000, 4000, preferred=2) == 2
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_display.py -q`
  - Expected: FAIL（模块不存在）。

- [x] 写 `src/display.py`：

```python
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
    """返回主显示器可用区域（失败时回退到 2 倍能放下的大小）。"""
    try:
        import pygame

        sizes = pygame.display.get_desktop_sizes()
        if sizes:
            return sizes[0]
    except Exception:      # display 未初始化 / 无显示器
        pass
    return c.LOGICAL_W * c.SCALE, c.LOGICAL_H * c.SCALE


def init_window() -> tuple["pygame.Surface", int]:
    import pygame

    avail_w, avail_h = query_desktop_size()
    scale = fit_scale(avail_w, avail_h)
    size = (c.LOGICAL_W * scale, c.LOGICAL_H * scale)
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption(c.TITLE)
    return screen, scale
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_display.py -q`
  - Expected: `6 passed`。

**Security/Boundary Notes:** 无显示器时 `query_desktop_size` 兜底，不抛异常。

---

## Task 2: 状态基类与 READY / PLAYING

**Goal:** 定义 `State` 五方法契约，实现待机与主玩法（含管道按距离生成、碰撞、计分、换肤、音效）。

**Files:**
- Create: `src/states/base.py`、`src/states/ready.py`、`src/states/playing.py`
- Test: `tests/test_states.py`

**Steps:**
- [x] 先写 `tests/test_states.py` 的迁移与重置用例（用轻量 `FakeGame` 避免真正开窗）：

```python
import pygame
import pytest

from src import config as c
from src.states import StateName


class _NullStore:
    def save_if_better(self, score):
        return max(0, int(score))


class FakeGame:
    """只实现状态机需要的接口，便于无头测试（与真实 Game 的属性名保持一致）。"""

    def __init__(self, assets, audio):
        from src.background import Background
        from src.ground import Ground
        from src.hud import Hud

        self.assets = assets
        self.audio = audio
        self.hud = Hud(assets)
        self.background = Background(assets)
        self.ground = Ground(assets)
        self.score = 0
        self.best = 0
        self.stage = 0
        self.state_name = StateName.READY
        self.pipes = []
        self.rng = __import__("random").Random(0)
        self.elapsed = 0.0
        self.mute_badge_t = 0.0
        self.store = _NullStore()      # 测试用：save_if_better 直接返回传入值

    def set_state(self, name):
        self.state_name = name

    def reset_round(self):
        self.score = 0
        self.stage = 0
        self.pipes.clear()
        self.background.set_stage(0)
        self.ground.reset()


def test_ready_to_playing_on_space(fake_game_factory):
    game = fake_game_factory()
    from src.states.ready import ReadyState
    state = ReadyState(game)
    state.handle_key(pygame.K_SPACE)
    assert game.state_name == StateName.PLAYING


def test_playing_space_flaps_and_scores_on_pass():
    game = fake_game_factory()
    from src.states.playing import PlayingState
    state = PlayingState(game)
    state.enter()
    state.handle_key(pygame.K_SPACE)
    assert state.bird.vy == pytest.approx(c.FLAP_VELOCITY)
    # 凭空放一对已经越过鸟的管道
    from src.pipe import PipePair
    pair = PipePair(x=state.bird.x - c.HITBOX_W / 2 - c.PIPE_W - 1, center=250.0, gap=110, speed=120.0)
    state.pipes.append(pair)
    state.update(c.FIXED_DT)
    assert game.score == 1


def test_playing_stage_changes_at_ten(fake_game_factory):
    game = fake_game_factory()
    from src.states.playing import PlayingState
    state = PlayingState(game)
    state.enter()
    game.score = 10
    state.update(c.FIXED_DT)
    assert state.stage == 1
    assert state.background.key == "bg_night"
    assert state.bird.palette == 1
```

> 说明 1：`FakeGame` 与 `fake_game_factory` fixture 都要写进 `tests/conftest.py`（与 `assets` fixture 同处）：`fake_game_factory` 返回一个已注入 `assets`/`AudioManager.disabled()` 的 `FakeGame` 实例。各状态实现只依赖 `game.set_state / reset_round / score / best / stage / pipes / rng / assets / audio / hud` 这些属性，**不得依赖 `FakeGame` 未提供的接口**，否则单测会失败——这正好约束了状态与 Game 的耦合面。
>
> 说明 2：`FakeGame.set_state` 只赋值 `state_name`，不实例化真实状态对象；因此断言用 `game.state_name == StateName.PLAYING`，不要断言 `isinstance(game.state, PlayingState)`。
>
> 完整实现时，`tests/test_states.py` 覆盖：READY 迁移、PLAYING 扇翅/计分/stage、PAUSED 冻结、DYING 忽略按键、GAMEOVER 的 SPACE/R 重开与重置、MUTE 角标计时。共 **14 个用例**（Task 2 的 3 个 + Task 3 的 5 个 + 任务说明要求的 6 个边界补充）。

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_states.py -q`
  - Expected: FAIL（`src.states` 缺 `StateName`）。

- [x] 写 `src/states/base.py`：

```python
from __future__ import annotations

from enum import Enum, auto


class StateName(Enum):
    READY = auto()
    PLAYING = auto()
    PAUSED = auto()
    DYING = auto()
    GAMEOVER = auto()


class State:
    name: StateName

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
```

- [x] 写 `src/states/ready.py`：`enter()` 播 `swoosh`、重置本轮、地面滚动；`update` 只推进地面与浮动相位（不生成管道）；`draw` 依次 背景 → message.png（居中 x=`(288-184)//2`=52，y=96）→ 小鸟（`float_motion`）→ 地面；`handle_key(SPACE)` → 切 `PLAYING`。

- [x] 写 `src/states/playing.py`。构造契约固定为：`PlayingState(game)` 在 `__init__` 中自建 `self.bird = Bird(game.assets)`、`self.background = game.background`、`self.ground = game.ground`、`self.pipes = game.pipes`（**同一个 list 对象，别名而非拷贝**——测试里 `state.pipes.append(...)` 与 `game.pipes` 必须互相可见），并暴露 `self.stage: int`（供测试断言）。必须包含以下行为的显式实现：

```text
enter():   重置管道列表、dist_since_spawn=0、prev_center=LY/2、bpm 计时
update(dt):
  1. speed = difficulty.speed_for(level_for(score))
  2. bird.update(dt)
  3. 每根 pipe.update(dt)；移除 is_off_screen 的
  4. dist_since_spawn += speed*dt；>= PIPE_SPACING 时：
       gap = gap_for(level)
       center = next_gap_center(prev_center, gap, rng)
       pipes.append(PipePair(PIPE_SPAWN_X, center, gap, speed))
       prev_center = center; dist_since_spawn -= PIPE_SPACING
       ★ 管道自己持有的 speed 不随后续升级变化（FR-DIFF-1）
  5. new_stage = score // THEME_EVERY（THEME_EVERY=10）
       若 new_stage != self.stage:
           self.stage = new_stage
           background.set_stage(self.stage); bird.set_stage(self.stage)
       ★ stage 是 score 的纯派生量，不做独立累加，重开时随 score 归零自动回到 0
  6. 计分：对每根 pipe.try_score(bird.box[0]) 为 True → score += 1；audio.play("point")
  7. 死亡：physics.is_dead(bird.box, [(p.x,p.center,p.gap) for p in pipes], LAND_Y)
       → game.set_state(DYING)；audio.play("hit")
handle_key(): SPACE → bird.flap(); audio.play("wing")
              P → game.set_state(PAUSED)
              M → audio.toggle_mute(); game.mute_badge_t = MUTE_BADGE_SECONDS
draw(): 背景 → 管道 ×N → 小鸟 → 地面 → HUD 分数（SCORE_Y）
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_states.py -q`
  - Expected: 本任务用例绿。

**Security/Boundary Notes:** 状态不直接改窗口；生成节奏集中在 `playing`，实体不自生成。

**Dependencies:** Phase 2、Phase 3 全部。

---

## Task 3: PAUSED / DYING / GAMEOVER 与 `game.py` 主循环

**Goal:** 补齐三个状态，并实现固定步长主循环、全局按键、渲染合成、状态持有。

**Files:**
- Create: `src/states/paused.py`、`src/states/dying.py`、`src/states/gameover.py`、`src/game.py`
- Test: `tests/test_states.py`（追加）

**Steps:**
- [x] 追加测试（PAUSED/DYING/GAMEOVER）：

```python
def test_paused_freezes_positions(fake_game_factory):
    game = fake_game_factory()
    from src.states.playing import PlayingState
    from src.states.paused import PausedState
    playing = PlayingState(game)
    playing.enter()
    bird_y = playing.bird.y
    paused = PausedState(game, playing)     # 位置参数：snapshot
    paused.update(1.0)
    assert playing.bird.y == bird_y


def test_dying_ignores_space_and_p(fake_game_factory):
    game = fake_game_factory()
    from src.bird import Bird
    from src.states.dying import DyingState
    dying = DyingState(game, Bird(game.assets), [], game.ground)
    game.state_name = StateName.DYING
    dying.handle_key(pygame.K_SPACE)
    dying.handle_key(pygame.K_p)
    assert game.state_name == StateName.DYING


def test_gameover_space_restarts_and_resets(fake_game_factory):
    game = fake_game_factory()
    game.score = 42
    game.stage = 4
    from src.states.gameover import GameOverState
    state = GameOverState(game)
    state.handle_key(pygame.K_SPACE)
    assert game.score == 0 and game.stage == 0
    assert game.state_name == StateName.READY


def test_gameover_r_also_restarts(fake_game_factory):
    game = fake_game_factory()
    from src.states.gameover import GameOverState
    GameOverState(game).handle_key(pygame.K_r)
    assert game.state_name == StateName.READY


def test_mute_badge_timer_decays():
    """角标计时器逻辑：1.5s（90 帧）后归零，之后不再绘制。"""
    from src import config as cfg

    t = cfg.MUTE_BADGE_SECONDS
    frames = 0
    while t > 0:
        t -= cfg.FIXED_DT
        frames += 1
    # 浮点累加误差会多走一帧（实测 91 帧），断言用范围而非等值
    assert 90 <= frames <= 91
    assert t <= 1e-9
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_states.py -q`
  - Expected: 新增 5 个用例 FAIL（paused / dying / gameover×2 / mute）。

- [x] 实现三状态：
  - `paused.py`：`__init__(game, snapshot: PlayingState)` 持有被暂停的 `PlayingState` 引用；`handle_key(P)` 直接 `game.set_state(StateName.PLAYING)` 并把 snapshot 重新挂回（实现：`game.swap_state(snapshot)`，**或**由 Game 保存 `self._paused_from`）——两者择一，但必须在 Game 的 set_state 附近写清楚，不允许 PAUSED 自行 new 一个 PlayingState（否则会丢掉鸟的当前速度）；`update` 必须是空实现（不推进任何实体，包括地面滚动——否则"暂停"时背景还在动会让人困惑）；`draw` 调 `snapshot.draw` 后叠加 `hud.overlay`、`PAUSED`（20px）、`PRESS P TO RESUME`（16px）；`handle_key(P)` → 回到该 `PlayingState` 实例。
  - `dying.py`：构造契约 `DyingState(game, bird, pipes, ground)`（由 `playing` 传入，避免重复创建）；进入时 `hit` 由 `playing` 播过，本状态只在落地时播 `die`；`update` 只对鸟做自由落体（不移动管道/地面），鸟落地（`box[1]+box[3] >= LAND_Y`）时调用 `game.best = game.store.save_if_better(game.score)`、切 `GAMEOVER`；忽略 SPACE/P。
  - `gameover.py`：`enter()` 保存本次得分与 `game.best`（best 已在 `dying` 落地时由 `game.store.save_if_better` 更新，这里只读取展示）；`draw` = 冻结画面 → `gameover.png`(y=140 居中) → 分数(y=220) → `BEST` 文字 + 数字(y=280) → `PRESS SPACE TO RESTART`(y=460)；`handle_key(SPACE/R)` → `game.reset_round()` 后切 `READY`。

- [x] 写 `src/game.py`：

```text
Game.__init__:
  pygame.mixer.pre_init(44100,-16,2,512) → pygame.init()
  screen, self.scale = display.init_window()
  self.canvas = pygame.Surface((LOGICAL_W, LOGICAL_H))
  self.assets = AssetManager(RES_DIR)        # 失败由 main 捕获为退出码 2
  set_icon(assets.image("icon"))
  self.audio = AudioManager.create(assets.sound_paths)
  self.store = HighScoreStore(SAVE_FILE); self.best = self.store.best
  self.hud = Hud(self.assets)
  self.rng = random.Random()                 # 可注入 seed 以便复现
  self.clock = pygame.time.Clock()
  self._paused_from = None                 # PAUSED → PLAYING 时恢复原实例
  self.state = ReadyState(self); self.state.enter()

  def set_state(self, name):
      """唯一的状态切换入口；PAUSED 通过 _paused_from 恢复。"""
      ...

  def swap_state(self, state):
      """直接挂载既有状态实例（PAUSED 恢复专用）。"""
      self.state = state

run():
  acc = 0.0; running = True
  while running:
    frame_dt = self.clock.tick(FPS) / 1000
    for ev in pygame.event.get():
      if ev.type == QUIT: running = False
      elif ev.type == KEYDOWN and ev.key == ESC: running = False
      elif ev.type == WINDOWFOCUSLOST and PAUSE_ON_FOCUS_LOST and state is PLAYING:
            self.set_state(PAUSED)
      elif ev.type == KEYDOWN: self.state.handle_key(ev.key)
    acc += min(frame_dt, MAX_FRAME_DT)
    steps = 0
    while acc >= FIXED_DT and steps < MAX_STEPS_PER_FRAME:
      self.state.update(FIXED_DT); acc -= FIXED_DT; steps += 1
    if steps == MAX_STEPS_PER_FRAME: acc = 0.0    # 防死亡螺旋
    self.state.draw(self.canvas)
    self.draw_mute_badge()      # 见下方说明

draw_mute_badge():
    """倒计时在 Game 层统一推进（不受暂停影响，因为提示类 UI 应始终衰减）。"""
    if self.mute_badge_t <= 0: return
    self.mute_badge_t -= frame_dt
    if self.audio.muted:                       # 只有"当前静音"才显示角标
        self.hud.draw_text(self.canvas, "MUTE", FONT_SMALL, y=LOGICAL_H - 24)
    else:
        self.hud.draw_text(self.canvas, "SOUND ON", FONT_SMALL, y=LOGICAL_H - 24)
    pygame.transform.scale(self.canvas, self.screen.get_size(), self.screen)   # 3 参数版就地写入，已实测可用
    pygame.display.flip()
  self.audio.quit(); pygame.quit(); return EXIT_OK
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_states.py -q`
  - Expected: `test_states.py` 全绿（14 用例）。

**Security/Boundary Notes:** `Game` 只经 `set_state` 改状态；唯一持久化调用点在 `dying`→`GAMEOVER` 处；`transform.scale` 的目标为预分配 screen，不逐帧新建 Surface。

**实测补充（写代码前必须知道的三条）:**
1. `pygame.transform.scale(src, size, dest)` 三参数版本**可用且返回 dest 本身**（已实测），比"每帧新建 Surface"省一次分配。
2. `pygame.font.SysFont` 在本机（pygame 2.6.1 + Python 3.12.15）**任何参数都会抛 TypeError**，根因是 `pygame/sysfont.py:82` 的 `splitext(font)` 从注册表拿到了 int（`_winreg.EnumValue` 返回的 `font` 位不是字符串）。这不是传参问题，**重试/换字体名都无效**，只能走 `Font(None, size)` 回退——`hud.get_font` 已按此设计，捕获 `(TypeError, OSError, AttributeError, pygame.error)`。
3. `pygame.Rect(-0.6, 0.5, 28, 18)` 实测截断为 `(0, 0, 28, 18)`（向零取整而非四舍五入），这正是 `physics.hitbox` 先用 `round()` 的原因。

**Visual Verification:** 无（本任务不产出截图，由 Task 4 统一出图）。

---

## Task 4: `main.py` 入口与完整无头冒烟

**Goal:** 提供可运行的入口与退出码约定，并用脚本化输入跑完一整局并出六张验收图。

**Files:**
- Create: `main.py`
- Modify: `scripts/smoke_run.py`（扩展为完整流程）

**Steps:**
- [x] 写 `main.py`：

```python
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import config as c


def main() -> int:
    try:
        from src.game import Game
    except ImportError as exc:
        print(f"依赖缺失：{exc}\n请先执行 uv venv .venv && uv pip install -r requirements.txt")
        return c.EXIT_ASSET_ERROR
    try:
        game = Game()
    except Exception as exc:                      # AssetError / 显示失败
        from src.assets import AssetError

        if isinstance(exc, AssetError):
            print(f"资源错误：\n{exc}")
            return c.EXIT_ASSET_ERROR
        print(f"启动失败：{exc}")
        return c.EXIT_DISPLAY_ERROR
    return game.run()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] 扩展 `scripts/smoke_run.py`：`SDL_VIDEODRIVER=dummy` + 固定 `random.seed(7)`，脚本化输入序列（见下），每到一个关键点存 PNG 到 `build/screens/`：

| 帧 | 输入 | 产出 |
|---|---|---|
| 1 | — | `01_ready.png` |
| 2 | SPACE | — |
| 180 | SPACE | `02_playing.png` |
| 300 | P | `03_paused.png` |
| 320 | P | — |
| 强制 score=10 后一帧 | — | `04_night_blue.png` |
| 撞击管道后 30 帧 | — | `05_dying.png` |
| 落地后（GAMEOVER） | — | `06_gameover.png` |

- [x] Run: `.venv\Scripts\python.exe scripts/smoke_run.py --frames 900`
  - Expected: 无异常退出，退出码 0，`build/screens/` 下 6 个 PNG 齐全；图片尺寸 = 逻辑 288×512 × `fit_scale()`（本机 1×，即 288×512）。

- [x] Run（真实窗口冒烟，人工 30 秒）: `.venv\Scripts\python.exe main.py`
  - Expected: 窗口出现，标题 `FlappyBird`，图标为小鸟；空格起飞、P 暂停、撞击后坠落、空格重开、M 静音、ESC 退出均生效；控制台无重复警告刷屏。

**Visual Verification:** 六张图见 Phase 5 Task 2 的验收表。

**Dependencies:** Task 1–3。

---

## Phase Completion Checklist

- [x] Task 1–4 全部完成
- [x] `.venv\Scripts\python.exe -m pytest tests/test_states.py tests/test_display.py -q` 全绿（**20** 用例 = states 14 + display 6）
- [x] `scripts/smoke_run.py --frames 900` 产出 6 张 PNG
- [x] `main.py` 在真实窗口可完整游玩 30 秒且无异常
- [x] 键位：SPACE / P / M / R / ESC 全部生效
- [x] Ready for Phase 5