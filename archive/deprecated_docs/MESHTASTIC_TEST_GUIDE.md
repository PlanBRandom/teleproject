# OI-7500 Meshtastic Two-Device Test Setup

## What You Need

✅ **Device 1**: Heltec V3 on COM16 (you have this)
🔲 **Device 2**: Another Meshtastic device (T-Beam, RAK, Heltec, etc.)

Both devices must be on the **same LoRa frequency/channel**.

## Quick Test Setup (Both Devices Local)

### Step 1: Install Mosquitto (Local MQTT Broker)

**Windows:**
Download: https://mosquitto.org/download/
Or run: `choco install mosquitto` (if you have Chocolatey)

**Verify installation:**
```bash
mosquitto --help
```

### Step 2: Start Local MQTT Broker

```bash
# Terminal 1: Start Mosquitto
mosquitto -v -c mosquitto_test.conf
```

You should see:
```
1673... mosquitto version 2.0.18 starting
1673... Opening ipv4 listen socket on port 1883
```

### Step 3: Test Simple Monitor with Local MQTT

Update `simple_config.json`:
```json
{
  "mqtt": {
    "enabled": true,
    "broker": "localhost",
    "port": 1883,
    "username": "",
    "password": "",
    "use_tls": false
  }
}
```

```bash
# Terminal 2: Start monitoring (publishes to localhost)
python simple_monitor.py
```

### Step 4: Start Bridge (Device 1 - Heltec V3)

The bridge is already configured for COM16 and localhost MQTT.

```bash
# Terminal 3: Start bridge
python meshtastic_bridge.py
```

You should see:
```
✓ MQTT connected - Subscribed to: oi7500/channel+
✓ Meshtastic connected: Meshtastic a910
🚀 Bridge active - forwarding telemetry to mesh network
```

### Step 5: Start Gateway (Device 2 - Your Other Meshtastic)

First, connect your second Meshtastic device and find its COM port:

```bash
# List COM ports
python -m serial.tools.list_ports
```

Update `meshtastic_config.json` gateway section:
```json
{
  "gateway_node": {
    "meshtastic_port": "COM17",  // Your second device port
    "location_name": "Central Hub"
  }
}
```

Then start gateway:
```bash
# Terminal 4: Start gateway
python meshtastic_gateway.py
```

You should see:
```
✓ Meshtastic gateway connected
✓ MQTT connected to cloud broker
🚀 Gateway active - receiving from mesh and publishing to MQTT
```

### Step 6: Watch Data Flow

```bash
# Terminal 5: Monitor cloud MQTT
mosquitto_sub -h a1bcc059f5f74a6d8271e8b567fecc6d.s1.eu.hivemq.cloud \
  -p 8883 -u laird -P LairdRM024 --cafile /path/to/ca.crt \
  -t "oi7500/#" -v
```

## Data Flow Diagram

```
WireFree Radio (COM11)
        ↓
simple_monitor.py
        ↓
localhost MQTT (port 1883)
        ↓
meshtastic_bridge.py
        ↓
Heltec V3 (COM16) → LoRa Mesh (5-10 miles) → Device 2 (COM17)
                                                      ↓
                                              meshtastic_gateway.py
                                                      ↓
                                              Cloud MQTT (HiveMQ)
                                                      ↓
                                              Your monitoring apps
```

## Testing Without Second Device

If you only have one Meshtastic device for now:

**Option 1**: Test bridge only
- Bridge will forward to mesh
- Use Meshtastic app on phone to see packets
- App must be on same channel

**Option 2**: Simulate with loopback
- Bridge and gateway can both connect to same device
- Not realistic but validates code

**Option 3**: Order second device
- Recommended: ~$40-60 on Amazon
- Any Meshtastic device works (same frequency band)

## When You Leave - Remote Deployment

### Leave at Edge Site:
- Raspberry Pi or PC
- WireFree radio (COM11)
- Heltec V3 (COM16)
- Power supply (or battery + solar)
- Runs: `simple_monitor.py` + `meshtastic_bridge.py`

### Take With You:
- Second Meshtastic device
- Laptop or Raspberry Pi
- Runs: `meshtastic_gateway.py`
- Publishes to cloud MQTT (internet connection needed)

### Network Range:
- **Line of sight**: 5-10 miles
- **Urban**: 1-3 miles  
- **Buildings**: 500-1000 feet through walls

### Can receive from anywhere with internet:
Once gateway publishes to cloud MQTT, you can monitor from anywhere:
- Your home computer
- Phone app
- Web dashboard
- All subscribe to same cloud MQTT topics

## Troubleshooting

### Bridge not forwarding
```bash
# Check local MQTT is running
mosquitto_sub -h localhost -p 1883 -t "oi7500/#" -v

# Verify simple_monitor is publishing
# Should see: oi7500/channel01 {...json data...}
```

### Gateway not receiving
```bash
# Check devices are on same channel
python test_meshtastic.py COM16  # Device 1
python test_meshtastic.py COM17  # Device 2

# Both should show in "Known nodes in mesh"
```

### No cloud MQTT messages
```bash
# Test gateway MQTT connection directly
mosquitto_pub -h a1bcc059f5f74a6d8271e8b567fecc6d.s1.eu.hivemq.cloud \
  -p 8883 -u laird -P LairdRM024 --cafile /etc/ssl/certs/ca-certificates.crt \
  -t "test" -m "hello"
```

## Next Steps

1. ✅ Install Mosquitto
2. ✅ Test simple_monitor → localhost MQTT
3. ✅ Test bridge → Heltec V3 (you can see packets in Meshtastic app)
4. 🔲 Get second Meshtastic device
5. 🔲 Configure both devices same channel
6. 🔲 Test gateway receives from mesh
7. 🔲 Verify cloud MQTT publishing
8. 🚀 Deploy to remote site!
