# OI-7500 Simple Monitor

Lightweight monitoring solution for end-user deployment on Raspberry Pi or ESP32.

## Features

✅ **Lightweight** - Minimal resource usage, no GUI overhead  
✅ **Single Network** - Monitor one WireFree network at a time  
✅ **Easy Setup** - Interactive configuration wizard  
✅ **MQTT Publishing** - Automatic cloud publishing  
✅ **Console Display** - Real-time packet display with color indicators  
✅ **Auto-logging** - All data saved to log file  

## Quick Start

### 1. Run Setup Wizard
```bash
python3 simple_monitor.py --setup
```

### 2. Start Monitoring
```bash
python3 simple_monitor.py
```

Or use the startup script:
```bash
# Linux/Pi
./start_simple.sh

# Windows (for testing)
START_SIMPLE.bat
```

## Configuration

Edit `simple_config.json` directly or use the setup wizard.

### Device Settings
```json
{
  "device": {
    "model": "OI-7530",
    "radio_port": "/dev/ttyUSB0",
    "radio_baud": 115200,
    "network": "Network_25"
  }
}
```

**For Raspberry Pi:**
- Radio port: `/dev/ttyUSB0` (or `/dev/ttyAMA0` for GPIO serial)
- Modbus port: `/dev/ttyUSB1` (if used)

**For ESP32:**
- Radio port: `/dev/ttyS1`
- Modbus port: `/dev/ttyS2`

**For Windows (testing):**
- Radio port: `COM11`
- Modbus port: `COM10`

### MQTT Settings
```json
{
  "mqtt": {
    "enabled": true,
    "broker": "your-broker.hivemq.cloud",
    "port": 8883,
    "username": "your_username",
    "password": "your_password",
    "use_tls": true,
    "topic_prefix": "oi7500"
  }
}
```

Topics published:
- `oi7500/channel01` - Channel 1 data
- `oi7500/channel02` - Channel 2 data
- etc.

## Command Line Options

```bash
# Run continuously
python3 simple_monitor.py

# Run for specific duration (minutes)
python3 simple_monitor.py --duration 60

# Use custom config file
python3 simple_monitor.py --config my_config.json

# Interactive setup
python3 simple_monitor.py --setup
```

## Console Output

```
================================================================================
OI-7500 Simple Monitor - OI-7530 - Network_25
================================================================================
Status | Channel | Gas Type | Reading | Battery | Fault
--------------------------------------------------------------------------------
✓ CH01 | LEL      |    12.3 | Battery: 3.2V | F0 - No Fault
✓ CH02 | O2       |    20.9 | Battery: 3.4V | F0 - No Fault
⚠️ CH03 | CO       |   125.0 | Battery: 2.8V | F1 - Low Battery
```

## Raspberry Pi Installation

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install python3 python3-pip python3-serial

# Install Python packages
pip3 install paho-mqtt pyserial

# Make startup script executable
chmod +x start_simple.sh

# Test run
python3 simple_monitor.py --setup
python3 simple_monitor.py
```

## Auto-start on Boot (Raspberry Pi)

Create systemd service:

```bash
sudo nano /etc/systemd/system/oi7500-monitor.service
```

Add:
```ini
[Unit]
Description=OI-7500 Simple Monitor
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/oi-7500-pipeline
ExecStart=/usr/bin/python3 /home/pi/oi-7500-pipeline/simple_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable oi7500-monitor.service
sudo systemctl start oi7500-monitor.service
sudo systemctl status oi7500-monitor.service
```

## Logging

All events are logged to `simple_monitor.log`:
- Startup/shutdown events
- Packet counts
- Connection status
- Errors

View recent logs:
```bash
tail -f simple_monitor.log
```

## Comparison: Simple vs Full

| Feature | Simple Monitor | Full Launcher |
|---------|---------------|---------------|
| **Platform** | Pi/ESP32/Windows | Windows only |
| **Interface** | CLI/Console | Tkinter GUI |
| **Networks** | Single | Multiple (1-3) |
| **Resource Usage** | Minimal | Moderate |
| **Database** | Optional | Built-in SQLite |
| **Diagnostics** | Basic | Advanced (F8/F14) |
| **Web GUI** | No | Yes |
| **Setup** | CLI wizard | GUI settings |
| **Use Case** | End-user deployment | In-house testing |

## Troubleshooting

### No data received
- Check radio port: `ls /dev/tty*` (Linux) or Device Manager (Windows)
- Verify baud rate: 115200 for radio (SECONDARY mode)
- Check network channel matches your radios

### MQTT not connecting
- Verify broker address and credentials
- Check firewall allows port 8883 (TLS) or 1883 (plain)
- Test with `mosquitto_pub` command

### Permission denied (Linux)
```bash
# Add user to dialout group for serial port access
sudo usermod -a -G dialout $USER
# Logout and login again
```

## Support

For full-featured testing and diagnostics, use the main Control Center:
```bash
python launcher.py
# or
START_CONTROL_CENTER.bat
```
