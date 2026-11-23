# FlappyBird 代码审查报告（两轴）

- 日期：2026-11-23
- 审查基线（fixed point）：仓库**首个提交**，无父提交 → 全量代码视为新增
- diff 命令：
  ```bash
  git diff 4b825dc642cb6eb9a060e54bf8d69288fbee4904...HEAD   # 空树 → HEAD
  ```
- 提交列表（1 条）：
  - `239f78e` feat: FlappyBird 完整实现（Python + pygame）
- 变更规模：95 文件 8971 行新增；其中**生产代码 23 文件 1602 行**
- 审查方式：两个子智能体并行（Standards / Spec），主智能体独立复验每条关键发现

---

## Standards（代码规范与坏味道）

> 本仓库**无** CODING_STANDARDS.md / CONTRIBUTING.md / AGENTS.md，README 只描述功能。因此本轴**完全依赖 Fowler smell baseline**，所有条目均为**判断性意见**，非硬性违规。

### (a) 命中的 smell

**1. Shotgun Surgery — 资源清单重复了 config 的尺寸真相**
`src/assets.py:28-42` 硬编码 `(288, 512)`、`(34, 24)`、`(52, 320)`，与 `config.py:16` `LOGICAL_W/H`、`config.py:40` `BIRD_W/H`、`config.py:63` `PIPE_W` 是同一知识的两份抄写。改窗口或鸟尺寸必须同步改 assets，否则启动即 `AssetError`。
→ 修：`ImageSpec` 的期望尺寸直接引用 config 常量。

**2. Shotgun Surgery — 布局魔法数散落状态层，违背「config 是唯一常量源」**
`src/states/paused.py:30-31`（220、256）、`src/game.py:148`（`c.LOGICAL_H - 24`）、`src/states/gameover.py:51`（`c.BEST_PANEL_Y - 26`）、`src/assets.py:112`（行号 200）。调一次版式要跨 4 个文件。
→ 修：Y 坐标收进 config。

**3. Duplicated Code — `Bird.__init__` 与 `Bird.reset` 八行完全一致**
`src/bird.py:17-24` 与 `bird.py:26-33`。加字段时必漏其一。
→ 修：`__init__` 末尾调 `self.reset()`。

**4. Duplicated Code — 三处世界渲染序列**
`states/ready.py:36-41`、`playing.py:86-92`、`dying.py:47-53` 都是「背景→管道→鸟→地面→分数」，其中 dying 与 playing 近乎逐行相同。
→ 修：抽 `render_world(surface, *, pipes, bird)`。

**5. Duplicated Code — 分数校验抄两遍 + 等级钳制抄三遍**
`score_store.py:19-30`（load）与 `34-42`（save）各自实现 bool 排除 + 范围检查（注释已承认「与 load 对称」）；`difficulty.py:11/15/19` 三次 `min(max(x,0), MAX_LEVEL)`。
→ 修：各抽一个判据/钳制函数。

**6. Duplicated Code — 上下管绘制镜像**
`pipe.py:42-47` 与 `50-58` 分支形状完全镜像，仅翻转参数不同；与 `physics.py:72` 的上下矩形构造同构。
→ 修：抽 `_draw_half(facing_up, ...)`。

**7. Data Clumps + Feature Envy — 管道几何三元组反复拆装**
`physics.py:11` 定义 `PipeGeom=(x,center,gap)`，`pipe.py:13-18` 又把同三值拆成字段，`playing.py:77` 再手工拼回 `[(p.x, p.center, p.gap) for p in self.pipes]`。碰撞逻辑比 `PipePair` 更了解几何。
→ 修：加 `PipePair.geom()`。

**8. Speculative Generality — 定义后从未被调用的钩子（已逐一验证）**
- `states/base.py:17` `name` 及 5 个状态类的 `name`：**全局无一处读取**（`state_name` 另存于 Game）
- `states/base.py:24` `exit()`：`set_state` **从不调用**，基类契约实现了一半
- `hud.py:23/36/53` 的 `bold` / `color` / `x_center` 参数：无调用方传非默认值
- `launcher.py:22` `_SMOKE_ENV`：定义后无人使用（`main.py:52` 另抄了同一字面量）
- `score_store.py:9` `_VERSION`：只写不读；`display.py:35` `screen_size` 参数无调用方；`game.py:46/86` `Game.stage` 只写不读
→ 修：删除或补上使用点。

**9. Duplicated Code — `Game.__init__` 重写了 `display.init_window` 的逻辑**
`game.py:25-32` 的 `scale` 分支复制了 `display.py:38-45` 的 set_mode/caption。
→ 修：`init_window(scale=...)` 单一入口。

**10. Middle Man / Feature Envy — `number_width` 是伪自由函数**
`hud.py:9` `number_width(hud, value)` 拿 Hud 当第一参并读 `hud.assets.digit`，本应是 Hud 方法；`draw_number` 还先算总宽再遍历一次，两趟迭代。

**11. Divergent Change — `PlayingState.update` 一个函数六种变化原因**
`playing.py:45-84` 同时负责难度、生成、主题、计分、碰撞、音效归属。
→ 修：拆 `_spawn` / `_advance_theme` / `_score` / `_check_death`。

**12. Primitive Obsession — 启动器裸写退出码**
`launcher.py:107/182` 硬编码 `return 2`，而 `config.py:110` 已有 `EXIT_ASSET_ERROR = 2`。

### (b) Bug / 健壮性

**B1 【已确认，可复现】`score_store` 内存与磁盘不一致**
`score_store.py:43` 的 `self.best = score` 位于写盘 `try` **之前**。写盘触发 `OSError` 时注释称「本次不保留」，但内存已升级。
实测：
```text
初始 best: 0
[score_store] 最高分写入失败（本次不保留）：[WinError 183] ...
返回值: 42
s.best 现在是: 42          ← 内存已变
磁盘是否存在: False        ← 磁盘没写
```
后果：本局结算显示新高分，重启后回退到旧纪录，用户观感是「最高分丢了」。
→ 修：写盘成功后再赋值；失败时保持旧 best。

**B2 【未证实，降级为观察项】保留通道可能被抢占**
`audio.py:78-84` 非保留音效走 `sound.play()`（自动挑通道），理论上可能在 8 通道用尽时抢占 0/1/2 号。
主智能体实测（pygame 2.6.1）：8 通道全占满后连续 20 次 `Sound.play()`，通道 0 的 `get_sound()` **仍是原 die 音效**，未被替换。
→ 结论：**当前 pygame 版本下不成立**，但依赖了未文档化的行为，建议改为显式通道分配以消除隐患。

**B3 `assets.pipe_cap/pipe_body` 每帧重复解码缩放**
`assets.py:103-114` 每次绘制都 `subsurface().copy()` + `transform.scale`，无缓存；而同一模块的鸟旋转帧却做了上限缓存（`assets.py:116-124`）。3 根管道 × 60fps 的稳态分配。
→ 修：按 `(height, facing)` 缓存 body，cap 只做一次。

**B4 旋转缓存键编码脆弱**
`assets.py:117` `key = (palette * 3 + flap, ...)` 的 `3` 是魔法数（应取 `len(FLAP_NAMES)`）。一旦新增 flap 帧，键会与既有 palette 组合静默碰撞 → 画面串帧且不报错。

---

## Spec（是否忠实实现需求）

> Spec：`docs/specs/2026-11-23-flappybird-design.md`（41 条 FR + §9 界面契约 + §11 错误处理 + 附录 A）
> 注：Spec v1.0 的部分参数在 v1.1 被刻意调整（非对称重力），已按文档最新表述判定。

### (a) 缺失 / 只实现一部分

**S1 【P1，可复现】READY→PLAYING 既无起跳初速、也无 wing 音效**
Spec 行 92：「READY → PLAYING｜`SPACE`｜播 `wing`，鸟获得起跳初速」
`playing.py:26-34` 的 `enter()` 只 `bird.reset()`（vy=0），`wing` 仅在 `handle_key` 里播。
实测：
```text
READY->PLAYING 后 bird.vy = 0.0
第 1 帧后 vy = 5.7   ← 第一帧就开始下坠
对比 PLAYING 里按空格：vy = -380.0, 第 1 帧后 -355.0  ← 正常扇翅
起飞后不操作 36 帧（0.60s）后状态 = DYING
```
**这是手感缺陷**：玩家按下空格的瞬间没有向上的反馈，鸟直接掉。

**S2 GAMEOVER 未播 `swoosh`**
Spec 行 166：「`swoosh`…进入 GAMEOVER」。`gameover.py:17-19` `enter()` 未播放；实际在 `handle_key`（重开时）与 `ready.py:21` 播了，等于位置颠倒。

**S3 `hit`/`die` 的 200ms 间隔限制从不生效**
Spec FR-AUDIO-4（行 171）：「`die`/`hit` 走固定通道」+「与 hit 至少间隔 200ms」。
`audio.py:12,74` 只按**音效名各自计时**，而 `dying.py:40-43` 撞地当步即落地——hit 与 die 是两个不同名字，间隔判定互不约束。

**S4 图标被当作致命资源**
Spec FR-WIN-3（行 70）：「图标…失败则用默认图标，不崩溃」。
`assets.py:35,81-85` 把 `icon` 列进必填清单，缺 `flappy.ico` 直接抛 `AssetError` → 退出码 2。

**S5 READY 状态翅膀动画冻结**
Spec 行 203：「小鸟播放 `midflap → upflap` 循环，0.1s/帧」。
`ready.py:26-29` 只调 `float_motion`，全项目仅 `playing.py:50` 调 `bird.update`。

**S6 未调用 `pygame.key.set_repeat(0)`**
Spec FR-INPUT（行 83）明确要求。全库无此调用（依赖默认行为，未按规格声明）。

**S7 存档读失败无警告**
Spec FR-STORE-4（行 186）：「记录一次 `print` 警告」。`score_store.py:18-22` 静默返回 0。

**S8 `ImageSpec.size` 定义了但从未使用**
Spec §7.4（行 297）：「尺寸若与清单不符，启动时打印一次警告」。`assets.py:24` 定义了 `spec.size`，全文未读取。

**S9 GAMEOVER 面板缺少 `SCORE` 文案**
Spec §6.10（行 222）版式画的是 `SCORE  12`，`gameover.py:50` 只画数字。

### (b) 有实现但 Spec 未要求（scope creep）

**S10 窗口倍率自适应与 Spec 直接冲突**
`display.py:6-19,35-42` 按桌面尺寸收缩整数倍率，与 FR-WIN-1（行 68）固定 `SCALE=2`、§9.2（行 432）「禁用…窗口自适应」**直接矛盾**。
→ 评：这是为兼容 1707×1019 桌面做的实用让步，Spec 应更新而非代码回退，但当前是**文档与代码不一致**。

**S11 `launcher.py` 整模块不在 Spec 架构中**
§8.1/§8.2 的文件清单无此模块；`main.py:38` 还复用退出码 2 表示「依赖缺失」，与 FR-ASSET-4 的语义冲突。
→ 评：由用户实际反馈驱动的新增，合理，但 Spec 未同步。

**S12 结算面板的实心底板与额外遮罩**
`gameover.py:30-47` + `config.py:85-93`：实心面板、70 alpha 遮罩、保留管道现场。§6.10 只要求 `gameover.png`+分数+BEST+提示；§9.3 要求「克制」。

### (c) 看起来实现了但方式有问题

**S13 【P2】鸟的旋转角度语义错误**
Spec FR-PHYS-8（行 133）：「精灵视觉旋转（仅 PLAYING/DYING）」，`vy = FLAP_VELOCITY` → `-25°`，`vy >= 400` → `+90°`。
`bird.py:59-62` 无状态判断，且 `rotation_for(0)` 返回 **31°**（而非 0°）。
实测：READY 下 `vy=0` → 绘制 31°，**待机小鸟整体低头 31°**（见 `build/review/ready_with_pitch.png`，肉眼可见）。
后果：待机画面小鸟姿态错误，与原版（水平朝前）不符。

**S14 【P2】主题切换恒定晚 1 步**
Spec FR-THEME-3（行 154）：「跨过 10 分那一刻瞬时生效」。
`playing.py:20-24` 先按旧分算 stage，`28-29` 才计分。实测顺序为 `new_stage`(20) → `try_score`(28) → `score+=`(29)，会渲染出「10 分 + 白天」一帧（16.7ms）。

**S15 管道速度冻结导致与地面不同步**
Spec FR-PHYS-4（行 125）/ FR-DIFF-1（行 145）。`pipe.py:17,21` 把 speed 冻结在生成时刻，升级后新管快、旧管慢；而 `playing.py:63` 地面按**当前**速度滚动，两者不同步。

**S16 管道派生帧无缓存**
Spec FR-ASSET-5（行 237）：「缓存常用旋转/翻转结果，避免每帧 `transform`」。`assets.py:106-114` 每次调用都重建，`pipe.py:43-56` 每帧每管调用。

**S17 `SysFont` 参数类型导致等宽粗体从未生效**
Spec FR-SCORE-4（行 179）要求 `SysFont("consolas,couriernew,monospace", …)`。`hud.py:28` 传 **tuple**，pygame 2.6.1 抛 `TypeError`（本机三种入参均抛），永远落 `Font(None)` 回退。
→ 评：已由 `try/except` 兜住不崩溃，但「等宽粗体」的视觉契约未达成。

**S18 MUTE 角标不在「角落」且会显示 SOUND ON**
Spec FR-INPUT（行 81）：「屏幕角落显示 `MUTE` 提示 1.5s」。`game.py:144-148` 居中于 y=488（压地面带），且未静音时显示 `SOUND ON`（Spec 未要求）。

---

## 汇总

| 轴 | 发现数 | 最严重项 |
|---|---|---|
| **Standards** | 12 个 smell + 4 个 bug（1 确认 / 1 未证实 / 2 性能与脆弱性） | **B1** `score_store` 内存与磁盘不一致：写盘失败仍显示新纪录，重启后「最高分丢失」 |
| **Spec** | 18 项（9 缺失/部分 + 3 scope creep + 6 实现方式问题） | **S1** 起飞无初速无音效：按空格瞬间鸟直接下坠，0.6s 撞地 |

**两轴结论互相独立**：代码结构问题（Standards）不掩盖需求偏差（Spec），反之亦然。

### 建议修复顺序（主智能体补充，非审查结论）

| 优先级 | 项 | 理由 |
|---|---|---|
| P1 | **S1 起飞初速** | 玩家每次开局必遇，手感直接受损 |
| P1 | **B1 存档一致性** | 数据正确性问题，「最高分丢失」体验极差 |
| P2 | **S13 旋转角度** | 待机画面肉眼可见的错误姿态 |
| P2 | **S14 主题晚一步** | 1 帧闪烁，可修 |
| P2 | **S4 图标致命化** | 与 Spec 明确要求相反 |
| P3 | S2/S3/S5/S6/S7/S8/S9 | 音效与提示类，影响面小 |
| P3 | B3 管道帧缓存 | 性能优化，当前无感知问题 |
| 文档 | S10/S11/S12 | Spec 需同步 v1.1 的实际实现，非代码问题 |

### 未采纳的审查意见（主智能体复验后排除）

- **B2 通道抢占**：实测 pygame 2.6.1 下 8 通道占满后连续 20 次 `Sound.play()`，保留通道 0 的 Sound 对象未变，**未复现**。降级为「依赖未文档化行为」的观察项。
- **"GAMEOVER 显示旧纪录"**：主智能体初测误报。在真实死亡路径（`dying.update` → `set_state(GAMEOVER)` → `enter()`）下面板正确显示新纪录 10；仅在人为直接 `set_state` 绕过 `enter()` 时出现，非真实缺陷。

---

## 附：审查过程的可复现命令

```powershell
cd "E:\AI study\homework\FlappyBird"
git log --oneline                              # 239f78e
git show --stat HEAD | Select-Object -Last 1   # 95 files, 8971 insertions
.venv\Scripts\python.exe -m pytest -q          # 168 passed
.venv\Scripts\python.exe -m pytest -q --cov=src  # 88%
```
