@echo off
setlocal
cd /d "%~dp0"

rem Keep messages ASCII-only so they display correctly in any Windows console code page.
if not exist "claude_style.py" (
    echo ERROR: claude_style.py was not found in:
    echo %CD%
    echo.
    echo Download the complete repository ZIP and extract this BAT file next to claude_style.py.
    echo Repository: https://github.com/dablocer/-
    pause
    exit /b 1
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 claude_style.py
    goto :finish
)

where python >nul 2>nul
if not errorlevel 1 (
    python claude_style.py
    goto :finish
)

echo ERROR: Python 3 was not found. Install Python and enable "Add Python to PATH".
pause
exit /b 1

:finish
if errorlevel 1 (
    echo.
    echo The interface exited with an error. Check that Python, Ollama, and a local model are installed.
    pause
)
endlocal
