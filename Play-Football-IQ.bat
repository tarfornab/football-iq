@echo off
cd /d "%~dp0"
if not exist launch.py (
    echo Use Extract All on the ZIP before opening this file.
    pause
    exit /b 1
)
where python >nul 2>nul
if errorlevel 1 (
    py -3 launch.py
) else (
    python launch.py
)
if errorlevel 1 (
    echo If a Python package is missing, run: python -m pip install Flask "qrcode[pil]"
    pause
)
