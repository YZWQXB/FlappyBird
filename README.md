# FlappyBird

基于 Python + pygame 复刻的经典 FlappyBird 小游戏。包含完整的五态状态机、非对称重力手感、阶梯难度、昼夜与鸟色同步切换、最高分持久化，以及 184 个自动化测试。

> 素材（图片与音效）来自 `res/`，代码与素材完全解耦：换素材不需要改逻辑。

---

## 快速开始

```powershell
python main.py
```

**不需要手动建虚拟环境。** 启动器会自动处理运行环境：

| 情况 | 行为 |
|---|---|
| 当前 Python 已有 pygame | 直接运行 |
| 有 `.venv` 但当前 Python 缺 pygame | 自动切换到 `.venv` 运行 |
| 还没有 `.venv` | 自动创建并安装依赖（优先 `uv`，否则 `python -m venv`） |
| 以上都失败 | 打印带绝对路径、可直接复制粘贴的命令 |

也可以双击 `start.bat`。

### 环境要求

- Windows 10 / 11
- Python 3.12（开发环境为 3.12.15）
- 音频设备可选（无声卡会自动降级为静音，不影响游玩）

### 手动安装（如需可控环境）

```powershell
uv venv .venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.venv\Scripts\python.exe main.py
```

---

## 玩法

| 按键 | 作用 |
|---|---|
| `SPACE` | 起飞 / 扇翅 / 结束后重开 |
| `P` | 暂停 / 继续 |
| `M` | 静音开关（右上角显示 MUTE 1.5 秒，任意状态可用） |
| `R` | 结束后重开（与 SPACE 等价） |
| `ESC` | 退出游戏 |

窗口失焦时自动暂停，避免切出去回来已经撞死。

### 规则

- 每穿过一对管道 **+1 分**
- 撞管道、撞地面、越过屏幕上边界 → 结束本局，播放坠落动画
- **难度阶梯**：每 5 分升一级（最高 6 级），速度 120 → 177.6 px/s，缝隙 110 → 80 px
- **昼夜与鸟色**：每 10 分切换一次昼夜背景，同时按 黄 → 蓝 → 红 循环换色
- **最高分**保存在 `save/highscore.json`，重启后保留

### 手感设计

起跳不是"匀速下落"，而是带**顶点滞空**的非对称重力：

| 指标 | 值 |
|---|---|
| 单跳升高 | 46 px |
| 总滞空 | 0.67 s |
| 顶点悬停 | 0.32 s |
| 终端下落速度 | 480 px/s |

下降段重力为上升段的 65%，接近顶点时进一步减弱到 35%，因此顶点附近会自然"飘"一下，给玩家在连续高低障碍间调整的时间。曲线在阈值处连续，不会有可感知的卡顿。

---

## 项目结构

```text
FlappyBird/
├── main.py              入口：先确保运行环境，再初始化游戏
├── start.bat            Windows 双击启动
├── requirements.txt     依赖声明
├── PromptHistory.txt    开发过程提示词历史记录
├── src/
│   ├── config.py        全部常量与可调参数（唯一常量源）
│   ├── launcher.py      运行环境探测/切换/创建
│   ├── display.py       窗口整数倍率自适应
│   ├── assets.py        资源清单与加载（唯一出现文件名的位置）
│   ├── audio.py         音效、静音、无设备降级
│   ├── physics.py       物理与碰撞（纯函数，不依赖 pygame）
│   ├── difficulty.py    难度曲线（纯函数）
│   ├── score_store.py   最高分原子读写
│   ├── bird.py          小鸟：物理、动画、旋转
│   ├── pipe.py          管道对：几何、移动、绘制
│   ├── ground.py        地面平铺滚动
│   ├── background.py    昼夜背景
│   ├── hud.py           数字精灵、描边文字、遮罩
│   ├── game.py          主循环、状态持有、渲染合成
│   └── states/          五态状态机
│       ├── base.py      State 基类（含共享的 draw_world）
│       ├── ready.py     READY   待机
│       ├── playing.py   PLAYING 主玩法
│       ├── paused.py    PAUSED  暂停
│       ├── dying.py     DYING   坠落
│       └── gameover.py  GAMEOVER 结算
├── tests/               184 个单元测试
├── scripts/             素材体检、调参校验、无头截图
├── res/                 素材（图片 27 张 + 音效 5 组）
├── save/                运行时生成：最高分存档
└── docs/                Spec、实施计划、测试报告、代码审查报告
```

### 架构要点

- **分层状态机**：五态迁移规则集中在 `states/`，非法按键由各状态自行忽略
- **纯函数核心**：`physics` / `difficulty` / `score_store` 不 import pygame，可无头单测
- **资源解耦**：游戏逻辑只认逻辑键（如 `bird_yellow_mid`），不认文件名
- **失败降级**：无声卡 → 静音；存档损坏 → 按 0；素材缺失 → 明确报错并退出

---

## 测试

```powershell
.venv\Scripts\python.exe -m pytest -q                    # 184 个用例
.venv\Scripts\python.exe -m pytest -q --cov=src          # 覆盖率 89%
```

| 测试文件 | 守护内容 |
|---|---|
| `test_feel.py` | 手感契约：非对称重力、顶点滞空、下落速度下限 |
| `test_physics.py` | 积分、速度钳制、旋转映射 |
| `test_collision.py` | hitbox、三种死亡判定、计分时机 |
| `test_difficulty.py` | 阶梯难度、缝隙中心钳制 |
| `test_tuning_invariant.py` | 调参红线（防止改出"理论不可通过"的管道） |
| `test_entities.py` | 鸟/管道/地面/背景/HUD 渲染 |
| `test_states.py` | 五态迁移、暂停冻结、重开重置 |
| `test_regressions.py` | 第一轮缺陷回归（24 条，按缺陷 ID 组织） |
| `test_review_fixes.py` | 两轴审查修复回归（16 条） |
| `test_launcher.py` | 启动器决策矩阵与执行路径 |
| `test_assets.py` / `test_audio.py` / `test_score_store.py` / `test_config.py` / `test_display.py` | 资源、音效、存档、配置、倍率 |

### 辅助脚本

```powershell
.venv\Scripts\python.exe scripts/check_assets.py    # 素材体检（不启动游戏）
.venv\Scripts\python.exe scripts/tune_sim.py        # 难度与手感参数校验
.venv\Scripts\python.exe scripts/smoke_run.py       # 无头跑一局并生成 6 张验收截图到 build/screens/
```

---

## 调参

所有参数集中在 **`src/config.py`**。手感相关参数：

| 参数 | 默认 | 作用 |
|---|---|---|
| `GRAVITY` | 1500 | 上升段基准重力 |
| `FLAP_VELOCITY` | -380 | 起跳初速度（绝对值越大跳越高） |
| `MAX_FALL_SPEED` | 480 | 终端下落速度（越小越"飘"） |
| `GRAVITY_FALL_SCALE` | 0.65 | 下降重力系数（越小落得越慢） |
| `HANG_VY_THRESHOLD` | 120 | 顶点滞空过渡区的速度阈值 |
| `HANG_GRAVITY_SCALE` | 0.35 | 顶点处重力系数（越小悬停越久） |

难度参数：`BASE_GAP` / `GAP_STEP` / `MIN_GAP` / `SPEED_STEP` / `MAX_LEVEL`。

### 修改参数后必须验证

```powershell
.venv\Scripts\python.exe scripts/tune_sim.py
.venv\Scripts\python.exe -m pytest tests/test_tuning_invariant.py tests/test_feel.py -q
```

两条红线：

1. `MIN_GAP - HITBOX_H >= 1.25 × 单跳升高` —— 最窄缝隙必须留出操作余量
2. 最窄缝隙的 `可停留时长 / 穿越耗时 >= 1.25` —— 否则最高难度"理论上无法通过"

违反任一条，游戏在最高难度会变成必须帧级精确，属设计缺陷而非难度。

---

## 文档

| 文档 | 内容 |
|---|---|
| [需求 Spec](docs/specs/2026-11-23-flappybird-design.md) | v1.1，41 条编号需求 + 资源映射 + 界面契约 + 调参分析 |
| [实施计划](docs/plans/2026-11-23-flappybird/flappybird.md) | 5 阶段 17 任务的开发计划与验收记录 |
| [测试计划](docs/testing/测试计划.md) | 测试范围、策略、进退出准则 |
| [测试用例](docs/testing/测试用例.md) | 76 条用例（前置条件/步骤/预期/优先级） |
| [缺陷报告](docs/testing/缺陷报告.md) | 发现的缺陷、根因、修复记录 |
| [代码审查](docs/reviews/2026-11-23-code-review.md) | 两轴审查（Standards + Spec） |
| [提示词历史](PromptHistory.txt) | 开发全过程的 12 条提示词与响应摘要 |

---

## 排障

| 现象 | 处理 |
|---|---|
| 提示"无法自动准备运行环境" | `uv` 与 `python -m venv` 都不可用；按提示里打印的绝对路径命令手动执行 |
| 窗口偏小 | 程序按桌面可用区取能放下的最大整数倍；可用 `config.FORCE_SCALE` 强制 |
| 没有声音 | 属正常降级，控制台会打印 `[audio]` 原因；按 `M` 可切换静音 |
| 控制台出现 `SysFont` 异常 | 已知的 pygame 2.6.1 + Python 3.12 缺陷，代码已自动回退内置字体，不影响显示 |
| 最高分不保存 | 检查 `save/` 是否可写；不可写时游戏仍可玩，仅本次成绩不保留 |
| 启动报素材缺失 | 运行 `scripts/check_assets.py` 查看具体缺失文件名 |

---

## 已知限制

| 项 | 说明 |
|---|---|
| HUD 非等宽字体 | pygame 2.6.1 在 Windows 下 `SysFont` 有缺陷（任何入参都抛 `TypeError`），实际恒定回退到内置 freesansbold。若需等宽字体应随项目附带 `.ttf` |
| 升级瞬间新旧管道速度不同 | `FR-DIFF-1` 要求已生成管道不变速，属设计取舍 |
| `Game.run()` 为阻塞循环 | 主循环本身不可单测，靠 `draw_frame` / `handle_events` 拆分覆盖 |

---

## 许可

课程作业项目。素材版权归原作者所有，仅用于学习。
