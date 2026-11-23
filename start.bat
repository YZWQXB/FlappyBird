@echo off
setlocal
cd /d "%~dp0"

rem 若已存在虚拟环境，直接用它运行
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" main.py
  exit /b %errorlevel%
)

rem 否则交给 main.py 的启动器自动创建环境（需要 uv 或 python）
echo [setup] 未检测到 .venv，正在准备运行环境...
python main.py
set EXITCODE=%errorlevel%
if %EXITCODE% neq 0 (
  echo.
  echo 启动失败，退出码 %EXITCODE%。请查看上方信息，或阅读 README 的"排障"一节。
  pause
)
exit /b %EXITCODE%
