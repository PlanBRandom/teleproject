@echo off
REM OI Monitor Control Center - Web GUI Launcher
REM
REM This launches the web interface for testing and configuring
REM OI gas monitors and Laird radio modules

cd /d "%~dp0"

echo.
echo ============================================================
echo   OI Monitor Control Center - Web GUI
echo ============================================================
echo.
echo   Starting server...
echo.

REM Activate virtual environment and run
call ..\..\.venv\Scripts\activate.bat
python app.py

pause
