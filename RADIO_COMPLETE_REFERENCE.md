# OI Radio Implementation - Complete Reference

## Quick Start

```bash
# Test radio reception
cd d:\oi-7500-pipeline
.venv\Scripts\activate
python example_laird_monitor.py
```

## Files Overview

| File | Purpose |
|------|---------|
| `pipeline/radio_receiver.py` | Core radio protocol implementation |
| `RADIO_PROTOCOL.md` | Complete protocol specification |
| `LAIRD_RADIO_SETUP.md` | Hardware setup and configuration |
| `example_laird_monitor.py` | RSSI/MAC monitoring example |
| `test_radio_protocol.py` | Protocol parsing test suite |
| `reference_docs/` | OI source code and protocol docs |

## Radio Modules

### Laird LT1110 (Primary - 900 MHz)
- **Model**: 1110LT200UPLG01
- **Frequency**: 900 MHz ISM band
- **Range**: 2 miles line-of-sight
- **Power**: 100 mW (+20 dBm)
- **Sensitivity**: -110 dBm
- **Baud**: 9600 (OI default)
- **Best For**: Long range, outdoor, penetrating obstacles

### Laird RM024 (Alternative - 2.4 GHz)
- **Model**: 2510LT100UPLG01
- **Frequency**: 2.4 GHz ISM band
- **Range**: 1 mile line-of-sight
- **Power**: 2.5 mW (+4 dBm)
- **Sensitivity**: -95 dBm
- **Baud**: 9600 (OI default)
- **Best For**: Indoor, less interference, cleaner spectrum

## Protocol Stack

```
┌─────────────────────────────────────┐
│   Home Assistant / MQTT Broker      │
├─────────────────────────────────────┤
│   Python Radio Receiver             │
│   - Protocol parsing                │
│   - RSSI/MAC extraction             │
│   - Callback system                 │
├─────────────────────────────────────┤
│   Serial Interface (9600 baud)      │
├─────────────────────────────────────┤
│   Laird Radio Module                │
│   - API Mode (0x7E frames)          │
│   - Network CH 5, System ID 37      │
├─────────────────────────────────────┤
│   OI Gen II Wireless Protocol       │
│   - Protocol 1: Full sensor data    │
│   - Protocol 2: Gas alerts          │
│   - Protocol 7: Maintenance         │
├─────────────────────────────────────┤
│   OI Wireless Sensors (1-255)       │
└─────────────────────────────────────┘
```

## Network Architecture

### Single Monitor
```
Sensors (1-32) ──► Laird Radio ──► Monitor (Primary)
                   CH 5, SID 37
```

### Multi-Monitor
```
                   ┌──► Monitor (Primary, Server)
Sensors (1-32) ──► │
                   ├──► Monitor (Secondary, Sniff)
                   └──► Monitor (Secondary, Sniff)
```

### Direct Radio (HA Add-on)
```
                   ┌──► Monitor (Primary, Server)
Sensors (1-32) ──► │
                   └──► HA Radio (Sniff, API Mode)
                        └──► MQTT Broker
                             └──► Home Assistant
```

### Repeater System
```
Sensors ──► Client Radio ──► ESP32 ──► Server Radio ──► Monitor
            CH 5               Repeater      CH 6
```

## Configuration Examples

### Python Receiver (API Mode)
```python
from pipeline.radio_receiver import RadioReceiver

receiver = RadioReceiver("COM5", baudrate=9600, api_mode=True)
receiver.connect()

# Get radio info
mac = receiver.get_mac_address()
rssi = receiver.get_rssi()
print(f"MAC: {mac}, RSSI: {rssi} dBm")

# Set channel
receiver.set_rf_channel(5)

# Start receiving
receiver.register_callback(lambda msg: print(f"Ch{msg.channel}: {msg.reading}"))
receiver.start()
```

### ESP32 Direct Connection
```cpp
#include <HardwareSerial.h>

HardwareSerial RadioSerial(1);

void setup() {
    // Laird LT1110 on GPIO16(RX), GPIO17(TX)
    RadioSerial.begin(9600, SERIAL_8N1, 16, 17);
}

void loop() {
    if (RadioSerial.available()) {
        uint8_t byte = RadioSerial.read();
        // Process 0x7E frames or raw Gen2 packets
    }
}
```

### Home Assistant Add-on
```yaml
# config.yaml
connection_mode: "radio_direct"
radio_port: "/dev/ttyUSB0"
radio_baudrate: 9600
radio_api_mode: true
network_channel: 5
system_id: 37

mqtt_broker: "192.168.1.100"
mqtt_topic_prefix: "oi/sensor"
```

## Packet Formats

### Protocol 1 (Full Data)
```
00 05 01 3F 80 00 00 00 24 00 04 XX
│  │  │  └─ Reading (float32)
│  │  └─ Protocol 1
│  └─ Address LSB (5)
└─ Address MSB (0)
```

### Protocol 2 (Gas Alert)
```
00 05 02 40 20 00 00 XX
│  │  │  └─ Reading (float32)
│  │  └─ Protocol 2
│  └─ Address LSB
└─ Address MSB
```

### XBee/Laird API Frame
```
7E 00 10 90 ... GEN2_PACKET ... XX
│  └─ Length   └─ Frame data   └─ Checksum
└─ Start delimiter
```

## Command Reference

### Laird Binary Commands

| Command | Description | Response |
|---------|-------------|----------|
| `0xCC 0x22` | Get RSSI | `0xCC <rssi_raw>` |
| `0xCC 0x10` | Get MAC | `0xCC <mac1> <mac2> <mac3>` |
| `0xCC 0xC1 0x40 0x01 <ch>` | Set RF Channel | None |
| `0xCC 0xC0 0x54 0x01` | Get RF Profile | `0xCC XX XX <profile>` |

### RSSI Calculation
```python
if rssi_raw >= 128:
    rssi_dbm = ((rssi_raw - 256) / 2) - 71
else:
    rssi_dbm = (rssi_raw / 2) - 71
```

### Laird AT Commands

| Command | Description |
|---------|-------------|
| `+++` | Enter command mode |
| `ATAP1` | Enable API mode |
| `ATAP0` | Transparent mode |
| `ATDN5` | Set network channel 5 |
| `ATSY37` | Set system ID 37 |
| `ATBD3` | Set baud 9600 |
| `ATCE1` | Server mode (Primary) |
| `ATCE0` | Client mode (Secondary) |
| `ATSP1` | Sniff Permit (listen only) |
| `ATWR` | Write to EEPROM |
| `ATCN` | Exit command mode |
| `ATS` | Show all settings |

## Signal Strength Interpretation

| RSSI (dBm) | Quality | Distance | Notes |
|------------|---------|----------|-------|
| -30 to -60 | Excellent | < 100 ft | Very close |
| -60 to -70 | Very Good | 100-500 ft | Normal indoor |
| -70 to -85 | Good | 500-1500 ft | Acceptable |
| -85 to -95 | Fair | 1500-3000 ft | Near limit |
| -95 to -110 | Poor | > 3000 ft | Unreliable |
| < -110 | No Signal | N/A | Out of range |

## Troubleshooting

### No Data Received
1. Check power: 3.3V or 5V depending on module
2. Verify serial TX/RX not swapped
3. Confirm baud rate: 9600
4. Check network: `ATDN` should be 5, `ATSY` should be 37
5. Verify API mode: `ATAP` should be 1
6. Check sensors transmitting (monitor shows radio icon)

### Weak Signal
1. **LT1110**: Check antenna connection (SMA)
2. **RM024**: Avoid WiFi interference
3. Move radio closer to sensors
4. Add external antenna
5. Use repeater for range extension

### Checksum Errors
1. Electrical noise: Add ferrite bead
2. Wrong mode: Verify `ATAP1` for API mode
3. Baud mismatch: Check both sides are 9600

### Intermittent Reception
1. Check RSSI: Should be > -95 dBm
2. Move obstacles between sensor and radio
3. Check for interference sources
4. Verify sensor battery voltage (> 3.0V)

## Testing Checklist

- [ ] Radio module powered (3.3V or 5V)
- [ ] Serial connection correct (TX↔RX, GND connected)
- [ ] Baud rate 9600
- [ ] API mode enabled (`ATAP1`)
- [ ] Network channel 5 (`ATDN5`)
- [ ] System ID 37 (`ATSY37`)
- [ ] Sensors transmitting (monitor shows radio icon)
- [ ] Python test script runs: `python example_laird_monitor.py`
- [ ] RSSI readable: `receiver.get_rssi()`
- [ ] MAC readable: `receiver.get_mac_address()`
- [ ] Packets received and parsed
- [ ] MQTT publishing (if using HA add-on)

## Performance Optimization

### For Best Range
- Use Laird LT1110 (900 MHz)
- External antenna on SMA
- Elevate radio above obstacles
- Network channel 5 (least interference)

### For Best Reliability
- Use Laird RM024 (2.4 GHz) in clean spectrum
- Keep RSSI > -85 dBm
- Enable Sniff Permit for monitoring
- Monitor watchdog timeout (3 seconds)

### For Low Power
- Transparent mode (less processing)
- Reduce transmission frequency if possible
- Use Protocol 2 for alerts (8 bytes vs 12)

## Development Resources

### Source Code
- `D:\Downloads\oi-6950-main\src\laird.c` - Laird radio driver
- `D:\Downloads\oi-6950-main\3609850_laird_repeater.c` - Repeater code
- `reference_docs/radio.c` - Radio UART functions
- `reference_docs/WireFree_Prot_GenII_W_Text.txt` - Protocol spec

### Documentation
- `RADIO_PROTOCOL.md` - Complete protocol reference
- `LAIRD_RADIO_SETUP.md` - Hardware setup guide
- `CONTROL_CAPABILITIES.md` - Modbus control API

### Test Tools
- `test_radio_protocol.py` - Protocol parsing tests
- `example_laird_monitor.py` - Live monitoring
- `pipeline/radio_receiver.py` - Main implementation

## Support Matrix

| Feature | LT1110 | RM024 | XBee |
|---------|--------|-------|------|
| API Mode | ✓ | ✓ | ✓ |
| Transparent | ✓ | ✓ | ✓ |
| RSSI Query | ✓ | ✓ | ✗ |
| MAC Query | ✓ | ✓ | ✗ |
| RF Channel | ✓ | ✓ | ✓ |
| Sniff Permit | ✓ | ✓ | ✗ |
| 900 MHz | ✓ | ✗ | ✓ |
| 2.4 GHz | ✗ | ✓ | ✗ |

## Next Steps

1. **Test Reception**: `python example_laird_monitor.py`
2. **Verify Protocol**: `python test_radio_protocol.py`
3. **Deploy HA Add-on**: Install on Home Assistant server
4. **Configure MQTT**: Point to your broker
5. **Monitor Sensors**: Watch for Protocol 1/2/7 packets
6. **Check Signal**: Monitor RSSI, aim for > -85 dBm
7. **Add Repeaters**: If range insufficient

## FAQ

**Q: Which Laird module should I use?**
A: LT1110 (900 MHz) for outdoor/long range, RM024 (2.4 GHz) for indoor/clean spectrum.

**Q: Can I use XBee instead?**
A: Yes, but you lose RSSI/MAC query features. XBee-PRO XSC works in API mode.

**Q: Do I need a Primary Monitor?**
A: Sensors require a Primary Monitor for ACKs. Your direct radio can Sniff alongside it.

**Q: What's the maximum range?**
A: LT1110: 2 miles outdoor. RM024: 1 mile outdoor. Use repeaters to extend.

**Q: How often do sensors transmit?**
A: Every 60 seconds normally, every 5 seconds when gas detected.

**Q: Can I change the network channel?**
A: Yes, but must match sensors. Default is 5. Use `set_rf_channel()` or `ATDN` command.

**Q: What's System ID 37?**
A: OI-specific network identifier. All OI devices use 37. Do not change.

**Q: How do I know if it's working?**
A: Run `example_laird_monitor.py`, should see sensor packets every 60 seconds.
