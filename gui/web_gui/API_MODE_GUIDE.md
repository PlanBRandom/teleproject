# Laird Radio API Mode vs Transparent Mode Guide

> **📚 Complete API Documentation:** For detailed information about API Control register (0xC1),
> API Receive/Transmit/Send Complete features, and implementation examples, see:
> **`../reference_docs/API_OPERATION_MODE.md`**

This guide provides a quick troubleshooting overview.

## What You're Seeing

The hex data you showed indicates your radio is in **API Mode**:

```
CC 41 54 4F 0D  = API frame containing "ATO\r" command
^^                ← CC byte = API mode frame delimiter
   ^^^^^^^^^^     ← Payload: 41='A', 54='T', 4F='O', 0D='\r'
```

All data in API mode is prefixed with **0xCC** byte.

## The Problem

When a Laird radio is in API mode:
- All incoming data has CC prefix
- All outgoing commands need CC prefix
- Simple `+++` command doesn't work - needs to be: `CC 2B 2B 2B`
- All AT commands need wrapping: `CC + command + \r`

This is why command mode entry was failing - the code was sending raw `+++` but the radio expected `CC 2B 2B 2B`.

## The Solution

I've updated the web GUI to automatically detect and handle API mode:

### 1. **Automatic Detection**
- When entering command mode, the code now checks for CC bytes in the buffer
- If detected, switches to API mode command entry automatically

### 2. **API Mode Command Entry**
```python
# API mode +++ command
0xCC 0x2B 0x2B 0x2B  # CC + "+++"

# API mode AT commands
0xCC + ASCII command + 0x0D
Example: CC 41 54 43 48 0D = "ATCH\r"
```

### 3. **Manual Mode Switch**
Use the web GUI:
1. Connect to radio
2. Click "🔍 Check API Mode" button
3. If API mode detected, click "Switch to Transparent Mode"
4. Radio will reboot (wait 5 seconds)
5. Reconnect - AT commands now work normally

## API Mode vs Transparent Mode

| Feature | Transparent Mode | API Mode |
|---------|------------------|-----------|
| **Data Format** | Raw bytes | CC-prefixed frames |
| **Command Entry** | `+++` (raw) | `CC 2B 2B 2B` |
| **AT Commands** | `ATCH25\r` | `CC 41 54 43 48 32 35 0D` |
| **Best For** | AT commands, simple use | Advanced apps, frame sync |
| **Web GUI** | Works perfectly | Auto-detected & handled |

## How to Switch Modes Manually

### Via Web GUI (Recommended)
1. Connect to radio at 115200 baud
2. Click "Check API Mode" button
3. Click "Switch to Transparent Mode" if needed
4. Wait for reboot, then reconnect

### Via AT Commands (if can enter command mode)
```
+++           (enter command mode)
ATAP00        (set transparent mode)
ATWR          (save to EEPROM)
ATFR          (reboot radio)
```

### Via API Mode Commands (if stuck in API mode)
```
CC 2B 2B 2B                           (API +++)
CC 41 54 41 50 30 30 0D               (API "ATAP00\r")
CC 41 54 57 52 0D                     (API "ATWR\r")
CC 41 54 46 52 0D                     (API "ATFR\r")
```

## Hex Reference for Common AT Commands

### Transparent Mode (Simple)
```
+++ = 2B 2B 2B (no CR!)
ATCH\r = 41 54 43 48 0D
ATSY\r = 41 54 53 59 0D
ATSP\r = 41 54 53 50 0D
ATAP00\r = 41 54 41 50 30 30 0D
ATWR\r = 41 54 57 52 0D
ATCN\r = 41 54 43 4E 0D
```

### API Mode (CC-Prefixed)
```
+++ = CC 2B 2B 2B
ATCH\r = CC 41 54 43 48 0D
ATSY\r = CC 41 54 53 59 0D
ATSP\r = CC 41 54 53 50 0D
ATAP00\r = CC 41 54 41 50 30 30 0D
ATWR\r = CC 41 54 57 52 0D
ATCN\r = CC 41 54 43 4E 0D
```

## Detecting API Mode

Look for these patterns in received data:
- **CC byte at start of packets** = API mode
- **No CC prefix** = Transparent mode

The OI Gen2 sensor packets you showed:
```
CC 44 41 54 81 11 00 32 E0 88...  ← API mode (CC prefix)
   ^^^^^^^^^^                     ← "DAT" header
            ^^^^^^^^^^...         ← OI Gen2 packet
```

Without API mode, you'd see:
```
44 41 54 81 11 00 32 E0 88...     ← Transparent (no CC)
^^^^^^^^^^                        ← "DAT" header
         ^^^^^^^^^^...            ← OI Gen2 packet
```

## Troubleshooting

### AT Commands Not Working?
1. **Check API Mode**: Click "Check API Mode" button
2. **If API Mode**: Click "Switch to Transparent Mode"
3. **Reconnect**: Wait 5 seconds after switch, then reconnect
4. **Try Again**: AT commands should now work

### Still Not Working?
- Check baud rate (115200 for monitors, 9600 for sensors)
- Verify radio has power and LED is on
- Try power cycling the radio
- Check COM port isn't locked by another app

### Want to Stay in API Mode?
The web GUI now automatically handles API mode, so you can leave it as-is. The code will:
- Detect CC frames
- Send API-wrapped commands
- Parse CC-prefixed responses

## Why API Mode Exists

API mode is designed for:
- **Frame synchronization** - CC delimiter helps parse data streams
- **Binary data** - Can send any bytes without confusion
- **Multi-packet apps** - Easier to separate packets
- **Advanced protocols** - Better for complex applications

For simple AT command usage and web GUI, **Transparent Mode is recommended** as it's simpler and more intuitive.

## Current Status

Your radio appears to be in API mode based on the hex dump. The web GUI has been updated to:
1. ✅ Auto-detect API mode (checks for CC bytes)
2. ✅ Handle API mode command entry (sends CC-wrapped +++  )
3. ✅ Provide easy mode switching (one button click)
4. ✅ Display mode status and warnings

**Try it now**: Refresh your browser, connect to the radio, and click "Check API Mode"!
