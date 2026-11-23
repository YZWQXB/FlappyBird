import json

import pytest

from src.score_store import HighScoreStore


def test_missing_file_is_zero(tmp_path):
    store = HighScoreStore(tmp_path / "highscore.json")
    assert store.load() == 0
    assert store.best == 0


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


def test_non_dict_json_is_zero(tmp_path):
    path = tmp_path / "highscore.json"
    path.write_text("[1,2,3]", encoding="utf-8")
    assert HighScoreStore(path).load() == 0


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


def test_creates_missing_parent_dir(tmp_path):
    path = tmp_path / "nested" / "dir" / "highscore.json"
    HighScoreStore(path).save_if_better(4)
    assert path.is_file()


def test_unwritable_dir_does_not_raise(tmp_path, monkeypatch):
    path = tmp_path / "highscore.json"

    def boom(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr("builtins.open", boom)
    store = HighScoreStore(path)
    assert store.save_if_better(7) == 7      # 内存值仍返回，不抛异常
