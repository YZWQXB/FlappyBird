import pytest

from src import config as c
from src.physics import hitbox, is_dead, overlaps, pipe_boxes, should_score


def pipe(x=200.0, center=250.0, gap=None):
    return (x, center, gap if gap is not None else c.BASE_GAP)


def test_touching_edges_is_not_death():
    box = hitbox(100.0, 250.0)                     # (86, 241, 28, 18)
    assert overlaps(box, (box[0] - c.PIPE_W, 0.0, c.PIPE_W, c.LAND_Y)) is False


def test_one_pixel_overlap_is_death():
    box = hitbox(100.0, 250.0)
    assert overlaps(box, (box[0] - c.PIPE_W + 1, 0.0, c.PIPE_W, c.LAND_Y)) is True


def test_pipe_boxes_are_consistent():
    top, bottom = pipe_boxes(pipe(x=200.0, center=250.0, gap=110.0), c.LAND_Y)
    assert top == (200.0, 0.0, c.PIPE_W, 195.0)
    assert bottom[1] == pytest.approx(305.0)
    assert bottom[1] + bottom[3] == pytest.approx(c.LAND_Y)


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
