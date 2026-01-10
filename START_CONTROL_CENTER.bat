@echo off
REM OI-7500 Pipeline Control Center Launcher
REM Automatically uses virtual environment

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    echo Starting OI-7500 Control Center...
    ".venv\Scripts\python.exe" launcher.py
) else (
    echo Virtual environment not found!
    echo Please run: python -m venv .venv
    echo Then: .venv\Scripts\activate
    echo Then: pip install -r requirements.txt
    pause
)
