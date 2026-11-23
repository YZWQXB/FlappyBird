@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================
echo   FlappyBird Launcher
echo ============================================
echo.

rem ---------- 1. Use existing .venv if present ----------
if exist ".venv\Scripts\python.exe" (
    echo [1/2] Found project venv, starting...
    ".venv\Scripts\python.exe" main.py
    set "RC=!errorlevel!"
    if !RC! neq 0 goto :fail
    goto :ok
)

echo [1/2] No .venv found, looking for a usable Python...

rem ---------- 2. Probe available Python interpreters ----------
rem NOTE: On Windows, python.exe may be a 0-byte Microsoft Store app
rem       execution alias that returns 9009. So we must actually run
rem       the interpreter to verify, not just check "where".
set "PY="

rem 2.1 py launcher (installed by the official Python installer)
py -3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY=py -3"
    echo       found: py launcher
    goto :found
)

rem 2.2 python on PATH (verify it really executes)
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY=python"
    echo       found: python
    goto :found
)

rem 2.3 python3 on PATH
python3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY=python3"
    echo       found: python3
    goto :found
)

rem 2.4 common conda locations
for %%D in ("%USERPROFILE%\miniconda3" "%USERPROFILE%\anaconda3" "C:\ProgramData\miniconda3" "C:\ProgramData\anaconda3") do (
    if exist "%%~D\python.exe" (
        "%%~D\python.exe" --version >nul 2>&1
        if !errorlevel! equ 0 (
            set "PY="%%~D\python.exe""
            echo       found: %%~D\python.exe
            goto :found
        )
    )
)

goto :no_python

:found
echo [2/2] Starting with !PY! (first run creates the venv automatically)...
echo.
call !PY! main.py
set "RC=!errorlevel!"
if !RC! neq 0 goto :fail
goto :ok

rem ---------- 3. No Python found ----------
:no_python
echo.
echo [ERROR] No usable Python found.
echo.
echo Please install Python 3.12 first:
echo   1. Download from https://www.python.org/downloads/
echo      (check "Add python.exe to PATH" during install)
echo   2. Or search "Python 3.12" in Microsoft Store
echo.
echo If you installed Python but "python" returns 9009, it is usually
echo the Microsoft Store app execution alias:
echo   Settings - Apps - Advanced app settings - App execution aliases
echo   - turn OFF python.exe
echo.
set "RC=9009"
goto :fail

:fail
echo.
echo ============================================
echo   Startup failed (exit code !RC!)
echo   See messages above, or README troubleshooting.
echo ============================================
pause
exit /b !RC!

:ok
echo.
echo Game exited normally.
exit /b 0
