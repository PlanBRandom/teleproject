# OI-7500 Radio Monitoring System

Production-ready monitoring system for Otis Instruments OI-6000 series gas sensors using Laird RM024 radio receivers and Home Assistant integration.

## System Status

✅ **Protocol 1 Decoder**: 100% success rate  
✅ **Home Assistant Integration**: MQTT discovery working  
✅ **Active Sensors**: 10 sensors on Network 15  
✅ **Validation**: O2 sensor reading 20.9 ppm (atmospheric oxygen)

## Quick Start

```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies (if needed)
pip install -r requirements.txt

# 3. Configure settings
# Edit config.yaml with your MQTT broker details and COM ports

# 4. Run the monitor
python monitor.py
```

## Hardware Configuration

### Active Radio Receivers

- **COM7** (Network 15): Laird RM024 @ 115200 baud - Direct sensor packets
- **COM11** (Network 25): Laird RM024 @ 115200 baud - Repeater packets  
- **COM12** (Network 20): Laird RM024 @ 115200 baud - Direct sensor packets

### Active Sensors (Network 15)

| Channel | Gas Type | Battery | Status |
|---------|----------|---------|--------|
| Ch002   | H2S      | 21.0V   | ✅     |
| Ch003   | H2S      | 3.4V    | ✅     |
| Ch005   | CO       | 3.6V    | ✅     |
| Ch010   | H2S      | 11.0V   | ✅     |
| Ch012   | LEL (NH3)| 11.0V   | ✅     |
| Ch020   | VOC (Cl2)| 3.9V    | ✅     |
| Ch022   | LEL (NH3)| 3.9V    | ✅     |
| Ch023   | LEL (NH3)| 3.9V    | ✅     |
| Ch033   | H2S      | 22.0V   | ✅     |
| Ch255   | O2       | 23.0V   | ✅     |

## Configuration

### config.yaml

```yaml
mqtt:
  host: "mqtt.example.com"
  port: 1883
  username: "user"
  password: "password"

radios:
  network15:
    port: "COM7"
    baudrate: 115200
    network_id: 15
  
  network25:
    port: "COM11"
    baudrate: 115200
    network_id: 25
```

## Repository Structure

```
oi-7500-pipeline/
├── monitor.py              # Main production script ⭐
├── config.yaml             # Configuration
├── requirements.txt        # Python dependencies
│
├── pipeline/               # Core library
│   ├── radio_receiver.py  # Protocol 1 decoder (100% working)
│   ├── mqtt.py             # MQTT client
│   └── register.py         # Modbus registers
│
├── tools/                  # Utility scripts
│   ├── configure_radio.py  # Radio configuration
│   ├── decode_packet.py    # Packet decoder
│   ├── manual_decode.py    # Interactive analysis
│   └── hardware_test.py    # Connection testing
│
├── reference/              # Documentation
│   ├── protocol/           # Protocol specifications
│   └── hardware/           # Hardware documentation
│
├── configs/                # HA dashboard configs
│   └── lovelace/          # Dashboard YAML files
│
├── logs/                   # Log files
├── test/                   # Unit tests
└── archive/                # Old/test files (150+ archived)
```

## 🔧 Features

### Monitoring
✅ 3-network simultaneous monitoring (COM7, COM11, COM12)  
✅ Complete WireFree Protocol 1 decoding (8 fields)  
✅ MQTT publishing with TLS  
✅ Real-time console display  
✅ Automatic packet database logging  

### Diagnostics
✅ Radio configuration verification (SECONDARY mode check)  
✅ F8 duplicate address detection  
✅ F14 primary timeout tracking  
✅ Channel packet history  
✅ Network health metrics  
✅ Raw packet hex viewing  
✅ CSV export for analysis  

### Database
✅ SQLite storage for all packets  
✅ Automatic fault event tracking  
✅ Network statistics  
✅ RSSI tracking  
✅ Query by channel, network, time range  

## ⚙️ Hardware Configuration

**3-Network Repeater Topology:**
```
Network_15:  COM7  @ 115200 baud → OI-7530 (Modbus slave 30)
Network_20:  COM12 @ 115200 baud → OI-7010 (Modbus slave 10)
Network_25:  COM11 @ 115200 baud → OI-7032 (Modbus slave 32)
```

All radios are **Laird RM024** modules in **SECONDARY** (receive-only) mode.

## 📊 Protocol Details

**WireFree Protocol 1 (0x81 packets):**
| Field | Bytes | Description |
|-------|-------|-------------|
| Channel | 8 | Channel number (1-255) |
| Reading | 10-13 | IEEE 754 float sensor value |
| Gas Type | 16 (bits 0-6) | O2, LEL, H2S, CO, SO2, etc. |
| Sensor Mode | 14 (bits 0-2) | Normal/Null/Calibration |
| Sensor Type | 14 (bits 3-7) | EC/IR/CB/MOS/PID |
| Battery | 15 + scale | 3.5V-23V range |
| Fault Code | 17 (bits 0-3) | F0-F15 |
| Precision | 17 (bits 4-6) | 0-7 decimal places |

## 🚨 Fault Codes (Official Oldham)

```
F0:  None
F1:  Top card lost comm with digital sensor board
F2:  No longer assigned (update firmware)
F3:  Low Power IR sensor beyond repair (must replace)
F4:  ADC/analog sensor board comm issue
F5:  Unit did not Null correctly
F6:  Unit did not Cal correctly (Autocal)
F7:  Internal fault (update firmware)
F8:  Two sensors with same address ⚠️ [DIAGNOSTIC TOOL AVAILABLE]
F9:  Radio timeout (no comm from sensor)
F10: Wired sensor not communicating
F11: Low Power IR temp changing too quickly (auto-clears)
F12: Low Power IR element restarting (auto-clears)
F13: 4-20mA fault condition (check sensor)
F14: Cannot see Primary Monitor (radio) ⚠️ [DIAGNOSTIC TOOL AVAILABLE]
F15: No longer assigned (update firmware)
```

## 🎯 Usage Examples

### Basic Monitoring

**Via GUI:**
```bash
python launcher.py
# → Monitoring tab → Set duration → Start Monitoring
```

**Via Command Line:**
```bash
# Monitor for 1 hour with MQTT
python monitoring/monitor_multi_network.py 1 \
  --mqtt-broker a1bcc059f5f74a6d8271e8b567fecc6d.s1.eu.hivemq.cloud \
  --mqtt-port 8883 \
  --mqtt-username laird \
  --mqtt-password LairdRM024 \
  --mqtt-use-tls
```

### Troubleshooting F8 Faults

F8 = Two sensors with same address (common in repeater networks)

```bash
# Find duplicate addresses
python diagnostics/packet_diagnostics.py --f8

# Example output:
# Transmitter Address 42 used by channels: 5, 12
# Fix: Change one sensor's address using OI-7010 diagnostic commands
```

### Troubleshooting F14 Faults

F14 = Sensor cannot see Primary Monitor (timeout issues)

```bash
# Track F14 occurrences
python diagnostics/packet_diagnostics.py --f14 --hours 24

# Check specific network health
python diagnostics/packet_diagnostics.py --network Network_25 --hours 1
```

### Channel History Analysis

```bash
# View last 100 packets for Channel 16
python diagnostics/packet_diagnostics.py --channel 16 --limit 100
```

### Export Data for Analysis

```bash
# Export last 24 hours to CSV
python diagnostics/packet_diagnostics.py --export packets.csv --hours 24
# Open in Excel/Python for detailed analysis
```

## 🔐 Safety - Radio Configuration

### CRITICAL: Verify Radios Are SECONDARY

Your monitoring radios **MUST** be in SECONDARY (receive-only) mode:
- ✅ **ATSP=00** (SECONDARY) - Safe, receive-only, 115200 baud
- ❌ **ATSP=01** (PRIMARY) - UNSAFE, will transmit and interfere!

**Check radios before monitoring:**
```bash
python diagnostics/verify_radio_config.py
```

**If any radios are PRIMARY, fix immediately:**
```bash
python diagnostics/fix_radio_secondary.py COM7
```

### Why This Matters

Your radios at **115200 baud** are configured for high-speed monitoring. If accidentally set to PRIMARY mode, they will transmit and:
- Cause F8 faults (duplicate address conflicts)
- Interfere with sensor-to-monitor communication
- Disrupt the entire sensor network

The 115200 baud configuration itself is strong evidence they're SECONDARY (primaries use 9600 baud to match sensor transmit rate).

## 📖 MQTT Data Format

Published to: `oi7500/<network>/<channel>`

```json
{
  "channel": 16,
  "reading": 21.9,
  "gas_type": "O2",
  "gas_type_code": 2,
  "battery_voltage": 3.6,
  "fault_code": 0,
  "fault": "None",
  "precision": 2,
  "sensor_mode": 0,
  "sensor_type": 0,
  "network": "Network_25",
  "timestamp": "2026-01-08T13:18:15.212861"
}
```

## 🛠️ Configuration

Edit [config.json](config.json) for your setup:

```json
{
  "mqtt": {
    "broker": "your-broker.hivemq.cloud",
    "port": 8883,
    "username": "your-username",
    "password": "your-password",
    "use_tls": true
  },
  "monitoring": {
    "duration_hours": 1.0,
    "networks": ["Network_15", "Network_20", "Network_25"]
  }
}
```

## 🔄 Typical Workflow

### Daily Operations
1. **Launch Control Center:**  
   ```bash
   python launcher.py
   ```

2. **Verify Radios** (first time or after changes):  
   Diagnostics tab → "✓ Verify Radio Config"

3. **Start Monitoring:**  
   Monitoring tab → Set duration → "▶ Start Monitoring"

4. **View Data:**  
   - MQTT Stream: Click "📊 View MQTT Stream"  
   - Database: Database tab → "🔄 Refresh"  
   - Web GUI: System tab → "🌐 Open Web GUI"

### When Faults Occur

1. **Run Diagnostics:**  
   Diagnostics tab → Select appropriate query:
   - F8: "🔍 Find F8 Duplicates"
   - F14: "🔍 Track F14 Timeouts"
   - Channel-specific: Enter channel → "View Channel History"

2. **Export for Analysis:**  
   Database tab → Set hours → "📤 Export to CSV"

3. **View Raw Packets** (if needed):  
   ```bash
   python diagnostics/packet_diagnostics.py --raw --network Network_25 --limit 10
   ```

## 🐛 Troubleshooting

### No Data from Radios
- Check COM ports available (close other programs)
- Verify baud rate (115200)
- Ensure RTS/CTS flow control enabled
- Radios powered on

### MQTT Connection Issues
- Check broker URL in config.json
- Verify port 8883 (TLS) or 1883 (non-TLS)
- Confirm username/password
- Check firewall settings

### F8 Faults (Duplicate Address)
```bash
python diagnostics/packet_diagnostics.py --f8
# Shows which channels share the same address
# Use OI-7010 diagnostic commands to change sensor addresses
```

### F14 Faults (Primary Timeout)
```bash
python diagnostics/packet_diagnostics.py --f14 --hours 24
# Check: RSSI, repeater status, network ID matches
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test
pytest test/test_fault_tracking.py

# With coverage
pytest --cov=pipeline
```

## 📚 Additional Documentation

- **Installation Guide**: [INSTALL.md](docs/INSTALL.md) _(if exists)_
- **Protocol Documentation**: See WireFree Protocol Generation II documentation
- **Fault Code Reference**: Official Oldham fault codes (F0-F15) with solutions
- **Old README**: [README_OLD.md](README_OLD.md) - Original comprehensive documentation

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

Internal tool for OI-7500 monitoring system.

## 🎯 Quick Command Reference

| Task | Command |
|------|---------|
| Launch GUI | `python launcher.py` |
| Start monitoring | Monitoring tab → Start |
| Check radios | `python diagnostics/verify_radio_config.py` |
| Find F8 duplicates | `python diagnostics/packet_diagnostics.py --f8` |
| Track F14 timeouts | `python diagnostics/packet_diagnostics.py --f14` |
| Export data | Database tab → Export to CSV |
| View logs | System tab → View Logs |

---

**Version:** 1.0  
**Last Updated:** January 2026  
**Status:** Production Ready ✅
