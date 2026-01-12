# OI-7500 Pipeline Troubleshooting Guide

## Radio Not Receiving Data

### Symptoms
- Radio shows as "Connected" in web UI
- Radio counter stays at 0 in diagnostic page
- No green items appearing in diagnostic view
- Terminal shows no "[RADIO] *** SENSOR MESSAGE RECEIVED ***" messages

### Possible Causes & Solutions

#### 1. Dev Board Issue (USB-Serial Adapter)
**Problem**: Some USB-to-serial adapters/dev boards don't properly pass through radio signals.

**Solution**: Connect radio **directly via UART** (straight serial connection)
- Bypass the dev board completely
- Use a proper RS-232 to USB adapter or direct serial port
- Check pinout: TX → RX, RX → TX, GND → GND
- Ensure proper voltage levels (3.3V or 5V depending on radio module)

#### 2. Radio Module Not Receiving RF
**Check**:
- Are sensors actually transmitting? (Battery OK? Powered on?)
- Is radio module powered properly? (Check LED indicators)
- Radio frequency match? (900 MHz vs 2.4 GHz)
- Radio range: Sensors within 1-2 miles for Laird modules?

**Test**:
```bash
# Run standalone radio monitor to see raw serial data
python example_laird_monitor.py COM7 9600
```

If you see packets here but not in web app → software issue
If you see NOTHING → hardware/RF issue

#### 3. Wrong API Mode Configuration
**Current Setting**: RM024 API mode (expects 0xCC frames)

**Try Different Modes**:
```python
# In app.py line 627, try:
radio_receiver = RadioReceiver(port, baudrate, api_mode=False)  # Transparent mode
# OR
radio_receiver = RadioReceiver(port, baudrate, api_mode=True, api_type='xbee')  # XBee API
```

#### 4. Baudrate Mismatch
**Common baudrates**: 9600, 19200, 38400, 115200

**Test**:
- Try each baudrate in web UI
- Watch terminal for garbage characters (wrong baudrate)
- Clean output = correct baudrate

#### 5. Serial Port Access Issue
**Windows specific**:
- Another program has port open?
- Check Task Manager for Python processes
- Restart to release port

## MQTT Not Publishing

### Check MQTT Configuration

1. **Is MQTT Publisher Running?**
```bash
# Check web app logs for MQTT messages
# Should see: "Connecting to MQTT broker at..."
```

2. **MQTT Broker Running?**
```bash
# If using Mosquitto locally:
mosquitto -v

# Test with mosquitto_sub:
mosquitto_sub -h localhost -t "homeassistant/#" -v
```

3. **Check app.py MQTT Config (lines 1637-1646)**
```python
mqtt_config = {
    'broker': 'localhost',  # ← Correct IP?
    'port': 1883,           # ← Correct port?
    'username': None,       # ← Credentials needed?
    'enabled': True         # ← Must be True
}
```

4. **Web UI Not Starting MQTT**
- MQTT publisher is defined but may not be auto-started
- Need to add MQTT initialization in app startup
- Or manually call MQTT API endpoints

### Solution: Manual MQTT Test

```python
# Add to app.py startup or create separate test file
from pipeline.mqtt import MQTTPublisher, MQTTConfig

mqtt_cfg = MQTTConfig(
    broker="192.168.1.100",  # Your broker IP
    port=1883,
    device_name="OI-7032",
    device_id="oi7032_01"
)

publisher = MQTTPublisher(mqtt_cfg)
publisher.connect()
publisher.publish_availability(True)

# Then publish sensor data in on_sensor_message callback
```

## Gas Types Showing Wrong Names

### Fixed in Latest Version
Updated to complete OI-7032 specification:

```python
0: H2S,      1: SO2,      2: O2,       3: CO,       4: CL2
5: CO2,      6: LEL,      7: VOC,      8: FEET,     9: HCl
10: NH3,     11: H2,      12: ClO2,    13: HCN,     14: F2
15: HF,      16: CH2O,    17: NO2,     18: O3,      19: INCHES
20: 4-20mA,  21: Not Specified,        22: °C,      23: °F
24: CH4,     25: NO,      26: PH3,     27: HBr,     28: EtO
29: CH3SH,   30: AsH3,    31: R410A,   32: R1234YF, 33: R32
```

Files updated:
- `pipeline/registers.py` (GAS_TYPES)
- `pipeline/radio_receiver.py` (GAS_TYPE_NAMES)
- `web_gui/app.py` (inline gas_names dict)

## Channel 32 Confusion (4-20mA Sensor)

### Understanding the Configuration

**Register 0x100 + 31 = 0x11F** (Gas Type for Channel 32)
- Value: 6
- Meaning: Sensor Type 6 = "4-20mA" **wired analog input**

**This is NOT a radio sensor**. It's a physical 4-20mA current loop connected to 7032 terminals.

### Expected Reading
- **Range**: 4.00 to 20.00 mA
- **4 mA** = 0% of sensor range (minimum)
- **12 mA** = 50% of sensor range (midpoint)
- **20 mA** = 100% of sensor range (maximum)

### Scaling Formula
```python
mA_reading = channel_32_value  # From register 0x20 + 31*2
percent = ((mA_reading - 4) / 16) * 100
```

### If Channel 32 Also Has Radio Address 16
**Problem**: OI-7032 can be configured to:
1. Read wired 4-20mA sensor on Channel 32
2. ALSO listen for radio packets from sensor address 16

**Result**: Ambiguity - which takes precedence?

**Solution**: 
- If Channel 32 should be **wired-only**, set radio address to 0 (disable radio)
- If should be **radio-only**, change sensor type from 6 to proper gas sensor type

## Using the Diagnostic Page

### Access
```
http://localhost:5000/diagnostic
```

### What It Shows

**Left Panel (Green) - Radio Data**
- Counter increments with each radio packet received
- Shows live SocketIO stream
- If counter = 0 after 30 seconds → **Radio not receiving**

**Right Panel (Orange) - Modbus Data**
- Click "Read Modbus" button
- Counter increments with each read
- Shows direct OI-7032 register data
- If counter = 0 → **Not connected to 7032**

**Channel 32 Analysis**
- Sensor type (should show 6 = 4-20mA)
- Raw mA reading
- Scaled percentage (0-100%)

### Interpretation

| Radio Counter | Modbus Counter | Diagnosis |
|---------------|----------------|-----------|
| 0 | 0 | Nothing connected |
| 0 | >0 | Radio not working, Modbus OK |
| >0 | 0 | Radio OK, Modbus not connected |
| >0 | >0 | Both working - check data source confusion |

## Enabling MQTT Publishing

### Add to app.py Startup (after line 1700)

```python
# Initialize MQTT publisher if enabled
mqtt_publisher = None
if mqtt_config.get('enabled'):
    try:
        from pipeline.mqtt import MQTTPublisher, MQTTConfig
        
        mqtt_cfg = MQTTConfig(
            broker=mqtt_config['broker'],
            port=mqtt_config['port'],
            username=mqtt_config.get('username'),
            password=mqtt_config.get('password'),
            device_name="OI-7032",
            device_id="oi7032_pipeline"
        )
        
        mqtt_publisher = MQTTPublisher(mqtt_cfg)
        mqtt_publisher.connect()
        mqtt_publisher.publish_availability(True)
        
        print("[MQTT] Connected to broker at {}:{}".format(
            mqtt_config['broker'], mqtt_config['port']))
            
    except Exception as e:
        print(f"[MQTT] Failed to connect: {e}")
```

### Publish Radio Data to MQTT

Modify `on_sensor_message` callback (around line 370):

```python
def on_sensor_message(msg):
    """Forward sensor messages to web GUI via SocketIO"""
    try:
        # ... existing code ...
        
        # Publish to MQTT if enabled
        if mqtt_publisher and mqtt_publisher.connected:
            topic = f"oi7032/sensor/{msg.transmitter_address}"
            payload = {
                'address': msg.transmitter_address,
                'channel': msg.channel,
                'reading': msg.reading,
                'gas_type': gas_name,
                'battery': msg.battery_voltage,
                'timestamp': time.time()
            }
            mqtt_publisher.publish(topic, payload)
        
        # ... rest of existing code ...
```

## Quick Diagnostic Commands

### Check Serial Ports
```powershell
# List all COM ports
Get-WmiObject Win32_SerialPort | Select-Object DeviceID, Description

# Or in Python
python -c "import serial.tools.list_ports; [print(p) for p in serial.tools.list_ports.comports()]"
```

### Test Radio Reception Standalone
```bash
# Terminal 1: Run radio monitor
cd d:\oi-7500-pipeline
.venv\Scripts\python.exe example_laird_monitor.py COM7 9600

# Terminal 2: Send test packet (if radio supports it)
.venv\Scripts\python.exe -c "from pipeline.radio_receiver import RadioReceiver; r = RadioReceiver('COM7', 9600); r.connect(); r.send_test_packet(1, 42.5, gas_type=0)"
```

### Test Modbus Connection
```bash
cd d:\oi-7500-pipeline
.venv\Scripts\python.exe hardware_test.py
# Select option 1: Test connection
# Select option 2: Read all channels
```

### Monitor MQTT Messages
```bash
# Subscribe to all topics
mosquitto_sub -h localhost -t "#" -v

# Subscribe to OI data only
mosquitto_sub -h localhost -t "homeassistant/sensor/oi7032/#" -v
```

## Still Not Working?

### Collect Diagnostics

1. **Terminal output when starting app**:
```bash
D:\oi-7500-pipeline\.venv\Scripts\python.exe web_gui\app.py > debug.log 2>&1
```

2. **Check for "[RADIO] *** SENSOR MESSAGE RECEIVED ***"**
   - If YES → Radio receiving, check SocketIO
   - If NO → Radio not receiving data

3. **Run radio_receiver standalone**:
```python
from pipeline.radio_receiver import RadioReceiver

r = RadioReceiver('COM7', 9600, api_mode=True, api_type='rm024')
r.connect()
r.start()

# Watch terminal for 60 seconds
import time; time.sleep(60)
r.stop()
```

4. **Check dev board**:
   - Bypass it completely
   - Use proper USB-to-serial adapter
   - Or direct motherboard serial port

### Post Issue with These Details
- Terminal output (first 100 lines)
- Diagnostic page screenshot
- Output of standalone radio test
- Hardware setup (dev board model, radio module model, connection method)
