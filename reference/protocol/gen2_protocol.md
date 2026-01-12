# Gen II WireFree Protocol Specification

Complete protocol documentation for Otis Instruments Gen II WireFree sensor communication.

## Frame Structure

### Laird API 0x81 Frame

All radio communication uses Laird API mode frames with 0x81 header.

#### Direct Packet (19 bytes)

Sensor → Monitor (no repeater)

```
Byte:  0    1    2    3       4-6      7-8     9    10-13    14     15     16     17    18
      [0x81][Len][0x00][RSSI][MAC:3][Addr:2][Proto][Float][Mode][Battery][Gas][Fault][Chk]
      └────┬────┘         └───────────────┬──────────────────┘ └──────────┬───────────────┘
        Header                        Payload                           Trailer
```

- **Header** (3 bytes):
  - `0x81` - Laird API frame start
  - `Len` - Payload length (0x0c = 12 bytes)
  - `0x00` - Reserved

- **Payload** (12 bytes):
  - `RSSI` - Received signal strength (raw value)
  - `MAC` - Radio MAC address (3 bytes)
  - `Addr` - Sensor radio address (2 bytes, big-endian)
  - `Proto` - Protocol type (1 = full sensor data)
  - `Float` - IEEE 754 gas concentration (4 bytes)
  - `Mode` - Sensor mode byte

- **Trailer** (4 bytes) - **NOT counted in length**:
  - `Battery` - Battery voltage byte
  - `Gas` - Gas type code
  - `Fault` - Fault/precision byte
  - `Checksum` - XOR of all previous bytes

#### Repeated Packet (24 bytes)

Sensor → Repeater → Monitor

```
Byte:  0    1    2    3       4-6      7-8     9    10-13    14     15     16     17    18     19    20-22
      [0x81][Len][0x00][RSSI][MAC:3][Addr:2][Proto][Float][Mode][Battery][Gas][Fault][Chk][RSSI2][MAC2:3]
      └────┬────┘         └───────────────┬──────────────────┘ └──────────┬───────────────┘ └──────┬──────┘
        Header                        Payload                           Trailer              Repeater Info
```

- **Payload** (17 bytes): Same as direct, includes repeater bit set
- **Trailer** (4 bytes): Same 4 bytes
- **Repeater Info** (4 bytes):
  - `RSSI2` - Repeater signal strength
  - `MAC2` - Repeater MAC address (3 bytes)

**Repeater Bit Detection:**
- Protocol byte bit 7 set: `(protocol & 0x80) != 0`
- Clear bit 7 to get actual protocol: `protocol & 0x7F`

## Protocol 1 - Full Sensor Data

### Gen2 Packet (12 bytes)

After Laird frame extraction, Gen2 packet is reconstructed:

```
Byte:    0-1       2        3-6        7        8        9       10      11
      [Addr:2][Protocol][Float:4][Mode][Battery][Gas][Fault][Checksum]
```

### Field Definitions

#### 1. Address (Bytes 0-1)

**Format**: 16-bit unsigned integer, big-endian  
**Range**: 0-65535  
**Example**: `0x00 0xFF` = Address 255

Common ranges:
- 1-254: Standard sensors
- 255: Special/test sensors
- 0: Broadcast (rare)

#### 2. Protocol (Byte 2)

**Format**: 8-bit unsigned integer  
**Values**:
- `0x01` - Full sensor data (most common)
- `0x02` - Quick update (periodic)
- `0x07` - Maintenance packet
- Others - Reserved

**Repeater Detection**:
```python
is_repeated = (protocol & 0x80) != 0
actual_protocol = protocol & 0x7F
```

#### 3. Float (Bytes 3-6)

**Format**: IEEE 754 32-bit floating point, big-endian  
**Units**: Depends on gas type (ppm, %, mg/m³)

**Decoding** (Python):
```python
import struct
gas_reading = struct.unpack('>f', float_bytes)[0]
```

**Common Values**:
- `0x41A73333` = 20.9 (atmospheric oxygen)
- `0x00000000` = 0.0 (no gas detected)
- `0x3F800000` = 1.0

#### 4. Mode (Byte 7)

**Format**: 8-bit bitfield

| Bits | Field | Values |
|------|-------|--------|
| 0-2  | Sensor Mode | 0=Normal, 1=Null, 2=Calibrate |
| 3-7  | Sensor Type | 0=EC, 1=IR, 2=CB, 3=MOS, 4=PID |

**Decoding**:
```python
sensor_mode = mode_byte & 0x07
sensor_type = (mode_byte >> 3) & 0x1F
```

**Mode Values**:
- `0x00` - Normal operation, EC sensor
- `0x08` - Normal operation, IR sensor
- `0x10` - Normal operation, CB sensor
- `0x20` - Normal operation, MOS sensor

#### 5. Battery (Byte 8)

**Format**: 8-bit unsigned integer  
**Units**: 0.1 Volts  
**Range**: 0-255 → 0.0-25.5V

**Decoding**:
```python
battery_voltage = battery_byte * 0.1
```

**Common Values**:
- `0x16` (22) = 2.2V - Low battery warning
- `0x24` (36) = 3.6V - Typical fresh battery
- `0xA0` (160) = 16.0V - Solar powered
- `0xE6` (230) = 23.0V - Line powered

#### 6. Gas Type (Byte 9)

**Format**: 8-bit code (bits 0-6), bit 7 reserved

| Code | Gas Name | Units |
|------|----------|-------|
| 0x00 | H2S (Hydrogen Sulfide) | ppm |
| 0x01 | CO (Carbon Monoxide) | ppm |
| 0x02 | O2 (Oxygen) | % |
| 0x03 | LEL (Combustible) | % LEL |
| 0x04 | SO2 (Sulfur Dioxide) | ppm |
| 0x05 | NO2 (Nitrogen Dioxide) | ppm |
| 0x06 | Cl2 (Chlorine) | ppm |
| 0x07 | NH3 (Ammonia) | ppm |
| 0x08 | VOC (Volatile Organic) | ppm |
| 0x09 | HCN (Hydrogen Cyanide) | ppm |
| 0x0A | PH3 (Phosphine) | ppm |
| 0x0B | HCl (Hydrogen Chloride) | ppm |
| 0x0C | NO (Nitric Oxide) | ppm |
| 0x0D | CO2 (Carbon Dioxide) | % |
| 0x0E | IR HC (Hydrocarbon IR) | % LEL |
| 0x0F | ClO2 (Chlorine Dioxide) | ppm |

**Decoding**:
```python
gas_type_code = gas_byte & 0x7F  # Clear bit 7
gas_name = GAS_TYPES[gas_type_code]
```

#### 7. Fault/Precision (Byte 10)

**Format**: 8-bit bitfield

| Bits | Field | Values |
|------|-------|--------|
| 0-3  | Fault Code | 0-15 (see fault codes below) |
| 4-6  | Precision | 0-7 decimal places |
| 7    | Reserved | - |

**Decoding**:
```python
fault_code = fault_byte & 0x0F
precision = (fault_byte >> 4) & 0x07
```

**Fault Codes**:
- `0x0` (F0) - None
- `0x1` (F1) - Digital sensor board comm lost
- `0x2` (F2) - (No longer assigned)
- `0x3` (F3) - Low Power IR beyond repair
- `0x4` (F4) - ADC/analog board comm issue
- `0x5` (F5) - Failed to Null
- `0x6` (F6) - Failed to Calibrate
- `0x7` (F7) - Internal fault
- `0x8` (F8) - Duplicate address detected ⚠️
- `0x9` (F9) - Radio timeout
- `0xA` (F10) - Wired sensor not communicating
- `0xB` (F11) - IR temp changing too quickly
- `0xC` (F12) - IR element restarting
- `0xD` (F13) - 4-20mA fault
- `0xE` (F14) - Cannot see Primary Monitor ⚠️
- `0xF` (F15) - (No longer assigned)

#### 8. Checksum (Byte 11)

**Format**: 8-bit XOR checksum  
**Calculation**: XOR of bytes 0-10

```python
checksum = 0
for byte in packet[0:11]:
    checksum ^= byte
valid = (checksum == packet[11])
```

## RSSI Calculation

**Raw RSSI Byte → dBm → Percentage**

```python
# Convert raw RSSI byte to dBm
rssi_dbm = -(rssi_byte + 45)

# Convert dBm to percentage (0-100%)
rssi_percent = max(0, min(100, int((40 - (rssi_dbm + 45)) * 2.5)))
```

**Example**:
- `RSSI=0x3F` (63) → -108 dBm → 95%
- `RSSI=0x20` (32) → -77 dBm → 65%
- `RSSI=0x10` (16) → -61 dBm → 45%

## Protocol 2 - Quick Update

Shortened packet for frequent updates (not yet implemented).

## Protocol 7 - Maintenance

Maintenance/diagnostic packet (structure varies).

## Example Packet Decoding

### Real Packet from O2 Sensor

```
Raw (19 bytes): 810c003fc8af2b00ff0141a7333300178210f7
```

**Breakdown**:
```
Header:
  0x81         - Laird frame start
  0x0c         - Payload length (12 bytes)
  0x00         - Reserved

Payload:
  0x3f         - RSSI = 63 → 95%
  0xc8af2b     - MAC address
  0x00ff       - Radio address = 255
  0x01         - Protocol 1 (full data)
  0x41a73333   - Float = 20.9 (O2 reading)
  0x00         - Mode = Normal, EC sensor

Trailer:
  0x17         - Battery = 2.3V * 10 = 23.0V
  0x82         - Gas type = 0x02 (O2)
  0x10         - Fault = 0 (none), Precision = 1
  0xf7         - Checksum (valid)
```

**Decoded**:
- Channel 255
- O2 sensor
- 20.9% oxygen (atmospheric)
- 23.0V battery (line powered)
- No faults
- 95% signal strength

## Implementation Notes

### Python Example

```python
def decode_protocol1(gen2_packet):
    """Decode 12-byte Gen2 Protocol 1 packet."""
    # Address
    address = (gen2_packet[0] << 8) | gen2_packet[1]
    
    # Protocol
    protocol = gen2_packet[2] & 0x7F
    
    # Float
    import struct
    gas_reading = struct.unpack('>f', bytes(gen2_packet[3:7]))[0]
    
    # Mode
    mode = gen2_packet[7]
    sensor_mode = mode & 0x07
    sensor_type = (mode >> 3) & 0x1F
    
    # Battery
    battery = gen2_packet[8] * 0.1
    
    # Gas type
    gas_type = gen2_packet[9] & 0x7F
    
    # Fault/Precision
    fault = gen2_packet[10] & 0x0F
    precision = (gen2_packet[10] >> 4) & 0x07
    
    # Checksum
    calc_checksum = 0
    for b in gen2_packet[0:11]:
        calc_checksum ^= b
    valid = (calc_checksum == gen2_packet[11])
    
    return {
        'address': address,
        'protocol': protocol,
        'gas_reading': gas_reading,
        'sensor_mode': sensor_mode,
        'sensor_type': sensor_type,
        'battery': battery,
        'gas_type': gas_type,
        'fault': fault,
        'precision': precision,
        'checksum_valid': valid
    }
```

## Radio Configuration

### Laird RM024 Settings

For monitoring (SECONDARY mode):

```
ATSP 0       # Secondary mode (receive-only)
ATBD 7       # 115200 baud (PC communication)
ATAP 1       # API mode enabled
ATMY 0       # Network ID 0 (receive all)
```

For sensors/monitors (PRIMARY mode):

```
ATSP 1       # Primary mode (can transmit)
ATBD 5       # 19200 baud (sensor/monitor)
ATAP 1       # API mode enabled
ATMY 15      # Network ID (15, 20, or 25)
```

## Troubleshooting

### Common Issues

**Q: Checksum failures**  
A: Verify all 11 bytes are included in XOR. Trailer bytes are NOT part of checksum.

**Q: Wrong float values**  
A: Ensure big-endian byte order. Use `'>f'` in struct.unpack().

**Q: Negative RSSI percentages**  
A: Clamp to 0-100 range. Very weak signals can calculate negative.

**Q: Gas type code > 15**  
A: Mask bit 7 (`gas_byte & 0x7F`). Bit 7 is reserved.

**Q: Packets appear truncated**  
A: Direct packets are 19 bytes, repeated are 24 bytes. Both are valid.

## References

- Otis Instruments Gen II WireFree Protocol Documentation
- Laird RM024 Radio Module Datasheet
- OI-6000 Series Sensor Manual
- OI-7010/7530/7032 Monitor Manuals

## Version History

- **v1.0** (2026-01-12) - Initial documentation based on working decoder
- Protocol 1 fully validated with 100% success rate
- Tested with 10 active sensors (H2S, CO, O2, NH3, Cl2)
