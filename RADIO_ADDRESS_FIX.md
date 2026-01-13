# Radio Address and Battery Voltage Fix

**Date**: January 13, 2026  
**Issue**: Gas reading sensor data showing incorrect radio address and battery voltage

## Problems Identified

### 1. Radio Address vs. Channel Confusion

**Issue**: The code was not distinguishing between:
- **Transmitter Address** (bytes 0-1): The radio sensor's unique ID (e.g., 0x8111 = 33041)
- **Channel** (byte 8): The monitor's receiving slot configured to listen to that transmitter

**Key Understanding**:
- The radio transmitter only knows its own address, NOT the channel number
- Channels are internal to the monitors - they are receiving slots that can be configured to listen to any radio address
- A monitor reads the transmitter address from bytes 0-1 and assigns it to a channel based on configuration

### 2. Battery Voltage Calculation

**Status**: ✅ Battery voltage calculation was actually correct
- Byte 15: Battery reading (8-bit unsigned integer)
- Byte 16, bit 7: Battery scale flag
  - Scale 0: `voltage = battery_reading / 10.0` (for 3.0V - 25.5V range)
  - Scale 1: `voltage = battery_reading` (for integer voltages)

## Changes Made

### Files Modified

1. **monitoring/monitor_multi_network.py**
   - ✅ Extract transmitter_address from bytes 1-2 (after 0x81 frame byte)
   - ✅ Keep channel extraction from byte 8
   - ✅ Add transmitter_address to decoded packet dictionary
   - ✅ Include transmitter_address in MQTT payloads
   - ✅ Update console output: `Addr 33041 → Ch 5` format
   - ✅ Update log file output to show transmitter address

2. **monitoring/mqtt_monitor.py**
   - ✅ Extract and display transmitter_address from MQTT messages
   - ✅ Show format: `Addr 33041 → Ch 5`

3. **pipeline/radio_decoder.py**
   - ✅ Add clarifying comments about transmitter_address vs channel
   - ✅ Remove automatic channel mapping from address

### Database Schema

No changes needed - the database already has the `transmitter_address` field:

```sql
CREATE TABLE decoded_packets (
    ...
    channel INTEGER NOT NULL,
    transmitter_address INTEGER NOT NULL,
    ...
);
```

## Packet Structure (0x81 Format)

```
Byte 0:    0x81 (frame marker)
Byte 1-2:  Transmitter Address (16-bit, big-endian) ← RADIO'S IDENTIFIER
Byte 3:    Protocol (usually 0x00)
Byte 8:    Channel (1-32) ← MONITOR'S RECEIVING SLOT
Byte 10-13: Reading (Float32, big-endian)
Byte 14:   Sensor Mode (bits 0-2) + Sensor Type (bits 3-7)
Byte 15:   Battery Reading (8-bit)
Byte 16:   Gas Type (bits 0-6) + Battery Scale (bit 7)
Byte 17:   Fault Code (bits 0-3) + Precision (bits 4-6)
```

## MQTT Payload Format (Updated)

```json
{
  "transmitter_address": 33041,
  "channel": 5,
  "reading": 1.25,
  "gas_type": "LEL",
  "battery_voltage": 23.0,
  "fault": "None",
  "network": "Network_25",
  "timestamp": "2026-01-13T10:30:00"
}
```

## Testing

To verify the fix:

1. **Monitor Console Output**:
   ```
   [10:30:15] Network_25   | Addr 33041 → Ch  5 | LEL      |       1.25 | Batt 23.0V | Fault: None
   ```

2. **MQTT Monitor Output**:
   ```
   [10:30:15] Network_25   | Addr 33041 → Ch  5 | LEL      |       1.25 | Batt 23.0V | ✓ None
   ```

3. **Database Query**:
   ```sql
   SELECT transmitter_address, channel, reading, battery_voltage 
   FROM decoded_packets 
   ORDER BY timestamp DESC LIMIT 10;
   ```

## Key Takeaways

1. **Radio transmitters** broadcast their address in bytes 1-2 (0x8111, 0x8112, etc.)
2. **Monitors** assign these transmitters to channels (1-32 receiving slots)
3. **Modbus** uses channel numbers to configure which radio address each channel listens to
4. **The radio doesn't know about channels** - only the monitor manages that mapping

## References

- [WireFree_Prot_GenII_W_Text.txt](reference_docs/WireFree_Prot_GenII_W_Text.txt) - Official protocol documentation
- [RADIO_PACKET_FORMAT.py](archive/experiments/RADIO_PACKET_FORMAT.py) - Verified packet structure
- [README.md](README.md) - Protocol details table
