# RM024 Firmware Upgrade Capability

## Overview

The binary protocol implementation now includes **complete firmware upgrade capability** for RM024 radios. This allows programmatic firmware updates without requiring the Laird Configuration Utility.

## Firmware Upgrade Commands Added

### Implementation

All firmware upgrade commands have been added to `test_binary_protocol.py`:

**LairdRM024 class methods:**
- ✅ `erase_flash()` - Erase firmware image from flash
- ✅ `write_flash(addr, data)` - Write encrypted firmware bytes
- ✅ `read_flash(addr, length)` - Read back for verification
- ✅ `decrypt_image()` - Decrypt downloaded firmware
- ✅ `verify_firmware_upgrade()` - Verify all pages upgraded

**Binary commands:**
```python
0xCC 0xC6                                  # Erase flash
0xCC 0xC4 <Addr_MSB> <Addr_LSB> <Len> <Data>  # Write flash
0xCC 0xC9 <Addr_MSB> <Addr_LSB> <Len>     # Read flash
0xCC 0xC5                                  # Decrypt image
0xCC 0x00 0x02                             # Verify upgrade
```

## Firmware Upgrade Utility

Created `firmware_upgrade.py` - a complete command-line utility for upgrading RM024 firmware.

**Features:**
- Automatic erase/write/verify/decrypt workflow
- Progress indicator with byte counts and percentage
- Chunk-based writing (configurable, default 128 bytes)
- Automatic write verification after each chunk
- Retry logic for failed writes (up to 3 retries)
- Multi-file support (for radios with multiple firmware pages)
- Safety prompts and warnings
- Detailed logging of upgrade process

**Usage:**
```bash
# Single firmware file
python firmware_upgrade.py COM7 rm024_fw_v25[00].bin

# Multiple files (if radio requires additional pages)
python firmware_upgrade.py COM11 rm024_fw_v25[00].bin rm024_fw_v25[01].bin
```

**Output example:**
```
======================================================================
RM024 Firmware Upgrade Utility
======================================================================

Port: COM7
Firmware files: 1
  1. rm024_fw_v25[00].bin

⚠ WARNING: Firmware upgrade process will:
  - Disconnect radio from network
  - Erase existing firmware
  - Take several minutes to complete
  - Require radio reset

Proceed with upgrade? (yes/no): yes

======================================================================
Upgrading firmware from: rm024_fw_v25[00].bin
File size: 12345 bytes
Chunk size: 128 bytes
======================================================================

1. Connecting to radio...
✓ Connected to COM7 @ 115200 baud

2. Entering command mode...
✓ Entered command mode (received: CC 43 4F 4D)

3. Erasing flash memory...
   ⚠ Radio will disconnect from network
✓ Flash erased successfully

4. Writing firmware binary (12345 bytes)...
   This may take several minutes...
   Progress: [==================================================] 100.0% (12345/12345 bytes)

   ✓ Wrote 12345 bytes successfully

5. Decrypting firmware image...
✓ Image decrypted successfully (will load on next reboot)

6. Resetting radio to activate new firmware...
✓ Soft reset sent (radio restarting)
   Waiting for radio to restart...

7. Verifying firmware upgrade...
✓ Firmware upgrade verified: FW=0x25, Status=0x03

✓ Firmware upgrade completed successfully!
   New firmware version: v2.5

======================================================================
Firmware Upgrade Summary
======================================================================
  Files processed: 1
  Successful: 1
  Failed: 0

🎉 All firmware files upgraded successfully!
======================================================================
```

## Upgrade Process Details

### Step-by-Step Workflow

**1. Preparation**
- Connect to radio serial port (115200, 8-N-1, Hardware handshaking)
- Enter command mode using binary protocol
- Radio must have firmware v1.3 or above

**2. Erase Flash**
```python
command = bytes([0xCC, 0xC6])
serial.write(command)
response = serial.read(2)  # Expect: CC C6
```
- Erases memory regions 0x0000-0x7FF immediately
- Upper region 0x800-0x3BFF erased on first write (300ms delay)
- Radio disconnects from network during this process

**3. Write Firmware Binary**
```python
# Write in chunks (128 bytes recommended)
for chunk in firmware_chunks:
    addr_msb = (address >> 8) & 0xFF
    addr_lsb = address & 0xFF
    len_msb = (len(chunk) >> 8) & 0xFF
    len_lsb = len(chunk) & 0xFF
    
    cmd = bytes([0xCC, 0xC4, addr_msb, addr_lsb, len_msb, len_lsb]) + chunk
    serial.write(cmd)
    
    response = serial.read(5)  # CC C4 <Result> <Addr_MSB> <Addr_LSB>
    assert response[2] == 0x00  # Check result = no error
```

**4. Verify Writes (Highly Recommended)**
```python
# Read back what was written
cmd = bytes([0xCC, 0xC9, addr_msb, addr_lsb, len_msb, len_lsb])
serial.write(cmd)

response = serial.read(5 + len(chunk))
data = response[5:]
assert data == chunk  # Verify match
```

**5. Decrypt Image**
```python
command = bytes([0xCC, 0xC5])
serial.write(command)
response = serial.read(3)  # CC C5 <Result>
assert response[2] == 0x00  # Success
```
- Once decrypted, image cannot be read
- Next reboot loads new firmware into active memory

**6. Reset and Verify**
```python
# Soft reset
command = bytes([0xCC, 0xFF])
serial.write(command)
time.sleep(3.0)  # Wait for restart

# Re-enter command mode and verify
command = bytes([0x41, 0x54, 0x2B, 0x2B, 0x2B, 0x0D])
serial.write(command)

# Verify all pages upgraded
command = bytes([0xCC, 0x00, 0x02])
serial.write(command)
response = serial.read(3)  # CC <FW> <Status>
```

**7. Multiple Files (If Required)**
- Some radios require multiple binary files
- Primary image `[00]` must be loaded first
- If verification fails, load corresponding `[XX]` file
- Repeat steps 2-6 for each file

## Timing Considerations

**Critical timing constraints:**
- Interface Timeout: 600µs (all command bytes must arrive within this window)
- Flash erase (0x800+): 300ms delay on first write to upper region
- Decrypt operation: ~500ms
- Radio restart: ~2-3 seconds
- Total upgrade time: 5-15 minutes depending on firmware size

**Implementation:**
- Send entire command as ONE `write()` operation
- Use `serial.flush()` after each write
- Include appropriate delays for erase/decrypt/reset operations

## Error Handling

**Write Flash Errors:**
- `0x00` = No Error (success)
- `0x03` = Command Timed Out (retry)
- `0x04` = Valid image exists (must erase first)
- `0x06` = Bounds Exceeded (invalid address/length)

**Read Flash Errors:**
- `0x00` = No Error (success)
- `0x02` = Not Enough Free Memory (reduce read length)
- `0x03` = Command Timed Out (retry)
- `0x04` = Image Already Decrypted (cannot read after decrypt)
- `0x06` = Bounds Exceeded (invalid address/length)

**Decrypt Errors:**
- `0x00` = No Error (success)
- `0x01` = File integrity error (erase and retry download)
- `0x02` = Not enough memory (reset and retry)
- `0x04` = Image Already Decrypted (already done)

**Recovery:**
- If write fails, retry up to 3 times
- If verify fails after retries, abort and inform user
- If decrypt fails with integrity error, erase and re-download
- If verification after reset fails, load additional `[XX]` binary files

## Safety Features

**Built-in safeguards:**
1. **Verification after every write** - Catches corruption early
2. **Retry logic** - Handles transient errors
3. **User confirmation** - Prevents accidental upgrades
4. **Progress monitoring** - Shows byte-level progress
5. **Error reporting** - Detailed error messages with recovery suggestions
6. **Multi-file support** - Handles complex firmware packages

**Warning prompts:**
- Confirms port and firmware files before starting
- Warns about network disconnection
- Warns about firmware erase
- Warns about expected duration
- Requires explicit "yes" to proceed

## Firmware Binary Files

**File naming convention:**
```
rm024_fw_v25[00].bin  # Primary image (always first)
rm024_fw_v25[01].bin  # Secondary page (if required)
rm024_fw_v25[XX].bin  # Additional pages (if required)
```

**Source:**
- Encrypted binary files from Ezurio (formerly Laird Technologies)
- Cannot create custom firmware (encryption keys required)
- Must use official firmware releases

**File structure:**
- Address range: 0x0000 - 0x3BFF
- Primary image contains core functionality
- Additional pages contain optional features
- Files are encrypted and signed
- Radio validates integrity during decrypt

## Integration with OI-7500 Pipeline

**Current status:**
- ✅ Complete firmware upgrade capability in `test_binary_protocol.py`
- ✅ Standalone utility `firmware_upgrade.py`
- ✅ Full documentation in `BINARY_PROTOCOL_GUIDE.md`
- ⏳ Web GUI integration (future enhancement)

**Potential web interface features:**
- Upload firmware .bin files
- Select radio(s) to upgrade
- Real-time progress bar
- Multi-radio batch upgrades
- Automatic verification
- Firmware version display

## Testing

**Test with current radios:**
```bash
# DO NOT run unless you have firmware files!
python firmware_upgrade.py COM7 rm024_fw_v25[00].bin
```

**⚠️ WARNING:** Only test with legitimate firmware files from Ezurio. Attempting to load invalid firmware will brick the radio and require hardware recovery.

**Pre-flight checks:**
1. Verify radio is on firmware v1.3 or above (`CC 00 00` command)
2. Verify you have correct firmware files for your radio model
3. Ensure stable serial connection (hardware flow control enabled)
4. Backup current radio configuration (read all EEPROM)
5. Have Laird Configuration Utility available as fallback

## Documentation Created

1. **BINARY_PROTOCOL_GUIDE.md** - Updated with:
   - Firmware upgrade commands section
   - Complete upgrade workflow with code
   - Error codes and recovery procedures
   - Safety warnings and best practices

2. **test_binary_protocol.py** - Added methods:
   - `erase_flash()` - Erase firmware memory
   - `write_flash(addr, data)` - Write firmware chunks
   - `read_flash(addr, length)` - Read for verification
   - `decrypt_image()` - Decrypt downloaded firmware
   - `verify_firmware_upgrade()` - Post-upgrade verification

3. **firmware_upgrade.py** - NEW utility:
   - Complete command-line tool
   - Automatic workflow with error handling
   - Progress tracking and verification
   - Multi-file support

4. **FIRMWARE_UPGRADE.md** - This document

## Benefits

**Advantages over Laird Configuration Utility:**
- ✅ Scriptable/automatable
- ✅ Batch upgrades possible
- ✅ Remote upgrade capability
- ✅ Integration with OI-7500 system
- ✅ Custom progress monitoring
- ✅ Logging and auditing
- ✅ No Windows dependency (Python only)

**Use cases:**
- Field upgrades of deployed radios
- Automated firmware management
- Factory provisioning
- Remote sensor network maintenance
- Batch upgrades of multiple radios
- Custom upgrade workflows

## Summary

The RM024 binary protocol implementation now includes **complete firmware upgrade capability**:

**Commands:** 5 firmware upgrade commands (erase, write, read, decrypt, verify)  
**Utility:** `firmware_upgrade.py` with automatic workflow  
**Safety:** Built-in verification, retry logic, user confirmation  
**Documentation:** Complete upgrade guide with examples  

Your OI-7500 pipeline can now **programmatically upgrade RM024 firmware** without requiring the Windows-only Laird Configuration Utility! 🚀
