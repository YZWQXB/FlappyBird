"""启动器测试：用户不建 venv、直接 `python main.py` 也应能跑起来。

对应缺陷 D-13（易用性）：用户用系统 Python 运行会得到"依赖缺失"提示，
但提示要求用户自己执行两条命令——对交付给他人运行的成品游戏而言不可接受。
"""

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- 环境探测

def test_find_venv_python_returns_path_when_venv_exists():
    from src.launcher import find_venv_python

    exe = find_venv_python(PROJECT_ROOT)
    assert exe is not None, ".venv 存在时应能找到解释器"
    assert exe.is_file()
    assert exe.name.lower().startswith("python")


def test_find_venv_python_returns_none_without_venv(tmp_path):
    from src.launcher import find_venv_python

    assert find_venv_python(tmp_path) is None


def test_requirements_present():
    assert (PROJECT_ROOT / "requirements.txt").is_file()


# ---------------------------------------------------------------- 决策逻辑

def test_should_reexec_when_pygame_missing_but_venv_exists():
    """当前解释器缺 pygame、且 .venv 可用 → 应该自动切到 .venv。"""
    from src.launcher import decide_startup_action

    action = decide_startup_action(
        has_pygame=False,
        has_venv_python=True,
        force_no_pygame=False,
        requirements_present=True,
    )
    assert action == "reexec"


def test_should_create_venv_when_missing():
    """当前解释器缺 pygame、且没有 .venv → 应该尝试创建环境。"""
    from src.launcher import decide_startup_action

    action = decide_startup_action(
        has_pygame=False,
        has_venv_python=False,
        force_no_pygame=False,
        requirements_present=True,
    )
    assert action == "create_venv"


def test_should_run_directly_when_pygame_available():
    from src.launcher import decide_startup_action

    action = decide_startup_action(
        has_pygame=True,
        has_venv_python=True,
        force_no_pygame=False,
        requirements_present=True,
    )
    assert action == "run"


def test_should_give_up_with_actionable_message_when_no_requirements():
    from src.launcher import decide_startup_action

    action = decide_startup_action(
        has_pygame=False,
        has_venv_python=False,
        force_no_pygame=False,
        requirements_present=False,
    )
    assert action == "abort"


def test_guard_prevents_infinite_reexec():
    """在 .venv 里仍缺 pygame 时不能无限重启自己。"""
    from src.launcher import decide_startup_action

    action = decide_startup_action(
        has_pygame=False,
        has_venv_python=True,
        force_no_pygame=True,      # 已重启过一次
        requirements_present=True,
    )
    assert action == "abort"


# ---------------------------------------------------------------- 提示文案

def test_manual_instructions_use_absolute_paths():
    """兜底提示必须给出可直接复制粘贴的绝对路径命令。"""
    from src.launcher import manual_instructions

    text = manual_instructions(PROJECT_ROOT)
    assert str(PROJECT_ROOT) in text
    assert "requirements.txt" in text
    assert "python" in text.lower()


# ---------------------------------------------------------------- 端到端

@pytest.mark.skipif(
    not (PROJECT_ROOT / ".venv" / "Scripts" / "python.exe").is_file(),
    reason="需要项目 .venv 才能验证自动重定向",
)
def test_launcher_reexecs_into_venv_end_to_end():
    """用缺 pygame 的系统解释器启动 main.py，应自动切到 .venv 并进入游戏初始化。"""
    import subprocess

    # 找一个肯定没有 pygame 的解释器：直接用 py 启动器的 base，或退而用当前环境但清空 site-packages
    env = dict(os.environ)
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    env["FLAPPYBIRD_SMOKE_FRAMES"] = "3"     # 让游戏跑 3 帧就退出，测试才能结束
    env.pop("PYGAME_HIDE_SUPPORT_PROMPT", None)

    # 用 .venv 的 python 跑一个"阉割"脚本：屏蔽 pygame 后调用 main
    probe = PROJECT_ROOT / "_probe_launcher.py"
    probe.write_text(
        "import sys, builtins\n"
        "sys.path.insert(0, r'%s')\n"
        "real = builtins.__import__\n"
        "def fake(name, *a, **k):\n"
        "    if name == 'pygame' or name.startswith('pygame.'):\n"
        "        raise ImportError('simulated missing pygame')\n"
        "    return real(name, *a, **k)\n"
        "builtins.__import__ = fake\n"
        "import main\n"
        "raise SystemExit(main.main())\n" % str(PROJECT_ROOT)
    , encoding="utf-8")
    try:
        proc = subprocess.run(
            [sys.executable, str(probe)],
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        combined = (proc.stdout or "") + (proc.stderr or "")
        assert "依赖缺失" not in combined, f"应自动重定向而非报依赖缺失：{combined[:400]}"
        assert proc.returncode == 0, f"退出码 {proc.returncode}：{combined[:400]}"
    finally:
        probe.unlink(missing_ok=True)

def test_start_bat_delegates_env_setup_to_launcher():
    """start.bat 不应再自己写 uv 命令，应交给 main.py 的启动器统一处理。"""
    text = (PROJECT_ROOT / "start.bat").read_text(encoding="utf-8", errors="replace")
    assert "main.py" in text
    assert ".venv" in text
    # 旧版把 uv venv / uv pip install 写死在 bat 里，逻辑与 launcher 重复
    assert "uv venv" not in text, "环境创建逻辑应集中在 src/launcher.py"


# ---------------------------------------------------------------- 执行路径（依赖注入）

def test_reexec_sets_guard_env_and_returns_child_code(monkeypatch, tmp_path):
    """重定向必须设置守卫变量，并透传子进程退出码。"""
    from src import launcher

    captured = {}

    def fake_call(cmd, cwd=None, env=None):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["guard"] = (env or {}).get(launcher._GUARD_ENV)
        return 7

    monkeypatch.setattr(launcher.subprocess, "call", fake_call)

    exe = tmp_path / "python.exe"
    exe.write_text("", encoding="utf-8")
    code = launcher._reexec_into(exe, tmp_path, ["--foo"])

    assert code == 7
    assert captured["guard"] == "1"
    assert captured["cwd"] == str(tmp_path)
    assert captured["cmd"][0] == str(exe)
    assert captured["cmd"][1].endswith("main.py")
    assert captured["cmd"][-1] == "--foo"


def test_reexec_returns_error_when_exec_raises(monkeypatch, tmp_path):
    from src import launcher

    def boom(*a, **k):
        raise OSError("no such file")

    monkeypatch.setattr(launcher.subprocess, "call", boom)
    exe = tmp_path / "python.exe"
    exe.write_text("", encoding="utf-8")
    assert launcher._reexec_into(exe, tmp_path, []) == 2


def test_create_venv_uses_uv_first(monkeypatch, tmp_path):
    """有 uv 时应优先用 uv，而不是 python -m venv。"""
    from src import launcher

    (tmp_path / "requirements.txt").write_text("pygame\n", encoding="utf-8")
    commands = []

    def fake_which(name):
        return "uv" if name == "uv" else None

    def fake_call(cmd, cwd=None, env=None):
        commands.append(cmd)
        if cmd[0] == "uv" and cmd[1] == "venv":
            # 模拟 uv 创建出解释器
            exe = tmp_path / ".venv" / "Scripts" / "python.exe"
            exe.parent.mkdir(parents=True, exist_ok=True)
            exe.write_text("", encoding="utf-8")
        return 0

    monkeypatch.setattr(launcher, "_which", fake_which)
    monkeypatch.setattr(launcher.subprocess, "call", fake_call)

    exe = launcher._create_venv(tmp_path)
    assert exe is not None
    assert commands[0][0] == "uv"
    assert any(c[0] == "uv" and c[1] == "pip" for c in commands)


def test_create_venv_falls_back_to_python_venv(monkeypatch, tmp_path):
    """没有 uv 时应回退到 python -m venv。"""
    from src import launcher

    (tmp_path / "requirements.txt").write_text("pygame\n", encoding="utf-8")
    commands = []

    def fake_which(name):
        return None

    def fake_call(cmd, cwd=None, env=None):
        commands.append(cmd)
        if "-m" in cmd and "venv" in cmd:
            exe = tmp_path / ".venv" / "Scripts" / "python.exe"
            exe.parent.mkdir(parents=True, exist_ok=True)
            exe.write_text("", encoding="utf-8")
        return 0

    monkeypatch.setattr(launcher, "_which", fake_which)
    monkeypatch.setattr(launcher.subprocess, "call", fake_call)

    exe = launcher._create_venv(tmp_path)
    assert exe is not None
    assert any("-m" in c and "venv" in c for c in commands)


def test_create_venv_returns_none_when_all_attempts_fail(monkeypatch, tmp_path):
    from src import launcher

    (tmp_path / "requirements.txt").write_text("pygame\n", encoding="utf-8")
    monkeypatch.setattr(launcher, "_which", lambda name: None)
    monkeypatch.setattr(launcher.subprocess, "call", lambda *a, **k: 1)
    assert launcher._create_venv(tmp_path) is None


def test_ensure_environment_returns_none_when_pygame_present(monkeypatch, tmp_path):
    from src import launcher

    (tmp_path / "requirements.txt").write_text("", encoding="utf-8")
    monkeypatch.setattr(launcher, "has_pygame", lambda: True)
    assert launcher.ensure_environment(tmp_path, []) is None


def test_ensure_environment_reexecs_when_venv_present(monkeypatch, tmp_path):
    from src import launcher

    (tmp_path / "requirements.txt").write_text("", encoding="utf-8")
    exe = tmp_path / ".venv" / "Scripts" / "python.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")

    monkeypatch.setattr(launcher, "has_pygame", lambda: False)
    monkeypatch.setattr(launcher, "_reexec_into", lambda e, r, a: 0)
    assert launcher.ensure_environment(tmp_path, []) == 0


def test_ensure_environment_aborts_without_requirements(monkeypatch, tmp_path):
    from src import launcher

    monkeypatch.setattr(launcher, "has_pygame", lambda: False)
    assert launcher.ensure_environment(tmp_path, []) == 2


def test_ensure_environment_aborts_under_guard(monkeypatch, tmp_path):
    """守卫已设且仍无 pygame → 立即 abort，不再尝试重启。"""
    from src import launcher

    (tmp_path / "requirements.txt").write_text("", encoding="utf-8")
    monkeypatch.setattr(launcher, "has_pygame", lambda: False)
    monkeypatch.setenv(launcher._GUARD_ENV, "1")
    called = []
    monkeypatch.setattr(launcher, "_reexec_into", lambda *a: called.append(1) or 0)
    assert launcher.ensure_environment(tmp_path, []) == 2
    assert called == []
