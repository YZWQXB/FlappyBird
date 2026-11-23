@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo ============================================
echo   FlappyBird 启动器
echo ============================================
echo.

rem ---------- 1. 已有 .venv，直接用 ----------
if exist ".venv\Scripts\python.exe" (
    echo [1/2] 检测到项目虚拟环境，直接启动...
    ".venv\Scripts\python.exe" main.py
    set "RC=!errorlevel!"
    if !RC! neq 0 goto :fail
    goto :ok
)

echo [1/2] 未检测到 .venv，正在查找可用的 Python...

rem ---------- 2. 依次探测可用的 Python 解释器 ----------
rem 注意：Windows 上 python.exe 可能是微软商店的 0 字节占位符，
rem       执行会返回 9009。因此必须实际验证，不能只看 where 结果。
set "PY="

rem 2.1 py launcher（Windows 官方安装器会装，最可靠）
py -3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY=py -3"
    echo       找到: py launcher
    goto :found
)

rem 2.2 PATH 中的 python（验证能真正执行）
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY=python"
    echo       找到: python
    goto :found
)

rem 2.3 PATH 中的 python3
python3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY=python3"
    echo       找到: python3
    goto :found
)

rem 2.4 conda 常见位置
for %%D in ("%USERPROFILE%\miniconda3" "%USERPROFILE%\anaconda3" "C:\ProgramData\miniconda3" "C:\ProgramData\anaconda3") do (
    if exist "%%~D\python.exe" (
        "%%~D\python.exe" --version >nul 2>&1
        if !errorlevel! equ 0 (
            set "PY="%%~D\python.exe""
            echo       找到: %%~D\python.exe
            goto :found
        )
    )
)

rem 2.5 都没找到
goto :no_python

:found
echo [2/2] 使用 !PY! 启动（首次运行会自动创建环境并安装依赖）...
echo.
call !PY! main.py
set "RC=!errorlevel!"
if !RC! neq 0 goto :fail
goto :ok

rem ---------- 3. 找不到 Python ----------
:no_python
echo.
echo [错误] 未找到可用的 Python。
echo.
echo 请先安装 Python 3.12，任选其一：
echo   1. 访问 https://www.python.org/downloads/ 下载安装
echo      （安装时务必勾选 "Add python.exe to PATH"）
echo   2. Microsoft Store 搜索 "Python 3.12" 安装
echo.
echo 如果你曾装过 Python 但 python 命令提示找不到（退出码 9009），
echo 通常是「应用执行别名」占位符未关闭：
echo   设置 - 应用 - 高级应用设置 - 应用执行别名 - 关闭 python.exe
echo.
goto :fail

:fail
echo.
echo ============================================
echo   启动失败（退出码 !RC!）
echo   详见上方信息，或阅读 README 的「排障」一节
echo ============================================
pause
exit /b !RC!

:ok
echo.
echo 游戏已正常退出。
exit /b 0
