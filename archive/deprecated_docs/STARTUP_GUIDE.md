# OI-7500 System Startup Guide

## Quick Start

Run the complete system with automatic recovery:

```powershell
.\start_full_system.ps1
```

**Default:** Runs for 15 hours with all components enabled.

## Options

```powershell
# Custom duration
.\start_full_system.ps1 -DurationHours 24

# Skip Meshtastic mesh networking
.\start_full_system.ps1 -SkipMeshtastic

# Skip WireFree radios (only Modbus)
.\start_full_system.ps1 -SkipRadios

# Skip Modbus (only radios)
.\start_full_system.ps1 -SkipModbus

# Combine options
.\start_full_system.ps1 -DurationHours 8 -SkipMeshtastic
```

## What It Does

The script will:

1. **Clean up** - Stops any existing Python/Mosquitto processes
2. **Start Mosquitto** - Local MQTT broker on port 1883
3. **Start Meshtastic Gateway** - Receives from roof node mesh → cloud MQTT
4. **Start Meshtastic Bridge** - Forwards localhost MQTT → Heltec V3 → mesh
5. **Start Main Pipeline** - Modbus RTU (COM10) → cloud MQTT
6. **Start Radio Monitors** - 3x WireFree radios (COM7, COM11, COM12) → localhost MQTT
7. **Monitor Health** - Checks every 30 seconds, auto-restarts crashed processes
8. **Status Updates** - Shows system status every 5 minutes
9. **Graceful Shutdown** - Stops all processes cleanly when done

## Improvements Over Previous Run

### Serial Port Recovery
- Automatic retry on serial port errors (up to 10 attempts)
- Reopens ports automatically if they disconnect
- 5-minute inactivity warnings

### Process Management
- Kills existing processes before starting to avoid port conflicts
- Retry logic with delays between attempts
- Health monitoring with automatic restart

### Logging
All output is captured in `logs/` directory:
- `Mosquitto-stdout.log` / `Mosquitto-stderr.log`
- `MeshtasticGateway-stdout.log` / `MeshtasticGateway-stderr.log`
- `MeshtasticBridge-stdout.log` / `MeshtasticBridge-stderr.log`
- `MainPipeline-stdout.log` / `MainPipeline-stderr.log`
- `Radio_COM7-stdout.log` / `Radio_COM7-stderr.log`
- `Radio_COM11-stdout.log` / `Radio_COM11-stderr.log`
- `Radio_COM12-stdout.log` / `Radio_COM12-stderr.log`

## System Architecture

```
OI-7500 Sensors
    ↓
┌─────────────────────┬─────────────────────┐
│                     │                     │
WireFree Radios       Modbus RTU            |
(COM7,11,12)          (COM10)               |
    ↓                     ↓                 |
Simple Monitors       Main Pipeline         |
    ↓                     ↓                 |
    └──→ localhost MQTT ←─┘                |
            ↓                               |
    Meshtastic Bridge                       |
    (Heltec V3 COM16)                       |
            ↓                               |
    LoRa Mesh Network                       |
    (Channel 1 - OI7500)                    |
            ↓                               |
    Meshtastic Gateway                      |
    (Roof Node WiFi)                        |
            ↓                               |
    Cloud MQTT (HiveMQ) ←───────────────────┘
            ↓
    Your Monitoring Apps
```

## Monitoring During Run

The script shows:
- ✓ Process status (running/stopped)
- Process IDs (PID)
- Uptime for each component
- Automatic restart attempts
- Time remaining

Press **Ctrl+C** to stop early (graceful shutdown).

## Troubleshooting

### "Serial port in use" errors
The script now kills existing processes first, but if you still see issues:
```powershell
Get-Process python* | Stop-Process -Force
Get-Process mosquitto | Stop-Process -Force
```

### No data from radios
- Check that sensors are powered on
- Verify they're on Network_25
- Look at `logs/Radio_COM*-stderr.log` for errors

### Meshtastic not connecting
- Verify devices with: `python verify_node.py COM16`
- Check roof node: `python verify_node.py 10.20.0.172` (will fail if you need TCP support)

### MQTT not publishing
- Check Mosquitto logs: `logs/Mosquitto-stdout.log`
- Verify cloud connection: Check HiveMQ dashboard

## After The Run

Check results:
```powershell
# View log summary
Get-ChildItem logs\*.log | Select-Object Name, Length, LastWriteTime

# Count packets from each radio
Select-String "✓" logs\Radio_COM7-stdout.log | Measure-Object
Select-String "✓" logs\Radio_COM11-stdout.log | Measure-Object
Select-String "✓" logs\Radio_COM12-stdout.log | Measure-Object

# Check for errors
Select-String "ERROR" logs\*.log
```

## Manual Components

If you need to run individual components:

```powershell
# Just the radio monitors
python simple_monitor.py --config simple_config_com7.json
python simple_monitor.py --config simple_config_com11.json
python simple_monitor.py --config simple_config_com12.json

# Just the pipeline
python -m pipeline.main

# Just the mesh system
mosquitto -v -p 1883
python meshtastic_gateway.py
python meshtastic_bridge.py
```
