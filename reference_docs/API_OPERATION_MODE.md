# RM024 API Operation Mode

## Overview

API Operation Mode is an alternative to the default **Transparent Mode** that provides dynamic packet accounting and routing capabilities. API mode uses specific packet formats with `0xCC` frame delimiters and can include source MAC addresses, RSSI values, and destination addressing.

## Transparent vs API Mode

| Feature | Transparent Mode | API Mode |
|---------|-----------------|----------|
| Packet Format | Raw data only | `0xCC` + headers + data |
| Source MAC | Not included | Optional (bit 0) |
| RSSI | Not included | Optional (bit 0) |
| Destination | System ID based | Per-packet (bit 1) |
| ACK Status | Transparent to host | Optional feedback (bit 2) |
| Use Case | Simple cable replacement | Advanced routing/mesh |

## API Control Register (0xC1)

Controls which API features are enabled via bit field:

```
Bit 7-3: Reserved (0)
Bit 2:   API Send Data Complete (ACK feedback)
Bit 1:   API Transmit Packet (per-packet addressing)
Bit 0:   API Receive Packet (source MAC + RSSI)
```

**Read/Write via EEPROM:**
```python
# Read current API Control
api_control = read_radio_eeprom(radio, 0xC1, 1)[0]

# Enable API Receive Packet (bit 0)
write_radio_eeprom(radio, 0xC1, api_control | 0x01)

# Reset radio for changes to take effect
soft_reset(radio)
```

## API Features

### 1. API Receive Packet (Bit 0)

**Purpose:** Include source MAC address and RSSI in received packets.

**When Enabled:**
- All received RF packets include sender's MAC address
- RSSI value included for link quality monitoring
- Useful for multi-radio networks where origin tracking is needed

**Packet Format:**
```
0xCC <SrcMAC[3]> <SrcMAC[2]> <SrcMAC[1]> <SrcMAC[0]> <RSSI> <Payload Data...>
```

**Example:**
```python
# Received packet with source MAC 00:50:67:E0:86:EB
received = b'\xCC\x00\x50\x67\xE0\x86\xEB\x75\x81\x11...'
#            ^    ^^^^^^^^^^^^^^^^^^^^^^^^^  ^   ^^^^^^
#            |    Source MAC (4 bytes)       |   Payload
#            CC                            RSSI (117)

frame_delim = received[0]     # 0xCC
src_mac = received[1:5]       # 00 50 67 E0 (last 4 bytes of full MAC)
rssi = received[5]            # 117 (0-199 scale, higher = better)
payload = received[6:]        # Actual sensor data

print(f"From: {src_mac.hex()}, RSSI: {rssi}, Data: {payload.hex()}")
# Output: From: 005067e0, RSSI: 117, Data: 8111...
```

**RSSI Scale:**
- Range: 0-199
- Higher value = better signal
- Typical: 100-150 = good, 50-100 = fair, <50 = poor

**Enable:**
```python
# Read current value
api_control = read_radio_eeprom(radio, 0xC1, 1)[0]

# Enable API Receive (bit 0)
api_control |= 0x01

# Write back
write_radio_eeprom(radio, 0xC1, api_control)
soft_reset(radio)  # Apply changes
```

### 2. API Transmit Packet (Bit 1)

**Purpose:** Specify destination MAC address on a per-packet basis.

**When Enabled:**
- OEM host must prepend destination MAC to each transmitted packet
- Allows dynamic routing without changing System ID
- Broadcast capability via `FF FF FF FF` destination

**Packet Format (Transmit):**
```
0xCC <DestMAC[3]> <DestMAC[2]> <DestMAC[1]> <DestMAC[0]> <Payload Data...>
```

**Example - Send to Specific Radio:**
```python
# Send data to radio with MAC 00:50:67:E0:86:EB
dest_mac = bytes([0x00, 0x50, 0x67, 0xE0])  # Last 4 bytes
payload = b'\x81\x11...'  # Your data

packet = bytes([0xCC]) + dest_mac + payload
serial.write(packet)

# Packet structure:
# CC 00 50 67 E0 81 11 ...
# ^  ^^^^^^^^^^^^ ^^^^^^^^
# |  Dest MAC     Payload
# Frame delimiter
```

**Example - Broadcast to All Radios:**
```python
# Broadcast to all radios on network
dest_mac = bytes([0xFF, 0xFF, 0xFF, 0xFF])
payload = b'Broadcast message'

packet = bytes([0xCC]) + dest_mac + payload
serial.write(packet)

# CC FF FF FF FF 42 72 6F 61 64 ...
# ^  ^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^
# |  Broadcast   "Broadcast..."
# Delimiter
```

**Payload Size:**
- Depends on RF Packet Size and RF Profile
- Auto Config: Maximum for profile (FEC or non-FEC)
- Typical: 80-96 bytes minus 5-byte header = 75-91 bytes payload

**Enable:**
```python
# Read current value
api_control = read_radio_eeprom(radio, 0xC1, 1)[0]

# Enable API Transmit (bit 1)
api_control |= 0x02

# Write back
write_radio_eeprom(radio, 0xC1, api_control)
soft_reset(radio)  # Apply changes
```

### 3. API Send Data Complete (Bit 2)

**Purpose:** Receive acknowledgement status after each addressed transmission.

**When Enabled:**
- Radio sends status packet after each transmission attempt
- Indicates success (ACK received) or failure (no ACK after retries)
- Allows OEM host to monitor packet delivery

**Packet Format (Received from Radio):**
```
0xCC <Status> <SentToMAC[3]> <SentToMAC[2]> <SentToMAC[1]> <SentToMAC[0]>
```

**Status Values:**
- `0x00` = Success (ACK received from destination)
- `0x01` = Failure (no ACK after all retries)

**Example:**
```python
# After sending data to 00:50:67:E0
# Radio sends acknowledgement:
ack_packet = b'\xCC\x00\x00\x50\x67\xE0'
#             ^    ^   ^^^^^^^^^^^^^^^^
#             |    |   MAC of destination
#             |    Success (0x00)
#             Frame delimiter

frame = ack_packet[0]      # 0xCC
status = ack_packet[1]     # 0x00 = success
dest_mac = ack_packet[2:6] # 00 50 67 E0

if status == 0x00:
    print(f"✓ Packet delivered to {dest_mac.hex()}")
else:
    print(f"✗ Packet failed to {dest_mac.hex()} - resend!")
```

**Important Notes:**
- Only applies to addressed packets (not broadcasts)
- Broadcast packets always report success (no ACK expected)
- False negative possible: Receiver may have gotten packet but ACK lost
- False positive NOT possible: Status 0x00 always means ACK was received

**Use Case - Reliable Delivery:**
```python
def send_with_confirmation(serial, dest_mac, payload, max_retries=3):
    """Send packet and wait for acknowledgement."""
    
    packet = bytes([0xCC]) + dest_mac + payload
    
    for attempt in range(max_retries):
        # Send packet
        serial.write(packet)
        serial.flush()
        
        # Wait for acknowledgement (timeout 1s)
        timeout = time.time() + 1.0
        while time.time() < timeout:
            if serial.in_waiting >= 6:
                ack = serial.read(6)
                if ack[0] == 0xCC and ack[2:6] == dest_mac:
                    if ack[1] == 0x00:
                        return True  # Success!
                    else:
                        break  # Failed, retry
            time.sleep(0.01)
        
        print(f"Attempt {attempt+1} failed, retrying...")
    
    return False  # All retries exhausted
```

**Enable:**
```python
# Read current value
api_control = read_radio_eeprom(radio, 0xC1, 1)[0]

# Enable API Send Complete (bit 2)
api_control |= 0x04

# Write back
write_radio_eeprom(radio, 0xC1, api_control)
soft_reset(radio)  # Apply changes
```

## API Mode Combinations

Common configurations:

### Transparent Mode (Default)
```python
# 0xC1 = 0x00 (all bits disabled)
write_radio_eeprom(radio, 0xC1, 0x00)
```
- No API features
- Simple cable replacement
- Raw data in/out
- **Current configuration for OI sensors**

### API Receive Only
```python
# 0xC1 = 0x01 (bit 0 enabled)
write_radio_eeprom(radio, 0xC1, 0x01)
```
- Track source MAC and RSSI of received packets
- Transmit remains simple (no prepended MAC)
- **Good for sensor monitoring with source tracking**

### API Transmit Only
```python
# 0xC1 = 0x02 (bit 1 enabled)
write_radio_eeprom(radio, 0xC1, 0x02)
```
- Prepend destination MAC to outgoing packets
- Receive remains simple (no MAC/RSSI)
- **Good for command transmission to specific sensors**

### API Receive + Transmit
```python
# 0xC1 = 0x03 (bits 0-1 enabled)
write_radio_eeprom(radio, 0xC1, 0x03)
```
- Full per-packet addressing in both directions
- Track all packet sources and destinations
- **Good for mesh networks and advanced routing**

### Full API Mode
```python
# 0xC1 = 0x07 (bits 0-2 enabled)
write_radio_eeprom(radio, 0xC1, 0x07)
```
- All API features enabled
- Maximum control and feedback
- **Good for critical applications requiring delivery confirmation**

## Packet Size Considerations

API mode headers reduce available payload:

**Without API mode:**
- RF Packet Size = 96 bytes
- Payload = 96 bytes

**With API Receive (bit 0):**
- Header = 5 bytes (CC + 4 MAC + RSSI)
- Payload = 91 bytes

**With API Transmit (bit 1):**
- Header = 5 bytes (CC + 4 MAC)
- Payload = 91 bytes

**With Both (bits 0-1):**
- RX Header = 5 bytes
- TX Header = 5 bytes
- Effective payload = 91 bytes each direction

**With Send Complete (bit 2):**
- Adds 6-byte ACK packet after transmission
- Does not reduce payload size
- Additional serial traffic to monitor

## Implementation Example

### Enable API Receive for Sensor Tracking

```python
#!/usr/bin/env python3
"""Enable API Receive mode to track sensor sources."""

from test_binary_protocol import LairdRM024

# Connect to radio
radio = LairdRM024('COM7', 115200)
radio.connect()

# Enter command mode
radio.enter_command_mode()

# Read current API Control
api_control_data = radio.read_eeprom(0xC1, 1)
current = api_control_data[0]
print(f"Current API Control: 0x{current:02X}")

# Enable API Receive Packet (bit 0)
new_value = current | 0x01
radio.write_eeprom(0xC1, new_value)

# Verify
verify = radio.read_eeprom(0xC1, 1)[0]
print(f"New API Control: 0x{verify:02X}")

# Exit and reset
radio.exit_command_mode()
radio.soft_reset()

print("✓ API Receive mode enabled - restarting radio...")
radio.disconnect()
```

### Parse API Receive Packets

```python
def parse_api_receive_packet(data):
    """Parse API Receive packet format.
    
    Format: 0xCC <SrcMAC[3:0]> <RSSI> <Payload>
    """
    if len(data) < 6 or data[0] != 0xCC:
        return None
    
    src_mac = data[1:5]
    rssi = data[5]
    payload = data[6:]
    
    return {
        'src_mac': src_mac.hex(),
        'rssi': rssi,
        'rssi_quality': 'Good' if rssi > 100 else 'Fair' if rssi > 50 else 'Poor',
        'payload': payload
    }

# Usage
received = serial.read(serial.in_waiting)
packet_info = parse_api_receive_packet(received)

if packet_info:
    print(f"Source: {packet_info['src_mac']}")
    print(f"RSSI: {packet_info['rssi']} ({packet_info['rssi_quality']})")
    print(f"Data: {packet_info['payload'].hex()}")
```

### Send to Specific Sensor

```python
def send_to_sensor(serial, sensor_mac, command):
    """Send command to specific sensor via API Transmit.
    
    Args:
        serial: Serial port with API Transmit enabled
        sensor_mac: 4-byte MAC address (last 4 bytes)
        command: Command bytes to send
    """
    # API Transmit format: CC + MAC + Data
    packet = bytes([0xCC]) + sensor_mac + command
    serial.write(packet)
    serial.flush()

# Example: Change sensor to Mode 5 (ATTM5)
sensor_mac = bytes([0x00, 0x50, 0x67, 0xE0])
attm5_command = b'ATTM5\r'

send_to_sensor(serial, sensor_mac, attm5_command)
```

## Advantages of API Mode

**For Sensor Monitoring:**
- ✅ Identify which sensor sent each packet
- ✅ Monitor link quality (RSSI) per sensor
- ✅ Detect sensor failures or weak signals
- ✅ Build signal quality maps

**For Command & Control:**
- ✅ Send commands to specific sensors
- ✅ Broadcast commands to all sensors
- ✅ Verify command delivery with ACK feedback
- ✅ Retry failed commands automatically

**For Mesh Networks:**
- ✅ Dynamic routing per packet
- ✅ No need to change System ID for different destinations
- ✅ Multi-hop capabilities
- ✅ Flexible network topologies

## OI-7500 Integration

**Current Configuration:**
- Radios in **Transparent Mode** (API Control = 0x00)
- 14 sensors transmitting Gen2 packets
- No source MAC in received data
- Simple cable replacement operation

**Potential Enhancement - API Receive:**
```python
# Enable API Receive mode
write_radio_eeprom(radio, 0xC1, 0x01)
soft_reset(radio)

# Update RadioReceiver to parse API packets
def parse_gen2_with_api(data):
    if data[0] == 0xCC:
        # API Receive packet
        src_mac = data[1:5]
        rssi = data[5]
        gen2_packet = data[6:]  # 81 11 ...
        
        # Parse Gen2 packet as before
        parsed = parse_gen2_packet(gen2_packet)
        parsed['radio_mac'] = src_mac.hex()
        parsed['rssi'] = rssi
        return parsed
    else:
        # Regular transparent packet
        return parse_gen2_packet(data)
```

**Benefits:**
- Track which sensor sent each reading
- Monitor sensor signal strength
- Detect sensor movement/relocation
- Alert on weak signals

## References

- RM024 User Guide Section 6: API Operation
- EEPROM Address 0xC1: API Control
- Packet formats and timing specifications
- Integration with OI Gen2 protocol

## Summary

API Operation Mode provides three powerful features:

1. **API Receive** (bit 0) - Track packet source and signal strength
2. **API Transmit** (bit 1) - Address specific radios per packet
3. **API Send Complete** (bit 2) - Monitor delivery confirmation

All controlled via EEPROM address **0xC1** with binary protocol read/write commands.

**Use Cases:**
- Transparent Mode (0x00): Simple sensor reception ✓ **Current**
- API Receive (0x01): Sensor tracking with source MAC
- API Transmit (0x02): Command specific sensors
- Full API (0x07): Advanced mesh networks
