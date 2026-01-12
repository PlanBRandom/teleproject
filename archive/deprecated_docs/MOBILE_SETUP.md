# View OI-7500 Data on Your Phone

## MQTT Connection Settings

Your OI-7500 telemetry is being published to a cloud MQTT broker that you can access from anywhere.

### Connection Info:
- **Broker**: `a1bcc059f5f74a6d8271e8b567fecc6d.s1.eu.hivemq.cloud`
- **Port**: `8883`
- **Protocol**: MQTT over TLS/SSL
- **Username**: `laird`
- **Password**: `LairdRM024`

### Topics:
- **All channels**: `oi7500/#`
- **Specific channel**: `oi7500/channel01`, `oi7500/channel02`, etc.
- **Mesh bridge**: Topics forwarded through Meshtastic mesh

---

## Android Setup (Recommended: MQTT Dash)

### 1. Install App
Download **"MQTT Dash (IoT, Smart Home)"** from Google Play Store
- Free, no ads
- Great visualization with tiles

### 2. Add Connection
1. Open MQTT Dash
2. Tap **"+"** (top right)
3. Enter connection details:
   ```
   Connection name: OI-7500 Pipeline
   Broker: a1bcc059f5f74a6d8271e8b567fecc6d.s1.eu.hivemq.cloud
   Port: 8883
   Client ID: (leave auto-generated)
   Username: laird
   Password: LairdRM024
   ```
4. Enable **SSL/TLS**
5. Tap **SAVE**

### 3. Add Dashboard Tiles
Tap the **connection** you just created, then:

**For each channel:**
1. Tap **"+"** → **Text tile**
2. Settings:
   - **Name**: Channel 01 (or 02, 03, etc.)
   - **Topic**: `oi7500/channel01`
   - **JSON Path**: `$.reading` (to show just the reading)
3. Add more tiles for:
   - Battery: JSON Path = `$.battery`
   - Gas Type: JSON Path = `$.gas_type`
   - Fault: JSON Path = `$.fault_description`

**Quick view all channels:**
- Add a **Text tile** subscribed to `oi7500/#` to see all data

---

## iPhone Setup (MQTTool or EasyMQTT)

### Option 1: MQTTool (Free)
1. Install from App Store
2. Tap **"+"** → **New Connection**
3. Enter same connection details as Android
4. Subscribe to `oi7500/#`

### Option 2: EasyMQTT (Simpler UI)
1. Install from App Store
2. Add broker with same settings
3. Subscribe to topics

---

## Alternative: Web Browser (Any Device)

### HiveMQ Web Client
1. Go to: http://www.hivemq.com/demos/websocket-client/
2. Click **Connect** (or enter your broker details manually)
3. Host: `a1bcc059f5f74a6d8271e8b567fecc6d.s1.eu.hivemq.cloud`
4. Port: `8884` (WebSocket port)
5. Username/Password: Same as above
6. Enable **TLS**
7. Subscribe to `oi7500/#`

---

## What You'll See

### Channel Data Example:
```json
{
  "channel": 1,
  "reading": 12.3,
  "gas_type": "LEL",
  "battery": 3.2,
  "fault_code": 0,
  "fault_description": "F0 - No Fault",
  "timestamp": "2026-01-09T10:30:45.123456"
}
```

### Topics Published:
- `oi7500/channel01` through `oi7500/channel32`
- Each channel publishes when data is received from:
  - **WireFree radios** (COM7, COM11, COM12)
  - **Modbus RTU** (COM10)
  - **Meshtastic mesh** (forwarded from remote nodes)

---

## Troubleshooting

### "Connection failed" or "Cannot connect"
- Check your phone has internet (WiFi or cellular)
- Verify TLS/SSL is enabled
- Make sure port is **8883** not 1883

### "No data appearing"
- Your pipeline must be running: `.\start_full_system.ps1`
- Check sensors are powered and transmitting
- Verify MQTT broker connection from PC:
  ```powershell
  # Test from PC
  Test-NetConnection a1bcc059f5f74a6d8271e8b567fecc6d.s1.eu.hivemq.cloud -Port 8883
  ```

### "Old data / not updating"
- Check timestamp in the message
- Verify radios are receiving fresh sensor data
- Pipeline may have stopped - check terminal

---

## Advanced: Custom Dashboard

### Home Assistant Integration
If you use Home Assistant:
1. Add MQTT integration
2. Point to same HiveMQ broker
3. Sensors will auto-discover via discovery messages
4. View on Home Assistant app

### Node-RED Dashboard
1. Install Node-RED
2. Add MQTT broker node
3. Create dashboard with gauges and charts
4. Access from phone browser

---

## Seedt1000 Note

If your phone is connected to a **Seedt1000** (assuming it's a local network device), you may also need:

**If Seedt1000 is on a different network:**
- Your phone needs **internet access** to reach HiveMQ cloud
- Or set up port forwarding/VPN to reach local Mosquitto (port 1883)

**If you want to use local MQTT only:**
1. Connect phone to same WiFi as PC
2. Find PC's local IP: `ipconfig` (look for IPv4 Address)
3. Use **local broker** settings instead:
   - Broker: `<your-pc-ip>` (e.g., 192.168.1.100)
   - Port: `1883`
   - No username/password
   - No TLS
4. Subscribe to `oi7500/#`

---

## Quick Test from Phone

Once connected, you should immediately see data if:
- ✅ Pipeline is running
- ✅ Sensors are transmitting
- ✅ Phone has connectivity

**Expect updates every 5-10 seconds** depending on sensor polling rate.
