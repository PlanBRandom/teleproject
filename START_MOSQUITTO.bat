@echo off
echo Starting Mosquitto MQTT Broker...
echo Port: 1883 (localhost)
echo Config: mosquitto_test.conf
echo.
echo Press Ctrl+C to stop
echo.

"C:\Program Files\mosquitto\mosquitto.exe" -c "%~dp0mosquitto_test.conf" -v

pause
