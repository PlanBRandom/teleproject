@echo off
REM Start 24-Hour Monitoring
REM Checks configuration and starts all monitoring processes

cd /d "%~dp0"

powershell.exe -ExecutionPolicy Bypass -File "START_MONITORING.ps1"

pause
