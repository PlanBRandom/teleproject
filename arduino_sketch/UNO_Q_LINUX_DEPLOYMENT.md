# Deploying Python Pipeline on Arduino UNO Q (Debian Linux)

## Overview

The Arduino UNO Q runs **full Debian Linux** on its Qualcomm QRB2210 processor. This means you can run the **complete Python pipeline** directly on the UNO Q - no separate computer needed!

## What You Get

✅ **Full pipeline functionality**
- All 32 channels monitoring
- Complete device control
- Laird radio support (primary/secondary modes)
- MQTT publishing to Home Assistant
- All register reading/writing

✅ **Standalone operation**
- UNO Q connects to WiFi
- Publishes directly to HA MQTT broker
- No PC required after setup

✅ **Better than HA Add-on**
- Can be placed directly at monitoring location
- Independent of Home Assistant server
- Can continue logging even if HA is down

## Hardware Setup

### Connections

```
Arduino UNO Q                    Hardware
-------------                    --------

USB-C Port -----------------> Power supply (5V 3A recommended)

WiFi Built-in --------------> Your network

UART Pins:
  TX (GPIO Pin) -----------> MAX485 DI
  RX (GPIO Pin) -----------> MAX485 RO
  GPIO for DE/RE ----------> MAX485 DE & RE
  5V ----------------------> MAX485 VCC
  GND ---------------------> MAX485 GND

MAX485:
  A -----------------------> OI Monitor A/+
  B -----------------------> OI Monitor B/-

Optional:
  USB Port ----------------> Laird Radio (COM port)
```

## Software Setup

### 1. Access UNO Q Linux

Connect to the UNO Q via SSH or serial console:

```bash
# Default credentials (check Arduino docs)
ssh arduino@uno-q.local
# or
ssh arduino@<ip-address>
```

### 2. Install Dependencies

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv git

# Install system dependencies for serial communication
sudo apt install -y python3-serial
```

### 3. Clone Repository

```bash
cd ~
git clone https://github.com/PlanBRandom/teleproject.git
cd teleproject
```

### 4. Create Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Configure Serial Ports

Find your serial devices:

```bash
ls -l /dev/tty*

# Common serial ports on UNO Q:
# /dev/ttyUSB0 - USB serial adapter (for Modbus or Radio)
# /dev/ttyS0   - UART pins on headers
# /dev/ttyACM0 - USB devices
```

Set permissions:

```bash
sudo usermod -a -G dialout arduino
sudo chmod 666 /dev/ttyUSB0  # or your serial port
```

**Log out and back in** for group changes to take effect.

### 6. Configure Pipeline

Edit `configs/lovelace/dashboard.yaml`:

```yaml
modbus:
  port: "/dev/ttyUSB0"  # or /dev/ttyS0 for UART pins
  baudrate: 9600
  timeout: 3
  
devices:
  - name: "OI-7530-1"
    slave_id: 1
    model: "OI-7530"
    channels: [1, 2, 3, 4, 5, 6, 7, 8]
    
  - name: "OI-7530-2"
    slave_id: 2
    model: "OI-7530"
    channels: [1, 2, 3, 4, 5, 6, 7, 8]

mqtt:
  broker: "192.168.1.100"  # Your Home Assistant IP
  port: 1883
  username: "homeassistant"
  password: "your_mqtt_password"
  base_topic: "oi_monitors"
  
radio:
  enabled: true
  port: "/dev/ttyUSB1"  # If radio on separate USB port
  baudrate: 9600
  mode: "secondary"  # or "primary"
  network_channel: 25
```

### 7. Test Connection

```bash
source venv/bin/activate
python hardware_test.py
```

You should see your OI monitors detected!

### 8. Run Pipeline Manually

```bash
source venv/bin/activate
python -m pipeline.main
```

### 9. Create Systemd Service (Auto-start)

Create `/etc/systemd/system/oi-monitor.service`:

```bash
sudo nano /etc/systemd/system/oi-monitor.service
```

Paste this configuration:

```ini
[Unit]
Description=OI Gas Monitor Bridge
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=arduino
WorkingDirectory=/home/arduino/teleproject
Environment="PATH=/home/arduino/teleproject/venv/bin:/usr/bin:/bin"
ExecStart=/home/arduino/teleproject/venv/bin/python -m pipeline.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable oi-monitor.service
sudo systemctl start oi-monitor.service

# Check status
sudo systemctl status oi-monitor.service

# View logs
sudo journalctl -u oi-monitor.service -f
```

## WiFi Configuration

The UNO Q has built-in WiFi. Configure via NetworkManager:

```bash
# List available networks
nmcli device wifi list

# Connect to network
sudo nmcli device wifi connect "YourSSID" password "YourPassword"

# Check connection
ip addr show wlan0
```

## Performance

The UNO Q specs for this application:

- **CPU**: Quad-core A53 @ 2.0 GHz - plenty for Python
- **RAM**: 2GB or 4GB - more than enough
- **Storage**: microSD card - ample space for logs
- **WiFi**: Dual-band 2.4/5GHz - fast MQTT
- **Power**: ~2-3W typical

**Expected Performance:**
- Read 32 channels: ~200ms
- MQTT publish: ~50ms
- CPU usage: <10%
- RAM usage: ~100MB

## Advantages Over Other Deployments

### vs Arduino Sketch (MCU side)
- ✅ Full 32 channels (MCU limited to 8-16)
- ✅ Radio protocol support
- ✅ Easier debugging
- ✅ More processing power
- ✅ Better logging

### vs Home Assistant Add-on
- ✅ Placed at monitoring location
- ✅ Independent of HA server
- ✅ Lower latency
- ✅ Can log locally
- ✅ Continues if HA is down

### vs Raspberry Pi
- ✅ More compact
- ✅ Lower power
- ✅ Arduino ecosystem compatible
- ✅ Built-in Arduino shield compatibility

## Monitoring and Logs

```bash
# View service logs
sudo journalctl -u oi-monitor.service -f

# View system logs
tail -f /var/log/syslog

# Check CPU/RAM usage
htop

# Monitor serial traffic
sudo cat /dev/ttyUSB0 | hexdump -C
```

## Remote Access

Access your UNO Q remotely:

### SSH Access
```bash
ssh arduino@<ip-address>
```

### VNC (if configured)
Connect to UNO Q desktop environment

### Web Dashboard (optional)
Create a simple Flask dashboard to view monitor status

## Updating Code

```bash
cd ~/teleproject
git pull origin main
sudo systemctl restart oi-monitor.service
```

## Troubleshooting

**"Permission denied" on serial port**
```bash
sudo usermod -a -G dialout arduino
sudo chmod 666 /dev/ttyUSB0
# Log out and back in
```

**"Module not found"**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Service won't start**
```bash
# Check logs
sudo journalctl -u oi-monitor.service -n 50

# Test manually
source venv/bin/activate
python -m pipeline.main
```

**WiFi not connecting**
```bash
# Check WiFi status
nmcli device status

# Restart WiFi
sudo nmcli radio wifi off
sudo nmcli radio wifi on
```

**Can't find serial port**
```bash
# List all serial devices
ls -l /dev/tty*

# Check USB devices
lsusb

# Check kernel messages
dmesg | grep tty
```

## Production Checklist

- [ ] UNO Q powered and booted
- [ ] WiFi connected and stable
- [ ] Serial ports configured and accessible
- [ ] Python environment created and working
- [ ] Config file updated with correct settings
- [ ] Hardware test passed
- [ ] MQTT connection to HA verified
- [ ] Systemd service enabled
- [ ] Service starts on boot
- [ ] Logs show successful readings
- [ ] HA entities appearing correctly
- [ ] Consider UPS for power backup

## Next Steps

1. **Deploy to UNO Q**: Follow setup steps above
2. **Test thoroughly**: Run for 24 hours to ensure stability
3. **Create HA dashboards**: Use the MQTT entities
4. **Set up alerts**: HA automations for gas levels
5. **Add monitoring**: Track UNO Q health (CPU, RAM, uptime)

## Hybrid Deployment Option

You can also run **BOTH**:
- **Python on Linux (MPU)**: Full monitoring pipeline
- **Arduino on MCU**: Custom real-time controls or displays

They can communicate via the **Arduino Bridge RPC** library!

Example: Python does monitoring, Arduino sketch controls local display or relays based on readings passed via RPC.
