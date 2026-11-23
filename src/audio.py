"""音效门面：所有失败路径降级为空操作，绝不向调用方抛异常。"""

from __future__ import annotations

from pathlib import Path

import pygame

from . import config as c

# 需要遵守最小间隔的音效（Spec FR-AUDIO-4：避免 hit/die 叠音）
_GAP_LIMITED = frozenset({"hit", "die"})


def sfx_gap_ok(name: str, now_ms: float, last_ms: float | None) -> bool:
    """判断某音效在当前时刻是否允许播放（纯函数，便于单测）。

    - 只对 _GAP_LIMITED 内的音效做间隔限制；
    - 从未播放过（last_ms is None）→ 允许；
    - 距上次播放不足 SFX_PRIORITY_GAP_MS → 拒绝。
    """
    if name not in _GAP_LIMITED or last_ms is None:
        return True
    return (now_ms - last_ms) >= c.SFX_PRIORITY_GAP_MS


class AudioManager:
    """音效门面：所有失败路径降级为空操作，绝不向调用方抛异常。"""

    RESERVED = {"hit": 0, "die": 1, "swoosh": 2}

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.muted = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._channels: list[pygame.mixer.Channel] = []
        self._last_play_ms: dict[str, float] = {}

    @classmethod
    def disabled(cls) -> "AudioManager":
        return cls(enabled=False)

    @classmethod
    def create(cls, sound_paths: dict[str, Path | None]) -> "AudioManager":
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            pygame.mixer.set_num_channels(c.AUDIO_CHANNELS)
        except (pygame.error, OSError) as exc:      # 无声卡 / 驱动缺失
            print(f"[audio] 音频不可用，已降级为静音：{exc}")
            return cls.disabled()
        am = cls(enabled=True)
        am._channels = [pygame.mixer.Channel(i) for i in range(c.AUDIO_CHANNELS)]
        for name, path in (sound_paths or {}).items():
            if path is None:
                continue
            try:
                am._sounds[name] = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError) as exc:
                print(f"[audio] 音效加载失败 {name}: {exc}")
        return am

    @property
    def sound_count(self) -> int:
        return len(self._sounds)

    def play(self, name: str) -> None:
        if not self.enabled or self.muted:
            return
        sound = self._sounds.get(name)
        if sound is None:
            return
        now_ms = pygame.time.get_ticks()
        if not sfx_gap_ok(name, now_ms, self._last_play_ms.get(name)):
            return
        try:
            self._last_play_ms[name] = now_ms
            index = self.RESERVED.get(name)
            if index is None:
                sound.play()
            else:
                channel = self._channels[index]
                channel.stop()
                channel.play(sound)
        except pygame.error:
            self.enabled = False      # 通道异常后彻底降级，避免刷屏

    def toggle_mute(self) -> None:
        self.muted = not self.muted

    def stop_all(self) -> None:
        if self.enabled:
            try:
                pygame.mixer.stop()
            except pygame.error:
                self.enabled = False

    def quit(self) -> None:
        if self.enabled and pygame.mixer.get_init():
            try:
                pygame.mixer.quit()
            except pygame.error:
                pass
        self.enabled = False
