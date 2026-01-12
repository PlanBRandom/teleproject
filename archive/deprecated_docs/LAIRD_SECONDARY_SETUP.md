# Laird Radio - Secondary Receiver Setup (Network Channel 25)

## Configuration Overview
- **Network Channel**: 25 (custom)
- **System ID**: 37 (OI standard - fixed)
- **Mode**: Secondary (Sniff Permit enabled)
- **Baud Rate**: 9600
- **API Mode**: Enabled (0x7E frames)

## Quick Setup Commands

### 1. Connect to Radio
Connect Laird module via USB-to-serial adapter:
- **TX (Green)** → USB-Serial RX
- **RX (White)** → USB-Serial TX  
- **GND (Black)** → USB-Serial GND
- **VCC (Red)** → 3.3V or 5V

### 2. Configure with AT Commands

```python
import serial
import time

# Open serial connection
ser = serial.Serial('COM11', 9600, timeout=1)  # Adjust COM port
time.sleep(0.5)

# Enter command mode (+++, wait 1 sec, no Enter)
ser.write(b'+++')
time.sleep(1.5)

# Configure radio
commands = [
    b'ATCN 25\r',        # Set Network Channel to 25
    b'ATSY 37\r',        # Set System ID to 37 (OI standard)
    b'ATSP 1\r',         # Enable Sniff Permit (secondary mode)
    b'ATAP 1\r',         # Enable API mode (0x7E frames)
    b'ATBD 3\r',         # Set baud to 9600 (3 = 9600)
    b'ATWR\r',           # Write to EEPROM
    b'ATCN\r',           # Exit command mode
]

for cmd in commands:
    print(f"Sending: {cmd.strip()}")
    ser.write(cmd)
    time.sleep(0.3)
    response = ser.read(100)
    print(f"Response: {response}")

ser.close()
print("\n✓ Radio configured as secondary receiver on channel 25")
```

### 3. Verify Configuration

```python
# Re-open connection
ser = serial.Serial('COM11', 9600, timeout=1)
time.sleep(0.5)

# Enter command mode
ser.write(b'+++')
time.sleep(1.5)

# Query settings
queries = [
    b'ATCN?\r',  # Network channel
    b'ATSY?\r',  # System ID
    b'ATSP?\r',  # Sniff Permit
    b'ATAP?\r',  # API mode
]

for query in queries:
    ser.write(query)
    time.sleep(0.2)
    response = ser.read(100)
    print(response.decode('ascii', errors='ignore').strip())

ser.write(b'ATCN\r')  # Exit command mode
ser.close()
```

Expected output:
```
25        # Network channel
37        # System ID
1         # Sniff Permit enabled
1         # API mode enabled
```

## Python Integration

```python
from pipeline.radio_receiver import RadioReceiver

# Initialize receiver
receiver = RadioReceiver("COM11", baudrate=9600, api_mode=True)

if receiver.connect():
    # Set RF channel to 25 (matches network channel)
    receiver.set_rf_channel(25)
    print("Radio configured: Channel 25, Secondary mode")
    
    # Register callback for received packets
    def on_sensor_data(msg):
        print(f"Ch {msg.channel}: {msg.reading:.2f}")
        if msg.battery_voltage:
            print(f"  Battery: {msg.battery_voltage:.1f}V")
    
    receiver.register_callback(on_sensor_data)
    receiver.start()
    
    # Listen indefinitely
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        receiver.disconnect()
```

## Network Topology

```
┌──────────────────────────────────────────────────────────┐
│  Network Channel 25                                      │
│                                                           │
│  ┌─────────────┐                    ┌─────────────┐     │
│  │   OI-7010   │  RF @ 900MHz       │   OI-7530   │     │
│  │  (Primary)  │◄──────────────────►│  (Primary)  │     │
│  │  Ch 1-32    │                    │  Ch 1-32    │     │
│  └─────────────┘                    └─────────────┘     │
│         │                                   │            │
│         │ OI Gen II Protocol               │            │
│         │ (Protocol 1,2,7)                 │            │
│         ▼                                   ▼            │
│  ┌──────────────────────────────────────────────────┐   │
│  │    Laird LT1110 Radio Module (Secondary)        │   │
│  │    RF Channel 25, Sniff Permit Enabled          │   │
│  │    Receives from all monitors                   │   │
│  └──────────────────────────────────────────────────┘   │
│         │                                                │
│         │ USB Serial @ 9600 baud                        │
│         │ API Mode (0x7E frames)                        │
│         ▼                                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │    Home Assistant Server                         │   │
│  │    Python radio_receiver.py                      │   │
│  │    Processes Protocol 1, 2, 7 packets           │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

## Secondary Mode Benefits

1. **Passive Listening**: Receives all broadcasts without transmitting
2. **No Interference**: Won't disrupt primary monitor communication  
3. **Multi-Monitor**: Can receive from all monitors on channel 25
4. **Low Power**: No TX operations reduce power consumption
5. **Flexibility**: Can be added/removed without network reconfiguration

## Troubleshooting

### No Packets Received
- **Check Network Channel**: Run `ATCN?` to verify channel 25
- **Check System ID**: Run `ATSY?` to verify 37
- **Check Sniff Permit**: Run `ATSP?` should return 1
- **Check API Mode**: Run `ATAP?` should return 1
- **Check Monitor Config**: Monitors must be set to transmit on channel 25

### Wrong Data Format
- Verify API mode is enabled (0x7E frames)
- Check `api_mode=True` in RadioReceiver initialization
- Ensure baud rate is 9600

### Weak Signal (RSSI < -95 dBm)
- Check antenna connection
- Verify frequency match (900 MHz LT1110 for OI monitors)
- Check for RF interference
- Increase radio module height/clearance

### Command Mode Issues
- Wait 1.5 seconds after `+++` before sending commands
- No data transmission for 1 second before `+++`
- Use `ATCN` to exit command mode
- Commands require `\r` (carriage return) terminator

## AT Command Reference

| Command | Description | Values |
|---------|-------------|--------|
| `ATCN <n>` | Set Network Channel | 1-78 (use 25) |
| `ATSY <n>` | Set System ID | 0-65535 (use 37) |
| `ATSP <n>` | Sniff Permit (secondary) | 0=off, 1=on |
| `ATAP <n>` | API Mode | 0=transparent, 1=API |
| `ATBD <n>` | Baud Rate | 3=9600, 4=19200 |
| `ATWR` | Write to EEPROM | - |
| `ATCN` | Exit Command Mode | - |
| `AT<cmd>?` | Query Parameter | - |

## Hardware Specs (Laird LT1110)

- **Model**: 1110LT200UPLG01
- **Frequency**: 902-928 MHz (ISM band)
- **Range**: Up to 2 miles (line of sight)
- **TX Power**: 100 mW (20 dBm)
- **RX Sensitivity**: -110 dBm
- **Interface**: 3.3V UART
- **Current**: 150mA TX, 35mA RX, 3μA sleep
