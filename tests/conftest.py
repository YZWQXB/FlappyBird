import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _display():
    """提供一个 288x512 的 dummy 显示，供需要 convert_alpha 的测试使用。"""
    import pygame

    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.display.set_mode((288, 512))
    yield pygame.display.get_surface()
    pygame.quit()


@pytest.fixture(scope="session")
def assets(_display):
    from src import config as c
    from src.assets import AssetManager

    return AssetManager(c.RES_DIR)
