"""可移植性回归测试：别人从仓库拉代码后能否直接运行。

对应缺陷 D-14（P1）：start.bat 与 launcher 依赖 "python" 命令，但：
  - Windows 上 python.exe 可能是微软商店的 0 字节 App Execution Alias 占位符
    （执行返回 9009），很多机器就是这种状态；
  - 也可能是 conda 的 python、py launcher、uv 托管的 python。
必须按可用性依次探测，而不是假设 "python" 一定可用。
"""

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- 解释器探测

def test_find_python_candidates_returns_list():
    from src.launcher import find_python_candidates

    candidates = find_python_candidates()
    assert isinstance(candidates, list)
    assert all(isinstance(p, Path) for p in candidates)
    # 至少当前解释器本身应被识别
    assert any(p.exists() for p in candidates)


def test_is_usable_python_rejects_missing_path(tmp_path):
    from src.launcher import is_usable_python

    assert is_usable_python(tmp_path / "nope.exe") is False


def test_is_usable_python_rejects_zero_byte_alias(tmp_path):
    """微软商店占位符是 0 字节文件，必须被识别为不可用。"""
    from src.launcher import is_usable_python

    fake = tmp_path / "python.exe"
    fake.write_bytes(b"")            # 0 字节
    assert is_usable_python(fake) is False


def test_current_interpreter_is_usable():
    from src.launcher import is_usable_python

    assert is_usable_python(Path(sys.executable)) is True


# ---------------------------------------------------------------- 环境创建

def test_decide_reports_actionable_message_when_no_python():
    """没有任何可用 Python 时，必须给出可操作的提示而不是 9009。"""
    from src.launcher import decide_startup_action

    action = decide_startup_action(
        has_pygame=False,
        has_venv_python=False,
        force_no_pygame=False,
        requirements_present=True,
        has_usable_python=False,
    )
    assert action == "abort"


def test_decide_creates_venv_when_usable_python_exists():
    from src.launcher import decide_startup_action

    action = decide_startup_action(
        has_pygame=False,
        has_venv_python=False,
        force_no_pygame=False,
        requirements_present=True,
        has_usable_python=True,
    )
    assert action == "create_venv"


# ---------------------------------------------------------------- 提示文案

def test_manual_instructions_mention_python_install_when_missing():
    """无 Python 时，提示必须告诉用户去装 Python，而不是让他跑 uv 命令。"""
    from src.launcher import manual_instructions

    text = manual_instructions(PROJECT_ROOT, no_python=True)
    assert "Python" in text
    assert "python.org" in text or "安装" in text


def test_manual_instructions_normal_case_has_commands():
    from src.launcher import manual_instructions

    text = manual_instructions(PROJECT_ROOT, no_python=False)
    assert "requirements.txt" in text
    assert str(PROJECT_ROOT) in text


# ---------------------------------------------------------------- start.bat

def test_start_bat_does_not_assume_python_is_available():
    """start.bat 必须按可用性探测解释器，不能直接写 python main.py。"""
    text = (PROJECT_ROOT / "start.bat").read_text(encoding="utf-8", errors="replace")
    # 必须探测 py launcher 或 uv，而不是无条件调用 python
    assert any(k in text for k in ("py -3", "uv ", "where python", "where py")), (
        "start.bat 应探测可用的解释器，而不是直接假设 python 命令可用"
    )


def test_start_bat_does_not_fail_on_9009():
    """start.bat 不应把 9009（命令未找到）当成普通失败而不给提示。"""
    text = (PROJECT_ROOT / "start.bat").read_text(encoding="utf-8", errors="replace")
    assert "9009" in text or "未找到 Python" in text or "where" in text


# ---------------------------------------------------------------- 端到端

def test_launcher_works_without_python_on_path(tmp_path, monkeypatch):
    """即使 PATH 里没有可用的 python，只要进程内解释器可用，仍应能建环境。"""
    from src import launcher

    # 模拟：PATH 查不到任何可用 python
    monkeypatch.setattr(launcher, "_which_all", lambda name: [])

    candidates = launcher.find_python_candidates()
    # sys.executable 是真实解释器，应被识别
    assert any(c == Path(sys.executable) for c in candidates), (
        f"应从 sys.executable 兜底，实际: {candidates}"
    )
