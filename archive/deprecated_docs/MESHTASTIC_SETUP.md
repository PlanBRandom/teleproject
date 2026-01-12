# OI-7500 Meshtastic Bridge Setup

Bridge your existing OI-7500 telemetry system over Meshtastic LoRa mesh network for extended range and redundancy.

## System Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│ OI-7500 Sensors │      │   Edge Node      │      │  Gateway Node   │
│   (WireFree)    │─────▶│  Raspberry Pi    │─────▶│  Central Hub    │
│                 │Radio │  + Meshtastic    │ LoRa │  + Meshtastic   │
│  CH01-CH32      │      │  simple_monitor  │ Mesh │  meshtastic_    │
└─────────────────┘      │  meshtastic_     │      │  gateway        │
                         │  bridge          │      └─────────────────┘
                         └──────────────────┘              │
                                                            │
                                                            ▼
                                                    ┌──────────────┐
                                                    │ Cloud MQTT   │
                                                    │ HiveMQ/AWS   │
                                                    └──────────────┘
```

## Hardware Requirements

### Edge Node (Remote Site)
- Raspberry Pi 3/4 or ESP32
- WireFree radio module (UART)
- Meshtastic device (T-Beam, RAK, Heltec, etc.)
- Power supply (can run on battery with solar)

### Gateway Node (Central Hub)
- Raspberry Pi 3/4 or Linux PC
- Meshtastic device (same frequency band as edge nodes)
- Internet connection (WiFi/Ethernet)

## Software Installation

### 1. Install Python Dependencies

```bash
pip3 install meshtastic pyserial paho-mqtt pypubsub
```

### 2. Configure Meshtastic Devices

**Edge Node Configuration:**
```bash
# Connect edge node via USB
meshtastic --set lora.region US  # Or your region
meshtastic --set lora.modem_preset LONG_FAST
meshtastic --ch-set name oi7500
meshtastic --info
```

**Gateway Node Configuration:**
```bash
# Connect gateway via USB
meshtastic --set lora.region US
meshtastic --set lora.modem_preset LONG_FAST
meshtastic --ch-set name oi7500
meshtastic --info
```

**Important:** Both devices must use the same region, modem preset, and channel name.

### 3. Configure Bridge

Edit `meshtastic_config.json`:

```json
{
  "edge_node": {
    "meshtastic_port": "/dev/ttyUSB2",  // Meshtastic device port
    "location_name": "Site A"
  },
  "gateway_node": {
    "meshtastic_port": "/dev/ttyUSB0",
    "location_name": "Central Hub"
  },
  "mqtt_source": {
    "broker": "localhost",  // Local MQTT from simple_monitor
    "port": 1883
  },
  "mqtt_destination": {
    "broker": "your-cloud-broker.com",  // Central MQTT
    "port": 8883,
    "username": "your_user",
    "password": "your_pass",
    "use_tls": true
  },
  "bridge": {
    "forward_interval": 5,  // Seconds between updates per channel
    "compress_data": true,  // Binary encoding (15 bytes vs ~200 JSON)
    "only_forward_faults": false  // Set true to only send alarms
  }
}
```

## Deployment

### Edge Node (Remote Site)

**Setup:**
1. Connect WireFree radio to USB/UART
2. Connect Meshtastic device to USB
3. Configure simple_monitor.py for local MQTT
4. Start monitoring and bridge

```bash
# Terminal 1: Start OI-7500 monitoring (local MQTT)
python3 simple_monitor.py

# Terminal 2: Start Meshtastic bridge
python3 meshtastic_bridge.py
```

**What it does:**
- Monitors WireFree packets from OI-7500
- Publishes to local MQTT
- Bridge subscribes to local MQTT
- Encodes telemetry to 15 bytes (compressed)
- Forwards over Meshtastic mesh

### Gateway Node (Central Hub)

```bash
# Start Meshtastic gateway
python3 meshtastic_gateway.py
```

**What it does:**
- Receives telemetry from Meshtastic mesh
- Decodes binary or JSON format
- Publishes to central cloud MQTT
- Same topic structure: `oi7500/channel##`

## Run as Services (Auto-start)

### Edge Node Service

Create `/etc/systemd/system/oi7500-bridge.service`:
```ini
[Unit]
Description=OI-7500 Meshtastic Bridge
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/oi-7500-pipeline
ExecStart=/usr/bin/python3 /home/pi/oi-7500-pipeline/meshtastic_bridge.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable oi7500-bridge.service
sudo systemctl start oi7500-bridge.service
```

### Gateway Service

Create `/etc/systemd/system/oi7500-gateway.service`:
```ini
[Unit]
Description=OI-7500 Meshtastic Gateway
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/oi-7500-pipeline
ExecStart=/usr/bin/python3 /home/pi/oi-7500-pipeline/meshtastic_gateway.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable oi7500-gateway.service
sudo systemctl start oi7500-gateway.service
```

## Data Encoding

### Binary Format (Compressed - Default)
**15 bytes total** - Perfect for LoRa bandwidth limits

| Byte(s) | Field | Type | Description |
|---------|-------|------|-------------|
| 0 | Channel | uint8 | Channel number (1-32) |
| 1-2 | Reading | int16 | Reading * 10 (divide by 10) |
| 3 | Gas Type | uint8 | Gas type code (0-26) |
| 4 | Battery | uint8 | Voltage * 10 (0.0-25.5V) |
| 5 | Fault Code | uint8 | Fault code (0-15) |
| 6-9 | Timestamp | uint32 | Unix epoch |
| 10 | Sensor Info | uint8 | Mode (4 bits) + Type (4 bits) |
| 11 | Precision | uint8 | Reading decimal places |
| 12-14 | Reserved | 3 bytes | Future use |

**Advantage:** 15 bytes vs ~200 bytes JSON = 13x smaller!

### JSON Format (Uncompressed)
Set `"compress_data": false` in config for human-readable JSON.

## Performance

### LoRa Range
- **Line of sight:** 5-10 miles
- **Urban:** 1-3 miles
- **Indoor:** 500-1000 feet (through walls)

### Data Rates
- **LONG_FAST preset:** ~1.95 kbps airtime
- **15-byte packet:** ~60ms airtime
- **Can forward 32 channels every 5 seconds** with room to spare

### Battery Life (Edge Node)
- Pi Zero 2W + Meshtastic: ~24-48 hours on 10,000mAh battery
- With solar panel: Continuous operation
- ESP32 + Meshtastic: ~7 days on battery (with sleep modes)

## Mesh Network Benefits

✅ **Extended Range** - Miles vs hundreds of feet (WireFree)  
✅ **Redundancy** - Multiple paths to gateway  
✅ **Self-healing** - Mesh routes around failures  
✅ **No Infrastructure** - No WiFi/cellular needed  
✅ **Low Power** - Battery + solar viable  
✅ **Encrypted** - AES-128 by default  
✅ **Multiple Sites** - Add more edge nodes easily  

## Troubleshooting

### No mesh packets received
```bash
# Check Meshtastic connection
meshtastic --info

# Monitor mesh traffic
meshtastic --listen

# Verify frequency/region match
meshtastic --get lora
```

### Edge node not forwarding
```bash
# Check simple_monitor is publishing to local MQTT
mosquitto_sub -h localhost -t "oi7500/#" -v

# Check bridge is subscribed
# Look for "Subscribed to: oi7500/channel+" in bridge logs
```

### Gateway not publishing to cloud
```bash
# Test cloud MQTT connection
mosquitto_pub -h your-broker.com -p 8883 \
  -u username -P password --cafile /etc/ssl/certs/ca-certificates.crt \
  -t "test" -m "hello"
```

### High packet loss
- Reduce `forward_interval` (send less frequently)
- Set `only_forward_faults: true` (alarms only)
- Improve antenna placement (higher = better)
- Check for RF interference (WiFi, other LoRa devices)

## Advanced Configuration

### Multiple Edge Nodes

Each edge node forwards to the mesh independently:
```
Site A Edge → ┐
Site B Edge → ├─▶ Mesh Network ─▶ Gateway ─▶ Cloud MQTT
Site C Edge → ┘
```

Just set unique `location_name` in each edge node config.

### Fault-Only Mode

Save bandwidth by only forwarding alarms:
```json
{
  "bridge": {
    "only_forward_faults": true
  }
}
```

### Custom Forward Intervals Per Priority

Modify code to set interval based on fault level:
- Normal reading: 30 seconds
- Low battery: 10 seconds
- Critical fault: Immediate

## Integration with Existing System

The Meshtastic bridge is **completely transparent** to your existing setup:

✅ **No changes to simple_monitor.py** - Still publishes to MQTT as before  
✅ **No changes to cloud consumers** - Same topic structure  
✅ **Can run both** - Direct MQTT + Meshtastic mesh simultaneously  
✅ **Easy testing** - Start bridge, stop bridge, no impact on monitoring  

## Cost Estimate

**Per Edge Node:**
- Raspberry Pi Zero 2W: $15
- Meshtastic T-Beam: $40-60
- Solar panel + battery: $25
- **Total: ~$80-100 per remote site**

**Gateway:**
- Raspberry Pi 4: $35
- Meshtastic device: $40-60
- **Total: ~$75-95**

Much cheaper than cellular modems ($200+ per site + monthly fees)!

## Next Steps

1. ✅ Configure two Meshtastic devices
2. ✅ Test mesh communication with `meshtastic --sendtext "test"`
3. ✅ Deploy edge node with simple_monitor + bridge
4. ✅ Deploy gateway node
5. ✅ Verify telemetry flowing through mesh to cloud MQTT
6. 🚀 Add more edge nodes as needed!
