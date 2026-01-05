# Laird Radio Configuration Modes

## Two Configuration Methods

Laird RM024 radios support two distinct configuration modes:

### 1. AT Command Mode (Pin 15 HIGH or floating)
- **Entry**: Send `+++` with 1+ second guard times before/after
- **Commands**: ATCH, ATSY, ATSP, ATBD, ATPL, etc.
- **Exit**: Send `ATCN` to return to transparent/API mode
- **Requirement**: Pin 15 (CMD/DATA) must be HIGH or not connected
- **Use Case**: Standard operation, most common configuration method

### 2. Standard Configuration Mode (Pin 15 LOW)
- **Entry**: Pull Pin 15 (CMD/DATA) to Logic LOW
- **Commands**: Binary EEPROM read/write commands (not AT commands)
- **Exit**: Release Pin 15 to HIGH
- **Requirement**: Physical hardware access to Pin 15
- **Use Case**: Factory programming, special configuration utilities

## Pin 15 (CMD/DATA) Status

**CRITICAL**: The radio will ONLY respond to AT commands if Pin 15 is:
- Logic HIGH, or
- Left floating (not connected)

If Pin 15 is pulled LOW:
- Radio enters "Standard Configuration Mode"
- AT commands (+++) will be IGNORED
- Must use binary EEPROM commands instead

## Checking Your Radio's Mode

### Symptoms of Pin 15 LOW (Standard Config Mode):
- `+++` receives no response
- No "OK" after guard times
- Radio continues transparent operation
- AT commands completely ignored

### Symptoms of Pin 15 HIGH (AT Command Mode):
- `+++` returns "OK" response
- AT commands work: ATCH, ATSY, etc.
- Can configure radio parameters
- ATCN returns to transparent mode

## Laird Configuration Utility Behavior

The official Laird configuration utility (the one you have working) likely:
1. Checks/controls Pin 15 status
2. Can switch between modes automatically
3. Uses whichever mode is appropriate
4. May have special driver access to control Pin 15

This explains why the Laird utility works but our AT commands don't!

## Solutions for Web App

### Option 1: Verify Pin 15 Status
- Use multimeter to check Pin 15 voltage
- Should be 3.3V (HIGH) for AT commands
- If 0V (LOW), radio is in Standard Config mode

### Option 2: Hardware Modification
- Ensure Pin 15 is pulled HIGH (3.3V)
- Or leave Pin 15 floating (disconnected)
- Requires physical radio access

### Option 3: Use Laird Utility for Configuration
- Configure radios using official Laird software
- Use our web app only for monitoring sensor data
- Best approach if Pin 15 is inaccessible

### Option 4: Implement Binary EEPROM Commands
- Reverse engineer the binary protocol
- Implement Standard Configuration commands
- Complex but would work with Pin 15 LOW

## Recommendation

**For your setup:**
1. Check if radios have Pin 15 accessible
2. If yes: Ensure Pin 15 is HIGH → AT commands will work
3. If no: Use Laird utility for configuration, web app for monitoring
4. Current web app is perfect for receiving/displaying sensor data (14 sensors detected!)

## Pin 15 Locations

### RM024 Module:
- Pin 15 is labeled "CMD/DATA" on the module pinout
- Usually on the 20-pin header
- Check RM024 datasheet for exact location

### Serial Cable/Adapter:
- Some USB-to-serial cables don't expose Pin 15
- May need direct module access
- Laird utility might have special driver access

## References

From Laird Configuration Software Documentation:
> "When this option is enabled, the application uses AT Commands for its 
> read/write EEPROM functions instead of the standard configuration 
> commands. This checkbox should be checked at all times unless Pin 15 
> (CMD/DATA) is pulled Logic Low."

This confirms:
- Default: Use AT Commands (Pin 15 HIGH)
- Special case: Use binary commands (Pin 15 LOW)
- Our web app assumes AT Command mode (Pin 15 HIGH)
