import pytest

from src import config as c
from src.display import fit_scale


def test_prefers_configured_scale_when_it_fits():
    assert fit_scale(1920, 1080, preferred=2) == 2


def test_falls_back_to_one_when_two_does_not_fit():
    # 本机真实情况：可用区 1707x1019，1024 高放不下
    assert fit_scale(1707, 1019, preferred=2) == 1


def test_never_returns_zero_on_tiny_screens():
    assert fit_scale(200, 300, preferred=2) == 1


def test_respects_force_scale_override():
    assert fit_scale(1707, 1019, preferred=2, force=3) == 3


def test_uses_largest_integer_that_fits():
    # 可用区刚好放下 3 倍（高度需 3*512 + 标题栏预留 48）
    avail = (288 * 3, 512 * 3 + 48)
    assert fit_scale(*avail, preferred=3) == 3
    # preferred 是上限：不放开时不得越界
    assert fit_scale(*avail, preferred=2) == 2


def test_ignores_titlebar_reserve_when_abundant():
    assert fit_scale(4000, 4000, preferred=2) == 2
