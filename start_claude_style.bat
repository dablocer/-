@echo off
setlocal
cd /d "%~dp0"

if not exist "claude_style.py" (
    echo Не найден claude_style.py. Убедитесь, что BAT-файл лежит рядом с файлами проекта.
    pause
    exit /b 1
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 claude_style.py
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python не найден. Установите Python 3 и добавьте его в PATH.
        pause
        exit /b 1
    )
    python claude_style.py
)

if errorlevel 1 pause
endlocal
