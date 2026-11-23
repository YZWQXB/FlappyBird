"""启动器：让 `python main.py` 在任何 Python 环境下都能开箱即用。

设计目标（按优先级）：
1. 用户用系统 Python 直接运行时，**自动重定向**到项目的 .venv，不需要用户懂虚拟环境；
2. 项目还没有 .venv 时，**自动创建并安装依赖**（需 uv 或 pip 可用）；
3. 以上都失败时，给出**可直接复制粘贴的绝对路径命令**，而不是含糊的提示；
4. 绝不无限重启自己（用环境变量做一次性守卫）。

本模块只做进程编排，不含游戏逻辑，不 import pygame。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from . import config as c

# 环境变量守卫：防止在 .venv 里仍缺 pygame 时无限自我重启
_GUARD_ENV = "FLAPPYBIRD_LAUNCHER_REEXEC"
# 开发/测试用：跳过 pygame 检查并直接进入游戏
SMOKE_FRAMES_ENV = "FLAPPYBIRD_SMOKE_FRAMES"

_VENV_CANDIDATES = (
    Path(".venv") / "Scripts" / "python.exe",      # Windows
    Path(".venv") / "bin" / "python",              # POSIX
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def find_venv_python(root: Path) -> Path | None:
    """返回项目 .venv 里的解释器路径；不存在则返回 None。"""
    for rel in _VENV_CANDIDATES:
        candidate = Path(root) / rel
        if candidate.is_file():
            return candidate
    return None


def has_pygame() -> bool:
    try:
        import pygame  # noqa: F401
    except ImportError:
        return False
    return True


def decide_startup_action(
    *,
    has_pygame: bool,
    has_venv_python: bool,
    force_no_pygame: bool,
    requirements_present: bool,
) -> str:
    """纯函数：决定启动策略。返回值见下方 DOC。

    - "run"         当前解释器已具备 pygame，直接运行
    - "reexec"      切换到项目 .venv 的解释器重新启动
    - "create_venv" 先创建 .venv 并安装依赖，再重新启动
    - "abort"       无法自动修复，打印手工指令后退出
    """
    # 有 pygame 就直接跑（重启后的子进程若环境正常，必须走这条）
    if has_pygame:
        return "run"
    if not requirements_present:
        return "abort"
    if force_no_pygame:
        # 已经重启过一次，新环境里仍然没有 pygame → 不再循环
        return "abort"
    if has_venv_python:
        return "reexec"
    return "create_venv"


def manual_instructions(root: Path) -> str:
    """给用户可直接复制粘贴的命令（使用绝对路径）。"""
    exe = find_venv_python(root)
    venv_py = str(exe) if exe else str(Path(root) / ".venv" / "Scripts" / "python.exe")
    req = str(Path(root) / "requirements.txt")
    main_py = str(Path(root) / "main.py")
    return (
        "无法自动准备运行环境，请手动执行以下命令（可直接复制）：\n\n"
        f'  cd "{root}"\n'
        "  uv venv .venv\n"
        f'  uv pip install --python "{venv_py}" -r "{req}"\n'
        f'  "{venv_py}" "{main_py}"\n\n'
        "若没有 uv，可改用：\n\n"
        f'  python -m venv .venv\n'
        f'  "{venv_py}" -m pip install -r "{req}"\n'
        f'  "{venv_py}" "{main_py}"\n'
    )


def _reexec_into(exe: Path, root: Path, args: list[str]) -> int:
    """用指定解释器重新启动 main.py，并透传退出码。"""
    env = dict(os.environ)
    env[_GUARD_ENV] = "1"                       # 一次性守卫
    cmd = [str(exe), str(Path(root) / "main.py"), *args]
    print(f"[启动器] 正在切换到项目虚拟环境：{exe}")
    try:
        return subprocess.call(cmd, cwd=str(root), env=env)
    except OSError as exc:
        print(f"[启动器] 切换失败：{exc}")
        return c.EXIT_ENV_ERROR


def _create_venv(root: Path) -> Path | None:
    """尝试用 uv / python -m venv 创建环境并安装依赖。返回解释器路径。"""
    exe = find_venv_python(root)
    if exe is not None:
        return exe
    req = Path(root) / "requirements.txt"
    py = sys.executable

    attempts: list[list[str]] = []
    if _which("uv"):
        attempts.append(["uv", "venv", str(Path(root) / ".venv"), "--python", "3.12"])
    attempts.append([py, "-m", "venv", str(Path(root) / ".venv")])

    for cmd in attempts:
        print(f"[启动器] 正在创建虚拟环境：{' '.join(cmd)}")
        try:
            if subprocess.call(cmd, cwd=str(root)) != 0:
                continue
        except OSError as exc:
            print(f"[启动器] 命令不可用：{exc}")
            continue
        exe = find_venv_python(root)
        if exe is None:
            continue
        installs: list[list[str]] = []
        if _which("uv"):
            installs.append(["uv", "pip", "install", "--python", str(exe), "-r", str(req)])
        installs.append([str(exe), "-m", "pip", "install", "-r", str(req)])
        for install in installs:
            print(f"[启动器] 正在安装依赖：{' '.join(install)}")
            try:
                if subprocess.call(install, cwd=str(root)) == 0:
                    return exe
            except OSError:
                continue
    return None


def _which(name: str) -> str | None:
    import shutil

    return shutil.which(name)


def ensure_environment(root: Path, argv: list[str]) -> int | None:
    """确保当前解释器可以运行游戏。

    返回 None 表示"当前解释器可用，继续运行"；返回 int 表示"已处理完毕，用该退出码退出"。
    """
    force_no_pygame = os.environ.get(_GUARD_ENV) == "1"
    action = decide_startup_action(
        has_pygame=has_pygame(),
        has_venv_python=find_venv_python(root) is not None,
        force_no_pygame=force_no_pygame,
        requirements_present=(Path(root) / "requirements.txt").is_file(),
    )

    if action == "run":
        return None

    if action == "reexec":
        exe = find_venv_python(root)
        if exe is not None:
            return _reexec_into(exe, root, argv)

    if action == "create_venv":
        exe = _create_venv(root)
        if exe is not None:
            return _reexec_into(exe, root, argv)
        print("[启动器] 自动创建环境失败。\n")

    print(manual_instructions(root))
    return c.EXIT_ENV_ERROR
