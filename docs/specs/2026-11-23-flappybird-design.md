# FlappyBird（Python / pygame 复刻）需求与设计文档

- 版本：**v1.1**（已实现并同步）
- 日期：2026-11-23
- 状态：**已实现**（168 → 184 个测试全绿，覆盖率 89%）

> **v1.1 修订说明**：本版在 v1.0 需求冻结后经历了两轮实际开发与一次代码审查，Spec 已回溯同步到真实实现。
> 主要变更：非对称重力手感（附录 A.4b）、窗口倍率自适应（FR-WIN-1）、图标改为可选资源（FR-WIN-3）、旋转角度分段映射（FR-PHYS-8）、音效共享间隔（FR-AUDIO-4b）、存档写盘一致性（FR-STORE-4b）。
> 每处变更均标注了 `> v1.1` 说明与原因，便于追溯。
- 项目根目录：`E:\AI study\homework\FlappyBird`
- 资源根目录：`res/`（素材已就位，本方案只使用、不修改）

---

## 1. Context（背景与目标）

课程作业：基于 Python 徒手复刻经典像素游戏 FlappyBird。素材包已提供在 `res/`，含背景、地面、管道、三色小鸟、数字、提示图与 5 组音效。当前目录**没有**任何代码、没有 Git 仓库、没有虚拟环境；本机为 Python 3.12.15（uv 托管解释器，受 externally-managed 限制，不能直接 `pip install` 到系统解释器），pygame 尚未安装。

因此本项目要做三件事：
1. 交付一个**可直接双击/命令行运行**的 Windows 桌面 pygame 小游戏，玩法与手感对齐原版；
2. 交付**可读、可调参、可测试**的模块化代码（作业评分看重模块划分与单测）；
3. 给出 `res/` 素材的**完整组织、加载、使用规划**，使资源与代码解耦，换素材不改逻辑。

## 2. Goals（必须达成的目标）

- G1 可运行：`python main.py` 一条命令启动（或经 `start.bat`），窗口 576×1024（逻辑 288×512 × 2 倍）。
- G2 核心循环完整：READY → PLAYING ⇄ PAUSED → DYING → GAMEOVER →（重开）READY。
- G3 物理手感：空格起跳 + 恒定重力；固定步长 1/60s 模拟，与渲染帧率解耦，不同机器手感一致。
- G4 障碍与计分：上下管道成对生成并左移；穿过一对 +1 分；撞管道/撞地面/越过屏幕上边界即死亡。
- G5 难度递增：按分数阶梯式提速并收窄缝隙，到上限封顶。
- G6 昼夜与换色：每 10 分切换白天/黑夜背景，同时按黄→蓝→红循环切换小鸟配色。
- G7 资源全部来自 `res/`：图片、音效、图标均按清单加载；音效优先 `.wav`、缺失回退 `.ogg`。
- G8 健壮性：无音频设备 / 存档损坏 / 缺文件时**不崩溃**，降级继续运行。
- G9 功能集：暂停(P)、重开(空格/R)、最高分本地持久化(JSON)、开始提示界面(message.png)、静音(M)。
- G10 工程化：`src/` 分层 + `tests/` pytest + README + 可调参数集中在 `src/config.py`。

## 3. Non-Goals（明确不做）

- N1 不做本地排行榜 / 姓名输入（用户已排除）。
- N2 不做设置菜单、音量滑条、按键自定义（仅 M 键静音）。
- N3 不做 exe 打包（PyInstaller）、不做安装包；运行方式固定为源码 + venv。
- N4 不做联网、不做上传分数、不做多语言。
- N5 不做鼠标玩法、不做触屏、不做手柄。
- N6 不使用 `res/__MACOSX/` 下的任何文件（macOS 打包垃圾，加载器必须显式忽略）。
- N7 不做背景视差滚动/昼夜渐变过渡（切换为瞬时，见 §6.6）。
- N8 不使用第三方游戏框架（不引入 arcade/pygame_gui），仅 pygame + 标准库。

## 4. Recommended Approach（推荐方案）

**分层状态机 + 纯函数核心逻辑 + 统一资源管理器**：

- `Game` 持有主循环与固定步长累加器，事件与更新/渲染分离；
- 每个游戏阶段一个 `State` 子类，状态间通过显式 `enter()/exit()/handle_event()/update()/draw()` 协作，避免 if-elif 巨型主循环；
- 物理、难度、碰撞判定抽成**不依赖 pygame 的纯函数/纯数据**，可在无显示器环境下单测；
- 资源由 `AssetManager` 统一启动加载（一次性预加载）、统一命名访问，代码里不出现裸路径字符串；
- 音效由 `AudioManager` 包装，所有失败路径降级为静默空实现。

## 5. Alternatives Considered（方案对比）

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| A. 分层状态机 + 纯函数逻辑 + 资源管理器 | 可测、可调参、模块边界清晰，贴合“模块化 + pytest”要求 | 文件数多于单文件，初学者需先理解状态机 | **采用** |
| B. `pygame.sprite.Sprite` + Scene 框架 + 事件总线 | 扩展性最强，加新玩法容易 | 对本作是过度设计；抽象层多，作业评审反而看不到玩法主线 | 否决（YAGNI） |
| C. 单文件过程式 `while True` + 全局变量 | 最快出结果，代码最短 | 不可测、魔法数字遍地、状态纠缠（暂停/重开需大量补丁） | 否决（无法满足 G9/G10） |

## 6. 功能需求（Functional Requirements）

编号规则：`FR-<模块>-<序号>`，验收时逐条对照。

### 6.1 FR-WIN 窗口、渲染与主循环

- **FR-WIN-1** 逻辑分辨率 `288×512`；窗口尺寸 = 逻辑尺寸 × **实际可用整数倍率**（`display.fit_scale()` 计算）。

  > **v1.1 变更**：原 v1.0 固定 `SCALE = 2`（576×1024），但实测开发机桌面可用区为 1707×1019，1024+标题栏放不下。现改为启动时取「能放下的最大整数倍」：本机 1×（288×512），1080p 以上可 2×。`config.SCALE` 降为**首选上限**，`config.FORCE_SCALE` 可强制覆盖。
  > 因此 §9.2 的「禁用窗口自适应」条款作废，改为「整数倍自适应，禁止非整数缩放」。
- **FR-WIN-2** 渲染策略：所有绘制在 `288×512` 的 `pygame.Surface`（逻辑画布）上完成，最后 `transform.scale` 到窗口并 `blit`。代码内的坐标、速度、尺寸**一律为逻辑像素**。
- **FR-WIN-3** 窗口标题 `FlappyBird`；窗口图标使用 `res/images/flappy.ico`。**图标属于可选资源**（`assets.OPTIONAL_SPECS`）：缺失或损坏时打印一行提示并回退默认图标，**不抛 AssetError、不影响启动**。
- **FR-WIN-4** 主循环：`clock.tick(60)` 限帧；使用累加器 `acc += min(frame_dt, 0.25)`，每次消耗 `FIXED_DT = 1/60` 步进一次 `update(dt)`；渲染每帧一次。单帧最多补 5 步，防“死亡螺旋”。
- **FR-WIN-5** 关闭窗口（`QUIT`）或按 `ESC` 立即退出并保存（若有必要）；退出码 0。
- **FR-WIN-6** 禁止在游戏以外的路径写文件；唯一写入点为存档（见 FR-STORE）。
- **FR-WIN-7** 窗口失焦（`WINDOWFOCUSLOST`）时，若当前为 `PLAYING` 则自动切到 `PAUSED`；由 `config.PAUSE_ON_FOCUS_LOST = True` 控制，可关闭。

### 6.2 FR-INPUT 输入

- `SPACE`：READY 起飞 / PLAYING 扇翅膀 / GAMEOVER 重开。
- `R`：GAMEOVER 重开（与 SPACE 等价）。
- `P`：PLAYING ⇄ PAUSED 切换（其他状态忽略）。
- `M`：静音开关（**任意状态生效**，屏幕**右上角**显示 `MUTE` 提示 1.5s，**仅静音时显示**）。
  > **v1.1 实现**：M 键在 `Game.handle_events` 层统一拦截，因此 5 个状态全部生效；状态层**不得**再处理 `K_m`（否则双次切换等于没切，有测试守护）。
  > 原实现居中显示于 y=488（压地面带），且未静音时显示 `SOUND ON`；现改为右上角且只在静音时出现。
- `ESC`：退出程序。
- 只响应 `KEYDOWN`，长按不连发（避免「按住空格无敌」）。
  > **v1.1 实现说明**：pygame **默认即为不重复**（`set_repeat` 默认关闭），因此代码中不显式调用 `pygame.key.set_repeat(0)`；行为符合要求，仅省略了冗余调用。若日后有人开启 repeat，需补回该调用。

### 6.3 FR-STATE 状态机

状态集合：`READY`、`PLAYING`、`PAUSED`、`DYING`、`GAMEOVER`。

| 迁移 | 触发条件 | 动作 |
|---|---|---|
| 启动 → READY | 程序启动 | 播 `swoosh`，鸟在中间上下浮动，地面滚动，`message.png` 显示 |
| READY → PLAYING | `SPACE` | 播 `wing`，鸟获得起跳初速（`vy = FLAP_VELOCITY`），管道开始生成，`message.png` 消失 |
| PLAYING → PAUSED | `P` | 冻结所有更新（含鸟、管道、地面、音效播放），覆盖 `PAUSED` 遮罩 |
| PAUSED → PLAYING | `P` | 恢复；累加器清零避免一次性补步 |
| PLAYING → DYING | 任一碰撞（FR-PHYS-5） | 播 `hit`，停止计分，鸟进入自由落体并旋转；管道/地面停止左移 |
| DYING → GAMEOVER | 鸟落到地面 | 播 `die`，写最高分（若刷新），显示 `gameover.png` + 分数 + BEST |
| GAMEOVER → READY | `SPACE`/`R` | 播 `swoosh`，重置分数/难度/昼夜与鸟色，保留 BEST |

约束：
- **FR-STATE-1** 状态迁移只允许上表列出的边；非法输入被忽略且不改变状态。
- **FR-STATE-2** 进入 READY / 重开时**重置**：分数、难度等级、管道列表、管道生成距离累加、昼夜与鸟色索引、鸟位置与速度。BEST 不重置。
- **FR-STATE-3** DYING 期间忽略 SPACE/P（不可“空中暂停”），仅响应 ESC。

### 6.4 FR-PHYS 物理与碰撞

- **FR-PHYS-1** 固定步长 `FIXED_DT = 1/60`，每步执行 `vy += GRAVITY * dt ; y += vy * dt`。
- **FR-PHYS-2** 初始参数（`config.py` 可调）：`GRAVITY = 1500` px/s²、`FLAP_VELOCITY = -380` px/s、`MAX_FALL_SPEED = 480` px/s。起跳时 `vy = FLAP_VELOCITY`（直接赋值，不叠加，保证手感稳定）。由上升段基准重力得**单跳升高** `hop = FLAP² / (2·GRAVITY) ≈ 48 px`（离散实测 46.2 px）。

- **FR-PHYS-2a**（v1.1 新增，解 v1.0 手感问题）**非对称重力 + 顶点滞空**，实现于 `physics.gravity_for()`：

| 参数 | 值 | 作用 |
|---|---|---|
| `GRAVITY_FALL_SCALE` | 0.65 | 下降段重力 = 基准 × 0.65，下落更"轻" |
| `HANG_VY_THRESHOLD` | 120 px/s | \|vy\| 小于该值进入顶点滞空过渡区 |
| `HANG_GRAVITY_SCALE` | 0.35 | 顶点处重力 = 基准 × 0.35，线性过渡到阈值处 |

曲线在 `|vy| = HANG_VY_THRESHOLD` 处**连续**（避免可感知的突变），且任意速度下加速度不超过基准重力。

**v1.0 的实际手感问题**（用户反馈）：总滞空仅 0.500 s、顶点**零悬停**、离开顶点 0.133 s 就下落 60 px —— 玩家来不及在连续高低障碍间调整。
**v1.1 修复后**：总滞空 0.667 s（+33%）、顶点悬停 0.317 s（从无到有）、落 60 px 用时 0.167 s（+26%）、终端速度 480 px/s（−25%）。

> 注意：解析式 `HOP` 仍用于调参红线（更保守）；实际手感由 `physics.jump_feel_metrics()` 度量，`tests/test_feel.py` 锁定下限。
- **FR-PHYS-2b**（数值自洽约束）管道最窄缝隙必须留出操作余量：`MIN_GAP − HITBOX_H ≥ 1.25 × hop`。按上方参数：`80 − 18 = 62 ≥ 1.25 × 48.1 = 60.2` ✓。**修改 GRAVITY / FLAP_VELOCITY / MIN_GAP 任一值时，必须重新校验该不等式与附录 A.2 的 `DWELL/CROSS ≥ 1.25`**，否则会出现“理论上无法通过”的管道。
- **FR-PHYS-3** `vy` 下限钳制为 `FLAP_VELOCITY`（连续按空格不能越跳越快），上限钳制为 `MAX_FALL_SPEED`（防高速穿模）。
- **FR-PHYS-4** 管道水平位置按 `x -= scroll_speed * dt` 更新，`scroll_speed` 由难度等级决定（FR-DIFF）。
- **FR-PHYS-5** 死亡判定（PLAYING 状态下每步检查）：
  1. 小鸟内缩矩形（hitbox）与任一管道上/下矩形相交；
  2. hitbox 底边 `>= LAND_Y`（撞地面）；
  3. hitbox 顶边 `<= 0`（越过屏幕上边界）。
  命中任一 → `DYING`。
- **FR-PHYS-6** hitbox：小鸟精灵 34×24，内缩 3px → 逻辑尺寸 **28×18**，以精灵中心对齐。碰撞使用 AABB（`pygame.Rect`），**不使用 mask 逐像素检测**（可测、开销低；像素级容错通过内缩实现）。
- **FR-PHYS-7** 计分判定：管道以 `pipe.x + PIPE_W <= bird.hitbox.x` 首次成立且该管道 `scored == False` 时，`score += 1`、播 `point`、置 `scored = True`。
- **FR-PHYS-8** 精灵视觉旋转（**仅 PLAYING/DYING 生效**）：角度由 `vy` 分段映射，旋转只影响绘制，不影响 hitbox。可用 `ROTATE_SPRITE` 开关关闭。

| vy 区间 | 角度 | 含义 |
|---|---|---|
| `vy <= FLAP_VELOCITY(-380)` | `-25°` | 起跳瞬间仰头 |
| `FLAP_VELOCITY < vy < 0` | `-25° → 0°` 线性 | 上升中回正 |
| `0 <= vy <= ROTATE_VY_LEVEL(120)` | **`0°`（水平）** | 顶点与待机 |
| `ROTATE_VY_LEVEL < vy < ROTATE_VY_FULL(400)` | `0° → 90°` 线性 | 开始俯冲 |
| `vy >= 400` | `+90°` | 急坠 |

  > **v1.1 修复**：原实现用 `FLAP_VELOCITY↔400` 单段线性插值，导致 `rotation_for(0) = 31°`——顶点和 READY 待机的鸟都低头 31°（肉眼可见的姿态错误）。现增加水平区段，`rotation_for(0) = 0°`。
  > **READY 不旋转**：待机时固定 `0°`，不调用 `rotation_for`。

### 6.5 FR-DIFF 难度曲线（阶梯式）

| 项 | 规则 |
|---|---|
| 等级 | `level = min(score // 5, MAX_LEVEL)`，`MAX_LEVEL = 6` |
| 滚动速度 | `speed = BASE_SPEED × (1 + SPEED_STEP × level)`，`BASE_SPEED = 120` px/s、`SPEED_STEP = 0.08` |
| 管道缝隙 | `gap = max(BASE_GAP − GAP_STEP × level, MIN_GAP)`，`BASE_GAP = 110`、`GAP_STEP = 5`、`MIN_GAP = 80` |
| 结果 | level 0→6：速度 120→**177.6** px/s（×1.48），缝隙 110→**80** px（可操作净空 92→62 px）|
| 自洽校验 | 最窄净空 62 px ≥ 1.25×hop(48.1)=60.2 px（见 FR-PHYS-2b）|

- **FR-DIFF-1** 难度变更仅影响**新生成**的管道高度/缝隙与后续滚动速度；已在屏幕上的管道几何不变（避免“管道抖动”）。
- **FR-DIFF-2** 速度提升后管道**按距离**生成：累计移动距离 `>= PIPE_SPACING(150)` 才生成下一对，保证提速时管道横向间距（以像素计）恒定，不会堆叠。
- **FR-DIFF-3** 缝隙中心高度：`center ∈ [PIPE_MARGIN + gap/2, LAND_Y − PIPE_MARGIN − gap/2]`（`PIPE_MARGIN = 48`，`LAND_Y = 400`）；与前一对的 `center` 差值钳制在 `±MAX_CENTER_DELTA = 120` px 内，避免出现物理上不可通过的一对管道。
- **FR-DIFF-4** 难度函数必须为纯函数（`level_for(score)`、`speed_for(level)`、`gap_for(level)`），供单测穷举。

### 6.6 FR-THEME 昼夜与小鸟配色

- **FR-THEME-1** `stage = score // 10`（0 起）；背景：`stage % 2 == 0` → `background-day.png`，否则 `background-night.png`。
- **FR-THEME-2** 小鸟配色：`palette = stage % 3` → 0 黄(`yellowbird-*`)、1 蓝(`bluebird-*`)、2 红(`redbird-*`)。
- **FR-THEME-3** 背景与配色变化**在跨过 10 分的那一刻瞬时生效**，不插值、不闪屏；同一帧内背景与鸟色同步切换（两者由同一个 `stage` 派生，天然一致）。
  > **v1.1 修复**：`PlayingState.update` 必须先**计分**再**按新分数推导 stage**。原实现顺序相反，导致跨过 10 分的那一步会渲染出「10 分 + 白天」的一帧（16.7ms 闪烁）。
- **FR-THEME-4** 组合周期为 `lcm(2,3) = 6` 个 stage（60 分）后完全回到初始外观。
- **FR-THEME-5** 昼夜与配色状态在 READY/重开时归零（day + 黄鸟）。

### 6.7 FR-AUDIO 音效

| 事件 | 音效 | 播放时机 |
|---|---|---|
| 起飞 / 扇翅 | `wing` | READY→PLAYING、PLAYING 每次空格成功起跳 |
| 得分 | `point` | 分数 +1 |
| 撞击 | `hit` | 进入 DYING 的瞬间 |
| 坠落触地 | `die` | DYING 中小鸟落地瞬间（与 hit 至少间隔 200ms） |
| 界面切换 | `swoosh` | 进入 **GAMEOVER**（结算）、进入 READY（启动）；重开时只播一次（由 ReadyState.enter 负责） |

- **FR-AUDIO-1** 加载优先级：同名 `.wav` 存在则用 `.wav`，否则回退 `.ogg`；两者都缺 → 该音效记为静音条目，不抛异常。
- **FR-AUDIO-2** 初始化：`pygame.mixer.pre_init(44100, -16, 2, 512)` 后 `pygame.mixer.init()`；任一步抛异常（无声卡/远程桌面/驱动缺失）→ `AudioManager` 进入**禁用模式**，所有 `play()` 为空操作，游戏完整可玩。
- **FR-AUDIO-3** 静音：`M` 切换；静音时 `play()` 不发声但事件与逻辑不受影响；静音状态**不持久化**（重启恢复有声）。
- **FR-AUDIO-4** 通道规划：预留 8 个通道；`die`/`hit`/`swoosh` 走**固定通道**（0/1/2）并 `stop()` 前一声，避免叠音爆音；`wing`/`point` 走自动分配通道。

  - **FR-AUDIO-4b**（v1.1 新增）`hit` 与 `die` 共享**同一条时间线**：二者距上次播放均需 ≥ `SFX_PRIORITY_GAP_MS(200)`，由 `audio.priority_gap_ok()` 判定。
    > 原实现按音效名各自计时，而 hit/die 是两个不同名字，互不约束，Spec 的「至少间隔 200ms」从未生效。
- **FR-AUDIO-5** 暂停时不主动停止已在播放的音效（音效都很短，<1s）；恢复后不补播。

### 6.8 FR-SCORE 计分与 HUD

- **FR-SCORE-1** 当前分数用数字精灵 `0.png`–`9.png` 渲染（`1.png` 宽 16，其余 24），顶部水平居中，`y = 44`，数字间距 1px。
- **FR-SCORE-2** 分数为 0 时不显示（与原版一致），≥1 时显示；不补前导零。
- **FR-SCORE-3** PLAYING / PAUSED / DYING 状态均显示当前分数（暂停时分数保持可见）。
- **FR-SCORE-4** HUD 文字（`PAUSED`、`PRESS SPACE`、`BEST`、`MUTE`）使用等宽粗体，16px（标题 20px）。**HUD 文案一律英文大写**，避免中文字形缺失。

  > **v1.1 已知限制**：pygame 2.6.1 + Python 3.12 在 Windows 下的 `sysfont.initsysfonts_win32` 有缺陷（`splitext` 收到 int），**任何 `SysFont` 入参都会抛 `TypeError`**。因此实际恒定回退到 `Font(None, size)`（内置 freesansbold）。
  > 代码通过 `Hud.font_fallback` 暴露该状态，并用 `try/except (TypeError, OSError, AttributeError, pygame.error)` 兜底。**等宽粗体的视觉契约在当前 pygame 版本下达不到**，属环境限制而非实现缺陷。
  > 若需真正等宽字体，应随项目附带 `.ttf` 并用 `pygame.font.Font(path, size)` 加载。

### 6.9 FR-STORE 最高分持久化

- **FR-STORE-1** 路径：`<项目根>/save/highscore.json`（首次写入时自动 `mkdir -p`）。
- **FR-STORE-2** 结构：`{"version": 1, "best_score": 0}`；读取时校验类型与范围（int，`0 <= best < 10^6`），不合法按 0 处理。
- **FR-STORE-3** 写策略：仅当 `score > best` 时在进入 GAMEOVER 时写一次；**原子写**（先写 `highscore.json.tmp` 再 `os.replace`），避免断电产生半文件。
- **FR-STORE-4** 任何读写异常（权限拒绝、磁盘满、JSON 损坏、目录不存在）→ 记录一次 `print` 警告，按 best=0 继续，绝不崩溃。存档失败不影响游戏流程。

  - **FR-STORE-4b**（v1.1 补充）**写盘失败时内存中的 best 不得升级**：先写盘、成功后才赋值。否则本局会显示「新纪录」，重启后又回退，用户观感是「最高分丢了」。
  - 文件**不存在**属正常首次运行，不告警；其余读失败（损坏/类型非法/超范围）均打印原因。
- **FR-STORE-5** 启动时读取一次并缓存到内存；GAMEOVER 界面显示 `BEST`（本次刷新后立即显示新值）。

### 6.10 FR-SCREEN 画面与各状态视觉

**READY**

```text
+--------------------------------------------------+ 288 x 512
|                                                  |
|                 [ message.png ]                  |  184x267，居中 x=52, y=96
|                      (小鸟)                       |  鸟 x=64, 居中 y≈256，上下浮动 ±5px
|                    [地面滚动]                     |  y=400..512
+--------------------------------------------------+
```

- 地面以 `scroll_speed = BASE_SPEED` 向左滚动；背景静止（素材正好 288×512）。
- 小鸟播放 `midflap → upflap → midflap → downflap` 循环，0.1s/帧。

**PLAYING**

```text
|                    [ 0 1 2 ]                     |  分数，y=44
|      [上管 · 倒置]         [上管]                 |  管道 52x320，cap 朝向缝隙
|                                                  |
|           (小鸟)                                  |
|      [下管]                [下管 · 正置]          |
|                    [地面滚动]                     |
```

**PAUSED**：完整冻结画面 + 半透明黑遮罩（alpha 120）+ 居中 `PAUSED`（20px，白字 2px 深色描边）+ 下方小字 `PRESS P TO RESUME`。

**GAMEOVER**

```text
|                [ gameover.png ]                  |  192x42，y=140 居中
|                 SCORE  12                        |  数字精灵，y=220
|                 BEST   30                        |  "BEST" + 数字精灵，y=280
|             PRESS SPACE TO RESTART               |  y=460
```

- **FR-SCREEN-1** 遮罩/文字必须使用 `SRCALPHA` 临时 Surface，不修改主画布 alpha。
- **FR-SCREEN-2** 窗口缩放在 `blit` 前完成（`transform.scale` 每帧一次到预分配的窗口 Surface），不做逐对象缩放。
- **FR-SCREEN-3** 场景中不出现任何中文字符渲染（资源无中文字体）。
- **FR-SCREEN-4**（v1.1）布局坐标统一收敛到 `config.py`（`READY_MSG_Y`、`PAUSED_TITLE_Y`、`PAUSED_HINT_Y`、`BEST_LABEL_OFFSET`、`MUTE_BADGE_X/Y` 等），状态层**不得**出现裸像素值。

### 6.11 FR-ASSET 资源加载契约

- **FR-ASSET-1** 资源根路径由 `Path(__file__).resolve().parents[1] / "res"` 推导，**与当前工作目录无关**（从任意目录启动都能找到资源）。
- **FR-ASSET-2** 启动时一次性预加载全部图片到 `dict[str, Surface]`，键名统一小写下划线（`bird_yellow_mid` 等）；游戏循环中**不得**出现 `pygame.image.load`（唯一允许位置是 `assets.py` 的加载函数）。
- **FR-ASSET-3** 必须跳过并忽略 `res/__MACOSX/`（不遍历、不加载、不校验）。
- **FR-ASSET-4** 缺图片 → 启动阶段抛 `AssetError` 并给出**具体缺失文件名**的可读报错 + 退出码 2（图片缺失属不可降级的致命错误；音效缺失不致命）。

  - **例外（v1.1）**：`flappy.ico` 属**可选资源**（`OPTIONAL_SPECS`），缺失只打印一行 `[assets] 可选资源缺失，已忽略` 并回退默认图标，**不触发 AssetError**。
  - **尺寸校验（v1.1）**：清单中的 `size` 若与实际不符，打印 `[assets] 尺寸不符：<文件名> 实际 WxH 清单 WxH` 后按实际尺寸绘制，不致命。
- **FR-ASSET-5** 图片统一转 `convert_alpha()`（需先 `set_mode`）；管道与小鸟的常用派生帧必须缓存，避免每帧 `transform`：
  - `pipe_cap(facing_up)` → 按朝向缓存 2 个；
  - `pipe_body(height, facing_up)` → 按 `(高度, 朝向)` 缓存，上限 256 条；
  - `rotated_bird(palette, flap, degrees)` → 按 `(帧索引, 整数角度)` 缓存，上限 `ROTATE_CACHE_MAX`；缓存键用 `palette * len(FLAP_NAMES) + flap`，**禁止硬编码帧数**（否则新增帧会与既有组合静默碰撞）。

## 7. 资源组织与使用规划（res/ 清单）

### 7.1 目录结构（现状）

```text
res/
├── audios/                     # 5 组音效，每组 .wav + .ogg 双份
│   ├── die.ogg / die.wav
│   ├── hit.ogg / hit.wav
│   ├── point.ogg / point.wav
│   ├── swoosh.ogg / swoosh.wav
│   └── wing.ogg / wing.wav
├── images/
│   ├── background-day.png      288x512
│   ├── background-night.png    288x512
│   ├── land.png                336x112
│   ├── pipe-green.png          52x320   （cap 在顶部，cap 高 25px，身宽 48px）
│   ├── pipe-red.png            52x320   （同上，备用，默认不用）
│   ├── yellowbird-{upflap,midflap,downflap}.png    34x24
│   ├── bluebird-{upflap,midflap,downflap}.png      34x24
│   ├── redbird-{upflap,midflap,downflap}.png       34x24
│   ├── 0.png … 9.png           24x36  （1.png 为 16x36）
│   ├── message.png             184x267
│   ├── gameover.png            192x42
│   └── flappy.ico              窗口图标
└── __MACOSX/                   # macOS 打包垃圾，全项目忽略（可安全删除）
```

### 7.2 逻辑键 → 物理文件映射（`AssetManager` 唯一权威表）

| 逻辑键 | 文件 | 用途 | 尺寸/备注 |
|---|---|---|---|
| `bg_day` | images/background-day.png | 白天背景 | 288×512，静态 |
| `bg_night` | images/background-night.png | 黑夜背景 | 288×512，静态 |
| `land` | images/land.png | 地面 | 336×112，横向平移 + 平铺 2 块覆盖 288 |
| `pipe_green` | images/pipe-green.png | 绿色管道（默认） | 52×320，拆分 cap 25px + 身 48px |
| `pipe_red` | images/pipe-red.png | 红色管道（保留，v1 不用） | 52×320 |
| `bird_{yellow,blue,red}_{up,mid,down}` | images/{c}bird-{upflap,midflap,downflap}.png | 三色小鸟各 3 帧 | 34×24；hitbox 内缩 3px |
| `digit_0`…`digit_9` | images/0.png … 9.png | 分数/最高分数字 | 高 36，宽 24（`digit_1` 为 16） |
| `msg_ready` | images/message.png | 开始提示 | 184×267 |
| `msg_gameover` | images/gameover.png | 结束提示 | 192×42 |
| `icon` | images/flappy.ico | 窗口图标 | 用 `image.load` 载入为 Surface |
| `sfx_{wing,point,hit,die,swoosh}` | audios/{name}.wav → 回退 .ogg | 音效 | 见 FR-AUDIO-1 |

> 未使用的素材：`pipe-red.png`（保留为可选主题，本版不启用）、`*.ogg`（在 `.wav` 缺失时才使用）。二者都在清单里登记，保证“素材无遗漏说明”。

### 7.3 加载流程（启动一次，之后只读缓存）

1. `AssetManager.__init__(res_root)`：校验 `res/images`、`res/audios` 目录存在；
2. 按 §7.2 表逐项加载图片（`convert_alpha()`），记录缺失项；缺失 → 抛 `AssetError`（含文件名列表）；
3. 派生缓存：管道拆分为 `cap` 与 `body`（body 取 y=200 处 1px 行拉伸）、上下管各自的翻转/拉伸辅助；小鸟旋转帧**按需 LRU 缓存**（角度离散到 1°，最多约 116 帧/配色，实际内存可忽略）；
4. 音效按 `.wav → .ogg` 顺序尝试加载，失败记录为 `None`；
5. `pygame.display.set_icon(icon)`。

### 7.4 音频与图片的解耦原则

- 游戏逻辑只认**逻辑键 + 事件名**，不认文件名与格式；换素材（例如只保留 `.ogg`）不需要改任何游戏代码；
- 资源路径字符串只出现在 `src/assets.py` 的清单常量中；
- 图片尺寸若与清单不符，启动时打印一次警告（不致命），渲染按实际尺寸自适应（hitbox 仍以清单尺寸为准，避免逻辑漂移）。

## 8. 架构与模块划分

### 8.1 目录树（交付物）

```text
FlappyBird/
├── main.py                     # 入口：sys.path 修正 → Game().run()
├── requirements.txt            # pygame>=2.5,<3  ; pytest（测试）
├── README.md                   # 安装/运行/按键/调参/目录说明
├── .gitignore                  # .venv/, __pycache__/, save/, *.pyc
├── start.bat                   # 可选：Windows 双击启动（校验 venv → 调用 python main.py）
├── res/                        # 既有素材（不改）
├── save/                       # 运行时生成：highscore.json（git 忽略）
├── docs/specs/2026-11-23-flappybird-design.md   # 本文档
├── src/
│   ├── __init__.py
│   ├── config.py               # 唯一常量源：尺寸/物理/难度/颜色/路径/文案
│   ├── launcher.py             # 启动器：自动切换/创建运行环境（v1.1 新增）
│   ├── display.py              # 窗口倍率自适应 fit_scale()（v1.1 新增）
│   ├── assets.py               # AssetManager + 资源清单 + AssetError
│   ├── audio.py                # AudioManager（回退/静音/禁用模式）
│   ├── physics.py              # 纯函数：integrate_step / clamp / 碰撞 AABB / 计分判定
│   ├── difficulty.py           # 纯函数：level_for / speed_for / gap_for / next_gap_center
│   ├── score_store.py          # HighScoreStore（原子读写/校验/降级）
│   ├── bird.py                 # Bird：状态、积分步、动画帧、旋转绘制
│   ├── pipe.py                 # PipePair：几何、缝隙、移动、计分标记、绘制
│   ├── ground.py               # Ground：平铺滚动
│   ├── background.py           # Background：昼夜切换（按 stage 选图）
│   ├── hud.py                  # 分数数字精灵渲染、文字绘制、遮罩
│   ├── game.py                 # Game：主循环、固定步长、状态切换、事件分发、渲染合成
│   └── states/
│       ├── __init__.py
│       ├── base.py             # State 抽象基类（enter/exit/handle_event/update/draw）
│       ├── ready.py
│       ├── playing.py
│       ├── paused.py
│       ├── dying.py
│       └── gameover.py
├── tests/
│   ├── conftest.py             # SDL_VIDEODRIVER=dummy、SDL_AUDIODRIVER=dummy fixture
│   ├── test_difficulty.py
│   ├── test_tuning_invariant.py # 调参红线（DWELL/CROSS、净空 ≥ 1.25×HOP）
│   ├── test_physics.py
│   ├── test_collision.py
│   ├── test_score_store.py
│   └── test_assets.py
└── scripts/
    ├── check_assets.py         # 独立资源体检脚本（不启动游戏即可校验素材）
    └── tune_sim.py             # 无头调参仿真：跑通“参数是否可通过”的可行性校验（见附录 A）
```

### 8.2 模块职责与依赖（禁止反向依赖）

| 模块 | 职责 | 依赖 | 明确不负责 |
|---|---|---|---|
| `config` | 全部可调常量与文案 | 无 | 无逻辑 |
| `launcher` | 运行环境探测/切换/创建、退出码约定 | 标准库（subprocess/shutil），不 import pygame | 不含游戏逻辑 |
| `display` | 整数倍率计算、窗口创建 | pygame, config | 不做状态管理 |
| `assets` | 加载/缓存/键名映射/派生帧 | pygame, config | 不碰游戏状态 |
| `audio` | 音效播放、静音、失败降级 | pygame.mixer, assets 的 Sound 对象 | 不决定“何时播” |
| `physics` | 积分、钳制、AABB 相交、越界判定 | 无（纯数据，允许传入 Rect 样元组） | 不持有 pygame.Surface |
| `difficulty` | 等级/速度/缝隙/下一个缝隙中心 | random（可注入 seed） | 不持有管道对象 |
| `score_store` | 最高分读写 | json, os, pathlib | 不渲染 UI |
| `bird` / `pipe` / `ground` / `background` | 自身状态 + 绘制 | assets, config, physics | 不处理输入、不切状态 |
| `hud` | 数字/文字/遮罩绘制 | assets, config | 不持有分数真值 |
| `states/*` | 阶段行为与迁移 | game 上下文、entities、audio、hud | 不直接改窗口 |
| `game` | 循环、步进、事件、状态持有、渲染合成 | 以上全部 | 不含具体玩法细节 |

### 8.3 关键接口（实施时以此为准）

```python
# config.py
LOGICAL_W, LOGICAL_H = 288, 512
SCALE = 2
FPS = 60
FIXED_DT = 1 / 60
GRAVITY = 1500.0            # px/s^2 上升段基准重力
FLAP_VELOCITY = -380.0      # px/s
MAX_FALL_SPEED = 480.0      # px/s 终端下落速度
GRAVITY_FALL_SCALE = 0.65   # 下降段重力系数
HANG_VY_THRESHOLD = 120.0   # 顶点滞空过渡区阈值
HANG_GRAVITY_SCALE = 0.35   # 顶点处重力系数
HOP = FLAP_VELOCITY**2 / (2 * GRAVITY)   # 派生量，仅供红线校验
BASE_SPEED = 120.0        # px/s
BASE_GAP, MIN_GAP, GAP_STEP = 110, 80, 5
LEVEL_EVERY, MAX_LEVEL, SPEED_STEP = 5, 6, 0.08
PIPE_W, PIPE_H, PIPE_CAP_H = 52, 320, 25
PIPE_SPACING, PIPE_MARGIN, MAX_CENTER_DELTA = 150, 48, 120
LAND_Y, LAND_H, LAND_TILE_W = 400, 112, 336
BIRD_X, BIRD_Y0, BIRD_W, BIRD_H, BIRD_INSET = 64, 256, 34, 24, 3
THEME_EVERY = 10

# 旋转（分段映射，见 FR-PHYS-8）
ROTATE_MIN_DEG, ROTATE_MAX_DEG = -25.0, 90.0
ROTATE_VY_LEVEL, ROTATE_VY_FULL = 120.0, 400.0

# 布局（状态层不得出现裸像素）
SCORE_Y, READY_MSG_Y = 44, 96
PAUSED_TITLE_Y, PAUSED_HINT_Y = 220, 256
SCORE_PANEL_Y, BEST_PANEL_Y, BEST_LABEL_OFFSET = 210, 284, 26
MUTE_BADGE_X, MUTE_BADGE_Y = LOGICAL_W - 34, 12

# 退出码
EXIT_OK, EXIT_ASSET_ERROR, EXIT_DISPLAY_ERROR, EXIT_ENV_ERROR = 0, 2, 3, 4

# difficulty.py  —— 纯函数，无副作用
def level_for(score: int) -> int: ...
def speed_for(level: int) -> float: ...
def gap_for(level: int) -> int: ...
def gap_band(gap: float) -> tuple[float, float]: ...
def next_gap_center(prev_center: float, gap: int, rng: random.Random) -> float: ...

# physics.py —— 纯函数，不 import pygame
def gravity_for(vy: float) -> float: ...          # 非对称重力曲线
def integrate(vy: float, y: float, dt: float) -> tuple[float, float]: ...
def clamp_vy(vy: float) -> float: ...
def hitbox(x: float, y: float) -> tuple[int, int, int, int]: ...
def pipe_boxes(pipe: PipeGeom, land_y: float) -> tuple[Box, Box]: ...
def overlaps(a: Box, b: Box) -> bool: ...
def is_dead(box: Box, pipes: Sequence[PipeGeom], land_y: float) -> bool: ...
def should_score(pipe_x: float, bird_left: float) -> bool: ...
def rotation_for(vy: float) -> float: ...          # 分段映射
def jump_feel_metrics(steps: int = 900) -> dict[str, float]: ...   # 手感度量

# assets.py
class AssetError(RuntimeError): ...
IMAGE_SPECS: tuple[ImageSpec, ...]                 # 必需资源（缺一即 fatal）
OPTIONAL_SPECS: tuple[ImageSpec, ...]              # 可选资源（如 icon）
class AssetManager:
    def __init__(self, res_root: Path) -> None: ...
    images: dict[str, Surface]
    def image(self, key: str) -> Surface: ...
    def optional_image(self, key: str) -> Surface | None: ...
    def digit(self, value: int) -> Surface: ...
    def bird_frame(self, palette: int, flap: int) -> Surface: ...
    def rotated_bird(self, palette: int, flap: int, degrees: float) -> Surface: ...
    def pipe_cap(self, facing_up: bool) -> Surface: ...
    def pipe_body(self, height: int, facing_up: bool) -> Surface: ...

# launcher.py（v1.1 新增，不 import pygame）
def decide_startup_action(*, has_pygame, has_venv_python, force_no_pygame, requirements_present) -> str: ...
def ensure_environment(root: Path, argv: list[str]) -> int | None: ...
def manual_instructions(root: Path) -> str: ...

# display.py（v1.1 新增）
def fit_scale(avail_w: int, avail_h: int, preferred: int = SCALE, force: int = FORCE_SCALE) -> int: ...
def query_desktop_size() -> tuple[int, int]: ...
def init_window(screen_size: tuple[int, int] | None = None) -> tuple[Surface, int]: ...

# audio.py
class AudioManager:
    enabled: bool
    muted: bool
    def play(self, name: str) -> None: ...
    def toggle_mute(self) -> None: ...

# score_store.py
class HighScoreStore:
    def load(self) -> int: ...
    def save_if_better(self, score: int) -> int: ...
```

## 9. Interface Design Contract（画面与交互契约）

### 9.1 Experience and Journeys

- **目标用户**：作业演示环境下的老师/同学，以及自己反复试玩；使用场景是**键盘单机短会话**（单局 10–60 秒）。
- **界面唯一的 job**：让玩家在 0.2 秒内知道“现在能不能动、按什么、我刚刚做错了什么”。
- **主旅程**：启动 → 看到提示图与浮动小鸟（知道按空格）→ 起飞（立刻有 `wing` 音与向上冲的反馈）→ 穿管计分（数字跳变 + `point` 音）→ 第 10 分世界变夜、鸟变蓝（明确的“进入下一阶段”信号）→ 撞管（`hit` + 画面急停）→ 坠落落地（`die`）→ 结束面板（本次 vs 最好）→ 空格再来。
- **恢复路径**：误触 P → 遮罩明确提示“PRESS P TO RESUME”；结束面板明确“PRESS SPACE TO RESTART”；任何时刻 ESC 可退出。

### 9.2 Layout

- 画布固定 288×512，纵向四段：**状态区**（0–400，游戏区）、**地面**（400–512）、**分数带**（y=44 顶部居中）、**提示带**（y=460 底部居中）。
- 3×3 分区原则：分数永远在顶部中线，提示永远在底部中线，主体玩法永远在中间，不随状态跳动位置。
- **整数倍缩放**（1× 或 2×，由 `fit_scale()` 决定），禁用非整数缩放（避免像素糊）。
  > v1.1 更正：原「禁用窗口自适应」已作废，详见 FR-WIN-1 的 v1.1 变更说明。

### 9.3 Visual System

- **方向**：完全服从素材的原版像素风（8-bit 手绘），代码**不引入任何新美术**；风格由素材自带，代码只负责对位与节奏。
- **Signature element（唯一释放的视觉个性）**：**昼夜 + 鸟色同步切换的“世界换肤”**——每 10 分整个世界换一次底色与鸟色，这是本版相对原版最明显的自定义设计，其余元素保持克制。
- **颜色角色（取自素材采样，UI 用）**：
  - `SKY_DAY` #4EC0CA、`SKY_NIGHT` #008793（背景，不用于文字）
  - `INK` #543847（描边/阴影，来自 gameover 深色）
  - `PAPER` #FFFFFF（文字主色，仅在描边衬托下使用）
  - `LAND_BASE` #DED895（地面基准，仅用于遮罩配色参考）
  - `PIPE_GREEN` #B4D468 / `PIPE_RED` #DF8A69（管道，素材自带）
  - `BIRD_YELLOW` #F8B733 / `BIRD_BLUE` #4BC1F8 / `BIRD_RED` #FC3800
- **文字样式**：monospace 粗体；白字 + 2px `INK` 四向描边（先画 4 个偏移暗字再画白字），保证在两种天空色上都可读（对比度 ≥ 4.5:1）。
- **字号**：HUD 16px，`PAUSED` 20px；数字使用精灵而非字体（像素一致性）。
- **动效原则**：只做**有信息量**的动效——地面滚动（世界在动）、小鸟扇翅（存活反馈）、浮动（待机呼吸）、坠落旋转（死亡因果）。不做无意义的缩放/闪烁。
- **Shape/Motion**：全项目无圆角、无渐变、无阴影模糊（像素风禁止）；遮挡用纯色 + 固定 alpha。

### 9.4 Components, Content, States

| 组件 | 内容/文案 | 状态 |
|---|---|---|
| 分数数字条 | 当前分数（精灵） | 0 分隐藏；暂停保持可见 |
| `message.png` | 开始提示（图形，不改文案） | 仅 READY |
| `gameover.png` | 结束标题（图形） | 仅 GAMEOVER |
| BEST 行 | `BEST` + 精灵数字 | GAMEOVER |
| 底部提示 | `PRESS SPACE TO RESTART` | GAMEOVER |
| 暂停遮罩 | `PAUSED` + `PRESS P TO RESUME` | PAUSED |
| 静音角标 | `MUTE` | 切换后 1.5s |
| 退出 | `ESC`（不显示提示，README 说明） | 全局 |

- **交互状态**：本作无按钮控件，无 hover/focus/disabled；键盘焦点即窗口焦点。窗口失焦（`WINDOWFOCUSLOST`）→ **自动进入 PAUSED**（PLAYING 时），防止“切出去回来已经撞死”。

### 9.5 Accessibility and Visual Verification

- 全键盘可玩，无鼠标依赖；PAUSED 提供明确恢复提示（弥补“按键无反馈”）。
- 文字对比：白字 + 深色描边，在 #4EC0CA 与 #008793 上均清晰；不使用红绿单独表意（避色盲歧义）。
- 不做降低动态效果开关（像素滚动为玩法本体，属非目标）。
- **视觉验收点**（截图核对）：① 启动 READY（提示图 + 浮动鸟 + 白天背景）；② 第 10 分瞬间（夜晚背景 + 蓝鸟）；③ PAUSED 遮罩；④ GAMEOVER 面板（分数与 BEST 正确）；⑤ 窗口 576×1024 无拉伸变形、无像素缝隙；⑥ 地面接缝 1px 抖动（滚动时必须无缝）。

## 10. Data Flow

```text
[启动]
 main.py → Game.__init__ → pygame.init/mixer.pre_init
        → AssetManager(res/)  ──缺失图片→ AssetError(exit 2)
        → AudioManager(enabled? 降级)
        → HighScoreStore.load() → best
        → State = ReadyState

[每帧]
 pygame.event.get()
   KEYDOWN → current_state.handle_event(ev)
              └ READY: SPACE → 切 Playing
              └ PLAYING: SPACE→bird.flap(), P→Paused, M→audio.toggle_mute()
              └ PAUSED: P→Playing
              └ GAMEOVER: SPACE/R→Ready(重置)
   QUIT/ESC → running=False
 acc += frame_dt (clamp 0.25)
 while acc >= FIXED_DT (≤5 次):
     current_state.update(FIXED_DT)      # 纯步进：鸟、管道、地面、碰撞、计分
     acc -= FIXED_DT
 current_state.draw(canvas)              # 逻辑画布 288x512
 transform.scale(canvas, 576x1024) → screen.blit → flip()
```

- 单向数据流：**状态机拥有输入与迁移权**；实体只被状态机修改；渲染只读取实体；存档只在 GAMEOVER 写一次。
- 随机性集中在 `difficulty.next_gap_center(prev, gap, rng)`，`rng` 由 `Game` 持有（可注入固定 seed 以便测试与“可复现对局”）。

## 11. Error Handling（失败模式与响应）

| 失败模式 | 检测点 | 响应 | 用户可见结果 |
|---|---|---|---|
| `res/images` 缺失某图 | AssetManager 启动 | 抛 `AssetError`，列出缺失文件 | 控制台红字清单，退出码 2 |
| 图标 `.ico` 加载失败 | 启动 | 忽略，用默认图标 | 无感 |
| 无音频设备 / mixer.init 失败 | AudioManager 启动 | 进入禁用模式 | 无感（无声，照常玩） |
| 单个音效两种格式都缺 | 加载 | 该音效置空 | 该事件无声 |
| 存档损坏 / 非 JSON / 字段非法 | `load()` | 按 0 处理，条件性重写 | 最高分显示 0 |
| 存档目录不可写 | `save_if_better()` | 捕获 OSError，打印警告 | 本次最高分不保留，游戏继续 |
| 窗口创建失败（无显示器） | `set_mode` | 打印提示并 `sys.exit(3)`（测试用 dummy driver） | 明确退出原因 |
| 帧时间异常大（切窗口/断点） | 累加器 | `min(frame_dt, 0.25)` + 最多补 5 步 | 不出现瞬移穿管 |

## 12. Security（安全与信任边界）

本项目为**纯本地单机**，无网络、无用户输入文本、无外部数据解析（仅读自己的 JSON 存档）。风险面与对策：

- **存档解析**：只解析本机自写 JSON，仍需 `json.loads` + 类型/范围校验，避免手工篡改导致 `int(None)` 崩溃或超大分数影响 UI 渲染。
- **路径**：资源路径固定由 `__file__` 推导，不拼接用户输入；存档路径固定为项目内 `save/`，不读环境变量中的可写路径。
- **写入**：仅写 `save/highscore.json`（及其 `.tmp`），不覆盖任何 `res/` 文件。
- **无 secret、无凭据、无第三方网络调用**，故无密钥管理议题。
- **不执行外部命令**，不 `eval`/`exec`，不反序列化 pickle。

## 13. Boundaries and Dependencies

### 13.1 运行时依赖

| 依赖 | 版本 | 说明 |
|---|---|---|
| Python | 3.12.x（本机 3.12.15） | 使用 `tuple[...]` 等 3.9+ 语法 |
| pygame（社区版 pygame-ce 或 pygame） | `>=2.5,<3` | 唯一第三方运行时依赖；提供图形/事件/音频 |
| 标准库 | — | `json`、`pathlib`、`random`、`os`、`sys`、`dataclasses` |
| pytest | `>=8` | 仅开发/测试依赖 |

**安装方式（必须写进 README，规避 externally-managed）**：

```powershell
cd "E:\AI study\homework\FlappyBird"
uv venv .venv
.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
python main.py
```

### 13.2 外部假设

- 目标机为 Windows 10/11，有可用的显示与（可选）音频设备；屏幕**可用高度 ≥ 1024**（1080p 下窗口几乎占满屏高，属预期行为；更小的屏可调小 `config.SCALE = 1`）。
- `res/` 目录结构保持现状；若换素材，只要文件名不变即可零代码改动。
- 系统不安装中文字体不影响运行（HUD 全英文）。

## 14. Testing（测试计划）

统一在 `tests/conftest.py` 设置 `SDL_VIDEODRIVER=dummy`、`SDL_AUDIODRIVER=dummy`，保证 CI/无显示器环境可跑。

| 测试文件 | 覆盖点 | 关键用例 |
|---|---|---|
| `test_difficulty.py` | 纯难度函数 | score 0→level 0/speed 120/gap 110；4→0；5→1；9→1；10→2；30→6；50→仍 6；speed 单调不减且 ≤ 177.6；gap 单调不增且 ≥ 80；`next_gap_center` 落在合法区间且相对上次钳制在 ±120 |
| `test_tuning_invariant.py` | 数值自洽 | `MIN_GAP − HITBOX_H ≥ 1.25 × HOP`；`BASE_GAP > MIN_GAP`；`speed_for(MAX_LEVEL) ≤ 1.6 × BASE_SPEED`（防止调参把游戏改坏） |
| `test_physics.py` | 积分与钳制 | 固定 dt 累积确定性；自由落体速度不超过 `MAX_FALL_SPEED`；起跳后 `vy == FLAP_VELOCITY`；连续起跳不叠加；单跳升高 ≈ `HOP`（误差 < 1px）；1 秒 60 步的位移与解析解误差 < 1px |
| `test_collision.py` | 碰撞与计分 | hitbox 内缩后尺寸 28×18；管道左右/上下边缘相切不判死、重叠 1px 判死；`y+h >= LAND_Y` 判死；`y <= 0` 判死；管道尾端完全越过鸟左沿才计分且只计一次 |
| `test_score_store.py` | 存档健壮性 | 文件不存在→0；损坏 JSON→0 且不抛；`{"best_score": "abc"}`→0；更小分数不覆盖；更大分数原子写成功；目录只读（monkeypatch `open` 抛 `PermissionError`）→ 不抛异常；写后无 `.tmp` 残留 |
| `test_assets.py` | 资源清单 | 清单中每个文件存在且尺寸符合 §7.2（`1.png` 例外为 16 宽）；`__MACOSX` 不被遍历；音效回退逻辑（临时目录只放 `.ogg` 时仍能解析）；缺图时抛 `AssetError` 且报错信息含文件名 |
| 手工验收 | 手感与视觉 | §9.5 六项截图核对；连续游玩 3 分钟无内存增长/无音效叠音爆音；反复暂停≥20 次无状态错乱；连续重开≥20 次分数/昼夜正确归零 |

**Definition of Done**：`pytest -q` 全绿；`python main.py` 从全新 venv 可启动；§9.5 六项验收全部通过；README 步骤在干净环境可复现。

## 15. Rollout（交付与回滚）

- 全新目录交付，无迁移成本；`save/` 与 `.venv/` 加入 `.gitignore`，不随代码提交。
- 调参回滚：所有数值集中在 `src/config.py`，出问题只回退该文件即恢复原手感。
- 若 pygame 安装失败：README 提供备选命令 `uv pip install pygame-ce`（API 兼容，仅包名不同）。
- 不涉及线上发布、灰度或数据迁移。

## 16. Blocking Questions

无。以下默认值已在 §6 中被采纳为需求：`SCALE=2`、每 5 分升一级、`MAX_LEVEL=6`、每 10 分换昼夜与鸟色、`.wav` 优先回退 `.ogg`、最高分 JSON。

## 17. Deferred Questions（实施期可定，含默认假设）

1. **管道颜色主题**：是否让 `pipe-red.png` 在夜晚使用？默认**不用**，统一绿色（保持单变量变化，避免视觉噪声）。
2. **静音状态是否持久化**：默认**不持久化**（重启恢复有声）；若后续想做，扩存档 `{"muted": false}` 即可。
3. **小鸟旋转**：默认**开启**（`ROTATE_SPRITE = True`），若发现像素抖动可关。
4. **BEST 显示位置**：默认 GAMEOVER 面板内（`BEST` + 数字），不常驻游戏画面。
5. **数字精灵间距**：默认 1px，若 `1.png` 视觉过挤可调 `DIGIT_GAP`。
6. **窗口聚焦丢失行为**：已定为 FR-WIN-7 的自动暂停，仅保留 `PAUSE_ON_FOCUS_LOST` 开关的默认值待试玩确认（默认 `True`）。
7. **手感数值微调**：`GRAVITY / FLAP_VELOCITY / BASE_GAP / GAP_STEP / SPEED_STEP` 为经附录 A 解析校验后的初版取值，实施后仍需试玩微调；调参必须满足附录 A.5 的红线并由 `test_tuning_invariant.py` 守护。

---

## 附录 A：难度参数可行性分析（需求冻结前已完成的一次量化验证）

### A.1 为什么需要它

FlappyBird 的"难"应当来自玩家反应与节奏控制，而不是来自**物理上无法通过**的管道。若缝隙小于"一次起跳的固有振幅 + 小鸟高度"，即便玩家操作完美也必然撞管，那属于设计缺陷而非难度。因此难度参数必须先通过解析判定，再交给试玩微调。

### A.2 派生量与判定式（脚本 `scripts/tune_sim.py` 可复现）

| 派生量 | 公式 | 当前取值 |
|---|---|---|
| 单跳升高 `HOP` | `FLAP_VELOCITY² / (2·GRAVITY)` | `(-380)² / (2×1500) = 48.1 px` |
| 缝隙净空 `CLEAR` | `gap − HITBOX_H` | 最窄 `80 − 18 = 62 px` |
| 缝隙内可停留时长 `DWELL` | 从上沿自由下落到下沿：`2·√(2·CLEAR / GRAVITY)` | 最窄缝隙 0.575 s |
| 穿越耗时 `CROSS` | `(PIPE_W + HITBOX_W) / max_speed` | `(52+28) / 177.6 = 0.450 s` |

**判定：`DWELL / CROSS ≥ 1.25`**。1.25 是为人类操作留出的余量系数；低于它意味着必须帧级精确才能通过，属不可接受。

### A.3 对比结论

| 方案 | 缝隙 0→6 级 | 最窄净空 | 最窄 DWELL/CROSS | 判定 |
|---|---|---|---|---|
| 初版草案（`BASE_GAP=100, GAP_STEP=6, MIN_GAP=58`） | 100→64 | 46 px | 0.495 / 0.450 = **1.10** | ❌ 过紧，最高难度近乎不可通过 |
| **定稿（`BASE_GAP=110, GAP_STEP=5, MIN_GAP=80`）** | 110→80 | 62 px | 0.575 / 0.450 = **1.28** | ✅ 采用 |
| 保守方案（`GAP_STEP=4, MIN_GAP=84`） | 110→86 | 68 px | 0.598 / 0.450 = 1.33 | ✅ 但后期变化过弱 |

这条分析**推翻了实施前草案里的 `MIN_GAP=58`**：它会让 level 6 变成"必须一帧不差"的死亡墙，与本作"难度递增但可控"的目标冲突。

### A.4 关于"无头 bot 全自动验证"的诚实记录

`scripts/tune_sim.py` 另含一个不依赖 pygame、可注入随机种子的无头仿真器，用于回归验证参数改动。需明确记录：**本轮尝试的几种简单控制策略（定高、预测下沿、对称滞空）均未能稳定通过**。原因是脚本 bot 的起跳方式与人类差异极大（人类靠"看到下坠再补跳"的视觉闭环反馈，bot 只有固定阈值），**因此不能据此判定参数不可行**。据此确立：

- 参数可行性的**权威判据是 A.2 的解析判定**，由单测 `test_tuning_invariant.py` 固化；
- 手感好坏最终以**人工试玩**为准（§14 手工验收）；
- bot 的长期价值是**确定性回归**（同种子 + 同输入序列必须复现同分数，可增 `test_replay_determinism.py`），而非代替人试玩。

### A.4b v1.1 手感调优（用户反馈驱动）

用户实测反馈："重力下降太快了，连续高低障碍很难飞跃调整下降速度，空格按下后在空中有一段短暂悬空不要立马就掉落。"

量化后确认是真实问题（非主观）：

| 指标 | v1.0 | v1.1 | 说明 |
|---|---|---|---|
| 单跳升高 | 45.0 px | 46.2 px | 基本不变，微操粒度不变 |
| 总滞空 | 0.500 s | **0.667 s** | +33%，给玩家反应时间 |
| 顶点悬停 | **0.000 s** | **0.317 s** | 从无到有，这正是"短暂悬空" |
| 落 60 px 用时 | 0.133 s | **0.167 s** | +26%，下落不再"瞬间栽下去" |
| 终端速度 | 640 px/s | **480 px/s** | −25%，长距离下坠更可控 |

**为什么不用"跳跃后短暂无重力"或"悬停计时器"**：那会做成"按一下飘 0.3 秒"的发木手感，且输入响应不连续。这里保持纯粹的**速度-加速度关系**——顶点附近重力小 → 自然飘一下，一旦开始下落重力迅速恢复 → 保留"重力感"。玩家补跳的响应始终是即时的。


---

## 附录 B：实施状态与审查修复记录（v1.1）

### B.1 交付状态

| 指标 | 值 |
|---|---|
| 生产代码 | 23 文件 / 约 1700 行 |
| 测试 | **184 个用例全绿** |
| 覆盖率 | **89%**（physics/difficulty/hud/background/ground/bird/playing 均 100%） |
| 素材体检 | PASS（27 图 + 5 音效，忽略 `__MACOSX` 39 文件） |
| 手感红线 | PASS（净空 62 ≥ 1.25×hop、DWELL/CROSS = 1.277 ≥ 1.25） |
| 仓库 | https://github.com/YZWQXB/FlappyBird（`main`） |

### B.2 两轮代码审查的修复对照

第一轮（实施计划验收）修复了 11 个缺陷；第二轮（两轴代码审查）修复了以下项，**每项均有对应回归测试**（`tests/test_review_fixes.py`，16 个用例按缺陷编号组织）：

| 编号 | 问题 | 修复方式 | 回归测试 |
|---|---|---|---|
| **S1** | READY→PLAYING 无起跳初速、无 wing 音效，按空格瞬间鸟直接下坠 | `ReadyState.handle_key` 播 wing 后调用 `begin_takeoff()`，把 `bird.flap()` 放在 `enter()` 之后 | `test_S1_*` ×3 |
| **B1** | 存档写盘失败时内存 best 已升级 → 本局显示新纪录、重启回退 | `save_if_better` 改为**写盘成功后才赋值** | `test_B1_*` ×2 |
| **S13** | `rotation_for(0) = 31°`，顶点与待机鸟低头 | 改为分段映射，新增 `ROTATE_VY_LEVEL` 水平区段；`rotation_for(0) = 0°` | `test_S13_*` ×3 |
| **S14** | 主题切换比计分晚一步，跨 10 分时闪「10 分+白天」一帧 | `update` 内**先计分、再推导 stage** | `test_S14_*` |
| **S4** | 缺 `flappy.ico` 抛 AssetError（违反 FR-WIN-3） | 新增 `OPTIONAL_SPECS`，图标改为可选 | `test_S4_*` |
| **S5** | READY 状态翅膀动画冻结 | 抽出 `Bird.update_animation()`，READY 也调用 | `test_S5_*` |
| **S2** | GAMEOVER 未播 swoosh（位置颠倒） | `GameOverState.enter` 播 swoosh；重开时不重复播 | `test_S2_*` |
| **S3** | hit/die 的 200ms 间隔从不生效（各自计时） | 新增 `priority_gap_ok()` 共享时间线 | 手工验证 |
| **S7** | 存档读失败静默返回 0 | 分类打印原因（不存在/损坏/类型非法/超范围） | `test_S7_*` |
| **S8** | `ImageSpec.size` 定义未用 | `_try_load` 校验尺寸并打印警告 | `test_S8_*` |
| **S17** | 字体回退状态不可观测 | `Hud.font_fallback` 暴露状态 | `test_S17_*` |
| **S18** | MUTE 角标居中压地面带，且未静音时显示 SOUND ON | 移到右上角（`MUTE_BADGE_X/Y`），仅静音时显示 | `test_S18_*` |
| **B3** | 管道派生帧每帧重建 | `pipe_cap`/`pipe_body` 加缓存 | 手工验证 |
| **B4** | 缓存键硬编码 `3` | 改用 `len(FLAP_NAMES)` | — |

### B.3 Standards 轴结构性重构

| 编号 | 重构 | 效果 |
|---|---|---|
| #1 | `IMAGE_SPECS` 尺寸改为引用 `config` 常量 | 改窗口/鸟尺寸不再需要同步两处 |
| #2 | 布局魔法数收进 config（`READY_MSG_Y`/`PAUSED_TITLE_Y`/`PAUSED_HINT_Y`/`BEST_LABEL_OFFSET`/`MUTE_BADGE_*`） | 调版式只改一个文件 |
| #3 | `Bird.__init__` 复用 `reset()` | 消除 8 行重复 |
| #4 | 抽出 `State.draw_world()` | 消除三处「背景→管道→鸟→地面」重复 |
| #7 | 新增 `PipePair.geom()` | 不再手工拼几何三元组 |
| #8 | `State.exit()` 在 `set_state` 中真正调用 | 基类契约完整 |
| #10 | `number_width` 收为 `Hud` 方法 | 消除伪自由函数 |
| #12 | 启动器退出码改用 `EXIT_ENV_ERROR=4` | 与 `EXIT_ASSET_ERROR=2` 语义分离 |

### B.4 仍存在的已知限制（不修复，需记录）

| 项 | 原因 | 影响 |
|---|---|---|
| `SysFont` 恒回退 | pygame 2.6.1 + Py3.12 在 Windows 的 `sysfont` 缺陷 | HUD 用内置 freesansbold，非等宽粗体；不影响可读性 |
| 等差管道速度冻结 | 设计取舍（FR-DIFF-1 要求既有管道不变速） | 升级瞬间新旧管道速度不同，视觉上略有差异 |
| `Game.run()` 为阻塞循环 | 便于简单实现 | 主循环本身不可单测，靠 `draw_frame`/`handle_events` 拆分覆盖 |

### B.5 测试清单（184 个）

| 文件 | 用例数 | 守护内容 |
|---|---|---|
| `test_feel.py` | 14 | 非对称重力曲线、顶点滞空、手感下限 |
| `test_physics.py` | 7 | 积分、钳制、旋转映射 |
| `test_collision.py` | 9 | hitbox、三种死亡、计分时机 |
| `test_difficulty.py` | 15 | 阶梯函数、缝隙中心钳制 |
| `test_tuning_invariant.py` | 5 | 调参红线 |
| `test_entities.py` | 15 | 鸟/管道/地面/背景/HUD 渲染 |
| `test_states.py` | 18 | 五态迁移、暂停、重开重置 |
| `test_review_fixes.py` | 16 | **两轴审查的修复回归** |
| `test_regressions.py` | 24 | 第一轮缺陷回归 |
| `test_launcher.py` | 20 | 启动器决策矩阵与执行路径 |
| `test_assets.py`/`test_audio.py`/`test_score_store.py`/`test_config.py`/`test_display.py` | 41 | 资源、音效、存档、配置、倍率 |
