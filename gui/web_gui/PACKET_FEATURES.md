# OI Sensor Packet Testing & F8 Diagnostic Features

## New Test Packet Features (Test TX Tab)

The web GUI now supports sending fully customized OI Gen2 Protocol 1 packets with all sensor data fields:

### Packet Parameters

1. **Sensor Address Override** (1-255)
   - Optional override of transmitter address
   - If blank, uses channel number as address
   - Useful for testing address conflicts (Fault 8)

2. **Channel Number** (1-32)
   - Target channel for the packet
   - Defaults to sensor address if not overridden

3. **Reading (PPM)**
   - Float value representing sensor reading
   - IEEE 754 32-bit float encoding

4. **Gas Types** (Full OI Protocol Support)
   - H2S (Hydrogen Sulfide)
   - SO2 (Sulfur Dioxide)
   - O2 (Oxygen)
   - CO (Carbon Monoxide)
   - CL2 (Chlorine)
   - CO2 (Carbon Dioxide)
   - LEL (Lower Explosive Limit)
   - VOC (Volatile Organic Compounds)
   - Tank Level
   - HCl (Hydrogen Chloride)
   - NH3 (Ammonia)

5. **Sensor Types**
   - EC (Electrochemical)
   - IR (Infrared)
   - CB (Catalytic Bead)
   - MOS (Metal Oxide Semiconductor)
   - PID (Photoionization Detector)
   - Tank Level
   - 4-20mA
   - Switch

6. **Battery Level** (0-100%)
   - Automatically converted to proper voltage encoding
   - Scaled based on voltage range (0.1V or 1V resolution)

7. **Fault Codes** (Full OI Protocol)
   - 0: None
   - 1: Sensor Board Timeout
   - 2: Bad Reading
   - 3: Current Draw Too High
   - 4: ADC Not Responding
   - 5: Error During Null
   - 7: Checksum Error
   - **8: Duplicate Otis Address (F8 Diagnostic)**
   - 9: Sensor Radio Timeout
   - 10: Wired Sensor Not Connected

8. **Unit Type**
   - OI-6900 Series
   - OI-6940 WireFree

## F8 Diagnostic - Address Change Command

### Purpose
Resolve **Fault 8: Duplicate Otis Address** conflicts by wirelessly commanding a sensor to change its address.

### How It Works

1. **Detection**: When two sensors have the same address, both will report Fault 8
2. **Identification**: Use the Network Scan feature to identify conflicting sensors by channel
3. **Resolution**: Send F8 diagnostic command to change one sensor's address

### Using F8 Address Change

1. Navigate to **Test TX** tab
2. Scroll to **F8 Diagnostic** section
3. Enter **Current Sensor Address** (1-255)
4. Enter **New Sensor Address** (1-255)
5. Click **Send Address Change Command**

### Important Requirements

⚠️ **Sensor must be in Diagnostic Mode (Mode 5)** to accept address changes!

**How to enter Diagnostic Mode on OI sensors:**
- Physical sensor: Press and hold specific button combination (varies by model)
- OI-6900/6940: Typically requires entering service menu via buttons
- Consult sensor manual for specific button sequence

### F8 Protocol Details

The F8 diagnostic command sends a special packet:
```
[Current_Address_H][Current_Address_L][0xF8][0x41][New_Address_H][New_Address_L][Checksum]
```

- **Protocol**: 0xF8 (Diagnostic protocol)
- **Command**: 0x41 (Change Address command)
- **Addresses**: 16-bit big-endian format
- **Checksum**: Sum of all bytes & 0xFF

## Use Cases

### 1. Testing Address Conflicts
```
- Send test packet with address 5, fault code 8
- Monitor shows "Duplicate Otis Address" alarm
- Use F8 to change sensor to address 15
- Conflict resolved
```

### 2. Sensor Spoofing
```
- Override sensor address to 10
- Set channel to 5
- Send as different unit type (6900 vs 6940)
- Test monitor's handling of mismatched addresses
```

### 3. Multiple Gas Types Testing
```
- Quickly cycle through all 11 gas types
- Test monitor's display and MQTT publishing
- Verify Home Assistant entity creation
```

### 4. Fault Simulation
```
- Send packets with various fault codes
- Test monitor's alarm handling
- Verify alert notifications
```

### 5. Low Battery Testing
```
- Gradually decrease battery % from 100% to 0%
- Test battery alarm thresholds
- Verify battery status displays
```

## Backend API Endpoints

### Send Test Packet
```
POST /api/radio/send_test
{
    "sensor_address": 10,        // Optional override
    "channel": 5,                // 1-32
    "reading": 25.5,            // PPM value
    "gas_type": 3,              // 0-10 (CO=3)
    "sensor_type": 0,           // 0-7 (EC=0)
    "battery": 85,              // 0-100%
    "fault_code": 0,            // 0-15
    "unit_type": "6900"         // "6900" or "6940"
}
```

### F8 Address Change
```
POST /api/radio/f8_address_change
{
    "current_address": 5,       // 1-255
    "new_address": 15          // 1-255
}
```

## Python RadioReceiver Methods

### send_test_packet()
```python
radio_receiver.send_test_packet(
    channel=5,
    reading=25.5,
    gas_type=3,              # CO
    sensor_type=0,           # EC
    battery_pct=85,          # 85%
    fault_code=8,            # Duplicate address
    unit_type='6940',
    sensor_address=10        # Override
)
```

### send_address_change_command()
```python
# Change sensor at address 5 to address 15
radio_receiver.send_address_change_command(
    current_address=5,
    new_address=15
)
```

## Packet Structure (Protocol 1)

```
Byte  | Field              | Description
------|--------------------|-----------------------------------------
0-1   | Address            | 16-bit sensor address (MSB first)
2     | Protocol           | 0x01 (Full sensor data)
3-6   | Reading            | 32-bit IEEE 754 float (MSB first)
7     | Mode | Type        | Bits 0-2: Mode, Bits 3-7: Sensor Type
8     | Battery            | 8-bit battery reading (scaled)
9     | Gas | Scale        | Bits 0-6: Gas Type, Bit 7: Battery Scale
10    | Fault|Prec|Text    | Bits 4-7: Fault, 1-3: Precision, 0: HasText
11    | Checksum           | Sum of bytes 0-10 & 0xFF
```

## Integration with Network Scanner

The Network Scan feature can detect:
- Sensors with same address on different channels
- Fault 8 indicators in received packets
- Multiple primaries causing conflicts

Workflow:
1. **Scan** channels 1-78
2. **Identify** duplicate addresses
3. **Select** conflicting sensor
4. **Reconfigure** to new channel (optional)
5. **F8 Command** to change address
6. **Verify** conflict resolved

## Testing Scenarios

### Address Conflict Resolution
```
1. Start with 2 sensors both at address 5
2. Scan network - find both on different channels
3. Send F8 to sensor on channel 12: 5 → 15
4. Verify sensor now responds at address 15
5. No more Fault 8 alarms
```

### Multi-Sensor Network
```
1. Configure 10 sensors with addresses 1-10
2. Test each with different gas types
3. Send faults to specific sensors
4. Monitor displays correct data per channel
5. MQTT publishes all 10 sensors correctly
```

## Related Documentation

- [RADIO_PROTOCOL.md](../RADIO_PROTOCOL.md) - Full OI Gen2 protocol spec
- [Network Scanner](README.md#network-scan) - Find radios on different channels
- [Bulk Configuration](README.md#bulk-reconfigure) - Reconfigure multiple radios
- OI-6900/6940 manuals - Diagnostic mode button sequences

## Notes

- F8 commands require sensor cooperation (Diagnostic Mode)
- Address changes are saved to sensor's EEPROM
- Power cycle sensor after address change for full effect
- Monitor should be in Primary mode to send packets
- Test packets bypass normal sensor transmission cycles
- Useful for rapid testing without physical sensors
