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
- **Laird Radio**: Direct wireless sensor monitoring via Laird WireFree modules

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
- Real-time WireFree Gen II packet decoding
- Battery level monitoring and alerts

🧠 **Machine Learning & Radio Intelligence**
- Real-time anomaly detection on radio sensor data
- Sensor health tracking (battery, signal, faults)
- Predictive maintenance scheduling
- Automatic fault alerting
- Historical data collection for ML training

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
│   ├── mqtt.py              # MQTT publisher with HA discovery
│   └── ml_analytics.py      # ML analytics and predictions
├── register_maps/
│   ├── 7500-RegMap.csv      # OI-7530 register definitions
│   └── 7500for python.csv   # Simplified register map
├── configs/
│   └── lovelace/            # Generated dashboards
├── ml_data/                 # ML training data storage
├── ml_reports/              # ML analysis reports
├── test/                    # Unit tests
├── test_data/               # Sample radio packets and test data
├── config.yaml              # Main configuration
├── config.esphome.yaml      # ESP32 configuration
├── secrets.yaml             # Credentials (don't commit!)
├── generate_channels.py     # Dashboard generator
├── train_ml_models.py       # ML training script
├── ml_live_monitor.py       # Real-time ML monitoring
├── decode_radio_packets.py  # Laird radio packet decoder
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

# Test ML analytics
python -m pipeline.ml_analytics
```

## 📡 Radio Monitoring with ML

### Live Radio + ML Analytics

Monitor wireless sensors with real-time ML analytics:

```powershell
# Start radio monitor with ML (recommended)
D:/oi-7500-pipeline/.venv/Scripts/python.exe radio_ml_monitor.py --port COM7

# Adjust anomaly sensitivity
D:/oi-7500-pipeline/.venv/Scripts/python.exe radio_ml_monitor.py --port COM7 --anomaly-sensitivity 2.5

# Custom low battery threshold
D:/oi-7500-pipeline/.venv/Scripts/python.exe radio_ml_monitor.py --port COM7 --low-battery-threshold 3.5

# Disable ML (raw monitoring only)
D:/oi-7500-pipeline/.venv/Scripts/python.exe radio_ml_monitor.py --port COM7 --disable-ml
```

**Features:**
- ✅ Decodes OI WireFree Gen II protocol packets
- ✅ Real-time anomaly detection
- ✅ Battery level monitoring
- ✅ Fault detection and alerting
- ✅ Automatic data collection for ML training
- ✅ Sensor health tracking

**Decoded Information:**
- Transmitter address/channel number
- Gas reading with units
- Gas type (H2S, CO, O2, etc.)
- Sensor type (EC, IR, PID, etc.)
- Operating mode (Normal, Calibration, etc.)
- Battery voltage
- Fault codes

### Packet Decoding (Advanced)

Low-level packet analysis:

```powershell
# Decode from captured hex file
D:/oi-7500-pipeline/.venv/Scripts/python.exe decode_radio_packets.py --file test_data/radio_packets_sample.txt

# Live decode from serial port
D:/oi-7500-pipeline/.venv/Scripts/python.exe decode_radio_packets.py --port COM7 --live

# Verbose output showing all fields
D:/oi-7500-pipeline/.venv/Scripts/python.exe decode_radio_packets.py --file test_data/radio_packets_sample.txt --verbose

# Export decoded data to JSON
D:/oi-7500-pipeline/.venv/Scripts/python.exe decode_radio_packets.py --file test_data/radio_packets_sample.txt --output decoded.json
```

**Protocol Details:**
- **Protocol 0**: Monitor control packets
- **Protocol 1**: Standard sensor data (most common)
  - Bytes 0-1: Transmitter address (channel)
  - Bytes 3-6: 32-bit float sensor reading
  - Byte 7: Sensor type and mode
  - Byte 8: Battery reading
  - Byte 9: Gas type and battery scale
  - Byte 10: Fault indicator
  - Byte 11: Checksum

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

## 🧠 Machine Learning & Predictive Analytics

### Features

**Sensor Degradation Prediction**
- Automatic drift detection and tracking
- Predictive maintenance scheduling
- Calculates days until calibration needed
- Confidence scoring for predictions

**Real-Time Anomaly Detection**
- Statistical anomaly detection (Z-score + IQR)
- Configurable sensitivity thresholds
- Automatic baseline learning
- Anomaly scoring and classification

**Response Time Analysis**
- Sensor performance monitoring
- Response time degradation detection
- Event correlation analysis

**Data Collection & Storage**
- Automatic sensor data archiving
- Efficient batch processing
- Historical data management
- JSON-based storage format

### Quick Start - ML Analytics

#### 1. Train Models on Historical Data

```powershell
# Run comprehensive analysis on 30 days of data
python train_ml_models.py --days 30 --export-report

# With custom sensitivity
python train_ml_models.py --days 90 --anomaly-sensitivity 2.5 --export-report

# Specify output location
python train_ml_models.py --days 60 --output ml_reports/ --export-report
```

#### 2. Real-Time ML Monitoring

```powershell
# Start live monitoring with ML
python ml_live_monitor.py --config config.yaml

# With verbose output
python ml_live_monitor.py --config config.yaml --verbose

# Custom anomaly detection
python ml_live_monitor.py --anomaly-sensitivity 2.0
```

#### 3. Analyze Specific Metrics

```python
from pipeline.ml_analytics import MLAnalyticsPipeline

# Initialize pipeline
pipeline = MLAnalyticsPipeline()

# Run comprehensive analysis
analysis = pipeline.run_analysis(days=30)

# Check maintenance predictions
for channel, prediction in analysis['maintenance_predictions'].items():
    if prediction.get('urgency') == 'critical':
        print(f"Channel {channel} needs immediate calibration!")
        print(f"Days remaining: {prediction['days_to_calibration']:.1f}")
```

### ML Configuration

Add to your `config.yaml`:

```yaml
ml:
  enabled: true
  storage_path: ml_data
  anomaly_detection:
    enabled: true
    sensitivity: 3.0        # Standard deviations for anomaly threshold
    window_size: 100        # Baseline calculation window
  
  maintenance_prediction:
    enabled: true
    drift_threshold: 0.1    # 10% drift triggers calibration alert
    analysis_interval: 24   # Hours between analyses
  
  batch_save_interval: 100  # Save data every N readings
```

### ML Output Reports

Training generates comprehensive reports:

```
ml_reports/
├── ml_analysis_report_20251219_143022.json  # Detailed JSON report
└── ml_summary_20251219_143022.txt           # Human-readable summary
```

**Report Contents:**
- Sensor drift rates and trends
- Days until calibration needed per channel
- Maintenance urgency levels (critical/high/medium/low)
- Response time analysis
- Anomaly detection baselines
- Statistical summaries

### Example ML Output

```
🔴 Channel 12: CRITICAL  | Days to cal:    3.2 | Drift: +0.0234/day
   → Immediate calibration required

🟠 Channel  5: HIGH      | Days to cal:   18.5 | Drift: +0.0089/day
   → Schedule calibration within 1 week

🟡 Channel  8: MEDIUM    | Days to cal:   67.3 | Drift: +0.0021/day
   → Plan calibration within 1 month

🟢 Channel  1: LOW       | Days to cal:  342.1 | Drift: +0.0003/day
   → Monitor - no immediate action needed
```

### Advanced ML Use Cases

**1. Predictive Maintenance Dashboard**
```python
# Generate maintenance schedule
analysis = pipeline.run_analysis(days=90)
critical_channels = [
    ch for ch, pred in analysis['maintenance_predictions'].items()
    if pred.get('urgency') in ['critical', 'high']
]
print(f"Channels requiring immediate attention: {critical_channels}")
```

**2. Automated Alerting**
```python
# Real-time anomaly monitoring
result = pipeline.process_reading(channel=5, value=12.3)
if result['anomaly']['is_anomaly']:
    send_alert(f"Anomaly on Channel 5: {result['anomaly']['reason']}")
```

**3. Trend Analysis**
```python
# Analyze drift patterns
from pipeline.ml_analytics import SensorDegradationPredictor

predictor = SensorDegradationPredictor()
drift_info = predictor.calculate_drift(df, channel=3)
print(f"Drift rate: {drift_info['drift_rate_per_day']:.4f} units/day")
```

### Data Storage Structure

ML data is stored in JSON batches:

```json
{
  "timestamp": "2025-12-19T14:30:22",
  "channel": 5,
  "value": 10.23,
  "metadata": {
    "temperature": 22.5,
    "humidity": 45.2
  }
}
```

## Use Cases

### Home Automation
- Real-time gas leak detection alerts
- Integration with ventilation systems
- Historical data logging and analysis
- Mobile notifications via Home Assistant
- **ML-powered predictive maintenance**
- **Anomaly detection for early leak warning**

### Industrial Monitoring
- Multi-zone gas concentration tracking
- Compliance data collection
- Remote monitoring of hazardous areas
- Wireless sensor flexibility
- **Predictive sensor calibration scheduling**
- **Automated drift detection and correction**
- **Performance trend analysis**

### Laboratory
- Fume hood monitoring
- Chemical storage safety
- Clean room air quality
- Research data logging
- **Sensor degradation tracking**
- **Response time analysis for QA**

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
