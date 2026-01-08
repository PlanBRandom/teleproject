@echo off
REM Startup script for Windows testing
REM OI-7500 Simple Monitor

echo Starting OI-7500 Simple Monitor...
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" simple_monitor.py
) else (
    python simple_monitor.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred! Press any key to exit...
    pause >nul
)
