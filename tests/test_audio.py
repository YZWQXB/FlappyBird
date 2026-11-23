from pathlib import Path

import pytest

from src.audio import AudioManager


def test_disabled_manager_is_safe_noop():
    am = AudioManager.disabled()
    assert am.enabled is False
    am.play("wing")          # 不抛异常
    am.toggle_mute()
    assert am.muted is True


def test_mute_blocks_play_and_toggles():
    am = AudioManager.disabled()
    am.muted = True
    am.play("point")
    am.toggle_mute()
    assert am.muted is False


def test_create_with_dummy_driver():
    # conftest 已把 SDL_AUDIODRIVER 设为 dummy，mixer 应能初始化
    am = AudioManager.create({})       # 空映射：所有音效为 None
    assert am.enabled is True
    for name in ("wing", "point", "hit", "die", "swoosh"):
        am.play(name)                  # 缺失音效 => 空操作，不抛
    am.quit()


def test_create_loads_real_sounds():
    from src import config as c
    from src.assets import resolve_sound_path

    paths = {n: resolve_sound_path(c.AUDIOS_DIR, n) for n in c.SFX_NAMES}
    am = AudioManager.create(paths)
    assert am.enabled is True
    assert am.sound_count == len(c.SFX_NAMES)
    for name in c.SFX_NAMES:
        am.play(name)                  # 不应抛异常
    am.quit()


def test_reserved_channels_exist():
    am = AudioManager.create({})
    assert am.enabled
    import pygame
    assert pygame.mixer.get_num_channels() >= 8
    am.quit()


def test_create_survives_broken_audio_driver(monkeypatch):
    import pygame

    def boom(*args, **kwargs):
        raise pygame.error("Audio target 'nope' not available")

    am = AudioManager.create({})
    am.quit()
    monkeypatch.setattr(pygame.mixer, "init", boom)
    am2 = AudioManager.create({})
    assert am2.enabled is False
    am2.play("wing")               # 禁用后仍可安全调用
