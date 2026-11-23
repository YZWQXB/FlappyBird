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
