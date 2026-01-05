# Laird RM024 Binary Protocol (0xCC) Guide

## Overview

The Laird RM024 radios support a **binary command protocol** that works regardless of:
- RF Packet Size settings
- Pin 15 (CMD/Data) state
- Auto Config enabled/disabled
- Traffic patterns or timing

This is the protocol used by the Laird Configuration Utility and is **ALWAYS available**.

## Critical Timing Requirement

**Interface Timeout**: All bytes of a command must arrive within **600µs** with no gaps > 600µs between bytes.

**Implementation**: Send entire command as ONE `write()` operation:
```python
# ✓ CORRECT - atomic write
command = bytes([0xCC, 0x00, 0x00])
serial.write(command)

# ✗ WRONG - byte gaps may exceed 600µs
serial.write(bytes([0xCC]))
serial.write(bytes([0x00]))
serial.write(bytes([0x00]))
```

## Command Mode Entry/Exit

### Enter Command Mode
```
Send:     41 54 2B 2B 2B 0D    ("AT+++\r")
Receive:  CC 43 4F 4D          (0xCC + "COM")
```

**Python Example:**
```python
command = bytes([0x41, 0x54, 0x2B, 0x2B, 0x2B, 0x0D])
serial.write(command)
serial.flush()

# Wait for response
response = serial.read(4)
if response == bytes([0xCC, 0x43, 0x4F, 0x4D]):
    print("✓ In command mode")
```

### Exit Command Mode
```
Send:     CC 41 54 4F 0D       (0xCC + "ATO\r")
Receive:  CC 44 41 54          (0xCC + "DAT")
```

**Python Example:**
```python
command = bytes([0xCC, 0x41, 0x54, 0x4F, 0x0D])
serial.write(command)
serial.flush()

response = serial.read(4)
if response == bytes([0xCC, 0x44, 0x41, 0x54]):
    print("✓ Exited to transparent mode")
```

## Status Commands

### Status Request
Gets firmware version and link status.

```
Send:     CC 00 00
Receive:  CC <Firmware> <Status>
```

**Status Byte Values:**
- `0x01` = Client not in Range
- `0x02` = Server
- `0x03` = Client in Range

**Example:**
```python
command = bytes([0xCC, 0x00, 0x00])
serial.write(command)

response = serial.read(3)
firmware = response[1]  # 0x25 = v2.5
status = response[2]    # 0x03 = Client in Range
```

### RSSI Request
Gets received signal strength indicator.

```
Send:     CC 22
Receive:  CC <RSSI>
```

RSSI values: 0-199 (higher = better signal)

### Temperature Request
Gets radio module temperature.

```
Send:     CC A4
Receive:  CC <Temp_MSB> <Temp_LSB>
```

Temperature in °C = (MSB * 256 + LSB) - 273

## EEPROM Commands

### Read EEPROM
```
Send:     CC C0 <Start> <Length>
Receive:  CC <Start> <Length> <Data...>
```

**Example - Read Channel (address 0x40):**
```python
command = bytes([0xCC, 0xC0, 0x40, 0x01])  # Read 1 byte at 0x40
serial.write(command)

response = serial.read(4)  # CC + Start + Length + Data
channel = response[3]
print(f"Channel: {channel}")
```

### Write EEPROM
```
Send:     CC C1 <Start> <Length> <Data...>
Receive:  <Start> <Length> <LastByte>
```

**Example - Write Channel 76:**
```python
command = bytes([0xCC, 0xC1, 0x40, 0x01, 0x4C])  # Write 0x4C (76) to 0x40
serial.write(command)

response = serial.read(3)
if response == bytes([0x40, 0x01, 0x4C]):
    print("✓ Channel updated")
    # Must reset radio for change to take effect
```

## On-the-Fly Commands

These commands take effect immediately (no EEPROM write, not persistent).

### Change Channel
```
Send:     CC 02 <Channel>
Receive:  CC <Channel>
```

Valid channels: 0-77 (for 79-hop profile)

**Example:**
```python
# Temporarily switch to channel 12
command = bytes([0xCC, 0x02, 0x0C])
serial.write(command)

response = serial.read(2)
if response == bytes([0xCC, 0x0C]):
    print("✓ Switched to channel 12 (temporary)")
```

### Set Server/Client Mode
```
Send:     CC 03 <Mode>
Receive:  CC <Mode>
```

Mode values:
- `0x01` = Server
- `0x02` = Client

### Set Broadcast Mode
```
Send:     CC 08 <Mode>
Receive:  CC <Mode>
```

Mode values:
- `0x00` = Normal
- `0x01` = Broadcast

### Set Output Power
```
Send:     CC 25 <Power>
Receive:  CC <Power>
```

Power values: 0-30 (dBm, depending on model)

## Reset Commands

### Soft Reset
Restarts radio with current EEPROM configuration.

```
Send:     CC FF
Receive:  (none - radio resets)
```

**Example:**
```python
command = bytes([0xCC, 0xFF])
serial.write(command)
time.sleep(1.0)  # Wait for radio to restart
# Radio will return to transparent mode after reset
```

### Factory Reset
Restarts with factory default configuration.

```
Send:     CC FF DF
Receive:  (none - radio resets to defaults)
```

**⚠️ WARNING**: This erases all configuration! Use with caution.

## Firmware Upgrade Commands

**Requirements:**
- Firmware version 1.3 or above
- Encrypted binary firmware files (from Ezurio/Laird)
- Must be in command mode
- Radio will disconnect from network during upgrade

### Firmware Upgrade Process

**Complete workflow to upgrade RM024 firmware:**

```python
# 1. Enter command mode
serial.write(bytes([0x41, 0x54, 0x2B, 0x2B, 0x2B, 0x0D]))
assert serial.read(4) == bytes([0xCC, 0x43, 0x4F, 0x4D])

# 2. Erase existing flash
serial.write(bytes([0xCC, 0xC6]))
assert serial.read(2) == bytes([0xCC, 0xC6])

# 3. Write firmware binary (in chunks)
with open('rm024_fw_v25[00].bin', 'rb') as f:
    address = 0x0000
    chunk_size = 128  # Write 128 bytes at a time
    
    while True:
        data = f.read(chunk_size)
        if not data:
            break
        
        # Write chunk
        addr_msb = (address >> 8) & 0xFF
        addr_lsb = address & 0xFF
        len_msb = (len(data) >> 8) & 0xFF
        len_lsb = len(data) & 0xFF
        
        cmd = bytes([0xCC, 0xC4, addr_msb, addr_lsb, len_msb, len_lsb]) + data
        serial.write(cmd)
        
        response = serial.read(5)
        assert response[2] == 0x00  # Check result byte
        
        # Verify write (optional but recommended)
        cmd = bytes([0xCC, 0xC9, addr_msb, addr_lsb, len_msb, len_lsb])
        serial.write(cmd)
        verify = serial.read(5 + len(data))
        assert verify[5:5+len(data)] == data
        
        address += len(data)
        print(f"Progress: {address} bytes written")

# 4. Decrypt the firmware image
serial.write(bytes([0xCC, 0xC5]))
response = serial.read(3)
assert response == bytes([0xCC, 0xC5, 0x00])  # 0x00 = success

# 5. Reset radio to activate new firmware
serial.write(bytes([0xCC, 0xFF]))
time.sleep(2.0)  # Wait for radio to restart

# 6. Verify upgrade (after reconnect and enter command mode)
serial.write(bytes([0x41, 0x54, 0x2B, 0x2B, 0x2B, 0x0D]))
serial.read(4)
serial.write(bytes([0xCC, 0x00, 0x02]))
response = serial.read(3)
print(f"Firmware: 0x{response[1]:02X}, Status: 0x{response[2]:02X}")

# 7. Repeat steps 2-6 for additional binary files if present
```

### Erase Flash

Erases firmware image from flash memory.

```
Send:     CC C6
Receive:  CC C6
```

**Memory regions:**
- `0x0000-0x7FF`: Erased immediately
- `0x800-0x3BFF`: Erased automatically on first write to this range (300ms delay)

**⚠️ Note:** Radio disconnects from network during upgrade process.

**Example:**
```python
command = bytes([0xCC, 0xC6])
serial.write(command)

response = serial.read(2)
if response == bytes([0xCC, 0xC6]):
    print("✓ Flash erased")
```

### Write Flash

Writes encrypted firmware data to flash.

```
Send:     CC C4 <Addr_MSB> <Addr_LSB> <Len_MSB> <Len_LSB> <Data...>
Receive:  CC C4 <Result> <Addr_MSB> <Addr_LSB>
```

**Parameters:**
- Address: `0x0000 - 0x3BFF` (16-bit)
- Length: `1 - 255` bytes per write
- Data: Encrypted firmware bytes

**Result codes:**
- `0x00` = No Error
- `0x03` = Command Timed Out
- `0x04` = Valid image exists (must erase first)
- `0x06` = Bounds Exceeded

**Example:**
```python
# Write 128 bytes starting at address 0x0000
data = encrypted_firmware[0:128]
address = 0x0000

addr_msb = (address >> 8) & 0xFF
addr_lsb = address & 0xFF
len_msb = (len(data) >> 8) & 0xFF
len_lsb = len(data) & 0xFF

command = bytes([0xCC, 0xC4, addr_msb, addr_lsb, len_msb, len_lsb]) + data
serial.write(command)

response = serial.read(5)
result = response[2]
if result == 0x00:
    print("✓ Write successful")
```

**⚠️ Important:** First write to address `0x800` or above causes 300ms delay while erasing upper memory region.

### Read Flash

Reads encrypted firmware data from flash (for verification).

```
Send:     CC C9 <Addr_MSB> <Addr_LSB> <Len_MSB> <Len_LSB>
Receive:  CC C9 <Result> <Addr_MSB> <Addr_LSB> <Data...>
```

**Parameters:**
- Address: `0x0000 - 0x3AFF` (16-bit)
- Length: `1 - 700` bytes (depends on heap memory)

**Result codes:**
- `0x00` = No Error
- `0x02` = Not Enough Free Memory (try shorter length)
- `0x03` = Command Timed Out
- `0x04` = Image Already Decrypted (cannot read after decrypt)
- `0x06` = Bounds Exceeded

**Example:**
```python
# Read 128 bytes from address 0x0000 to verify write
address = 0x0000
length = 128

addr_msb = (address >> 8) & 0xFF
addr_lsb = address & 0xFF
len_msb = (length >> 8) & 0xFF
len_lsb = length & 0xFF

command = bytes([0xCC, 0xC9, addr_msb, addr_lsb, len_msb, len_lsb])
serial.write(command)

response = serial.read(5 + length)
result = response[2]
if result == 0x00:
    data = response[5:5+length]
    print(f"✓ Read {len(data)} bytes")
```

### Decrypt Image

Decrypts downloaded firmware image in flash.

```
Send:     CC C5
Receive:  CC C5 <Result>
```

**Result codes:**
- `0x00` = No Error (image ready, will load on next reboot)
- `0x01` = File integrity error (erase flash and retry download)
- `0x02` = Not enough memory (reset module and retry)
- `0x04` = Image Already Decrypted

**Example:**
```python
command = bytes([0xCC, 0xC5])
serial.write(command)

response = serial.read(3)
result = response[2]
if result == 0x00:
    print("✓ Firmware decrypted (will activate on reset)")
```

**⚠️ Note:** Once decrypted, image cannot be read from flash. Next reboot loads new firmware into active memory.

### Verify Firmware Upgrade

Verifies all firmware pages were upgraded successfully.

```
Send:     CC 00 02
Receive:  CC <Firmware> <Status>
```

Should be called after firmware upgrade and reset. If this reports an error, one or more binary files failed to upgrade - locate and retry.

**Example:**
```python
# After reset and re-entering command mode
command = bytes([0xCC, 0x00, 0x02])
serial.write(command)

response = serial.read(3)
if len(response) == 3 and response[0] == 0xCC:
    firmware = response[1]
    status = response[2]
    print(f"✓ Firmware: v{firmware/16:.1f}, Status: 0x{status:02X}")
else:
    print("✗ Firmware verification failed - retry upgrade")
```

## Firmware Binary Files

RM024 firmware may consist of multiple binary files:
- `rm024_fw_v25[00].bin` - Primary image (must be loaded first)
- `rm024_fw_v25[01].bin` - Secondary image (if present)
- `rm024_fw_v25[XX].bin` - Additional pages (if present)

**Upgrade order:**
1. Load `[00]` file (primary)
2. Decrypt and reset
3. Verify with `CC 00 02`
4. If error, load corresponding `[XX]` file and repeat

**File naming:** The `[XX]` number in the filename corresponds to the page that failed verification.

## EEPROM Address Map

Key configuration addresses:

| Address | Description | Default |
|---------|-------------|---------|
| 0x40 | RF Channel | Varies |
| 0x41 | Mode (Server/Client) | 0x02 (Client) |
| 0x42 | Baud Rate | 0x09 (115200) |
| 0x54 | RF Profile | 0x00 |
| 0x56 | Control1 (Auto Config) | 0x41 |
| 0x57 | Control2 (9600 Boot) | 0x01 |
| 0x58 | Interface Timeout | 0x03 (600µs) |
| 0x5A | RF Packet Size | 0x60 (96 bytes) |
| 0x76 | System ID (MSB) | 0x0E |
| 0x77 | System ID (LSB) | 0x01 |
| 0xC1 | API Control | 0x00 (Disabled) |

### API Control Register (0xC1)

Controls API operation mode features (bit field):

**Bit 0: API Receive Packet**
- When enabled, received packets include source MAC address and RSSI
- Format: `0xCC <SrcMAC[3:0]> <RSSI> <Data...>`
- Useful for identifying packet source in multi-radio networks

**Bit 1: API Transmit Packet**
- When enabled, OEM host must prepend destination MAC to transmitted data
- Format: `0xCC <DestMAC[3:0]> <Data...>`
- Allows packet-by-packet destination control
- Destination `0xFF 0xFF 0xFF 0xFF` = broadcast to all radios

**Bit 2: API Send Data Complete**
- When enabled, radio sends acknowledgement status after each transmission
- Format: `0xCC <Status> <SentMAC[3:0]>`
- Status: `0x00` = success (ACK received), `0x01` = failure (no ACK)
- Provides software acknowledgement indicator for addressed packets

**Example values:**
- `0x00` = All API features disabled (transparent mode)
- `0x01` = API Receive only (bit 0)
- `0x02` = API Transmit only (bit 1)
- `0x03` = API Receive + Transmit (bits 0-1)
- `0x04` = API Send Complete only (bit 2)
- `0x07` = All API features enabled (bits 0-2)

## Complete Command Reference

### Entry/Exit
- `41 54 2B 2B 2B 0D` - Enter command mode
- `CC 41 54 4F 0D` - Exit command mode

### Status/Info
- `CC 00 00` - Status request (FW + Link)
- `CC 00 02` - Verify firmware upgrade
- `CC 22` - RSSI request
- `CC A4` - Temperature request

### On-the-Fly
- `CC 02 <Ch>` - Change channel (temporary)
- `CC 03 <Mode>` - Server/Client mode (temporary)
- `CC 08 <Mode>` - Broadcast mode (temporary)
- `CC 25 <Pwr>` - Output power (temporary)

### EEPROM
- `CC C0 <Start> <Len>` - Read EEPROM
- `CC C1 <Start> <Len> <Data>` - Write EEPROM

### Firmware Upgrade (FW 1.3+)
- `CC C6` - Erase flash
- `CC C4 <Addr_MSB> <Addr_LSB> <Len_MSB> <Len_LSB> <Data>` - Write flash
- `CC C9 <Addr_MSB> <Addr_LSB> <Len_MSB> <Len_LSB>` - Read flash (verify)
- `CC C5` - Decrypt firmware image

### Reset
- `CC FF` - Soft reset (apply EEPROM changes)
- `CC FF DF` - Factory reset (⚠️ erases all config)

## Usage Workflow

### Read Configuration
```python
# 1. Connect to radio
serial = serial.Serial('COM7', 115200, rtscts=True)

# 2. Enter command mode
serial.write(bytes([0x41, 0x54, 0x2B, 0x2B, 0x2B, 0x0D]))
response = serial.read(4)  # Expect CC 43 4F 4D

# 3. Get status
serial.write(bytes([0xCC, 0x00, 0x00]))
status = serial.read(3)

# 4. Read channel
serial.write(bytes([0xCC, 0xC0, 0x40, 0x01]))
channel_data = serial.read(4)

# 5. Exit command mode
serial.write(bytes([0xCC, 0x41, 0x54, 0x4F, 0x0D]))
serial.read(4)  # Expect CC 44 41 54
```

### Write Configuration
```python
# 1. Enter command mode (same as above)

# 2. Write new channel (76 = 0x4C)
serial.write(bytes([0xCC, 0xC1, 0x40, 0x01, 0x4C]))
verify = serial.read(3)  # Expect 40 01 4C

# 3. Soft reset to apply
serial.write(bytes([0xCC, 0xFF]))
time.sleep(1.0)  # Wait for restart

# Radio now on channel 76 in transparent mode
```

### Temporary Channel Scan
```python
# 1. Enter command mode

# 2. Scan channels 10-15 for 5 seconds each
for ch in range(10, 16):
    # Change channel temporarily
    serial.write(bytes([0xCC, 0x02, ch]))
    response = serial.read(2)
    
    # Exit and listen for sensor traffic
    serial.write(bytes([0xCC, 0x41, 0x54, 0x4F, 0x0D]))
    serial.read(4)
    
    # Listen for 5 seconds
    time.sleep(5.0)
    data = serial.read(serial.in_waiting)
    print(f"Ch {ch}: {len(data)} bytes received")
    
    # Re-enter command mode for next channel
    serial.write(bytes([0x41, 0x54, 0x2B, 0x2B, 0x2B, 0x0D]))
    serial.read(4)
```

## Advantages Over +++ String

The binary protocol:
- ✓ Works with Auto Config enabled
- ✓ Works regardless of RF Packet Size
- ✓ Doesn't require traffic gaps
- ✓ Doesn't need guard times (1.3s each)
- ✓ No Pin 15 hardware signal needed
- ✓ Can be sent any time (respects 600µs timeout)
- ✓ Used by official Laird Configuration Utility

The +++ string:
- ✗ Disabled when RF Packet Size < 7
- ✗ Disabled when Auto Config enabled
- ✗ Requires 1.3s guard times before/after
- ✗ Needs traffic gaps (2.6s minimum)
- ✗ Can be disabled by Pin 15 LOW

## Integration in OI-7500 Pipeline

The binary protocol is now integrated in `web_gui/app.py`:

**Functions:**
- `enter_radio_command_mode(radio)` - Uses `41 54 2B 2B 2B 0D`
- `exit_radio_command_mode(radio)` - Uses `CC 41 54 4F 0D`
- `read_radio_eeprom(radio, addr, length)` - Uses `CC C0`
- `write_radio_eeprom(radio, addr, data)` - Uses `CC C1`
- `get_radio_status(radio)` - Uses `CC 00 00`

**Test Script:**
- `test_binary_protocol.py` - Complete test suite for both radios

## References

- Laird RM024 Command Reference Manual
- RM024 EEPROM Parameter Specification
- User-provided documentation (January 5, 2026)
- Test results from COM7 (Ch 76) and COM11 (Ch 12)
