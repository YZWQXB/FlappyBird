# Phase 2: 纯逻辑核心

**Goal:** 完成三个**不依赖 pygame** 的核心模块：物理与碰撞判定、难度曲线、最高分存档；全部行为由单测固化，并加入调参红线守护。
**Prerequisites:** Phase 1 完成（`config` 可用）。
**Deliverables:** `src/physics.py`、`src/difficulty.py`、`src/score_store.py`、`tests/test_physics.py`、`tests/test_collision.py`、`tests/test_difficulty.py`、`tests/test_tuning_invariant.py`、`tests/test_score_store.py`、`scripts/tune_sim.py`。

**Interface Decisions Implemented:** 无可见界面；本阶段实现 Spec §9.5 中“同一随机种子 + 同一输入序列必复现同一结果”的确定性基础。

---

## Task 1: `physics.py` 积分、钳制与碰撞判定

**Goal:** 用纯函数实现固定步长积分、`vy` 钳制、hitbox 计算、AABB 相交、三种死亡判定、计分时机判定。

**Files:**
- Create: `src/physics.py`
- Test: `tests/test_physics.py`、`tests/test_collision.py`

**Steps:**
- [x] 先写 `tests/test_physics.py`：

```python
import math

import pytest

from src import config as c
from src.physics import clamp_vy, hitbox, integrate


def test_clamp_respects_both_bounds():
    assert clamp_vy(-9999) == c.FLAP_VELOCITY
    assert clamp_vy(9999) == c.MAX_FALL_SPEED
    assert clamp_vy(0.0) == 0.0


def test_flap_sets_exact_velocity():
    vy, y = integrate(c.FLAP_VELOCITY, 256.0, c.FIXED_DT)
    assert vy > c.FLAP_VELOCITY            # 下一步就开始被重力拉回
    assert vy < c.FLAP_VELOCITY + c.GRAVITY * c.FIXED_DT + 1e-9
    assert y < 256.0


def test_free_fall_is_deterministic():
    vy, y = 0.0, 0.0
    for _ in range(600):                              # 10 秒
        vy, y = integrate(vy, y, c.FIXED_DT)
    assert vy == pytest.approx(c.MAX_FALL_SPEED)      # 早已触顶并被钳制
    assert y > 0


def test_hop_matches_config_formula():
    """单跳升高用离散积分实测，与解析 HOP 的偏差固定在 ~3.5px。

    半隐式欧拉（先加速后位移）在第 1 步就损失 |FLAP|*dt/2 ≈ 3.17px，
    实测值为 44.67（解析 48.13）。此处用「只允许偏低、不允许偏高」的单侧
    断言锁住该行为：若有人把积分顺序改成先位移后加速，rise 会变高而被抓到。
    """
    vy, y = c.FLAP_VELOCITY, 0.0
    start = y
    steps = 0
    while vy < 0:
        vy, y = integrate(vy, y, c.FIXED_DT)
        steps += 1
    rise = start - y
    assert 16 <= steps <= 17              # 滞空上升段 16 步 ≈ 0.27s
    assert c.HOP - 4.5 < rise <= c.HOP    # 44.67 落在 (43.63, 48.13]
    assert rise == pytest.approx(44.667, abs=0.01)


def test_repeated_flap_does_not_accumulate():
    vy = c.FLAP_VELOCITY
    for _ in range(30):
        vy = c.FLAP_VELOCITY          # 模拟连续按空格：每次都直接赋值
        vy, _ = integrate(vy, 100.0, c.FIXED_DT)
    assert vy >= c.FLAP_VELOCITY


def test_hitbox_is_centered_and_inset():
    x, y, w, h = hitbox(100.0, 200.0)
    assert (w, h) == (c.HITBOX_W, c.HITBOX_H)
    assert x == pytest.approx(100.0 - c.HITBOX_W / 2)
    assert y == pytest.approx(200.0 - c.HITBOX_H / 2)
```

- [x] 先写 `tests/test_collision.py`：

```python
import pytest

from src import config as c
from src.physics import hitbox, is_dead, overlaps, should_score


def pipe(x=200.0, center=250.0, gap=None):
    return (x, center, gap if gap is not None else c.BASE_GAP)


def test_touching_edges_is_not_death():
    box = hitbox(100.0, 250.0)                     # (86, 241, 28, 18)
    # 管道右沿正好等于鸟左沿 => 相切，不算碰撞
    assert overlaps(box, (box[0] - c.PIPE_W, 0.0, c.PIPE_W, c.LAND_Y)) is False


def test_one_pixel_overlap_is_death():
    box = hitbox(100.0, 250.0)
    assert overlaps(box, (box[0] - c.PIPE_W + 1, 0.0, c.PIPE_W, c.LAND_Y)) is True


def test_pipe_gap_pass_through_is_safe():
    box = hitbox(150.0, 250.0)
    assert is_dead(box, [pipe(x=140.0, center=250.0)], c.LAND_Y) is False


def test_hitting_pipe_body_is_death():
    box = hitbox(150.0, 100.0)                     # 远高于缝隙
    assert is_dead(box, [pipe(x=140.0, center=250.0)], c.LAND_Y) is True


def test_landing_is_death():
    box = hitbox(100.0, c.LAND_Y)                  # 中心已在地面高度
    assert is_dead(box, [], c.LAND_Y) is True


def test_ceiling_is_death():
    box = hitbox(100.0, 5.0)
    assert is_dead(box, [], c.LAND_Y) is True


def test_score_only_after_pipe_tail_crosses_bird_left():
    left = 86.0                                     # 鸟左沿（hitbox 左边界）
    assert should_score(33.0, left) is True         # 33+52=85 < 86 => 已完全越过
    assert should_score(34.0, left) is True         # 34+52=86 == 86 => 相切即计分
    assert should_score(35.0, left) is False        # 35+52=87 > 86 => 还没完全越过
    assert should_score(150.0, left) is False
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_physics.py tests/test_collision.py -q`
  - Expected: FAIL（`ModuleNotFoundError: src.physics`）。

- [x] 写 `src/physics.py`：

```python
"""纯物理与碰撞判定：不 import pygame，全部输入输出为普通数值/元组。"""

from __future__ import annotations

from typing import Iterable, Sequence

from . import config as c

Box = tuple[float, float, float, float]   # x, y, w, h
PipeGeom = tuple[float, float, float]     # x, gap_center, gap_height


def clamp_vy(vy: float) -> float:
    return max(c.FLAP_VELOCITY, min(c.MAX_FALL_SPEED, vy))


def integrate(vy: float, y: float, dt: float) -> tuple[float, float]:
    """一步欧拉积分：先加速再位移，返回 (vy, y)。"""
    vy = clamp_vy(vy + c.GRAVITY * dt)
    return vy, y + vy * dt


def hitbox(x: float, y: float) -> Box:
    """鸟中心 (x, y) → 内缩后的 AABB；先 round 再交给 Rect，避免浮点截断漂移。"""
    half_w = c.HITBOX_W / 2
    half_h = c.HITBOX_H / 2
    return (
        round(x - half_w),
        round(y - half_h),
        c.HITBOX_W,
        c.HITBOX_H,
    )


def overlaps(a: Box, b: Box) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def pipe_boxes(pipe: PipeGeom, land_y: float) -> tuple[Box, Box]:
    """上管矩形与下管矩形（缝隙以外全部是实体）。"""
    x, center, gap = pipe
    top = center - gap / 2
    bottom = center + gap / 2
    return (x, 0.0, c.PIPE_W, max(0.0, top)), (x, bottom, c.PIPE_W, max(0.0, land_y - bottom))


def is_dead(box: Box, pipes: Sequence[PipeGeom], land_y: float) -> bool:
    x, y, w, h = box
    if y + h >= land_y:        # 撞地面
        return True
    if y <= 0:                 # 越过屏幕上边界
        return True
    for pipe in pipes:
        if overlaps(box, pipe_boxes(pipe, land_y)[0]) or overlaps(box, pipe_boxes(pipe, land_y)[1]):
            return True
    return False


def should_score(pipe_x: float, bird_left: float) -> bool:
    """管道尾端完全越过鸟左沿的那一步计分。"""
    return pipe_x + c.PIPE_W <= bird_left


def rotation_for(vy: float) -> float:
    """vy → 精灵视觉角度（仅绘制用，不影响 hitbox）。"""
    if vy <= c.FLAP_VELOCITY:
        return c.ROTATE_MIN_DEG
    if vy >= c.ROTATE_VY_FULL:
        return c.ROTATE_MAX_DEG
    span = c.ROTATE_VY_FULL - c.FLAP_VELOCITY
    t = (vy - c.FLAP_VELOCITY) / span
    return c.ROTATE_MIN_DEG + (c.ROTATE_MAX_DEG - c.ROTATE_MIN_DEG) * t
```

> 注意 1：`should_score` 的签名是 `(pipe_x, bird_left)`（**不含 pipe_w 参数**，宽度取自 config），与上面测试一致；Spec §8.3 里写作三参数是示意，以实现为准。
>
> 注意 2（已实测）：离散积分单跳实际升高 **44.67 px**，低于解析值 48.13 px（半隐式欧拉的固有偏差 ≈ 3.2 px）。`test_tuning_invariant` 继续用**解析 HOP** 做判据——因为解析值更大，算出的净空需求更严，属于**偏保守的安全侧**，这是有意的选择，不要"优化"成离散值。

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_physics.py tests/test_collision.py -q`
  - Expected: `13 passed`（physics 6 + collision 7）。

**Security/Boundary Notes:** 本模块不 import pygame、不读写文件，任何输入都不会抛异常（含 `inf`/`nan` 由 `clamp_vy` 兜底为边界值）。

**Dependencies:** Phase 1 Task 2（`config`）。

---

## Task 2: `difficulty.py` 阶梯难度与缝隙中心

**Goal:** 用纯函数表达难度曲线，并保证相邻缝隙中心的落差受钳制、中心始终落在合法区间。

**Files:**
- Create: `src/difficulty.py`
- Test: `tests/test_difficulty.py`

**Steps:**
- [x] 先写 `tests/test_difficulty.py`：

```python
import random

import pytest

from src import config as c
from src.difficulty import gap_for, level_for, next_gap_center, speed_for


@pytest.mark.parametrize(
    "score,expected",
    [(0, 0), (4, 0), (5, 1), (9, 1), (10, 2), (29, 5), (30, 6), (31, 6), (999, 6)],
)
def test_level_for(score, expected):
    assert level_for(score) == expected


def test_speed_is_monotonic_and_capped():
    speeds = [speed_for(lv) for lv in range(c.MAX_LEVEL + 1)]
    assert speeds == sorted(speeds)
    assert speeds[0] == pytest.approx(120.0)
    assert speeds[-1] == pytest.approx(120.0 * (1 + 0.08 * 6))
    assert speed_for(99) == speed_for(c.MAX_LEVEL)


def test_gap_is_monotonic_and_capped():
    gaps = [gap_for(lv) for lv in range(c.MAX_LEVEL + 1)]
    assert gaps == sorted(gaps, reverse=True)
    assert gaps[0] == c.BASE_GAP
    assert gaps[-1] == c.MIN_GAP
    assert gap_for(99) == c.MIN_GAP


def test_center_within_legal_band():
    rng = random.Random(0)
    prev = 250.0
    for _ in range(500):
        gap = gap_for(level_for(rng.randrange(0, 60)))
        center = next_gap_center(prev, gap, rng)
        assert c.PIPE_MARGIN + gap / 2 <= center <= c.LAND_Y - c.PIPE_MARGIN - gap / 2 + 1e-9
        assert abs(center - prev) <= c.MAX_CENTER_DELTA + c.PIPE_MARGIN * 2
        prev = center


def test_center_delta_is_smooth_when_prev_is_extreme():
    rng = random.Random(1)
    for prev in (60.0, 250.0, 340.0):
        center = next_gap_center(prev, c.MIN_GAP, rng)
        assert abs(center - prev) <= c.MAX_CENTER_DELTA
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_difficulty.py -q`
  - Expected: FAIL（模块不存在）。

- [x] 写 `src/difficulty.py`：

```python
"""难度曲线：全部为纯函数，rng 可注入以便复现。"""

from __future__ import annotations

import random

from . import config as c


def level_for(score: int) -> int:
    return min(max(score, 0) // c.LEVEL_EVERY, c.MAX_LEVEL)


def speed_for(level: int) -> float:
    return c.BASE_SPEED * (1.0 + c.SPEED_STEP * min(max(level, 0), c.MAX_LEVEL))


def gap_for(level: int) -> int:
    level = min(max(level, 0), c.MAX_LEVEL)
    return max(c.BASE_GAP - c.GAP_STEP * level, c.MIN_GAP)


def gap_band(gap: float) -> tuple[float, float]:
    """缝隙中心的合法取值区间。"""
    lo = c.PIPE_MARGIN + gap / 2
    hi = c.LAND_Y - c.PIPE_MARGIN - gap / 2
    return lo, max(lo, hi)


def next_gap_center(prev_center: float, gap: float, rng: random.Random) -> float:
    lo, hi = gap_band(gap)
    target = rng.uniform(lo, hi)
    # 先按最大落差钳制，再夹回合法区间（保证两个约束同时满足）
    delta = max(-c.MAX_CENTER_DELTA, min(c.MAX_CENTER_DELTA, target - prev_center))
    return max(lo, min(hi, prev_center + delta))
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_difficulty.py -q`
  - Expected: `13 passed`（4 个普通用例 + `test_level_for` 的 9 个参数化用例）。

**Security/Boundary Notes:** 负分/超大分由 `level_for` 钳制，不会产生负数等级或 IndexError。

**Dependencies:** Phase 1 Task 2。

---

## Task 3: `score_store.py` 最高分原子读写 + 调参红线 + `tune_sim.py`

**Goal:** 存档在损坏、只读目录、半写文件下都不崩溃；并用单测把 Spec 附录 A.5 的调参红线固化，同时提供可复现附录 A 结论的脚本。

**Files:**
- Create: `src/score_store.py`、`scripts/tune_sim.py`
- Test: `tests/test_score_store.py`、`tests/test_tuning_invariant.py`

**Steps:**
- [x] 先写 `tests/test_tuning_invariant.py`（**这是防“把游戏改坏”的守门测试**）：

```python
import pytest

from src import config as c
from src.difficulty import gap_for, level_for, speed_for


def test_min_gap_leaves_enough_clearance():
    clear = c.MIN_GAP - c.HITBOX_H
    assert clear >= 1.25 * c.HOP, f"最窄净空 {clear} < 1.25×hop({1.25 * c.HOP})"


def test_dwell_beats_crossing_time():
    import math

    clear = c.MIN_GAP - c.HITBOX_H
    dwell = 2 * math.sqrt(2 * clear / c.GRAVITY)
    cross = (c.PIPE_W + c.HITBOX_W) / speed_for(c.MAX_LEVEL)
    assert dwell / cross >= 1.25, f"DWELL/CROSS={dwell / cross:.2f} < 1.25"


def test_gap_ordering():
    assert c.BASE_GAP > c.MIN_GAP
    assert gap_for(0) > gap_for(c.MAX_LEVEL)


def test_speed_is_not_absurdly_fast():
    assert speed_for(c.MAX_LEVEL) <= 1.6 * c.BASE_SPEED


def test_level_progression_reaches_cap():
    assert level_for(c.LEVEL_EVERY * c.MAX_LEVEL) == c.MAX_LEVEL
```

- [x] 先写 `tests/test_score_store.py`：

```python
import json

import pytest

from src.score_store import HighScoreStore


def test_missing_file_is_zero(tmp_path):
    store = HighScoreStore(tmp_path / "highscore.json")
    assert store.load() == 0


def test_corrupt_json_is_zero_and_not_raised(tmp_path):
    path = tmp_path / "highscore.json"
    path.write_text("{not json", encoding="utf-8")
    assert HighScoreStore(path).load() == 0


def test_invalid_field_type_is_zero(tmp_path):
    path = tmp_path / "highscore.json"
    path.write_text(json.dumps({"version": 1, "best_score": "abc"}), encoding="utf-8")
    assert HighScoreStore(path).load() == 0


def test_negative_or_huge_value_is_zero(tmp_path):
    path = tmp_path / "highscore.json"
    for bad in (-1, 10**9, None, True):
        path.write_text(json.dumps({"best_score": bad}), encoding="utf-8")
        assert HighScoreStore(path).load() == 0, bad


def test_saves_only_when_better(tmp_path):
    path = tmp_path / "highscore.json"
    store = HighScoreStore(path)
    assert store.save_if_better(5) == 5
    assert json.loads(path.read_text(encoding="utf-8"))["best_score"] == 5
    assert store.save_if_better(3) == 5
    assert json.loads(path.read_text(encoding="utf-8"))["best_score"] == 5


def test_atomic_write_leaves_no_tmp(tmp_path):
    path = tmp_path / "highscore.json"
    HighScoreStore(path).save_if_better(9)
    assert path.is_file()
    assert not (tmp_path / "highscore.json.tmp").exists()


def test_unwritable_dir_does_not_raise(tmp_path, monkeypatch):
    path = tmp_path / "highscore.json"

    def boom(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr("builtins.open", boom)
    store = HighScoreStore(path)
    assert store.save_if_better(7) == 7      # 内存值仍返回，不抛异常
```

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_tuning_invariant.py tests/test_score_store.py -q`
  - Expected: FAIL（模块不存在）。

- [x] 写 `src/score_store.py`：

```python
"""最高分持久化：原子写、损坏容错、只读目录容错。"""

from __future__ import annotations

import json
import os
from pathlib import Path

_VERSION = 1
_MAX_REASONABLE = 10**6


class HighScoreStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.best = self.load()

    def load(self) -> int:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return 0
        if not isinstance(raw, dict):
            return 0
        value = raw.get("best_score")
        if isinstance(value, bool) or not isinstance(value, int):
            return 0
        if not 0 <= value < _MAX_REASONABLE:
            return 0
        return value

    def save_if_better(self, score: int) -> int:
        if score <= self.best:
            return self.best
        self.best = score
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"version": _VERSION, "best_score": score}, fh)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        except OSError as exc:
            print(f"[score_store] 最高分写入失败（本次不保留）：{exc}")
        return self.best
```

- [x] 写 `scripts/tune_sim.py`：输出 Spec 附录 A 的派生量与判定表（`HOP`/`CLEAR`/`DWELL`/`CROSS`/比值），逐行打印 `PASS`/`FAIL` 并以 0/1 退出；另提供 `--bot` 参数跑无头仿真（同种子同结果），复现附录 A.4 的说明。

- [x] Run: `.venv\Scripts\python.exe -m pytest tests/test_tuning_invariant.py tests/test_score_store.py -q`
  - Expected: `12 passed`。

- [x] Run: `.venv\Scripts\python.exe scripts/tune_sim.py`
  - Expected: 打印 `HOP=48.1 CLEAR=62 DWELL=0.575 CROSS=0.450 RATIO=1.28 PASS`，退出码 0。

**Security/Boundary Notes:** 只写 `save/highscore.json` 与其 `.tmp`；`best_score` 必须是非 bool 的 int 且 `0 <= v < 10^6`，防止手改文件导致渲染死循环；`fsync` + `os.replace` 保证不出现半文件。

**Dependencies:** Task 2（`tune_sim` 用到 `difficulty`）、Phase 1 Task 2。

---

## Phase Completion Checklist

- [x] Task 1–3 全部完成
- [x] `.venv\Scripts\python.exe -m pytest tests/test_physics.py tests/test_collision.py tests/test_difficulty.py tests/test_tuning_invariant.py tests/test_score_store.py -q` 全绿（**38** 用例 = physics 6 + collision 7 + difficulty 13 + tuning 5 + score 7）
- [x] `scripts/tune_sim.py` 输出 PASS
- [x] 全模块不 import pygame（除测试）：`Select-String -Path src/physics.py,src/difficulty.py,src/score_store.py -Pattern 'import pygame'` 无结果
- [x] Ready for Phase 3