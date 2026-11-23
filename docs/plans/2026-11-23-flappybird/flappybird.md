# FlappyBird 项目实施计划（Python / pygame）

**Created:** 2026-11-23
**Status:** Done
**Source Spec:** [docs/specs/2026-11-23-flappybird-design.md](../../specs/2026-11-23-flappybird-design.md)

## Overview

**Goal:** 按已冻结的需求文档，交付一个可运行的 Windows pygame 版 FlappyBird：288×512 逻辑画面、空格起跳、管道障碍、阶梯式难度、昼夜与鸟色同步切换、暂停/重开/最高分/静音，资源全部取自 `res/`。

**Architecture:** 分层状态机（READY / PLAYING / PAUSED / DYING / GAMEOVER）+ 纯函数核心逻辑（physics、difficulty、score_store 不依赖 pygame，可无头单测）+ 统一资源管理器（AssetManager 启动预加载，逻辑键访问）+ 音效包装（AudioManager，无声卡自动降级）。渲染先在 288×512 逻辑画布完成，整数倍缩放后 blit 到窗口。

**Tech Stack:** Python 3.12.15（uv 托管解释器）、pygame 2.6.1（SDL 2.28.4 已验证可安装）、pytest ≥ 8。

**规模概览:** 5 个阶段 / 17 个任务 / 交付 22 个源文件（含 `main.py`、`display.py`）、10 个测试文件、3 个脚本、2 份文档 + 1 个 bat。`pytest` 用例规划 **90** 个。无 git 提交步骤（用户未要求，目录也未版本控制）。

## 环境事实（已实测，非假设）

| 事实 | 实测值 | 对计划的影响 |
|---|---|---|
| Python | 3.12.15（uv 托管，explicitly externally-managed） | 必须 `uv venv .venv`，不能装到系统解释器 |
| pygame 安装 | `uv pip install pygame` → 2.6.1 成功（约 1.6 s） | 用 `uv pip install -r requirements.txt` |
| 桌面可用区域 | 1707×1019 逻辑像素（150% DPI，任务栏占 48） | **576×1024 的 2× 窗口放不下**（需 1024+标题栏 ≈ 1064 > 1019）→ 见 Phase 4 Task 1 的 `fit_scale` 自动降级 |
| `pygame.font.SysFont` | **抛 TypeError**（pygame 2.6.1 + Python 3.12 的 `initsysfonts_win32` 缺陷，`splitext` 收到 int） | HUD 字体必须 `try: SysFont; except: Font(None, size)`，本机恒定走回退分支 |
| `pygame.font.Font(None, size)` | 正常（内置 freesansbold.ttf） | 回退方案可靠 |
| `pygame.image.load("res/images/flappy.ico")` | 16×16 带 alpha Surface，`set_icon` 成功 | 图标直接用，无需转 ICO 专用 API |
| 无声卡（`SDL_AUDIODRIVER=xxx`） | `mixer.init()` 抛 `pygame.error`；之后 `Sound()` 抛 "mixer not initialized" | AudioManager 必须在 init 失败后再不触碰 Sound |
| `pygame.Rect(1.6, 2.4, 3.5, 4.5)` | 截断为 `(1,2,3,4)` | hitbox 必须先 `round()` 再建 Rect，避免 -0.4 的判定漂移 |
| `pygame.transform.flip / scale` | 均可用（322KB wav / 17KB ogg 均可加载） | 管道 cap/body 派生缓存方案可行 |

## Files and Responsibilities

| File/Module | Action | Responsibility | Notes |
|---|---|---|---|
| `requirements.txt` | Create | 依赖声明 | `pygame>=2.5,<3`、`pytest>=8` |
| `.gitignore` | Create | 忽略 `.venv/`、`__pycache__/`、`save/`、`build/`、`*.pyc` | `save/` 与 `build/` 均为运行时产物 |
| `main.py` | Create | 进程入口：初始化顺序、异常→退出码 | 只做编排，无玩法逻辑 |
| `src/config.py` | Create | 唯一常量源 + 派生量（HOP/HITBOX） | 不含逻辑分支 |
| `src/display.py` | Create | `fit_scale()` 纯函数：按可用桌面区算整数倍率 | 新增模块，见环境事实表 |
| `src/assets.py` | Create | 资源清单、图片加载、派生帧、音效路径解析、`AssetError` | 唯一出现资源路径的地方 |
| `src/audio.py` | Create | Sound 加载、通道分配、静音、无设备降级 | 不决定“何时播放” |
| `src/physics.py` | Create | 纯函数：积分、钳制、hitbox、AABB、死亡判定、计分判定 | 不 import pygame |
| `src/difficulty.py` | Create | 纯函数：等级/速度/缝隙/下一个缝隙中心 | 不 import pygame，rng 可注入 |
| `src/score_store.py` | Create | 最高分原子读写、校验、降级 | 只写 `save/highscore.json` |
| `src/bird.py` | Create | 小鸟状态、扇翅帧动画、旋转绘制 | 不处理输入 |
| `src/pipe.py` | Create | `PipePair` 几何、移动、计分标记、绘制 | 不处理生成节奏 |
| `src/ground.py` | Create | 地面无缝平铺滚动 | 不持速度配置 |
| `src/background.py` | Create | 按 stage 选 day/night | 不做渐变 |
| `src/hud.py` | Create | 数字精灵、带描边文字、遮罩、字体回退 | 不持分数真值 |
| `src/states/base.py` | Create | `State` 抽象基类 | 五态共同契约 |
| `src/states/ready.py` | Create | 待机：浮动鸟、滚动地面、message.png | |
| `src/states/playing.py` | Create | 主玩法：物理、生成、碰撞、计分、换肤 | |
| `src/states/paused.py` | Create | 冻结快照 + 遮罩 | 不改实体状态 |
| `src/states/dying.py` | Create | 坠落与旋转，落地后转 GAMEOVER | |
| `src/states/gameover.py` | Create | 结束面板（分数/BEST/重开提示） | |
| `src/game.py` | Create | 主循环、固定步长、状态持有、渲染合成、全局键 | 不含具体玩法 |
| `scripts/check_assets.py` | Create | 不启动游戏的资源体检（清单 vs 磁盘） | 输出 PASS/FAIL |
| `scripts/smoke_run.py` | Create | 无头跑 900 帧 + 脚本化输入 + 存 PNGB 截图 | 视觉验收的素材来源 |
| `scripts/tune_sim.py` | Create | 调参可行性解析校验 + 无头 bot 回归 | 复现 Spec 附录 A |
| `tests/conftest.py` | Create | `SDL_VIDEODRIVER/AUDIODRIVER=dummy`、`sys.path` | 必须在 import pygame 前设 env |
| `tests/test_config.py` | Create | 常量与派生量 | |
| `tests/test_assets.py` | Create | 清单/尺寸/回退/缺失报错 | |
| `tests/test_audio.py` | Create | 禁用模式、静音、通道 | |
| `tests/test_physics.py` | Create | 积分、钳制、确定性 | |
| `tests/test_collision.py` | Create | hitbox、相切/重叠、三种死亡、计分 | |
| `tests/test_difficulty.py` | Create | 阶梯函数、中心钳制 | |
| `tests/test_tuning_invariant.py` | Create | 调参红线（DWELL/CROSS、净空） | Spec 附录 A.5 |
| `tests/test_score_store.py` | Create | 损坏/权限/原子写 | |
| `tests/test_entities.py` | Create | 管道矩形、地面偏移、数字排版宽度 | |
| `tests/test_states.py` | Create | 状态迁移表、重开重置、暂停快照 | |
| `tests/test_display.py` | Create | `fit_scale` 倍率选择（含本机 1707×1019 实测场景） | |
| `docs/plans/2026-11-23-flappybird/acceptance.md` | Create | 六项视觉验收的可追溯记录 | Phase 5 Task 2 产出 |
| `README.md` | Create | 安装/运行/按键/调参/目录/排障 | |
| `start.bat` | Create | 双击启动（缺 venv 自动建并安装依赖） | 交付物，Phase 5 Task 1 |
| `docs/specs/2026-11-23-flappybird-design.md` | Read-only | 需求与验收依据 | 不修改 |

## Interface Implementation Map

（Spec §9 的界面契约 → 落点文件 / 任务 / 验收方式）

任务编号格式：`P<阶段号>-T<任务号>`（如 `P4-T2` = Phase 4 Task 2）。

| 契约项（Spec 出处） | 实现落点 | 任务 | 验收方式 |
|---|---|---|---|
| 主旅程 READY→PLAYING→DYING→GAMEOVER（§9.1） | `states/*`、`game.py` | P4-T2、P4-T3 | `test_states.py` 迁移用例 + `smoke_run` 全流程 |
| 布局：分数带 y=44 / 提示带 y=460 / 地面 400（§9.2） | `config.py` 常量、`hud.py` | P1-T2、P3-T3 | 截图核对（P5-T2）；数字居中由 `test_entities.py` 断言宽度 |
| 视觉系统：素材原生像素风、无渐变圆角（§9.3） | 全部绘制代码 | P3-T1~T3、P5-T2 | 代码审查：无圆角矩形/无 alpha 渐变；截图比对 |
| 签名元素：每 10 分昼夜+鸟色同步换肤（§9.3） | `background.py`、`bird.py`、`playing.py` | P3-T1、P3-T2、P4-T2 | `test_entities.py` 断言 stage 派生；`smoke_run` 在第 10 分处截图 |
| 文字样式：白字 + 2px INK 描边（§9.3） | `hud.text_surface` | P3-T3 | 截图核对两套背景下的对比度 |
| 组件状态：分数 0 分隐藏、暂停可见（§9.4） | `hud.draw_number` 及其调用方 | P3-T3、P4-T2 | `test_entities.py` 的 0 分不绘制断言 + 截图 |
| 暂停遮罩 + 恢复提示（§9.4） | `paused.py` | P4-T3 | `smoke_run` 按 P 后截图（`03_paused.png`） |
| MUTE 角标 1.5 s（§9.4） | `game.py` 计时器 + `hud` | P3-T3、P4-T3 | `test_states.py` 计时器衰减单测 |
| 窗口失焦自动暂停（FR-WIN-7） | `game.py` 事件处理 | P4-T3 | 手工验证（切窗口）+ 代码审查 |
| 键盘可玩、无鼠标依赖（§9.5） | `game.py` 事件分发 | P4-T3 | `test_states.py` 用 keycode 直接断言迁移 |
| 视觉验收 6 项（§9.5） | `scripts/smoke_run.py` 截图 | P4-T4、P5-T2 | 逐项比对 §9.5 清单（P5-T2 的验收表） |

## Spec Coverage Matrix

Spec 中每条编号需求 → 落地任务。**实施时若某条需求找不到任务，说明计划有缺口，须先补计划再动手。**

| Spec 需求 | 任务 | 验收手段 |
|---|---|---|
| G1/G2/G3 可运行·核心循环·物理手感 | P2-T1、P4-T2、P4-T4 | `test_physics.py`、`main.py` 实跑 |
| G4 障碍与计分 | P2-T1、P3-T1、P4-T2 | `test_collision.py`、`test_entities.py` |
| G5 难度递增 | P2-T2 | `test_difficulty.py` |
| G6 昼夜与换色 | P3-T2、P4-T2 | `test_entities.py`、`smoke_run` 第 10 分截图 |
| G7 资源来自 res/ + wav→ogg 回退 | P1-T3 | `test_assets.py` |
| G8 健壮性（无声卡/存档损坏/缺文件） | P1-T3、P1-T4、P2-T3 | `test_audio.py`、`test_score_store.py`、P1-T4 手工无设备验证 |
| G9 暂停/重开/最高分/开始界面/静音 | P3-T3、P4-T2、P4-T3 | `test_states.py`、`smoke_run` |
| G10 工程化（分层+pytest+README+集中配置） | 全部阶段 + P5-T1 | `pytest`、README 复现 |
| N1–N8 非目标（不做排行榜/打包/联网等） | — | 计划中无对应任务，即为遵守 |
| FR-WIN-1~3 窗口/渲染策略/图标 | P1-T2、P4-T1、P4-T3 | `test_display.py`、实跑观察 |
| FR-WIN-4 固定步长累加器 | P4-T3 | 代码审查 + 暂停恢复无瞬移 |
| FR-WIN-5 ESC/QUIT 退出 | P4-T3 | 实跑验证 |
| FR-WIN-6 只写存档目录 | P2-T3 | `test_score_store.py` |
| FR-WIN-7 失焦自动暂停 | P4-T3 | 手工切窗口验证 |
| FR-INPUT 键位（SPACE/P/M/R/ESC 不连发） | P4-T2、P4-T3 | `test_states.py` + 实跑 |
| FR-STATE-1/2/3 迁移表·重置·DYING 锁 | P4-T2、P4-T3 | `test_states.py` |
| FR-PHYS-1~4 步长/参数/钳制/管道移动 | P2-T1、P4-T2 | `test_physics.py` |
| FR-PHYS-5/6 三种死亡判定 + 内缩 hitbox | P2-T1 | `test_collision.py` |
| FR-PHYS-7 计分时机 | P2-T1、P3-T1 | `test_collision.py`、`test_entities.py` |
| FR-PHYS-8 视觉旋转 | P2-T1、P3-T1 | `rotation_for` 单测隐含 + 截图 |
| FR-PHYS-2b 数值自洽约束 | P2-T3 | `test_tuning_invariant.py` |
| FR-DIFF-1~4 阶梯难度/按距离生成/中心钳制/纯函数 | P2-T2、P4-T2 | `test_difficulty.py` |
| FR-THEME-1~5 昼夜与配色 | P3-T1、P3-T2、P4-T2 | `test_entities.py`、截图 |
| FR-AUDIO-1~5 回退/降级/静音/通道/暂停 | P1-T3、P1-T4、P4-T3 | `test_audio.py`、手工无设备 |
| FR-SCORE-1~4 数字精灵/HUD 文案/字体回退 | P3-T3 | `test_entities.py`、截图 |
| FR-STORE-1~5 存档路径/schema/原子写/降级 | P2-T3 | `test_score_store.py` |
| FR-SCREEN-1~3 遮罩/缩放/不渲染中文 | P3-T3、P4-T3、P5-T2 | 截图 + 代码审查 |
| FR-ASSET-1~5 路径推导/预加载/忽略 MACOSX/缺图报错/缓存 | P1-T3 | `test_assets.py`、`check_assets.py` |
| §7.2 资源映射表完整性 | P1-T3 | `check_assets.py` 与 Spec 表逐项比对 |
| §9.1~9.5 界面契约 | 见上方 Interface Implementation Map | 截图 + 单测 |
| §11 八类失败模式 | P1-T3、P1-T4、P2-T3、P4-T1 | 各对应单测 |
| §14 测试计划全部用例 | P1–P4 | 累计 90 用例 |
| 附录 A 调参红线 | P2-T3 | `test_tuning_invariant.py`、`tune_sim.py` |

## Phases

### Phase 1: 骨架、配置与资源层
**File:** [phase-1-foundation.md](phase-1-foundation.md)
**Goal:** 建好 venv 与工程骨架，落地 `config`、`assets`、`audio` 三个基础模块及其单测；产出可校验的素材体检脚本。
**Tasks:** 4（P1-T1 ~ P1-T4）　**Status:** Done
**Completion:** √

### Phase 2: 纯逻辑核心
**File:** [phase-2-core-logic.md](phase-2-core-logic.md)
**Goal:** 无 pygame 依赖的物理、难度、存档三个模块 + 完整单测，含调参红线守护。
**Tasks:** 3（P2-T1 ~ P2-T3）　**Status:** Done
**Completion:** √

### Phase 3: 实体与渲染层
**File:** [phase-3-entities-rendering.md](phase-3-entities-rendering.md)
**Goal:** 小鸟、管道、地面、背景、HUD 的绘制与自更新；用离屏脚本产出可用于视觉核对的 PNG。
**Tasks:** 3（P3-T1 ~ P3-T3）　**Status:** Done
**Completion:** √

### Phase 4: 状态机与主循环
**File:** [phase-4-states-loop.md](phase-4-states-loop.md)
**Goal:** 五态状态机、固定步长主循环、窗口缩放适配、入口脚本；无头 900 帧全流程冒烟并出图。
**Tasks:** 4（P4-T1 ~ P4-T4）　**Status:** Done
**Completion:** √

### Phase 5: 打磨与验收
**File:** [phase-5-hardening.md](phase-5-hardening.md)
**Goal:** README/start.bat、六项视觉验收、全量测试与调参收尾。
**Tasks:** 3（P5-T1 ~ P5-T3）　**Status:** Done
**Completion:** √

## Risks and Mitigations

| 风险 | 影响 | 缓解 |
|---|---|---|
| 桌面可用高度 1019 < 1024，2× 窗口放不下 | 按 Spec 硬编码 `SCALE=2` 会导致窗口超出屏幕、底部被任务栏遮住 | Phase 4 Task 1 的 `fit_scale()` 自动降到 1×（288×512），并保留 `FORCE_SCALE` 覆盖；`test_display.py` 用本机真实尺寸做用例 |
| `pygame.font.SysFont` 在本机必抛 TypeError（pygame 2.6.1 + Py3.12 缺陷） | HUD 文字全部崩溃 | `hud.get_font` 捕获 `(TypeError, OSError, AttributeError, pygame.error)` 并回退 `Font(None, size)`；单测用 monkeypatch 模拟该异常 |
| 离散积分与解析 HOP 差 3.5px | 手感比理论值略"软"，可能让人误判参数不对 | 已在 Phase 2 用单侧断言锁死该行为并注明这是半隐式欧拉的固有偏差；调参判据继续用更保守的解析值 |
| 管道 cap/body 拼接出现错位或透明缝 | 视觉穿帮，验收第 5 项不过 | Phase 3 Task 1 给出精确拼接算法（cap 贴缝隙、body 从 cap 外侧延伸），并由 `smoke_run` 出图核对 |
| 多次暂停/重开导致累加器残留引发瞬移 | 恢复后鸟直接飞出屏幕 | Phase 4 Task 3 主循环在 `MAX_STEPS_PER_FRAME` 用尽时 `acc = 0.0`；PAUSED 期间不调用 `update` |
| 旋转帧缓存无限增长 | 长时间游玩内存上升 | `ROTATE_CACHE_MAX=160`，超限清空；Phase 5 有 3 分钟内存观察 |
| 最高分文件被手改或权限不足 | 崩溃或显示异常分数 | `score_store` 校验非 bool int 且 `0 <= v < 10^6`，写入失败只打印警告 |

## Dependencies

- **顺序**：Phase 1 → 2 → 3 → 4 → 5 严格串行（后续模块 import 前面的模块）。每个阶段末尾有 Completion Checklist，**未勾完不得进入下一阶段**；跨阶段问题（如接口不一致）必须回改对应阶段再前进，不允许用"先跑起来再说"绕过。
- **运行时**：Python 3.12.15（`D:\Tools\uv\python\cpython-3.12.15-windows-x86_64-none\python.exe`），项目内 `.venv` 由 `uv venv` 创建。
- **第三方**：pygame 2.6.1、pytest ≥ 8，均从 PyPI 安装（已验证可离线缓存安装成功）。
- **素材**：`res/` 保持现状（本次已核对 27 个图片文件尺寸与 Spec §7.2 完全一致）；`res/__MACOSX/` 忽略。
- **无网络、无服务、无数据库、无密钥**。
- **无 git 仓库**：计划不包含任何 commit 步骤（用户未要求，且目录未初始化版本控制）。

## Success Criteria

- [x] `.venv\Scripts\python.exe -m pytest -q` 全绿（**110** 个用例，覆盖 Spec §14 全部测试行）。
- [x] `.venv\Scripts\python.exe main.py` 可启动，窗口自适应到能放下的最大整数倍（本机预期 1× = 288×512），并可完整游玩。
- [x] 五态迁移、暂停、重开、最高分持久化、静音均按 Spec §6 工作。
- [x] `smoke_run.py` 产出的 6 张截图逐项通过 Spec §9.5 的六项视觉验收。
- [x] `README.md` 中的安装命令在全新 venv 可复现。
- [x] 无遗留 `TODO`/`TBD`/裸魔法数（除 `config.py`）。

## Blocking Questions

无。所有会影响实现的决策已在 Spec 中冻结；本计划新增的两个实现级决策已固化如下，不再悬置：

1. **窗口倍率**：Spec 写死 `SCALE=2`，但实测桌面可用高度 1019 < 1024+标题栏。处理方式为新增 `src/display.py::fit_scale()`，启动时取“能放下的最大整数倍”，并在 `config.py` 保留 `SCALE` 作为**首选值**、`FORCE_SCALE` 作为**覆盖开关**（Phase 4 Task 1）。
2. **字体**：本机 `SysFont` 必然抛 `TypeError`，因此 `hud.get_font()` 必须捕获 `TypeError`/`OSError` 并回退 `Font(None, size)`（Phase 3 Task 3），不能假设 SysFont 可用。

## Deferred Decisions

| 决策 | 为何可延后 | 安全默认值 |
|---|---|---|
| 管道是否在夜晚改用 `pipe-red.png` | 不影响任何模块接口，只影响一处取图 | 统一绿色（`pipe_green`） |
| 静音状态是否持久化 | 存档 schema 已预留扩展位 | 不持久化，重启恢复有声 |
| 小鸟旋转开关默认值 | 纯 config 开关 | `ROTATE_SPRITE = True` |
| `BEST` 是否常驻画面 | 只影响 HUD 调用点 | 仅 GAMEOVER 面板显示 |
| 数字间距像素值 | 单个常量 | `DIGIT_GAP = 1` |
| 失焦自动暂停是否开启 | 单个开关 | `PAUSE_ON_FOCUS_LOST = True` |
| 最终手感数值微调 | 需人工试玩；解析红线已由单测守护 | Spec 附录 A 定稿值 |