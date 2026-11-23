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
        # 文件不存在是正常首次运行，不告警
        if not self.path.exists():
            return 0
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"[score_store] 存档读取失败，按 0 处理：{exc}")
            return 0
        if not isinstance(raw, dict):
            print("[score_store] 存档格式非法（非对象），按 0 处理")
            return 0
        value = raw.get("best_score")
        if isinstance(value, bool) or not isinstance(value, int):
            print("[score_store] 存档 best_score 类型非法，按 0 处理")
            return 0
        if not 0 <= value < _MAX_REASONABLE:
            print("[score_store] 存档 best_score 超出合理范围，按 0 处理")
            return 0
        return value

    def save_if_better(self, score: int) -> int:
        try:
            score = int(score)
        except (TypeError, ValueError):
            return self.best
        # 与 load() 对称：超出可接受范围的分数一律拒绝，
        # 否则会写入一个读不回来的值，下次启动表现为"最高分丢失"
        if not 0 <= score < _MAX_REASONABLE:
            return self.best
        if score <= self.best:
            return self.best
        # 先写盘、成功后才升级内存。否则写盘失败时本局会显示"新纪录"，
        # 重启后又回退，用户观感是"最高分丢了"。
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
        self.best = score
        return self.best
