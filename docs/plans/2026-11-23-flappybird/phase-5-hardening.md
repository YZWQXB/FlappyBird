# Phase 5: 打磨与验收

**Goal:** 补齐文档与启动脚本，逐项完成 Spec §9.5 的六项视觉验收，跑通全量测试并做最后的手感/性能收尾。
**Prerequisites:** Phase 1–4 完成（游戏可玩、六张截图已产出）。
**Deliverables:** `README.md`、`start.bat`、视觉验收记录（`docs/plans/2026-11-23-flappybird/acceptance.md`）、全量测试通过。

**Interface Decisions Implemented:** Spec §9.5 全部视觉验收项；Spec §9.3 视觉系统的最终一致性复核（无渐变/无圆角/描边对比度）。

---

## Task 1: README 与 start.bat

**Goal:** 让另一个工程师/老师在干净环境按文档即可复现运行，并能自行调参。

**Files:**
- Create: `README.md`、`start.bat`

**Steps:**
- [x] 写 `README.md`，必须包含以下小节（内容按本计划与 Spec 的实际结论填写，不得写"待补充"）：

```text
# FlappyBird（Python / pygame）

## 环境要求
Python 3.12 / Windows 10-11 / 可选音频设备

## 安装（首次）
uv venv .venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r requirements.txt

## 运行
.venv\Scripts\python.exe main.py
（或双击 start.bat）

## 操作
SPACE 起飞/扇翅/重开 | P 暂停 | M 静音 | R 重开 | ESC 退出

## 玩法规则
+1 分/管道；撞管道/地面/顶部即死；每 5 分提速 +8%、缝隙 -5px（上限 6 级）；
每 10 分切换昼夜并循环 黄→蓝→红 鸟色

## 调参
全部参数在 src/config.py。改 GRAVITY/FLAP_VELOCITY/MIN_GAP 后必须跑
.venv\Scripts\python.exe scripts/tune_sim.py 确认 PASS，
以及 .venv\Scripts\python.exe -m pytest tests/test_tuning_invariant.py

## 目录说明
main.py / src/ / tests/ / scripts/ / res/ / save/ / docs/

## 测试
.venv\Scripts\python.exe -m pytest -q

## 排障
- 窗口大小：默认按桌面可用区取最大整数倍；可用 config.FORCE_SCALE 强制
- 无声音：静音降级属正常，控制台会打印 [audio] 原因
- SysFont 报错：已内置回退，属已知 pygame 2.6.1 缺陷
- 最高分不保存：检查 save/ 是否可写（不可写时游戏仍可玩）
- 素材缺失：scripts/check_assets.py 会列出具体文件名
```

- [x] 写 `start.bat`（双击启动；缺 venv 自动创建并安装）：

```bat
@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [setup] 首次运行，正在创建虚拟环境...
  uv venv .venv --python 3.12 || goto :err
  uv pip install --python .venv\Scripts\python.exe -r requirements.txt || goto :err
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto :err
exit /b 0
:err
echo.
echo 启动失败（见上方信息），或按 README 的“排障”一节处理。
pause
exit /b 1
```

- [x] Run: `cmd /c start.bat`（在可交互环境下）或 `.venv\Scripts\python.exe main.py`
  - Expected: 一次成功启动；若删掉 `.venv` 再跑 `start.bat`，应看到 setup 提示并成功装好依赖。

**Security/Boundary Notes:** `start.bat` 只在项目目录内操作，不修改系统 PATH、不写注册表。

---

## Task 2: 六项视觉验收

**Goal:** 用 `scripts/smoke_run.py` 产出的截图逐项核对 Spec §9.5，形成可追溯的验收记录。

**Files:**
- Create: `docs/plans/2026-11-23-flappybird/acceptance.md`
- Read: `build/screens/*.png`

**Steps:**
- [x] Run: `.venv\Scripts\python.exe scripts/smoke_run.py --frames 900`
  - Expected: 6 张 PNG 生成，尺寸等于"逻辑画布 × `fit_scale` 结果"（本机 288×512，1080p+ 机器 576×1024）。脚本内部用 `pygame.transform.scale` 复现真实的窗口合成路径，因此截图即用户所见。

- [x] 逐张打开核对下表，并在 `acceptance.md` 中记录结论（通过/问题+截图路径）：

| # | 验收项（Spec §9.5） | 对应截图 | 通过判据 |
|---|---|---|---|
| 1 | 启动 READY：提示图 + 浮动鸟 + 白天背景 | `01_ready.png` | message.png 居中显示于上方；小鸟位于屏幕中部偏下且不完全遮挡提示图；背景为 `#4EC0CA` 白天色 |
| 2 | 第 10 分瞬间换成夜晚 + 蓝鸟 | `04_night_blue.png` | 背景为 `#008793` 夜晚色；小鸟为蓝色系；两者同帧生效；分数用数字精灵显示且值为 10 |
| 3 | PAUSED 遮罩 | `03_paused.png` | 画面整体压暗（alpha≈120）；居中显示 `PAUSED`；下方显示 `PRESS P TO RESUME`；文字有描边且清晰 |
| 4 | GAMEOVER 面板 | `06_gameover.png` | `gameover.png` 标题居中于 y≈140；本次分数与 BEST 两行均可读且位置在 y≈220/280；底部 `PRESS SPACE TO RESTART` 完整不越界 |
| 5 | 整数倍缩放无拉伸变形、无像素缝隙 | 全部截图 | `smoke_run` 按**窗口实际尺寸**出图（本机 `fit_scale` 结果为 1× → 288×512；若在 1080p 以上机器为 2× → 576×1024）；图像边缘锐利、无模糊插值；地面与背景交界处无 1px 透明缝；管道 cap 与 body 拼接处无错位 |
| 6 | 地面滚动时接缝无抖动 | `02_playing.png` 与连拍 | 连续两帧地面纹理间距恒定；无每帧 1px 跳动（代码层由 `Ground.offset` 整像素量化保证） |

- [x] 若任一项不通过 → 回到对应 Phase 修复后重跑本任务（不跳过、不"先记着"）。

- [x] **视觉收尾复核（Critique Pass）**：检查所有截图的层次与留白——分数不被管道遮挡、GAMEOVER 两行数字不重叠提示语、暂停文字不在屏幕边缘被裁切；发现问题即修并重跑。

**Visual Verification:** 上表 6 项 + 收尾复核，全部需在 `acceptance.md` 留下"通过"+ 截图文件名。

---

## Task 3: 全量测试、性能与手感收尾

**Goal:** 确认整套交付在测试、性能、稳定性三个维度达标，并把遗留的可调项记录清楚。

**Files:**
- Modify: `docs/plans/2026-11-23-flappybird/flappybird.md`（更新状态）
- Test: 全部

**Steps:**
- [x] Run: `.venv\Scripts\python.exe -m pytest -q`
  - Expected: 全绿；用例总数 **90**（Phase 1: 17、Phase 2: 38、Phase 3: 15、Phase 4: 20）；允许只多不少，少于 90 说明有测试没实现。无导致 error 的 warning。

- [x] Run: `.venv\Scripts\python.exe -m pytest -q --collect-only | Select-String "test" | Measure-Object`
  - Expected: 用例数与预期量级吻合（允许 ±10% 偏差，超出说明有测试未实现）。

- [x] Run: `.venv\Scripts\python.exe scripts/check_assets.py`
  - Expected: `PASS`，退出码 0。

- [x] Run: `.venv\Scripts\python.exe scripts/tune_sim.py`
  - Expected: `PASS`，退出码 0；比值与 Spec 附录 A 一致（1.28）。

- [x] 性能检查（人工，3 分钟连续游玩）：
  - 观察任务管理器内存是否稳定（旋转帧缓存上限 160，不应持续增长）；
  - 连按空格 50 次不出现音效叠音爆音（`hit`/`die` 走固定通道并先 stop）；
  - 反复 P 暂停/恢复 ≥ 20 次无状态错乱、无累加器爆炸（恢复后不应瞬移）；
  - 连续重开 ≥ 20 次后分数/昼夜/鸟色均归零。

- [x] 手感检查（人工，试玩 5 局）：
  - 记录主观难度：level 0 应"容易上手"，level 6 应"紧张但可通过"；
  - 若 level 6 明显不可通过，按 Spec 附录 A.5 调 `GAP_STEP`/`MIN_GAP` 后重跑 `tune_sim.py` + `test_tuning_invariant.py`；
  - 把最终取值写回 `docs/specs/2026-11-23-flappybird-design.md` 的 Deferred 第 7 条（追加"实测结论"），不改动已冻结的其他需求。

- [x] 更新计划状态：将 `flappybird.md` 与本阶段所有 Phase 的 **Status** 改为 `Done`，勾选各 Phase Completion Checklist。

**Security/Boundary Notes:** 收尾时确认全项目无网络调用、无 `eval/exec`、无 pickle 反序列化；`save/` 是唯一写入目录。

---

## Phase Completion Checklist

- [x] Task 1–3 全部完成
- [x] `README.md` 的安装步骤在**删除 `.venv` 后**重新执行可复现
- [x] 六项视觉验收全部通过并记录在 `acceptance.md`
- [x] `pytest -q` 90 用例全绿
- [x] 3 分钟连续游玩无内存增长、无叠音、无状态错乱
- [x] 计划状态全部同步为 Done
- [x] **交付完成**