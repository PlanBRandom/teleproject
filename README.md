# OI-7530/7010/7032 Modbus to MQTT Bridge

Complete Modbus-to-MQTT bridge for OI Analytical gas monitors with wireless sensor support via Laird radio modules.

## 🚀 Quick Install (Home Assistant Add-on)

**One-Click Installation:**

[![Add Repository to Home Assistant][repository-badge]][repository-url]

1. Click the button above to add the repository
2. Install "OI Gas Monitor Bridge" from the add-on store
3. Configure your settings (Modbus port, MQTT credentials)
4. Start the add-on

📖 **Detailed Instructions**: [ADDON_INSTALL.md](ADDON_INSTALL.md)

## Features

✨ **Multi-Platform Support**
- **Direct USB/RS485**: Run on any computer with RS485-to-USB converter
- **ESP32 + ESPHome**: Wireless monitoring via WiFi using ESP32-WROOM + MAX485
- **Arduino**: Portable monitoring with Arduino boards

🔄 **Robust Communication**
- Modbus RTU (serial) and TCP support
- Automatic retry and reconnection handling
- Configurable polling intervals
- Error tracking and recovery

🏠 **Home Assistant Integration**
- Automatic MQTT discovery
- Pre-built Lovelace dashboards
- Gas sensor monitoring with device classes
- Real-time telemetry data

📊 **Sensor Support**
- Up to 32 wireless gas sensor channels
- Wired sensor inputs
- Diagnostic registers (alarms, faults, status)
- Configuration registers (radio addresses)

## Hardware Requirements

### Option 1: Direct USB Connection
- OI-7530 or OI-7010 gas monitor
- RS485-to-USB converter
- Computer running Python 3.8+

### Option 2: ESP32 WiFi Bridge
- ESP32-WROOM development board
- MAX485 TTL-to-RS485 converter module
- 5V power supply
- Jumper wires

**Wiring (ESP32 + MAX485):**
```
ESP32          MAX485
GPIO17    ->   DI (Transmit)
GPIO16    ->   RO (Receive)
GPIO4     ->   DE and RE (Direction control)
5V        ->   VCC
GND       ->   GND

MAX485         OI-7530
A         ->   A/+ (Modbus)
B         ->   B/- (Modbus)
```

### Option 3: Arduino
- Arduino board with RS485 shield or MAX485 module
- Similar wiring to ESP32 (adjust pins)

## Quick Start

### 1. Installation

```powershell
# Clone or navigate to project
cd d:\oi-7500-pipeline

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configuration

Edit `config.yaml` to match your setup:

```yaml
modbus:
  type: rtu  # or 'tcp' for ESP32
  port: COM3  # Your RS485 port (Windows: COMx, Linux: /dev/ttyUSB0)
  baudrate: 9600
  slave_id: 1

mqtt:
  broker: localhost  # Your Home Assistant IP
  device_name: OI-7530 Gas Monitor
  device_id: oi7530_01
```

### 3. Run the Bridge

```powershell
# Direct execution
python -m pipeline.main

# With custom config
python -m pipeline.main -c config.yaml

# Verbose mode for debugging
python -m pipeline.main -v
```

### 4. Generate Home Assistant Dashboards

```powershell
python generate_channels.py
```

Import generated dashboards in Home Assistant:
- `configs/lovelace/dashboard.yaml` - Main overview
- `configs/lovelace/channels.yaml` - Detailed channel view

## ESP32 + ESPHome Deployment

### 1. Install ESPHome

```powershell
pip install esphome
```

### 2. Edit Configuration

1. Copy `config.esphome.yaml` to your ESPHome folder
2. Edit `secrets.yaml` with your WiFi credentials
3. Adjust GPIO pins if needed

### 3. Flash ESP32

```powershell
# First time (USB connected)
esphome run config.esphome.yaml

# Over-the-air updates (after first flash)
esphome run config.esphome.yaml --upload-port oi7530-bridge.local
```

### 4. Add to Home Assistant

The ESP32 will appear automatically in Home Assistant:
- Settings → Devices & Services → ESPHome

## Project Structure

```
oi-7500-pipeline/
├── pipeline/
│   ├── main.py              # Main application
│   ├── register.py          # Register map parser
│   ├── modbus_client.py     # Modbus RTU/TCP client
│   └── mqtt.py              # MQTT publisher with HA discovery
├── register_maps/
│   ├── 7500-RegMap.csv      # OI-7530 register definitions
│   └── 7500for python.csv   # Simplified register map
├── configs/
│   └── lovelace/            # Generated dashboards
├── test/                    # Unit tests
├── config.yaml              # Main configuration
├── config.esphome.yaml      # ESP32 configuration
├── secrets.yaml             # Credentials (don't commit!)
├── generate_channels.py     # Dashboard generator
└── requirements.txt         # Python dependencies
```

## Configuration Options

### Modbus Settings

```yaml
modbus:
  type: rtu              # Connection type: 'rtu' or 'tcp'
  port: COM3             # Serial port (RTU only)
  baudrate: 9600         # Serial baudrate
  parity: N              # Parity: N, E, O
  host: 192.168.1.100    # IP address (TCP only)
  tcp_port: 502          # TCP port
  slave_id: 1            # Modbus device address
  timeout: 3             # Timeout in seconds
  retries: 3             # Retry attempts
```

### MQTT Settings

```yaml
mqtt:
  broker: localhost              # MQTT broker address
  port: 1883                     # MQTT port
  username: null                 # Optional authentication
  password: null
  device_name: OI-7530 Gas Monitor
  device_id: oi7530_01          # Unique device identifier
  discovery_enabled: true        # Enable HA autodiscovery
```

### Polling Settings

```yaml
poll_interval: 5.0              # Seconds between polls
poll_sensor_readings: true      # Poll gas sensor data
poll_configuration: false       # Poll config registers
poll_diagnostics: true          # Poll status/alarms
```

## Register Map

The CSV register map defines all available modbus registers:

| Address | Description           | Type    | Units | Access |
|---------|-----------------------|---------|-------|--------|
| 0x01    | Channel 1 Radio Addr  | uint16  | -     | R/W    |
| 0x21    | Channel 1 Reading     | float32 | PPM   | R      |
| 0x23    | Channel 2 Reading     | float32 | PPM   | R      |
| ...     | ...                   | ...     | ...   | ...    |

See `register_maps/7500-RegMap.csv` for complete list.

## Development

### Testing

```powershell
# Run all tests
pytest

# Run specific test file
pytest test/test_modbus.py

# With coverage
pytest --cov=pipeline
```

### Testing Components Individually

```powershell
# Test register parser
python -m pipeline.register

# Test modbus client (requires device)
python -m pipeline.modbus_client

# Test MQTT publisher (requires broker)
python -m pipeline.mqtt
```

## Troubleshooting

### Cannot connect to COM port

- Check port name: `mode` (Windows) or `ls /dev/tty*` (Linux)
- Ensure no other application is using the port
- Verify RS485 wiring (A to A, B to B)
- Check modbus slave address in config

### MQTT not connecting

- Verify broker address and port
- Check firewall settings
- Test with `mosquitto_pub/sub` or MQTT Explorer
- Confirm credentials if authentication is enabled

### No data from sensors

- Verify modbus connection (check logs for errors)
- Confirm correct register addresses in CSV
- Check sensor calibration on OI-7530 device
- Verify wireless sensors are paired (for remote channels)

### ESP32 not connecting to WiFi

- Double-check WiFi credentials in `secrets.yaml`
- Ensure 2.4GHz WiFi (ESP32 doesn't support 5GHz)
- Check signal strength
- Look at serial monitor during boot: `esphome logs config.esphome.yaml`

## Use Cases

### Home Automation
- Real-time gas leak detection alerts
- Integration with ventilation systems
- Historical data logging and analysis
- Mobile notifications via Home Assistant

### Industrial Monitoring
- Multi-zone gas concentration tracking
- Compliance data collection
- Remote monitoring of hazardous areas
- Wireless sensor flexibility

### Laboratory
- Fume hood monitoring
- Chemical storage safety
- Clean room air quality
- Research data logging

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is provided as-is for educational and personal use.

## Hardware References

- **OI-7530**: 32-channel wireless gas monitor
- **OI-7010**: 64-channel wired/wireless gas monitor
- **MAX485**: RS485 transceiver module
- **ESP32-WROOM**: WiFi/Bluetooth microcontroller
- **Home Assistant**: Open-source home automation platform

## Resources

- [OI-7530 Documentation](https://www.otis-instruments.com/)
- [Modbus Protocol](https://modbus.org/)
- [ESPHome Documentation](https://esphome.io/)
- [Home Assistant](https://www.home-assistant.io/)
- [PyModbus](https://pymodbus.readthedocs.io/)
- [Paho MQTT](https://www.eclipse.org/paho/clients/python/)

## Support

For issues or questions:
- **Documentation**: See [ADDON_INSTALL.md](ADDON_INSTALL.md) for add-on installation
- **Issues**: https://github.com/PlanBRandom/teleproject/issues
- **Hardware Setup**: See hardware test scripts and documentation
- Review logs with `-v` verbose flag

## License

MIT License - See LICENSE file

[repository-badge]: https://img.shields.io/badge/Add%20Repository-41BDF5?logo=home-assistant&style=for-the-badge
[repository-url]: https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FPlanBRandom%2Fteleproject
- Open an issue with detailed error messages and configuration

---

**Built for telemetry data and gas sensor monitoring** 🛡️💨
