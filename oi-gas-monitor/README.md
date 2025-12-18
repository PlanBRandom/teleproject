# OI Gas Monitor Home Assistant Add-on

Complete monitoring solution for OI-7530, OI-7010, and OI-7032 gas monitors.

## Features

- ✅ Modbus RTU/TCP support
- ✅ Direct wireless radio module support
- ✅ Home Assistant MQTT auto-discovery
- ✅ Multi-device support
- ✅ Real-time gas readings
- ✅ Battery monitoring
- ✅ Fault detection
- ✅ Maintenance tracking (null/cal timing on 7010/7032)

## Installation

### Method 1: Local Add-on (Development)

1. Copy the entire `oi-gas-monitor` folder to your Home Assistant:
```bash
# From your Windows machine
scp -r /path/to/oi-gas-monitor root@homeassistant.local:/addons/
```

2. In Home Assistant:
- Go to **Settings** → **Add-ons** → **Add-on Store**
- Click menu (⋮) → **Repositories**
- Add: `file:///addons/oi-gas-monitor`
- Install "OI Gas Monitor Bridge"

### Method 2: GitHub Repository (Recommended)

1. Create a GitHub repository with this structure:
```
your-repo/
├── oi-gas-monitor/
│   ├── config.yaml
│   ├── Dockerfile
│   ├── run.sh
│   └── pipeline/
│       └── (all Python files)
└── repository.yaml
```

2. In Home Assistant:
- Settings → Add-ons → Add-on Store → Menu → Repositories
- Add your GitHub URL: `https://github.com/yourusername/your-repo`

## Configuration

### RS485 Modbus Only (What you have now)

```yaml
connection_mode: modbus_rtu
modbus:
  port: /dev/ttyUSB0
  baudrate: 9600
radio:
  enabled: false
devices:
  - slave_id: 1
    name: "Gas Monitor 1"
    model: "7530"
  - slave_id: 2
    name: "Gas Monitor 2"
    model: "7530"
mqtt:
  broker: core-mosquitto
  port: 1883
  username: ""
  password: ""
poll_interval: 30
```

### Direct Radio Module

```yaml
connection_mode: radio_direct
modbus:
  port: /dev/ttyUSB0
  baudrate: 9600
radio:
  enabled: true
  port: /dev/ttyUSB1
  baudrate: 9600
  protocol: oi_wireless
devices:
  - slave_id: 1
    name: "Monitor with Radio"
    model: "7530"
    radio_channels: [1, 5, 7, 16, 21, 32]
mqtt:
  broker: core-mosquitto
  port: 1883
```

### Hybrid (Modbus + Radio)

```yaml
connection_mode: hybrid
modbus:
  port: /dev/ttyUSB0
  baudrate: 9600
radio:
  enabled: true
  port: /dev/ttyUSB1
  baudrate: 9600
devices:
  - slave_id: 1
    name: "Monitor 1"
    model: "7530"
  - slave_id: 2
    name: "Monitor 2"
    model: "7532"
```

## Hardware Connections

### Current Setup (RS485 Modbus)
```
Home Assistant Server
    └─ USB-RS485 Adapter (/dev/ttyUSB0)
        ├─ A/B+ to OI-7530 #1 (Slave 1)
        └─ A/B+ to OI-7530 #2 (Slave 2)
```

### With Direct Radio Module
```
Home Assistant Server
    ├─ USB-RS485 (/dev/ttyUSB0)
    │   └─ Monitors via Modbus
    └─ OI Radio Module (/dev/ttyUSB1)
        └─ Wireless sensors directly
```

### ESP32/Arduino Bridge
```
Home Assistant (MQTT Broker)
    ↑ WiFi/Network
ESP32 with MAX485
    ├─ RS485 to monitors
    └─ Serial to radio module
```

## Radio Module Protocol

**Important:** The radio receiver code is a template. The actual OI wireless protocol needs to be determined by:

1. **Capturing radio data:**
```bash
# Connect radio module and capture raw data
cat /dev/ttyUSB1 | xxd > radio_dump.txt
```

2. **Reverse engineering:**
- Analyze message structure
- Identify start/end markers
- Determine data format
- Calculate checksums

3. **Update `pipeline/radio_receiver.py`** with actual protocol

### Known OI Radio Details
- Frequency: Check your radio module specs
- Typical formats: Fixed-length frames or delimited packets
- Common markers: 0xAA, 0xFF, or custom sequences

## ESP32/Arduino Support

Want to run this on ESP32 or Arduino? See:
- [arduino_sketch/oi7530_modbus_mqtt/](../arduino_sketch/) - Arduino/ESP32 version
- Uses same Modbus library
- Connects via WiFi to HA MQTT broker

## Entities Created in Home Assistant

For each channel:
- **Sensor**: `sensor.monitor1_ch1_reading` (PPM, %, etc.)
- **Sensor**: `sensor.monitor1_ch1_battery` (Volts)
- **Binary Sensor**: `binary_sensor.monitor1_ch1_fault` (Fault status)
- **Sensor**: `sensor.monitor1_ch1_mode` (Operating mode)
- **Sensor**: `sensor.monitor1_ch1_gas_type` (H2S, CO, O2, etc.)

For OI-7010/7032 only:
- **Sensor**: `sensor.monitor1_ch1_days_since_null`
- **Sensor**: `sensor.monitor1_ch1_days_since_cal`

## Troubleshooting

### Can't find USB device
```bash
# SSH to Home Assistant
ha > login
# Find serial devices
ls -l /dev/ttyUSB* /dev/ttyAMA* /dev/serial/by-id/*
dmesg | grep tty
```

### No MQTT messages
- Check MQTT integration is installed
- Verify broker settings
- Check add-on logs: Settings → Add-ons → OI Gas Monitor → Logs

### Modbus timeouts
- Verify baud rate (9600 for OI monitors)
- Check RS485 A/B wiring
- Confirm slave addresses are correct
- Try increasing poll_interval

### Radio not receiving
- Verify radio module is powered
- Check antenna connection
- Confirm baud rate
- Enable debug logging to see raw data

## Development

Test locally before deploying:
```bash
# On your Windows machine
cd d:\oi-7500-pipeline
python pipeline/main.py

# Test radio receiver
python pipeline/radio_receiver.py
```

## Next Steps

1. **Deploy add-on to HA**
2. **Configure your 2 OI-7530s**
3. **Test Modbus connection**
4. **Add radio module if available**
5. **Create HA dashboards**

## Support

- Check logs in Settings → Add-ons → OI Gas Monitor → Logs
- Review [CONTROL_CAPABILITIES.md](../CONTROL_CAPABILITIES.md) for full API
- Test scripts in repository for debugging
