# Arduino UNO R4 WiFi Setup for OI Gas Monitors

## Hardware You Have

✅ **Arduino UNO R4 WiFi**
- Qualcomm QRB2210 (WiFi)
- STM32U585 MCU
- 32KB RAM, 256KB Flash
- Built-in WiFi - perfect for MQTT!

✅ **Arduino UNO SPE Shield** (Optional)
- Single Pair Ethernet
- Alternative to WiFi if preferred

## What You Need

1. **MAX485 RS-485 Module** (~$2)
2. **Jumper wires**
3. **5V power supply** for Arduino

## Wiring Diagram

```
Arduino UNO R4 WiFi          MAX485 Module          OI Monitor
-----------------            -------------          ----------
D0 (RX) ----OR---┐
D2 (RX) ---------├---------> RO
                 │
D1 (TX) ----OR---┤
D3 (TX) ---------├---------> DI
                 │
D4 --------------├---------> DE & RE (tied together)
                 │
5V --------------├---------> VCC
                 │
GND -------------├---------> GND
                 │
                 └---------> A --------> A/+ (Green)
                             B --------> B/- (White)
```

**Note**: Use D0/D1 (Hardware Serial1) OR D2/D3 (SoftwareSerial)
- D0/D1 is faster but you lose USB debugging during operation
- D2/D3 allows USB debugging (recommended for setup)

## Arduino IDE Setup

### 1. Install Board Support

1. Open Arduino IDE
2. Go to **Tools → Board → Boards Manager**
3. Search for "Arduino UNO R4"
4. Install **"Arduino UNO R4 Boards"**

### 2. Install Libraries

**Tools → Manage Libraries**, search and install:

1. **ModbusMaster** by Doc Walker
2. **ArduinoMqttClient** by Arduino
3. **WiFiS3** (should be included with board package)

### 3. Configure the Sketch

Open `oi7530_uno_r4_wifi.ino` and edit:

```cpp
// WiFi Configuration
const char* WIFI_SSID = "YourWiFiSSID";
const char* WIFI_PASSWORD = "YourWiFiPassword";

// MQTT Configuration
const char* MQTT_BROKER = "192.168.1.100";  // Your HA IP
const char* MQTT_USERNAME = "homeassistant";
const char* MQTT_PASSWORD = "your_mqtt_pass";

// Modbus Configuration
#define MODBUS_SLAVE_ID 1  // Your OI-7530 slave address

// Serial Choice
#define USE_HARDWARE_SERIAL false  // Use true for D0/D1, false for D2/D3
```

### 4. Upload

1. **Tools → Board**: Arduino UNO R4 WiFi
2. **Tools → Port**: Select your COM port
3. Click **Upload** (→)

### 5. Monitor

Open **Tools → Serial Monitor** (115200 baud) to see:
```
===========================================
  OI Gas Monitor - Arduino UNO R4 WiFi
===========================================

✓ Modbus initialized
  Slave ID: 1
  Baud Rate: 9600
Connecting to WiFi: YourNetwork
✓ WiFi connected
  IP Address: 192.168.1.150
✓ MQTT connected
✓ Published discovery messages

✓ System Ready
===========================================

--- Polling OI Monitor ---
Channel 1: 0.00 PPM
Channel 2: 0.00 PPM
Channel 3: 15.34 PPM
...
```

## Features

✅ **WiFi Connection**: Built-in, no shield needed
✅ **MQTT Publishing**: Sends readings to Home Assistant
✅ **Auto-Discovery**: Creates HA entities automatically
✅ **8 Channels**: Reads channels 1-8 (expandable to 32)
✅ **Diagnostics**: Uptime, memory usage
✅ **Robust**: Auto-reconnect for WiFi and MQTT

## Home Assistant Integration

Once running, sensors automatically appear in Home Assistant:
- `sensor.oi_7530_1_channel_1`
- `sensor.oi_7530_1_channel_2`
- ... (up to channel 8)
- `sensor.oi_7530_1_uptime`

No manual configuration needed!

## Troubleshooting

**"WiFi connection failed"**
- Check SSID and password
- Ensure 2.4GHz WiFi (not 5GHz)
- Move closer to router

**"MQTT connection failed"**
- Verify broker IP address
- Check MQTT username/password
- Ensure port 1883 is open

**"Modbus read error"**
- Check wiring (A/B correct?)
- Verify baud rate (9600)
- Check slave ID matches monitor
- Try swapping A and B wires

**No channels reading**
- Check MAX485 DE/RE tied together
- Verify monitor is powered on
- Try reversing A/B wires
- Check GND connection

## Using SPE Shield (Optional)

If you prefer wired Ethernet over WiFi:

1. Stack SPE shield on UNO R4
2. Change code to use Ethernet library instead of WiFi
3. Connect Ethernet cable
4. Adjust wiring since SPE may use some pins

## Memory Usage

UNO R4 has **32KB RAM** - plenty for this application:
- Modbus: ~2KB
- WiFi/MQTT: ~8KB  
- Application: ~2KB
- **Free: ~20KB** ✓

## Next Steps

1. Wire up MAX485 to UNO R4
2. Edit sketch with your WiFi/MQTT credentials
3. Upload and test
4. Check Home Assistant for new sensors
5. Create dashboards!

## Advantages vs Python/HA Add-on

**Arduino Pros:**
- ✅ Standalone operation
- ✅ Lower power consumption
- ✅ Can run without HA server
- ✅ Direct at monitoring location

**HA Add-on Pros:**
- ✅ No hardware setup
- ✅ Easier to update
- ✅ Full 32 channels
- ✅ Better for multiple monitors
- ✅ Includes radio support

**Recommendation**: 
- Use **Arduino** for single monitor at remote location
- Use **HA Add-on** for 2+ monitors or when HA server nearby
