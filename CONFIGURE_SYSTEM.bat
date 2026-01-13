@echo off
REM Configuration Wizard Launcher
REM Double-click this file to configure your OI-7500 monitoring system

cd /d "%~dp0"
echo.
echo ================================================================================
echo   OI-7500 SYSTEM CONFIGURATION WIZARD
echo ================================================================================
echo.

.venv\Scripts\python.exe configure_system.py

if errorlevel 1 (
    echo.
    echo Configuration failed or was cancelled.
    pause
    exit /b 1
)

echo.
echo Configuration complete!
echo.
echo To start monitoring, run: START_MONITORING.bat
echo.
pause
