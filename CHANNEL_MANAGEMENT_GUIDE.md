# OI-7032 Channel Management System

## Overview

The channel management system provides automated tools to monitor, configure, and optimize OI-7032 radio channels. It helps you:

1. **Identify active channels** - Which sensors are transmitting?
2. **Disable inactive channels** - Free up resources by turning off silent channels
3. **Scan for rogue radios** - Detect unauthorized or unconfigured sensors
4. **Auto-assign rogues** - Automatically configure new sensors to available channels

## Quick Start

### Via Web Interface (Recommended)

1. Start the web server:
   ```powershell
   cd web_gui
   python app.py
   ```

2. Open browser to `http://localhost:5000`

3. Click the green **"🔧 Channel Management"** button

4. Connect to your OI-7032 via Modbus (if not already connected)

5. The page will automatically scan all 32 channels and categorize them:
   - **Active** (✓) - Received messages in last 10 minutes
   - **Inactive** (⚠) - Configured but no recent messages
   - **Unused** (○) - No radio address assigned

### Via Command Line

1. Run the channel activity scanner:
   ```powershell
   python scan_channel_activity.py
   ```

2. Run the complete channel manager:
   ```powershell
   python channel_manager.py
   ```

## Channel Management Workflow

### Step 1: Scan Current Status

The system reads all 32 channels and checks:
- **Radio Address** - What sensor address is assigned?
- **Time Since Last Message** - How long since last transmission?
- **Battery Level** - Current battery voltage

**Active** channels have time_since < 600 seconds (10 minutes)

### Step 2: Disable Inactive Channels

Channels that are configured but haven't received messages in >10 minutes should be disabled to:
- Free up OI-7032 processing resources
- Reduce unnecessary polling
- Clean up the channel display

**Web UI:** Click "Disable All Inactive" button
**CLI:** Manager automatically offers to disable them

This sets the radio address to 0, effectively turning off the channel.

### Step 3: Setup Scan Channel

Use one of your unused channels to scan for "rogue" radios - sensors that are transmitting but not configured in any channel.

**How it works:**
- Set a channel's radio address to **255** (catch-all/broadcast)
- This special address will receive transmissions from ANY sensor
- Monitor this channel to detect unconfigured sensors

**Web UI:** 
1. Select unused channel (default: first available)
2. Click "Setup Scan Channel"

**Scan Address 255** acts as a wildcard - it will capture any radio transmission on the network.

### Step 4: Monitor for Rogues

After setting up scan mode, monitor the scan channel for a period of time (e.g., 30 seconds) to detect rogue radios.

**Detection Criteria:**
- time_since_last_message < 5 seconds
- Radio address is NOT already assigned to another channel

**Web UI:**
1. Set scan duration (default: 30 seconds)
2. Click "Start Scanning"
3. Wait for results

The system will display any detected rogue radio addresses.

### Step 5: Auto-Assign Rogues

Once a rogue is detected, you can automatically assign it to an unused channel:

**Web UI:** Click "Assign to Ch X" button next to detected rogue

**What happens:**
1. System finds first available unused channel
2. Sets that channel's radio address to the rogue's address
3. Rogue is now properly configured and monitored

## Technical Details

### OI-7032 Register Addresses (Modbus RTU, 0-based)

For channel N (1-32):

```
Radio Address:     0x0000 + (N-1)
Time Since Msg:    0x00C0 + (N-1)  (seconds)
Battery Voltage:   0x0080 + (N-1)*2  (Float32, 2 registers)
Reading:           0x0020 + (N-1)*2  (Float32, 2 registers)
Sensor Type:       0x00E0 + (N-1)
Gas Type:          0x0100 + (N-1)
```

**Note:** PLC/Modbus Poll shows addresses +1 from actual Modbus RTU addresses
- PLC Address 0x0006 = Modbus Address 0x0005

### Activity Threshold

```
time_since < 600 seconds (10 minutes)  →  Active
time_since ≥ 600 seconds               →  Inactive
address == 0                           →  Unused
address == 255                         →  Scan Mode
```

### Scan Mode Details

Setting radio address to **255** enables promiscuous mode:
- Channel will receive ANY radio transmission
- Useful for network discovery
- Can detect sensors not assigned to any channel
- Monitor time_since to detect recent activity (<5s = new transmission)

## REST API Endpoints

All endpoints require Modbus connection to OI-7032:

### GET `/api/channels/scan`
Scan all channels and return status

**Response:**
```json
{
  "success": true,
  "active": [
    {"channel": 1, "radio_addr": 2, "time_since": 23, "battery": 23.5},
    ...
  ],
  "inactive": [
    {"channel": 3, "radio_addr": 4, "time_since": 65535},
    ...
  ],
  "unused": [17, 18, 19, ...]
}
```

### POST `/api/channels/disable`
Disable multiple channels

**Request:**
```json
{
  "channels": [3, 4, 21, 32]
}
```

**Response:**
```json
{
  "success": true,
  "results": [
    {"channel": 3, "success": true},
    {"channel": 4, "success": true},
    ...
  ]
}
```

### POST `/api/channels/enable`
Enable channel with specific radio address

**Request:**
```json
{
  "channel": 17,
  "radio_addr": 255
}
```

### POST `/api/channels/setup_scan`
Setup scan mode for rogue detection

**Request:**
```json
{
  "channel": 17,
  "scan_addr": 255
}
```

### POST `/api/channels/monitor_rogues`
Monitor scan channel for rogue radios

**Request:**
```json
{
  "channel": 17,
  "duration": 30
}
```

**Response:**
```json
{
  "success": true,
  "detected": [42, 73],
  "count": 2
}
```

### POST `/api/channels/auto_assign`
Assign rogue to unused channel

**Request:**
```json
{
  "rogue_addr": 42,
  "unused_channel": 18
}
```

## Troubleshooting

### No Active Channels Detected
- Verify Modbus connection to OI-7032
- Check correct COM port and slave ID (default: 3)
- Ensure sensors are powered on and transmitting
- Verify network channel matches between sensors and 7032

### Inactive Channels Show 65535 Seconds
This is the maximum timeout value, indicating:
- Sensor powered off or out of range
- Radio interference blocking transmissions
- Sensor battery depleted
- Wrong network channel configuration

### Rogue Detection Not Working
1. Verify scan channel is set to address 255
2. Ensure rogue sensor is on same network channel as 7032
3. Wait longer - some sensors transmit infrequently (5 min intervals)
4. Check rogue sensor is powered on and battery charged

### Can't Disable Channels
- Verify Modbus connection is active
- Check you have write permission to 7032
- Ensure correct register addresses for your 7032 firmware version

## Example Use Case

**Scenario:** Industrial facility with 20 gas sensors. Several sensors were recently replaced, and new sensors added. Channel assignments are unknown.

**Solution:**

1. **Scan channels** → Find 17 active, 4 inactive (probably removed sensors), 11 unused

2. **Disable inactive** → Free up channels 3, 4, 21, 32 (no recent messages)

3. **Setup scan on Ch 17** → Set address 255 to detect unconfigured sensors

4. **Monitor for 60 seconds** → Detect rogue addresses: 42, 73 (new sensors not configured)

5. **Auto-assign rogues:**
   - Rogue 42 → Channel 18
   - Rogue 73 → Channel 19

6. **Result:** All sensors now properly configured and monitored!

## Files

### Web Interface
- `web_gui/templates/channels.html` - Channel management UI
- `web_gui/app.py` - Flask backend with channel API endpoints

### CLI Tools
- `scan_channel_activity.py` - Quick channel status scanner
- `channel_manager.py` - Complete management tool with OI7032Manager class

### Documentation
- `OI7032_REGISTER_MAP.py` - Complete register map documentation
- `CHANNEL_MANAGEMENT_GUIDE.md` - This file

## Safety Notes

⚠️ **Warning:**
- Disabling active channels will stop monitoring those sensors
- Changing radio addresses may cause sensors to go offline temporarily
- Always verify channel assignments before disabling
- Scan mode (address 255) will interfere with normal operation on that channel

✓ **Best Practice:**
- Use unused channels for scanning
- Disable inactive channels only after verifying sensors are removed
- Document channel assignments after making changes
- Test auto-assigned rogues to verify proper operation
