# Laird Radio Module Setup Guide

Quick setup guide for Laird LT1110 and RM024 radio modules used with OI Gen II wireless sensors.

## Radio Models

### Laird LT1110 (900 MHz) - Primary
- **Full Model**: 1110LT200UPLG01
- **Frequency**: 900 MHz ISM band
- **Range**: Up to 2 miles line-of-sight (outdoor)
- **Power**: 3.3V/5V compatible
- **Firmware**: V 2.9-0 or later
- **Antenna**: SMA connector
- **Use Case**: Best for long range, outdoor deployments

### Laird RM024 (2.4 GHz) - Alternative
- **Full Model**: 2510LT100UPLG01 (LT series)
- **Frequency**: 2.4 GHz ISM band
- **Range**: Up to 1 mile line-of-sight (outdoor)
- **Power**: 3.3V compatible
- **Firmware**: V 2.4-1 or later
- **Antenna**: Built-in or SMA
- **Use Case**: Good for indoor, less interference-prone environments

## Connection

### Serial Interface
```
Radio Module    Arduino/ESP32    USB-Serial
-----------     -------------    -----------
TX        -->   RX (GPIO16)  --> RX
RX        <--   TX (GPIO17)  <-- TX
GND       ---   GND          --- GND
VCC       ---   3.3V         --- 3.3V
```

### Serial Settings
- **Baud Rate**: 9600
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 1
- **Flow Control**: None (or RTS/CTS if available)

## OI Network Configuration

These settings are pre-configured on OI monitors and sensors. Your radio module should match:

### Critical Settings
- **Network Channel**: 5 (OI default)
  - Range: 0-15
  - Must match sensor network
  - Change if multiple OI systems nearby
  
- **System ID**: 37 (Fixed - DO NOT CHANGE)
  - OI-specific identifier
  - All OI devices use 37
  
- **Baud Rate**: 9600 (OI default)

### Operating Modes

**API Mode** (Recommended):
- Frames start with 0x7E delimiter
- Provides packet metadata (RSSI, timestamps)
- Used by OI monitors in Primary/Secondary configuration
- Enable with AT command: `ATAP1`

**Transparent Mode**:
- Raw Gen2 protocol packets
- No frame overhead
- Used for direct sensor-to-receiver
- Enable with AT command: `ATAP0`

## Python Usage

### Basic Receiver (API Mode)
```python
from pipeline.radio_receiver import RadioReceiver

# Laird LT1110 or RM024 in API mode
receiver = RadioReceiver("COM5", baudrate=9600, api_mode=True)

def on_message(msg):
    print(f"Ch{msg.channel}: {msg.reading:.2f}")
    if msg.battery_voltage:
        print(f"  Battery: {msg.battery_voltage}V")

receiver.connect()
receiver.register_callback(on_message)
receiver.start()
```

### Transparent Mode
```python
# Direct sensor connection (no monitor)
receiver = RadioReceiver("COM5", baudrate=9600, api_mode=False)
# ... same callback setup
```

## AT Command Configuration

Connect to radio at 9600 baud and enter command mode:

### Enter Command Mode
```
+++  (wait 1 second for "OK")
```

### Check Current Settings
```
ATS                 # Show all settings
ATI                 # Show model and firmware
```

### Essential OI Settings
```
ATAP1               # Enable API mode (for monitor operation)
ATDN5               # Set Network Channel to 5 (OI default)
ATSY37              # Set System ID to 37 (OI fixed)
ATBD3               # Set baud rate to 9600
ATWR                # Write settings to flash
ATCN                # Exit command mode
```

## Laird Binary Protocol Commands

Laird radios support binary commands (0xCC prefix) for runtime queries without AT mode:

### Get RSSI (Signal Strength)
```python
# Command: 0xCC 0x22
# Response: 0xCC <rssi_raw>
# RSSI (dBm) = (rssi_raw / 2) - 71  # if rssi_raw < 128
# RSSI (dBm) = ((rssi_raw - 256) / 2) - 71  # if rssi_raw >= 128

def get_rssi(serial):
    serial.write(b'\xCC\x22')
    time.sleep(0.1)
    if serial.in_waiting >= 2:
        header = serial.read(1)[0]
        if header == 0xCC:
            rssi_raw = serial.read(1)[0]
            if rssi_raw >= 128:
                return ((rssi_raw - 256) / 2) - 71
            else:
                return (rssi_raw / 2) - 71
    return -128  # No response
```

### Get MAC Address
```python
# Command: 0xCC 0x10
# Response: 0xCC <mac_byte1> <mac_byte2> <mac_byte3>

def get_mac(serial):
    serial.write(b'\xCC\x10')
    time.sleep(0.1)
    if serial.in_waiting >= 4:
        header = serial.read(1)[0]
        if header == 0xCC:
            mac = serial.read(3)
            return mac.hex()
    return None
```

### EEPROM Configuration Commands
```python
# These are used in OI repeaters to configure Laird radios
# All commands: 0xCC 0xC1 <address> <length> <data>

commands = [
    b'\xCC\xC1\x45\x01\x8B',  # CMD mode settings
    b'\xCC\xC1\xC1\x01\x03',  # API mode enable
    b'\xCC\xC1\x41\x01\x02',  # Server mode
    b'\xCC\xC1\x56\x01\x41',  # Control register
    b'\xCC\xC1\x76\x01\x25',  # System ID = 37 (0x25)
]

for cmd in commands:
    serial.write(cmd)
    time.sleep(0.1)
```

### RF Channel Control
```python
# Set RF Channel: 0xCC 0xC1 0x40 0x01 <channel>
# Channel range: 1-78 (for LT2510/RM024)

def set_rf_channel(serial, channel):
    cmd = bytes([0xCC, 0xC1, 0x40, 0x01, channel])
    serial.write(cmd)

# Example: Set to channel 5 (OI default)
set_rf_channel(ser, 5)
```

### Get RF Profile
```python
# Command: 0xCC 0xC0 0x54 0x01
# Response: 0xCC <skip> <skip> <profile>

def get_rf_profile(serial):
    serial.write(b'\xCC\xC0\x54\x01')
    time.sleep(0.1)
    if serial.in_waiting >= 4:
        header = serial.read(1)[0]
        if header == 0xCC:
            serial.read(2)  # Skip 2 bytes
            profile = serial.read(1)[0]
            return profile
    return 0xFF
```

### For Primary Monitor Radio
```
ATCE1               # Enable Server mode (Primary Monitor only)
ATSP1               # Enable Sniff Permit OFF (Primary only)
```

### For Secondary Monitor Radio
```
ATCE0               # Disable Server mode (Secondary)
ATSP1               # Enable Sniff Permit (listen only)
```

### For Direct Receiver (No Monitor)
```
ATCE0               # Disable Server mode
ATSP1               # Enable Sniff Permit (listen to all)
ATAP1               # Use API mode to receive frames
```

## Troubleshooting

### No Data Received

1. **Check Power**
   - LT1110: 3.3V or 5V
   - RM024: 3.3V only
   - Verify voltage with multimeter

2. **Check Serial Connection**
   - TX/RX not swapped?
   - GND connected?
   - Use serial monitor to see raw data

3. **Check Network Settings**
   ```
   ATS          # Should show DN=5, SY=37
   ```

4. **Check Sensors Transmitting**
   - Monitor LCD shows radio icon?
   - Sensors should transmit every 60s (no gas) or 5s (gas detected)

5. **Check API Mode**
   ```
   ATAP         # Should return 1 for API mode
   ```

### Weak Signal

1. **LT1110 (900 MHz)**:
   - Check antenna connection (SMA)
   - Try external antenna for better range
   - 900 MHz penetrates walls better than 2.4 GHz

2. **RM024 (2.4 GHz)**:
   - More affected by WiFi interference
   - Try different Network Channel (0-15)
   - Better for line-of-sight

### Checksum Errors

1. **Electrical Noise**:
   - Add ferrite bead on serial cable
   - Keep cables short
   - Separate from power lines

2. **Wrong Mode**:
   - If expecting API mode (0x7E frames), check `ATAP1`
   - If expecting transparent, use `ATAP0`

3. **Baud Rate Mismatch**:
   - Verify 9600 on both sides
   - Check with: `ATBD` (should return 3 for 9600)

## Home Assistant Integration

### Add-on Configuration
```yaml
# config.yaml
connection_mode: "radio_direct"
radio_port: "/dev/ttyUSB1"
radio_baudrate: 9600
radio_api_mode: true  # For Laird modules

# Network settings (must match OI system)
network_channel: 5
system_id: 37
```

### Hardware Setup
1. Connect Laird module to USB-Serial adapter
2. Plug into Home Assistant server
3. Find device: `ls /dev/ttyUSB*` or `ls /dev/ttyACM*`
4. Configure add-on with correct port

## ESP32 Example

```cpp
#include <HardwareSerial.h>

HardwareSerial RadioSerial(1);  // Use UART1

void setup() {
    Serial.begin(115200);
    // Laird LT1110 on GPIO16(RX), GPIO17(TX)
    RadioSerial.begin(9600, SERIAL_8N1, 16, 17);
    Serial.println("Listening for OI sensors...");
}

void loop() {
    if (RadioSerial.available()) {
        uint8_t byte = RadioSerial.read();
        // Process API frame (0x7E) or Gen2 packet
        Serial.printf("%02X ", byte);
    }
}
```

## Performance Specifications

### Laird LT1110 (900 MHz)
- **Range (Outdoor)**: Up to 2 miles (3.2 km)
- **Range (Indoor)**: Up to 800 ft (244 m)
- **Data Rate**: 38.4 kbps
- **TX Power**: +20 dBm (100 mW)
- **RX Sensitivity**: -110 dBm
- **Current Draw**: 150 mA TX, 40 mA RX

### Laird RM024 (2.4 GHz)
- **Range (Outdoor)**: Up to 1 mile (1.6 km)
- **Range (Indoor)**: Up to 400 ft (122 m)
- **Data Rate**: 250 kbps
- **TX Power**: +4 dBm (2.5 mW)
- **RX Sensitivity**: -95 dBm
- **Current Draw**: 30 mA TX, 25 mA RX

## Network Planning

### Single Monitor System
- 1 Primary Monitor with LT1110/RM024
- Up to 32 wireless sensors
- All sensors sync with Primary
- Network Channel: 5, System ID: 37

### Multi-Monitor System
- 1 Primary Monitor (Server mode, ATCE1)
- Multiple Secondary Monitors (Sniff Permit, ATSP1)
- All monitors hear sensor broadcasts
- Only Primary ACKs sensors
- Network Channel: 5, System ID: 37

### Direct Receiver (No Monitor)
- Standalone Laird module
- Sniff Permit enabled (ATSP1)
- Listens to sensor broadcasts
- Does not ACK (sensors must have Primary Monitor)
- Network Channel: 5, System ID: 37

## Advanced: OI Repeater Application

OI uses ESP32-based repeaters with dual Laird radios to extend range:

### Repeater Architecture
```
Sensors --> Client Radio (CH 5) --> ESP32 --> Server Radio (CH 6) --> Monitor
```

### Key Features
- **MAC Address Tracking**: Identifies individual sensors via Laird MAC
- **RSSI Monitoring**: Signal strength for each sensor
- **Dual Channel**: Client listens on CH 5, Server transmits on CH 6
- **Packet Forwarding**: Gen2 packets wrapped with MAC + RSSI metadata
- **Watchdog**: Auto-reset on radio timeout (3 seconds)
- **RF Channel Hopping**: Can change channels dynamically

### Repeater Packet Format
```
Byte   | Field
-------|------------------
0      | Protocol (0x81 for repeater)
1      | Payload Length
2-n    | Gen2 Packet (Protocol 1/2/7)
n+1-3  | MAC Address (3 bytes)
n+4    | RSSI (signed byte)
n+5    | Checksum
```

### ESP32 Repeater Configuration
```cpp
// From OI 3609850 repeater design
#define CLIENT_TX 8   // To sensor-side radio
#define CLIENT_RX 9
#define SERVER_TX 10  // To monitor-side radio
#define SERVER_RX 11

HardwareSerial clientRadio(1);
HardwareSerial serverRadio(2);

void setup() {
    clientRadio.begin(115200, SERIAL_8N1, CLIENT_RX, CLIENT_TX);
    serverRadio.begin(115200, SERIAL_8N1, SERVER_RX, SERVER_TX);
    
    // Configure client radio (sensor side)
    setRFChannel(clientRadio, 5);  // Sensor network
    
    // Configure server radio (monitor side)
    setRFChannel(serverRadio, 6);  // Monitor network
}
```

### When to Use Repeaters
- **Long Range**: Sensors > 2 miles from monitor
- **Obstacles**: Buildings, terrain blocking signal
- **Multiple Buildings**: Sensors in separate structures
- **Weak RSSI**: Signal strength < -90 dBm

### Repeater vs Direct Radio
- **Repeater**: Extends network, requires dual radios, adds latency
- **Direct Radio**: Simpler, single radio, listens to existing network

If you need to add radio capability to existing Home Assistant system:

1. **Purchase Laird LT1110 or RM024 module**
   - LT1110 for outdoor/long range
   - RM024 for indoor/shorter range

2. **USB-Serial Adapter**
   - FTDI FT232RL or similar
   - 3.3V logic compatible

3. **Configure Module**
   - Set baud 9600, API mode
   - Set Network Channel 5, System ID 37
   - Enable Sniff Permit

4. **Install HA Add-on**
   - Configure for `radio_direct` mode
   - Point to USB device

5. **Test Reception**
   ```bash
   python pipeline/radio_receiver.py
   ```

## Resources

- **Laird Documentation**: AT command reference
- **OI Protocol**: See RADIO_PROTOCOL.md
- **Source Code**: pipeline/radio_receiver.py
- **Test Suite**: test_radio_protocol.py
