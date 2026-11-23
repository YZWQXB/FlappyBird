# FlappyBird（Python / pygame）

基于 `res/` 素材的经典 FlappyBird 复刻：空格起跳、穿越管道、阶梯式难度、昼夜与鸟色同步切换。

## 环境要求

- Windows 10 / 11
- Python 3.12（本机为 uv 托管的 3.12.15）
- 音频设备可选（无声卡会自动静音，不影响游玩）

## 运行（推荐：零配置）

```powershell
python main.py
```

**不需要手动建虚拟环境。** 启动器会自动处理：

1. 当前 Python 有 pygame → 直接运行；
2. 项目已有 `.venv` 但当前 Python 没 pygame → **自动切换**到 `.venv` 运行；
3. 还没有 `.venv` → **自动创建并安装依赖**（优先用 `uv`，没有则用 `python -m venv`）；
4. 以上都失败 → 打印**带绝对路径、可直接复制**的命令。

也可以双击 `start.bat`。

## 手动安装（如需可控环境）

```powershell
uv venv .venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.venv\Scripts\python.exe main.py
```

## 操作

| 按键 | 作用 |
|---|---|
| `SPACE` | 起飞 / 扇翅 / 结束后重开 |
| `P` | 暂停 / 继续 |
| `M` | 静音开关（屏幕底部显示 MUTE / SOUND ON，1.5 秒） |
| `R` | 结束后重开（与 SPACE 等价） |
| `ESC` | 退出游戏 |

窗口失焦时游戏会自动暂停（避免切出去回来已经撞死）。

## 玩法规则

- 每穿过一对管道 +1 分。
- 撞管道、撞地面、越过屏幕上边界都会结束本局，随后播放坠落动画。
- 难度阶梯（每 5 分升一级，最高 6 级）：速度 120 → 177.6 px/s，缝隙 110 → 80 px。
- 起跳手感（v1.1）：单跳升高 46 px，滞空 0.67 s（其中顶点悬停 0.32 s），下降比上升"轻"，
  终端下落速度 480 px/s —— 留出在连续高低障碍间调整的时间。
- 每 10 分切换一次昼夜背景，同时按 黄 → 蓝 → 红 循环切换小鸟配色。
- 最高分保存到 `save/highscore.json`，重启后仍然保留。

## 测试

```powershell
.venv\Scripts\python.exe -m pytest -q                    # 133 个用例
.venv\Scripts\python.exe -m pytest -q --cov=src          # 覆盖率 88%
```

测试文件对应关系：

| 文件 | 守护的内容 |
|---|---|
| `test_physics.py` / `test_collision.py` | 物理积分、碰撞判定、计分时机 |
| `test_difficulty.py` / `test_tuning_invariant.py` | 难度曲线、调参红线 |
| `test_states.py` | 五态迁移、暂停冻结、重开重置 |
| `test_entities.py` | 小鸟/管道/地面/背景/HUD 渲染 |
| `test_assets.py` / `test_audio.py` / `test_score_store.py` | 资源、音效、存档 |
| `test_regressions.py` | **缺陷回归**：每个用例对应 `docs/testing/缺陷报告.md` 中的一个缺陷 ID |

辅助脚本：

```powershell
.venv\Scripts\python.exe scripts/check_assets.py    # 素材体检（不启动游戏）
.venv\Scripts\python.exe scripts/tune_sim.py        # 难度参数可行性校验
.venv\Scripts\python.exe scripts/smoke_run.py       # 无头跑一局并出 6 张验收截图
```

## 调参

所有可调参数集中在 `src/config.py`，包括物理（`GRAVITY` / `FLAP_VELOCITY`）、
难度（`BASE_GAP` / `GAP_STEP` / `MIN_GAP` / `SPEED_STEP`）、布局与开关。

**改动物理或缝隙参数后必须执行**：

```powershell
.venv\Scripts\python.exe scripts/tune_sim.py            # 含手感指标 + 红线校验
.venv\Scripts\python.exe -m pytest tests/test_tuning_invariant.py tests/test_feel.py -q
```

手感相关参数（`src/config.py`）：

| 参数 | 默认 | 作用 |
|---|---|---|
| `GRAVITY` | 1500 | 上升段基准重力 |
| `FLAP_VELOCITY` | -380 | 起跳初速度（越大跳越高） |
| `MAX_FALL_SPEED` | 480 | 终端下落速度（越小越"飘"） |
| `GRAVITY_FALL_SCALE` | 0.65 | 下降重力系数（越小落得越慢） |
| `HANG_VY_THRESHOLD` | 120 | 顶点滞空过渡区的速度阈值 |
| `HANG_GRAVITY_SCALE` | 0.35 | 顶点处重力系数（越小悬停越久） |

两条红线（`tests/test_tuning_invariant.py` 会强制校验）：

1. `MIN_GAP - HITBOX_H >= 1.25 * HOP`
2. 最窄缝隙的 `DWELL / CROSS >= 1.25`

违反任一条，最高难度将变成"理论上无法通过"，属设计缺陷而非难度。

## 目录结构

```text
main.py            入口
src/               游戏代码
  launcher.py      启动器：自动选择/创建运行环境
  config.py        全部常量与可调参数
  assets.py        资源清单与加载（唯一出现文件名的位置）
  audio.py         音效与静音降级
  physics.py       物理与碰撞（纯函数，无 pygame 依赖）
  difficulty.py    难度曲线（纯函数）
  score_store.py   最高分持久化
  bird/pipe/ground/background/hud.py   实体与渲染
  states/          五态状态机（READY/PLAYING/PAUSED/DYING/GAMEOVER）
  game.py          主循环与状态持有
tests/             pytest 单元测试
scripts/           素材体检、调参校验、无头截图
res/               素材（图片、音频），不修改
save/              运行时生成：highscore.json
docs/              需求文档与实施计划
```

## 排障

| 现象 | 处理 |
|---|---|
| 窗口偏小 | 程序按桌面可用区取能放下的最大整数倍；可用 `config.FORCE_SCALE` 强制倍数 |
| 没有声音 | 属正常降级，控制台会打印 `[audio]` 原因；按 `M` 可切换静音 |
| 控制台有 `SysFont` 相关异常信息 | 已知的 pygame 2.6.1 + Python 3.12 缺陷，代码已自动回退到内置字体，不影响显示 |
| 最高分不保存 | 检查 `save/` 是否可写；不可写时游戏仍可玩，仅本次成绩不保留 |
| 启动报素材缺失 | 运行 `.venv\Scripts\python.exe scripts/check_assets.py` 查看具体缺失文件名 |
| 提示"无法自动准备运行环境" | 说明 `uv` 与 `python -m venv` 都不可用；按提示里打印的**绝对路径命令**手动执行即可 |
| 故意用系统 Python 跑 | 正常现象：启动器会打印 `[启动器] 正在切换到项目虚拟环境` 然后正常运行 |