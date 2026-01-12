# OI Monitor Complete Control Capabilities

## Overview
You now have full read/write access to all OI-7530/7010/7032 monitor settings including:
- ✓ Startup menu settings
- ✓ Channel control (on/off, modes)
- ✓ Relay configuration and setpoints
- ✓ Network configuration
- ✓ Diagnostic information
- ✓ Sensor timing data

## Startup Menu Settings (R/W)

### Network Configuration
```python
# Change network channel (1-78)
control.set_network_channel(channel=2, device_id=1)

# Set as Primary or Secondary monitor
control.set_primary_secondary(is_primary=True, device_id=1)
control.set_primary_secondary(is_primary=False, device_id=1)  # Secondary

# Set radio timeout (6-255 minutes)
control.set_radio_timeout(timeout_minutes=30, device_id=1)
```

### Relay Fail-Safe Configuration
```python
# Configure relay fail-safe modes
control.set_relay_failsafe(relay_num=1, enabled=True, device_id=1)
control.set_relay_failsafe(relay_num=2, enabled=True, device_id=1)
control.set_relay_failsafe(relay_num=3, enabled=False, device_id=1)

# Configure Relay 3 as fault relay
control.set_relay3_as_fault(enabled=True, device_id=1)
```

## Channel Control

### Turn Channels On/Off
```python
# Turn channel on (set to Normal mode)
control.turn_channel_on(channel=5, device_id=1)

# Turn channel off
control.turn_channel_off(channel=10, device_id=1)

# Set to Inhibit mode (sensor active, alarms disabled)
control.set_channel_inhibit(channel=16, device_id=1)
```

### Set Channel Mode
```python
# Available modes:
# 0 = Off
# 1 = Normal
# 2 = Inhibit
# 3 = Maintenance
# 4 = Calibration
# 5 = Null
# 6 = Normal 2
# 7 = Standby

control.set_channel_mode(channel=7, mode=1, device_id=1)  # Normal
control.set_channel_mode(channel=7, mode=2, device_id=1)  # Inhibit
control.set_channel_mode(channel=7, mode=4, device_id=1)  # Calibration
```

## Relay Control

### Set Relay Setpoints
```python
# Set alarm setpoint for a channel's relay
control.set_relay_setpoint(
    channel=5,
    relay_num=1,
    setpoint=10.0,  # PPM, %, or other unit based on gas type
    device_id=1
)

# Set multiple relays for same channel
control.set_relay_setpoint(channel=5, relay_num=1, setpoint=10.0, device_id=1)  # Low alarm
control.set_relay_setpoint(channel=5, relay_num=2, setpoint=25.0, device_id=1)  # High alarm
```

### Enable/Disable Relays
```python
# Enable relay for a channel
control.enable_relay(channel=5, relay_num=1, enabled=True, device_id=1)

# Disable relay for a channel
control.enable_relay(channel=7, relay_num=2, enabled=False, device_id=1)
```

## Device Commands

### Reset/Reboot
```python
# Soft reset (reboot device)
control.reset_device(device_id=1)

# Factory reset (restore all defaults) - USE WITH CAUTION
control.factory_reset(device_id=1)
```

## Timing Data

### Seconds Since Last Message
```python
# Get seconds since last message from a sensor (radio communication timing)
seconds = control.get_seconds_since_message(channel=5, device_id=1)

# Return values:
# -1 = Never received message
# 0 = Timeout (no recent message)
# Positive = Seconds since last message
```

### Days Since Last Null
```python
# Get days since channel was last nulled
# NOTE: Only available on OI-7010/7032, returns -1 on OI-7530
days = control.get_days_since_null(channel=5, device_id=1)

# Return values:
# 0-65534 = Days since last null
# 65535 = Never nulled (or invalid)
# -1 = Not supported on this model or error
```

### Days Since Last Calibration
```python
# Get days since channel was last calibrated
# NOTE: Only available on OI-7010/7032, returns -1 on OI-7530
days = control.get_days_since_calibration(channel=5, device_id=1)

# Return values:
# 0-65534 = Days since last calibration
# 65535 = Never calibrated (or invalid)
# -1 = Not supported on this model or error
```

## Information Retrieval

### Device Information
```python
info = control.get_device_info(device_id=1)
print(f"Serial: {info.serial_number}")
print(f"Network Channel: {info.network_channel}")
print(f"Mode: {'Primary' if info.is_primary else 'Secondary'}")
print(f"Radio Timeout: {info.radio_timeout_minutes} min")
```

### Diagnostics
```python
diag = control.get_diagnostics(device_id=1)
print(f"Uptime: {diag.uptime_string}")
print(f"Serial Error Rate: {diag.serial_error_rate:.2%}")
print(f"Radio Error Rate: {diag.radio_error_rate:.2%}")
```

### Relay Status
```python
relay = control.get_relay_status(device_id=1)
print(f"Relay 1: {'On' if relay.relay1_on else 'Off'}")
print(f"Relay 2: {'On' if relay.relay2_on else 'Off'}")
print(f"Relay 3: {'On' if relay.relay3_on else 'Off'}")
```

## Complete API Reference

### DeviceControl Methods

#### Startup Menu Settings (Write)
- `set_network_channel(channel, device_id)` - Set radio network channel (1-78)
- `set_primary_secondary(is_primary, device_id)` - Set Primary/Secondary mode
- `set_radio_timeout(timeout_minutes, device_id)` - Set radio timeout (6-255 min)
- `set_relay3_as_fault(enabled, device_id)` - Configure Relay 3 as fault relay
- `set_relay_failsafe(relay_num, enabled, device_id)` - Set relay fail-safe mode

#### Channel Control (Write)
- `turn_channel_on(channel, device_id)` - Turn channel on (Normal mode)
- `turn_channel_off(channel, device_id)` - Turn channel off
- `set_channel_inhibit(channel, device_id)` - Set Inhibit mode
- `set_channel_mode(channel, mode, device_id)` - Set specific mode (0-7)

#### Relay Control (Write)
- `set_relay_setpoint(channel, relay_num, setpoint, device_id)` - Set alarm setpoint
- `enable_relay(channel, relay_num, enabled, device_id)` - Enable/disable relay

#### Device Commands (Write)
- `reset_device(device_id)` - Soft reset/reboot
- `factory_reset(device_id)` - Restore factory defaults

#### Information (Read)
- `get_device_info(device_id)` - Get device configuration
- `get_diagnostics(device_id)` - Get device diagnostics
- `get_relay_status(device_id)` - Get relay states
- `get_seconds_since_message(channel, device_id)` - Get radio timing
- `get_days_since_null(channel, device_id)` - Get days since last null
- `get_days_since_calibration(channel, device_id)` - Get days since last calibration

## Usage Examples

### Example 1: Configure Device as Secondary on Channel 5
```python
from pipeline.modbus_client import ModbusClient, ModbusConfig
from pipeline.device_control import DeviceControl

config = ModbusConfig(port='COM10', slave_id=2, baudrate=9600)
client = ModbusClient(config)
client.connect()

control = DeviceControl(client)

# Configure OI-7530 as secondary on network channel 5
control.set_primary_secondary(is_primary=False, device_id=2)
control.set_network_channel(5, device_id=2)
control.set_radio_timeout(30, device_id=2)

client.disconnect()
```

### Example 2: Enable H2S Alarm on Channel 1
```python
# Turn on channel 1
control.turn_channel_on(channel=1, device_id=1)

# Enable Relay 1 for channel 1
control.enable_relay(channel=1, relay_num=1, enabled=True, device_id=1)

# Set low alarm at 5 PPM
control.set_relay_setpoint(channel=1, relay_num=1, setpoint=5.0, device_id=1)

# Enable Relay 2 for high alarm
control.enable_relay(channel=1, relay_num=2, enabled=True, device_id=1)

# Set high alarm at 10 PPM
control.set_relay_setpoint(channel=1, relay_num=2, setpoint=10.0, device_id=1)
```

### Example 3: Check Sensor Communication and Maintenance Status
```python
# Check all active channels
for channel in [5, 7, 16, 21, 32]:
    seconds = control.get_seconds_since_message(channel, device_id=1)
    days_null = control.get_days_since_null(channel, device_id=1)
    days_cal = control.get_days_since_calibration(channel, device_id=1)
    
    print(f"Channel {channel}:")
    
    if seconds == -1:
        print(f"  Radio: Never received message")
    elif seconds == 0:
        print(f"  Radio: TIMEOUT!")
    else:
        print(f"  Radio: Last message {seconds}s ago")
    
    if days_null < 65535:
        print(f"  Last Null: {days_null} days ago")
    else:
        print(f"  Last Null: Never")
    
    if days_cal < 65535:
        print(f"  Last Cal: {days_cal} days ago")
    else:
        print(f"  Last Cal: Never")
```

## Interactive Demo

Run the interactive demonstration:
```bash
python device_control_demo.py
```

This provides an interactive menu to:
- View current settings
- View channel status
- Change network settings
- Control channels
- Configure relays
- Test all control functions

## Register Map Summary

| Function | Register Range | Type | Access |
|----------|---------------|------|--------|
| Radio Addresses | 0x01-0x20 | Uint16 | R/W |
| Readings | 0x21-0x5F | Float32 | R |
| Modes | 0x61-0x80 | Uint16 | R/W |
| Battery | 0x81-0xBF | Float32 | R |
| Sec Since Msg | 0xC1-0xE0 | Int16 | R |
| Sensor Types | 0xE1-0x100 | Uint16 | R |
| Gas Types | 0x101-0x120 | Uint16 | R |
| Faults | 0x121-0x140 | Uint16 | R |
| Relay 1 Enable | 0x161-0x180 | Uint16 | R/W |
| Relay 1 Setpoint | 0x1A1-0x1DF | Float32 | R/W |
| Relay 2 Enable | 0x201-0x220 | Uint16 | R/W |
| Relay 2 Setpoint | 0x221-0x25F | Float32 | R/W |
| Relay 3 Enable | 0x2A1-0x2C0 | Uint16 | R/W |
| Relay 3 Setpoint | 0x2C1-0x2FF | Float32 | R/W |
| Days Since Null | 0x3E1-0x400 | Uint16 | R (7010/7032 only) |
| Days Since Cal | 0x401-0x420 | Uint16 | R (7010/7032 only) |
| Device Config | 0x1771-0x1787 | Various | R/W |
| Diagnostics | 0x2704-0x270F | Various | R |

## Notes

### Model Compatibility
**Important:** The OI-7010, OI-7530, and OI-7032 have different register maps:
- **OI-7010/7032** use the same register map (OI-7010-32-RegMap.pdf)
- **OI-7530** uses a different register map (7500-RegMap.csv)

Some registers are only available on certain models:
- Days since null/calibration registers (0x3E1, 0x401) are **only available on OI-7010/7032**
- The OI-7530 does not have these registers

### Calibration/Null Timing
The OI-7010 and OI-7032 monitors track calibration and null history automatically:
- **Days Since Last Null** (0x3E1-0x400): Per-channel register showing days since last null operation
- **Days Since Last Cal** (0x401-0x420): Per-channel register showing days since last calibration

**OI-7530 Note:** These registers do not exist on the OI-7530. Methods will return -1 when queried.

### Safety Considerations
- Test on ONE device before deploying to all three
- Factory reset ERASES ALL CONFIGURATION - use with extreme caution
- Changing network channel may cause loss of communication with wireless sensors
- Setting incorrect relay setpoints may cause false alarms
- Always verify settings after writes
