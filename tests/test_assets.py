from pathlib import Path

import pytest

from src import config as c
from src.assets import IMAGE_SPECS, AssetError, AssetManager, resolve_sound_path


def test_every_spec_exists_and_matches_size():
    import pygame

    for spec in IMAGE_SPECS:
        path = c.IMAGES_DIR / spec.relative
        assert path.is_file(), f"缺少素材 {path}"
        if spec.size:
            surf = pygame.image.load(str(path))
            assert surf.get_size() == spec.size, f"{spec.key} 尺寸不符"


def test_macosx_is_never_referenced():
    for spec in IMAGE_SPECS:
        assert "__MACOSX" not in spec.relative


def test_sound_prefers_wav(tmp_path):
    (tmp_path / "wing.wav").write_bytes(b"")
    (tmp_path / "wing.ogg").write_bytes(b"")
    assert resolve_sound_path(tmp_path, "wing").name == "wing.wav"


def test_sound_falls_back_to_ogg(tmp_path):
    (tmp_path / "wing.ogg").write_bytes(b"")
    assert resolve_sound_path(tmp_path, "wing").name == "wing.ogg"


def test_sound_missing_returns_none(tmp_path):
    assert resolve_sound_path(tmp_path, "wing") is None


def test_manager_loads_all_images(assets):
    assert "bg_day" in assets.images and "bg_night" in assets.images
    assert assets.digit(0).get_height() == 36
    assert assets.digit(1).get_width() == 16
    assert assets.pipe_cap(True).get_size() == (52, 25)
    assert assets.pipe_body(100, True).get_size() == (48, 100)
    for palette in range(3):
        for flap in range(3):
            assert assets.bird_frame(palette, flap).get_size() == (34, 24)


def test_rotated_bird_is_cached(assets):
    a = assets.rotated_bird(0, 1, 30.0)
    b = assets.rotated_bird(0, 1, 30.0)
    assert a is b                      # 同角度命中缓存，不重复 transform


def test_missing_image_raises_with_filename(tmp_path):
    broken = tmp_path / "res"
    (broken / "images").mkdir(parents=True)
    (broken / "audios").mkdir(parents=True)
    with pytest.raises(AssetError) as ei:
        AssetManager(broken)
    assert "background-day.png" in str(ei.value)
