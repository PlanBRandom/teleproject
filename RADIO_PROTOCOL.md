# OI Gen II Wireless Protocol Implementation

## Overview

This implementation provides direct support for OI (Otis Instruments) Generation II WireFree wireless sensors. It can receive sensor data directly from OI radio modules (XBee, Laird, Digi) without requiring connection to a monitor's Modbus interface.

## Protocol Reference

Based on OI-6950 source code (radio.c, laird.c, digi.c) and "WireFree Generation 2 Protocol" specification document.

## Radio Module Modes

### API Mode (XBee/Laird/Digi)
- **Frame Structure**: `[0x7E][LenH][LenL][FrameType][Data...][Checksum]`
- **Start Delimiter**: `0x7E`
- **Length**: 16-bit big-endian (payload + frame type + addressing)
- **Checksum**: `0xFF - sum(frame_data) & 0xFF`
- **Gen2 Packet**: Embedded within the RF data section of the frame
- **Usage**: Set `api_mode=True` when creating `RadioReceiver`

### Transparent Mode (Direct)
- **Frame Structure**: Raw Gen2 packets
- **No Framing**: Packets start immediately with sensor address
- **Usage**: Set `api_mode=False` when creating `RadioReceiver`

## Gen2 Protocol Packets

All Gen2 packets have the following common structure:
- **Byte 0-1**: Transmitter address (16-bit MSB first, range 1-255)
- **Byte 2**: Protocol number (1, 2, or 7)
- **Remaining**: Protocol-specific data
- **Last Byte**: Checksum (`sum(all_bytes_except_checksum) & 0xFF`)

### Protocol 1: Full Sensor Data (12+ bytes)

Complete sensor information including battery, gas type, faults.

```
Byte  | Field              | Description
------|--------------------|------------------------------------------
0-1   | Address            | 16-bit sensor address (MSB first)
2     | Protocol           | 0x01
3-6   | Reading            | 32-bit IEEE 754 float (MSB first)
7     | Mode | Type        | Bits 0-2: Mode, Bits 3-7: Sensor Type
8     | Battery            | 8-bit unsigned battery reading
9     | Gas | Scale        | Bits 0-6: Gas Type, Bit 7: Battery Scale
10    | Fault|Prec|Text    | Bits 4-7: Fault, 1-3: Precision, 0: HasText
11    | Checksum/TextLen   | Checksum if no text, else text length
12+   | Text (optional)    | ASCII text message
n+1   | Checksum           | Final checksum if text present
```

**Transmission Rate**:
- Every 60 seconds in normal operation (no gas)
- Every 5 seconds when gas detected above background

**Sensor Modes** (Bits 0-2 of Byte 7):
- 0: Normal
- 1: Null
- 2: Calibration
- 3: Relay Test
- 4: Radio Address
- 5: Diagnostic
- 6: Advanced Menu
- 7: Administration Menu

**Sensor Types** (Bits 3-7 of Byte 7):
- 0: EC (Electrochemical)
- 1: IR (Infrared)
- 2: CB (Catalytic Bead)
- 3: MOS (Metal Oxide Semiconductor)
- 4: PID (Photoionization Detector)
- 5: Tank Level
- 6: 4-20mA
- 7: Switch
- 30: OI-WF190
- 31: None Selected

**Gas Types** (Bits 0-6 of Byte 9):
- 0: H2S (Hydrogen Sulfide)
- 1: SO2 (Sulfur Dioxide)
- 2: O2 (Oxygen)
- 3: CO (Carbon Monoxide)
- 4: CL2 (Chlorine)
- 5: CO2 (Carbon Dioxide)
- 6: LEL (Lower Explosive Limit)
- 7: VOC (Volatile Organic Compounds)
- 8: Tank Level (Feet)
- 9: HCl (Hydrogen Chloride)
- 10: NH3 (Ammonia)

**Battery Calculation**:
- If Bit 7 of Byte 9 == 0: `voltage = Byte8 / 10.0` (0.1V resolution)
- If Bit 7 of Byte 9 == 1: `voltage = Byte8` (1V resolution)

**Fault Codes** (Bits 4-7 of Byte 10):
- 0: None
- 1: Sensor Board Timeout
- 2: Bad Reading
- 3: Current Draw Too High
- 4: ADC Not Responding
- 5: Error During Null
- 6: Future Error (reserved)
- 7: Checksum Error
- 8: Duplicate Otis Address (two sensors same address)
- 9: Sensor Radio Timeout
- 10: Wired Sensor Not Connected
- 15: Monitor Error

**Precision** (Bits 1-3 of Byte 10):
- 0-7: Number of decimal places to display

### Protocol 2: Quick Gas Detection (8 bytes)

Minimal packet sent every 5 seconds when gas is detected above background level.

```
Byte  | Field              | Description
------|--------------------|------------------------------------------
0-1   | Address            | 16-bit sensor address (MSB first)
2     | Protocol           | 0x02
3-6   | Reading            | 32-bit IEEE 754 float (MSB first)
7     | Checksum           | sum(bytes 0-6) & 0xFF
```

**Purpose**: Fast alert mechanism without battery/mode overhead

### Protocol 7: Maintenance Timing (13 bytes)

Sent when sensor is nulled or calibrated, and hourly thereafter.

```
Byte  | Field              | Description
------|--------------------|------------------------------------------
0-1   | Address            | 16-bit sensor address (MSB first)
2     | Protocol           | 0x07
3-6   | Reading            | 32-bit IEEE 754 float (MSB first)
7-8   | Days Since Null    | 16-bit unsigned (MSB first)
9-10  | Days Since Cal     | 16-bit unsigned (MSB first)
11    | Mode | Type        | Bits 0-2: Mode, Bits 3-7: Sensor Type
12    | Checksum           | sum(bytes 0-11) & 0xFF
```

**Transmission**: 
- When null performed
- When calibration performed
- When either value increases by 1 hour

## Python Implementation

### Basic Usage

```python
from pipeline.radio_receiver import RadioReceiver, RadioMessage

def on_message(msg: RadioMessage):
    if msg.protocol == 1:
        print(f"Ch{msg.channel}: {msg.reading:.{msg.precision}f}")
        print(f"  Battery: {msg.battery_voltage:.1f}V")
        print(f"  Fault: {msg.fault_code}")

# API mode (Laird LT1110/RM024 with 0x7E frames) - RECOMMENDED
receiver = RadioReceiver("COM5", baudrate=9600, api_mode=True)

# OR Transparent mode (raw Gen2 packets) - for direct sensor connection
receiver = RadioReceiver("COM5", baudrate=9600, api_mode=False)

receiver.connect()
receiver.register_callback(on_message)
receiver.start()
```

### Hybrid Mode (Radio + Modbus)

```python
from pipeline.radio_receiver import HybridBridge, RadioReceiver
from pipeline.modbus_client import ModbusClient, ModbusConfig

bridge = HybridBridge()

# Set up radio for wireless sensors
radio = RadioReceiver("COM5", api_mode=True)
radio.connect()
bridge.set_radio_receiver(radio)

# Set up modbus for monitor configuration
modbus = ModbusClient(ModbusConfig(...))
bridge.set_modbus_client(modbus)

bridge.start()

# Get data from either source (radio preferred)
data = bridge.get_channel_data(channel=5)
if data:
    print(f"Reading: {data['reading']} from {data['source']}")
```

## Hardware Setup

### Radio Module Connection

**Primary OI Radio Modules**:

**Laird LT1110** (900 MHz, Primary):
- Model: 1110LT200UPLG01
- Frequency: 900 MHz ISM band
- Baud rate: 9600 (default)
- Firmware: V 2.9-0 or later
- Mode: API mode with Sniff Permit for secondary monitors
- Power: Typically 3.3V/5V compatible
- Range: Up to 2 miles line-of-sight (outdoor)

**Laird RM024** (2.4 GHz, Alternative):
- Model: 2510LT100UPLG01 (LT series)
- Frequency: 2.4 GHz ISM band
- Baud rate: 9600 (default)
- Firmware: V 2.4-1 or later
- Mode: API mode with Sniff Permit
- Power: 3.3V/5V compatible
- Range: Up to 1 mile line-of-sight (outdoor)

**XBee/Digi Module** (Legacy/Alternative):
- Models: XBee-PRO XSC (also compatible)
- Can be used but Laird modules are preferred
- Configure for API mode (AT command: `ATAP1`) or transparent mode

**Serial Connection (All Modules)**:
- Baud rate: 9600 (default for OI)
- 8 data bits, no parity, 1 stop bit
- Flow control: None (or RTS/CTS if available)
- Connect TX, RX, GND minimum
- VCC: 3.3V or 5V depending on module

**Arduino/ESP32**:
- Connect to Hardware Serial or Software Serial
- Same serial parameters as above
- Laird modules use 3.3V logic (ESP32 compatible)
- Can interface directly without level shifters on ESP32

**USB-Serial Adapter**:
- FTDI, CH340, CP2102 adapters work well
- Set for 3.3V logic if possible (Laird modules)
- 9600 baud, 8N1

### Network Configuration

**Laird Radio Settings**:
- **Network Channel**: 5 (default, configurable 0-15)
- **System ID**: 37 (fixed for OI, do not change)
- **TX Power**: Adjustable (default max for range)
- **API Mode**: Enabled (allows packet metadata)
- **Sniff Permit**: Enabled on secondary monitors only
- **Encryption**: Optional (when available in firmware)

**Primary Monitor (PM)**:
- Acts as network Server (Laird terminology)
- Only monitor that sends ACKs to sensors
- Sensors sync with PM and send data to it
- Network Channel: 5 (default, user configurable 0-15)
- System ID: 37 (fixed for OI)
- Radio configured as Server mode

**Secondary Monitors (SM)**:
- Listen only, no ACKs (Sniff Permit mode on Laird)
- Receive all sensor broadcasts
- Do not interfere with PM-sensor communication

**Radio Direct Connection**:
- Connect radio module directly to server/Raspberry Pi/ESP32
- Bypass monitor completely for data collection
- Can operate alongside monitors (hybrid mode)

## Checksum Validation

OI uses simple 8-bit checksum:

```python
def calculate_checksum(data: bytes) -> int:
    return sum(data) & 0xFF
```

Some implementations accept either:
- `checksum == sum(data) & 0xFF`
- `checksum == (0xFF - sum(data)) & 0xFF` (inverted)

This implementation accepts both for compatibility.

## Address Mapping

- **Sensor Addresses**: 1-255 (originally up to 1000, but limited to 255)
- **Monitor Address**: 1001 (0x3E9) for Protocol 0 (monitor discovery)
- **Channel Number**: 1:1 mapping with sensor address

## Protocol 0: Monitor Discovery (Reserved)

```
Byte  | Field              | Description
------|--------------------|------------------------------------------
0-1   | Address            | 0x03E9 (1001 in decimal)
2     | Protocol           | 0x00
3     | Checksum           | 0xEC
```

**Purpose**: Primary monitor tells secondary to become client again

**Note**: Not implemented in this version (monitor-to-monitor only)

## XBee API Frame Extraction

Based on `radio_extract_xbee_gen2()` from OI-6950 laird.c source code:

1. **Validate 0x7E start delimiter**
2. **Extract frame length** (bytes 1-2)
3. **Verify API frame checksum**
4. **Scan frame payload** for Gen2 protocol markers (byte[2] == 1, 2, or 7)
5. **Validate Gen2 checksum**
6. **Extract complete Gen2 packet**

The Gen2 packet can appear at any offset within the XBee frame's RF data section. The implementation scans for valid protocol numbers and verifies checksums.

## Testing

### Test Radio Reception

```bash
cd d:\oi-7500-pipeline
.venv\Scripts\activate
python pipeline\radio_receiver.py
```

Expected output:
```
OI Gen II Radio Receiver Test
==================================================
Connected to OI radio module on COM5 (API mode)
Radio receiver started

Listening for OI wireless sensors...
Press Ctrl+C to stop

=== Protocol 1: Full Sensor Data ===
Address: 5 (Ch5)
Reading: 0.00
Gas: H2S
Sensor: EC
Mode: Normal
Battery: 3.6V
Fault: None
```

### Troubleshooting

**No data received**:
- Check serial port and baud rate (9600)
- Verify radio module power (3.3V or 5V depending on model)
- Confirm sensors are transmitting (monitor LCD should show radio icon)
- Check network channel matches (default 5)
- Verify System ID is 37 (Laird specific)
- Ensure API mode is enabled on Laird modules (ATAP setting)

**Laird LT1110 Specific**:
- 900 MHz has better range but may have more interference
- Check antenna connection (SMA connector)
- Verify firmware version 2.9-0 or later
- Use `ATS` AT command to check status

**Laird RM024 Specific**:
- 2.4 GHz has less range but cleaner spectrum
- May compete with WiFi in same band
- Check channel selection (avoid WiFi channels)

**Checksum errors**:
- Verify API mode setting matches radio configuration
- Check for electrical noise on serial lines
- Try transparent mode if API mode fails

**Partial data**:
- Increase buffer processing timeout
- Check for data loss on serial connection
- Verify baud rate is correct (9600 standard)

## References

- OI-6950 Source Code: `radio.c`, `laird.c`, `digi.c`, `radio_task.c`
- Protocol Documentation: "WireFree Generation 2 Protocol" (WireFree_Prot_GenII_W_Text.txt)
- XBee Documentation: Digi XBee API mode specification
- Laird Documentation: BT900 radio module AT commands

## Future Enhancements

- [ ] Protocol 0 support (monitor discovery)
- [ ] Protocol 3-6 support (multi-monitor forwarding - currently unused)
- [ ] RSSI extraction from XBee frames
- [ ] MAC address tracking (Laird radios)
- [ ] Signal strength monitoring
- [ ] Automatic API/Transparent mode detection
- [ ] Encryption support (when available in Laird firmware)
- [ ] Network channel scanning
- [ ] Sensor address conflict detection (Fault 8)
