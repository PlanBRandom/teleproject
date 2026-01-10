# Radio Data Logging - Findings and Decoder Reference

## Summary

Successfully logged 6 hours of radio data (6,181 packets) from COM7. However, discovered that the raw hex log format doesn't match the standard OI WireFree Gen II protocol structure expected by the parser.

## Issue Discovered

The logged hex data has a format that includes additional framing/timing bytes not present in standard Gen2 Protocol 1 packets:
- Expected: `[Address 2B][Protocol 1B][Reading 4B][Sensor 1B][Battery 1B][Gas 1B][Fault 1B][Checksum 1B]`
- Actually logged: `81 11 00 XX e0 88 ...` (includes extra bytes 2-5 that aren't part of Gen2 spec)

This suggests the serial port is capturing a proprietary RM024/radio module format rather than pure Gen2 packets.

## Gas and Sensor Type Decoder Created

Created **`gas_sensor_decoder.py`** with complete decoding reference for:

### Gas Types (0-12 documented, 63-65 observed):
- 0: H2S (Hydrogen Sulfide)
- 1: SO2 (Sulfur Dioxide)  
- 2: O2 (Oxygen)
- 3: CO (Carbon Monoxide)
- 4: CL2 (Chlorine)
- 5: CO2 (Carbon Dioxide)
- 6: LEL/Combustible
- 7: H2 (Hydrogen)
- 8: HCN (Hydrogen Cyanide)
- 9: NO2 (Nitrogen Dioxide)
- 10: NH3 (Ammonia)
- 11: PH3 (Phosphine)
- 12: CH4 (Methane)
- **63-65: Unknown (possibly custom calibration gases)**

### Sensor Types (0-20 documented, raw values 128-192 observed):
- 0: Electrochemical (EC)
- 1: Infrared (IR)
- 2: Catalytic Bead (CB)
- 3: Metal Oxide Semiconductor (MOS)
- 4: PID (Photoionization Detector)
- 5: Tank Level
- 6: 4-20mA Analog
- 7: Switch
- 8-20: Various sensors (Pressure, Temperature, pH, etc.)
- 30: OI-WF190
- 31: None Selected

**Note**: Raw values like 128, 175, 192 need bit extraction:
- `sensor_type = (byte_7 >> 3) & 0x1F`
- `sensor_mode = byte_7 & 0x07`

Example: Raw 128 = mode 0 (Normal), type 16 (Dissolved Oxygen)

### Fault Codes:
- 0: No Fault
- 1: Over Range
- 2: Under Range
- 3: Sensor Fault
- 4: Low Battery
- 5: Calibration Required
- 8, 16, 32: Unknown (observed in field)

## Files Created

1. **`gas_sensor_decoder.py`** - Complete decoder reference with all gas/sensor types
2. **`analyze_radio_logs.py`** - Log analyzer (needs hex format fix to work properly)
3. **`log_radio_6hours.py`** - 6-hour data logger
4. **`radio_logs/radio_log_COM7_20260105_171202_hex.txt`** - 6-hour hex capture (6,181 packets)

## Recommendations

### Option 1: Use Built-in Radio Receiver Logging
Instead of raw serial logging, use `radio_receiver.py`'s message callback to log PARSED messages:

```python
from pipeline.radio_receiver import RadioReceiver

def log_message(msg):
    print(f"Sensor {msg.transmitter_address}: {msg.reading} {decode_gas_type(msg.gas_type)}")
    # Log to file in structured format

receiver = RadioReceiver(port='COM7', api_mode=True, api_type='rm024')
receiver.add_callback(log_message)
receiver.start()
```

### Option 2: Decode the Proprietary Format
Reverse-engineer the exact byte positions in the logged hex data. The pattern suggests:
- Bytes [0-1]: Address (0x8111, 0x8112, etc.)
- Byte [2]: Always 0x00 (flag/reserved)
- Byte [3]: Sequence/length
- Bytes [4-5]: Often 0xE0 0x88 (possibly channel 224 + module header)
- Bytes [6+]: Actual sensor data (needs investigation)

### Option 3: Recapture with API Mode
Enable proper RM024 API mode to get framed packets with MAC/RSSI:
```python
receiver = RadioReceiver(port='COM7', api_mode=True, api_type='rm024', baudrate=115200)
```

## Usage

Run the decoder reference:
```bash
python gas_sensor_decoder.py
```

This will print:
- Complete gas type table
- Complete sensor type table  
- Fault code table
- Protocol 1 packet structure
- Bit extraction formulas
- Usage examples

## Next Steps

1. **Immediate**: Use `gas_sensor_decoder.py` to decode known gas/sensor types
2. **Short-term**: Implement Option 1 (use radio_receiver.py for logging)
3. **Long-term**: If proprietary format is needed, reverse-engineer byte positions

The decoder provides all documented gas and sensor types. Values 63-65 for gas types are likely custom calibration gases specific to your sensors and would need to be identified through sensor documentation or testing.
