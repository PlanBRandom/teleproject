@echo off
REM Download and run Mosquitto MQTT broker for Windows
REM Lightweight local MQTT broker for testing

echo ====================================
echo Mosquitto MQTT Broker Setup
echo ====================================
echo.

REM Check if mosquitto is already installed
where mosquitto >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Mosquitto is already installed!
    echo.
    echo Starting broker on port 1883...
    echo Press Ctrl+C to stop
    echo.
    mosquitto -v
) else (
    echo Mosquitto not found.
    echo.
    echo Please download and install Mosquitto:
    echo https://mosquitto.org/download/
    echo.
    echo Or use this direct link:
    echo https://mosquitto.org/files/binary/win64/mosquitto-2.0.18-install-windows-x64.exe
    echo.
    echo After installation, run this script again.
    pause
)
