# RM024 Radio Configuration - Decoded from EEPROM

## COM7 Radio (MAC: 005067E086EB)

### Network Configuration
- **0x40 - Channel**: Value in EEPROM shows **Ch 76 (0x4C)**
- **0x41 - Mode**: **0x02 = Client** (receiver mode)
- **0x42 - Baud**: **0x09 = 115200 baud** ✓
- **0x76 - System ID**: **0x0E01** (matches both radios)

### Critical Settings  
- **0x54 - RF Profile**: Determines data rate and hops
- **0x56 - Control 1**: **0x41**
  - bit 7 (0): Auto Destination on Beacons Only = **DISABLED**
  - bit 6 (1): Hop Frame = **DISABLED**
  - bit 5 (0): Reserved
  - bit 4 (0): Auto Destination = **DISABLED** (uses fixed destination)
  - bit 3 (0): Auto Channel = **DISABLED**
  - bit 2 (0): RTS handshaking = **DISABLED**
  - bit 1 (0): Full Duplex = **DISABLED** (Half duplex)
  - bit 0 (1): Auto Config = **ENABLED**

- **0x57 - Control 2**: **0x01**
  - bit 0 (1): 9600 Boot Option = **ENABLED**

- **0x5A - RF Packet Size**: **0x60 = 96 bytes**
  - **This is GREATER than 0x07, so +++ SHOULD work!**

- **0x58 - Interface Timeout**: **0x03** (600µs)

- **0x5C-5D - CTS On**: **0x01C0 = 448 bytes**
- **0x5E-5F - CTS Off**: **0x0180 = 384 bytes**

### API Settings
- **0xC1 - API Control**: Various API mode settings
  - bit 7: Broadcast Mode
  - bit 5: Antenna Select (chip vs U.FL)
  - bit 0-2: API mode flags

## Key Finding: RF Packet Size is 96 bytes!

**CORRECTION**: I previously said RF Packet Size was 3 bytes - that was **WRONG**!

Looking at address 0x5A in the EEPROM dump:
```
0050  00 01 00 01 01 FF 41 01 03 FF 60 E3 01 C0 01 80
                                    ^^
                                   0x5A = 0x60 = 96 decimal
```

**RF Packet Size = 96 bytes**, which is **WELL ABOVE the 0x07 (7 byte) minimum** needed for +++ commands!

## Why +++ Still Doesn't Work

Since RF Packet Size is fine, the issues are:

1. **9600 Boot Option ENABLED** (0x57 bit 0 = 1)
   - This may interfere with normal AT command entry
   
2. **Auto Config ENABLED** (0x56 bit 0 = 1)
   - Radio uses predetermined values instead of EEPROM settings
   - May override the RF Packet Size value!

3. **Client Mode with Fixed Destination**
   - Radio is focused on receiving from specific sensors
   - May ignore command mode attempts during active reception

4. **RTS Handshaking DISABLED** (0x56 bit 2 = 0)
   - Explains why RTS manipulation didn't help!

## The Real Solution

Since **Auto Config is ENABLED**, the radio ignores the 0x5A RF Packet Size value and uses **optimized preset values** based on the RF Profile. These preset values might be < 7 bytes for sensor reception optimization, which would disable +++!

### To Enable AT Commands:

**Option 1: Disable Auto Config**
- Change 0x56 bit 0 from 1 to 0
- Requires Laird Configuration Utility or binary EEPROM write

**Option 2: Use Force 9600 Mode**
- Pull Force 9600 pin LOW at boot
- Enter command mode at 9600 baud
- +++ will work in Force 9600 mode

**Option 3: Use 9600 Boot Option**
- Since it's already enabled (0x57 bit 0 = 1)
- Radio may accept commands at boot time
- Test connecting at 9600 baud during power-up

## COM11 Radio Configuration

Similar configuration to COM7 but on **Channel 12 (0x0C)** instead of Channel 76.

## Summary

Your radios are configured as **optimized sensor receivers** with:
- ✓ Client mode (receive only)
- ✓ Auto Config enabled (preset optimizations)
- ✓ 115200 baud serial
- ✓ 96-byte EEPROM RF Packet Size (but Auto Config may override)
- ✗ Auto Config likely uses <7 byte packets for sensors
- ✗ AT commands disabled due to Auto Config overriding packet size

**Best solution**: Use **Laird Configuration Utility** or test **Force 9600 mode** or try connecting at **9600 baud during boot** (since 9600 Boot Option is enabled).
