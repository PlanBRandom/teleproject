# Project Overview

## OI-7530/7010 Modbus to MQTT Bridge

### Purpose
Convert gas sensor telemetry data from OI-7530 and OI-7010 industrial gas monitors into MQTT messages for Home Assistant integration and monitoring.

### Target Monitors
- **OI-7530**: 32-channel wireless gas monitoring system
- **OI-7010**: 64-channel wired/wireless gas monitoring system

Both support:
- Wired 4-20mA sensors
- Wireless sensors (900MHz radio)
- Modbus RTU/TCP communication

### Deployment Options

#### 1. **Native Python (Recommended for Development)**
- **Hardware**: Any computer + RS485-to-USB converter
- **Pros**: Full Python ecosystem, easy debugging, flexible
- **Cons**: Requires dedicated computer or always-on server
- **Use Case**: Development, testing, permanent home server installation

#### 2. **ESPHome on ESP32 (Recommended for Production)**
- **Hardware**: ESP32-WROOM + MAX485 module
- **Pros**: WiFi-enabled, low power, integrated with Home Assistant, OTA updates
- **Cons**: Limited to predefined sensors in YAML
- **Use Case**: Wireless remote monitoring, clean integration

#### 3. **Arduino (For Embedded/Portable)**
- **Hardware**: Arduino + Ethernet/WiFi shield + MAX485
- **Pros**: Standalone operation, portable, reliable
- **Cons**: Limited memory, manual MQTT implementation
- **Use Case**: Portable monitoring, offline data logging

### Key Features

✅ **Complete Modbus Support**
- CSV-based register map parsing
- RTU (serial) and TCP (ethernet) connections
- Automatic data type handling (uint16, uint32, float32)
- Robust error handling and retry logic

✅ **MQTT Publishing**
- Paho MQTT client with auto-reconnect
- Home Assistant autodiscovery
- Configurable topics and QoS
- Device availability tracking

✅ **Home Assistant Integration**
- Automatic sensor discovery
- Pre-built Lovelace dashboards
- Gas sensor device classes
- Diagnostic and configuration entities

✅ **Flexible Configuration**
- YAML-based configuration
- Multiple register categories (sensors, diagnostics, config)
- Adjustable polling intervals
- Selective register polling

### Architecture

```
┌─────────────────┐
│   OI-7530/7010  │
│  Gas Monitor    │
└────────┬────────┘
         │ RS485 Modbus
         │
    ┌────▼────────────────┐
    │  Hardware Bridge    │
    │  - RS485 Interface  │
    │  - Python/ESP32     │
    └────┬────────────────┘
         │ MQTT
         │
    ┌────▼────────────────┐
    │  MQTT Broker        │
    │  (Mosquitto)        │
    └────┬────────────────┘
         │
    ┌────▼────────────────┐
    │  Home Assistant     │
    │  - Dashboards       │
    │  - Automation       │
    │  - Alerts           │
    └─────────────────────┘
```

### Register Map

The register map CSV defines all modbus registers:

**Structure:**
- Address (hex and decimal)
- Description
- Access mode (R, W, R/W)
- Data type (16-bit, 32-bit, float)
- Units
- Valid ranges

**Categories:**
- **Radio Addresses** (0x01-0x20): Wireless sensor pairing
- **Sensor Readings** (0x21-0x61): Gas concentration values
- **Alarms/Status**: Fault detection and status flags
- **Configuration**: Device settings and parameters

### Data Flow

1. **Register Map Parsing**: Load CSV definitions
2. **Modbus Polling**: Read registers at configured interval
3. **Data Processing**: Convert raw values to floats/integers
4. **MQTT Publishing**: Send to broker with metadata
5. **HA Discovery**: Auto-create entities on first publish
6. **Dashboard Display**: Real-time visualization

### File Structure Explained

| File/Directory | Purpose |
|----------------|---------|
| `pipeline/` | Core Python modules |
| `├─ register.py` | Register map parser and definitions |
| `├─ modbus_client.py` | Modbus RTU/TCP communication |
| `├─ mqtt.py` | MQTT publisher with HA discovery |
| `└─ main.py` | Main application orchestration |
| `register_maps/` | CSV register definitions |
| `configs/lovelace/` | Generated HA dashboards |
| `arduino_sketch/` | Arduino implementation |
| `test/` | Unit tests |
| `config.yaml` | Main configuration file |
| `config.esphome.yaml` | ESP32 ESPHome configuration |
| `generate_channels.py` | Dashboard generator utility |
| `test_connection.py` | Connection testing tool |
| `start.ps1` | Quick start PowerShell script |

### Configuration Quick Reference

**Modbus RTU (USB/RS485):**
```yaml
modbus:
  type: rtu
  port: COM3  # or /dev/ttyUSB0
  baudrate: 9600
  slave_id: 1
```

**Modbus TCP (Ethernet/WiFi):**
```yaml
modbus:
  type: tcp
  host: 192.168.1.100
  tcp_port: 502
  slave_id: 1
```

**MQTT:**
```yaml
mqtt:
  broker: localhost
  device_name: OI-7530 Gas Monitor
  device_id: oi7530_01
  discovery_enabled: true
```

### Sensor Data Format

**MQTT Topic:**
```
homeassistant/sensor/oi7530_01/channel_1_reading/state
```

**Payload:**
```json
{
  "value": 42.5,
  "timestamp": "2025-12-17T09:30:00Z",
  "unit": "PPM",
  "address": 33
}
```

**HA Discovery:**
```json
{
  "name": "Channel 1 Reading",
  "unique_id": "oi7530_01_channel_1_reading",
  "state_topic": "homeassistant/sensor/oi7530_01/channel_1_reading/state",
  "value_template": "{{ value_json.value }}",
  "unit_of_measurement": "PPM",
  "device_class": "gas",
  "device": {
    "identifiers": ["oi7530_01"],
    "name": "OI-7530 Gas Monitor",
    "model": "OI-7530/7010",
    "manufacturer": "Otis Instruments"
  }
}
```

### Use Cases

#### Industrial Safety
- Real-time gas leak detection
- Multi-zone monitoring
- Compliance data logging
- Emergency shutdown integration

#### Home Automation
- Garage CO monitoring
- Natural gas leak detection
- Basement radon monitoring
- Air quality tracking

#### Laboratory
- Fume hood monitoring
- Chemical storage safety
- Clean room monitoring
- Research data collection

### Performance

**Polling Rate:**
- Recommended: 5-10 seconds per cycle
- Minimum: 1 second (limited by Modbus timing)
- Maximum sensors: 32 channels (OI-7530) or 64 (OI-7010)

**Network:**
- MQTT: ~200 bytes per sensor update
- Modbus: ~8 bytes per 16-bit register read
- Typical bandwidth: <5 KB/s for 32 channels @ 5s interval

**Resources:**
- Python: ~50 MB RAM
- ESP32: ~100 KB RAM, <1% CPU
- Arduino: ~2 KB RAM (basic sketch)

### Security Considerations

⚠️ **Important:**
- Use `secrets.yaml` for credentials (not in git)
- Enable MQTT authentication
- Use WiFi WPA2/WPA3 encryption
- Consider VPN for remote access
- Implement firewall rules

### Troubleshooting Reference

| Issue | Solution |
|-------|----------|
| COM port access denied | Close other applications using port |
| Modbus timeout | Check wiring, slave ID, baudrate |
| MQTT not connecting | Verify broker IP, check credentials |
| No sensor values | Confirm sensors paired to OI-7530 |
| ESP32 won't flash | Hold BOOT button during upload |
| HA entities not appearing | Check discovery prefix, restart HA |

### Future Enhancements

Potential additions:
- [ ] Web-based configuration interface
- [ ] Historical data storage (InfluxDB)
- [ ] Alarm threshold configuration
- [ ] Multi-device support (multiple monitors)
- [ ] Grafana dashboards
- [ ] Email/SMS alerts
- [ ] Data export (CSV, JSON)
- [ ] OI-7010 specific register map

### Resources

- **Modbus Protocol**: [modbus.org](https://modbus.org)
- **OI-7530 Manual**: Check manufacturer website
- **Home Assistant**: [home-assistant.io](https://www.home-assistant.io)
- **ESPHome**: [esphome.io](https://esphome.io)
- **PyModbus**: [pymodbus.readthedocs.io](https://pymodbus.readthedocs.io)

---

**Project Status**: ✅ Fully Functional  
**Last Updated**: December 2025  
**Python Version**: 3.8+  
**License**: Open Source (Educational/Personal Use)
