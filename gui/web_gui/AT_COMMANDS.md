# Laird Radio AT Command Reference

## Command Mode Entry/Exit
- **`+++`** - Enter AT command mode (1+ second silence before/after, NO carriage return)
- **`ATCN`** - Exit command mode and return to transparent/API mode

## Network Configuration
- **`ATCH`** - Read current RF channel (1-78)
- **`ATCH##`** - Set RF channel (e.g., ATCH25 for channel 25)
- **`ATSY`** - Read System ID (0-99)
- **`ATSY##`** - Set System ID (e.g., ATSY37)
- **`ATSP`** - Read mode (00=Secondary, 01=Primary)
- **`ATSP00`** - Set as Secondary (RX only)
- **`ATSP01`** - Set as Primary (TX/RX)

## Serial/Communication
- **`ATBD`** - Read baud rate (0=9600, 1=19200, 2=38400, 3=57600, 4=115200)
- **`ATBD#`** - Set baud rate (e.g., ATBD4 for 115200)
- **`ATAP`** - Read API mode (00=Transparent, 01=API)
- **`ATAP00`** - Set transparent mode
- **`ATAP01`** - Set API mode

## RF Power & Performance
- **`ATPL`** - Read RF power level (0-31, higher = more power)
- **`ATPL##`** - Set RF power (e.g., ATPL31 for max power)
- **`ATDB`** - Read last received signal strength (RSSI in -dBm)
- **`ATER`** - Read RF error count
- **`ATRO`** - Read RF packet timeout value
- **`ATRO##`** - Set packet timeout (0-255 x 100ms)

## Radio Information
- **`ATMY`** - Read radio MAC address (unique hardware ID)
- **`ATVR`** - Read firmware version
- **`ATGD`** - Read guard time (default 1000ms = 1.1 seconds)
- **`ATGD####`** - Set guard time in milliseconds

## Sensor Mode (OI Gen2 Sensors)
- **`ATTM`** - Read current transmit mode (0-7)
- **`ATTM0`** - Mode 0: Normal (5 minutes)
- **`ATTM1`** - Mode 1: Fast (1 minute)
- **`ATTM2`** - Mode 2: Very Fast (30 seconds)
- **`ATTM3`** - Mode 3: Ultra Fast (15 seconds)
- **`ATTM4`** - Mode 4: Rapid (12 seconds)
- **`ATTM5`** - **Mode 5: High Speed (10 seconds)** ← Most common request
- **`ATTM6`** - Mode 6: Burst (8 seconds)
- **`ATTM7`** - Mode 7: Maximum (5 seconds)

## Remote Commands
- **`ATRC`** - Enter remote command mode (send +++ wirelessly to paired radio)
  - Must be in local command mode first
  - Remote radio must be on same channel and system ID
  - Send commands normally, they execute on remote radio
  - Exit with ATCN, then exit local command mode with ATCN again

## Save & Reset
- **`ATWR`** - Write current settings to EEPROM (permanent save)
- **`ATRE`** - Restore factory defaults
- **`ATFR`** - Software reset (reboot radio)

## Usage Examples

### Change Sensor to Mode 5 (10 second transmit)
```
1. Connect to sensor radio at 9600 baud
2. Wait 1.1 seconds
3. Send: +++
4. Wait 1.1 seconds for OK
5. Send: ATTM5\r
6. Wait for OK response
7. Send: ATWR\r (save to EEPROM)
8. Wait for OK
9. Send: ATCN\r (exit command mode)
```

### Configure Monitor Radio to Channel 32, Primary, 115200 baud
```
+++
ATCH32
ATSP01
ATBD4
ATWR
ATCN
```

### Wirelessly Read Remote Radio Settings
```
+++                (enter local command mode)
ATCH25             (switch to remote's channel)
ATCN               (exit and apply)
+++                (re-enter)
ATRC               (enter remote command mode)
ATCH               (read remote channel)
ATSY               (read remote system ID)
ATSP               (read remote mode)
ATCN               (exit remote)
ATCN               (exit local)
```

## Important Notes

1. **Guard Times**: Must have 1+ second of SILENCE before and after +++
2. **No CR on +++**: The +++ command should NOT have a carriage return
3. **All Other Commands**: Need carriage return (\r) after command
4. **Save Required**: Use ATWR to save changes to EEPROM, otherwise lost on power cycle
5. **Channel Changes**: Must exit and re-enter command mode to apply channel changes
6. **Sensor Baud**: Sensors typically run at 9600 baud
7. **Monitor Baud**: Monitors typically run at 115200 baud
8. **Mode 5 Popular**: 10-second transmit interval is common for faster data collection

## Web GUI Usage

### Advanced AT Tab Features
- **Local Radio**: Send commands directly to connected radio
- **Remote Radio**: Send commands wirelessly via ATRC to any channel
- **Quick Buttons**: Pre-configured common commands
- **Sensor Mode**: Easy dropdown to set transmit intervals (Mode 0-7)
- **Custom Commands**: Type any AT command manually

### Typical Workflow
1. Connect to radio at appropriate baud rate (9600 for sensors, 115200 for monitors)
2. Use "Read Profile" to see current settings
3. Use "Advanced AT" tab for full command access
4. Select Local or Remote target
5. Click quick buttons or type custom commands
6. Always use ATWR to save changes
7. ATFR to reboot radio if needed
