# OI Monitor Control Center - Web GUI

A unified web interface for testing, configuring, and monitoring OI gas detection systems.

## Features

### 🔌 Modbus Device Management
- Connect to OI-7530/7010/7032 monitors
- Read device information (serial, model, firmware)
- Monitor real-time gas readings
- View all 32 channels simultaneously
- Control channels (enable/disable)
- Set relay setpoints

### 📡 Laird Radio Configuration
- Connect to Laird LT1110/RM024 modules
- Configure network channel (1-78)
- Set primary/secondary mode
- Configure System ID
- Check RSSI and MAC address
- Send test packets (primary mode)

### 📊 Real-time Monitoring
- Live channel updates via WebSocket
- Alert highlighting for high readings
- Activity logging
- Connection status indicators

### 🎛️ Unified Interface
- No need to switch between CLI scripts
- All tools in one place
- Works on any device with a browser
- No Arduino flashing required

## Quick Start

### Windows

1. **Double-click** `start_gui.bat`
2. Open browser to http://localhost:5000
3. Start testing!

### Manual Start

```bash
cd web_gui
python app.py
```

Then open: http://localhost:5000

## Usage

### 1. Connect to Modbus Device

1. Click "🔄 Refresh Ports" to scan available COM ports
2. Select your device's COM port
3. Set Slave ID (usually 1, 2, or 3)
4. Click "Connect"
5. Device info will appear automatically

### 2. Read Channels

1. Click "📊 Read All Channels" for one-time read
2. OR click "🔴 Start Live Monitoring" for continuous updates
3. Channels with readings >100 PPM will highlight red

### 3. Configure Radio

**Connect Tab:**
1. Select radio COM port
2. Click "Connect Radio"
3. View RSSI and MAC address

**Configure Tab:**
1. Set Network Channel (1-78)
2. Choose Primary or Secondary mode
3. Set System ID
4. Click "Configure Radio"
5. Settings saved to EEPROM

**Test TX Tab:**
1. (Primary mode only)
2. Set test channel, reading, and gas type
3. Click "Send Test Packet"
4. Watch for packet on secondary radio

### 4. Device Control

- Turn channels on/off
- Set relay setpoints
- Reset device
- View diagnostics

## Access from Other Devices

The web server runs on port 5000 and is accessible from:

- **Same PC**: http://localhost:5000
- **Other devices on network**: http://YOUR_PC_IP:5000

Find your PC's IP:
```bash
ipconfig
# Look for IPv4 Address
```

## Benefits Over CLI Scripts

### Before (Multiple scripts)
```bash
python hardware_test.py       # Test devices
python configure_radio.py     # Configure radio
python test_radio.py          # Test radio
python generate_channels.py   # Generate configs
```

### Now (One web interface)
- Open browser → http://localhost:5000
- Everything in one place!

## Features

✅ **No reflashing** - Test Arduino and PC setups without code changes
✅ **Visual feedback** - See readings, status, and logs in real-time
✅ **Multi-device** - Access from phone, tablet, or another PC
✅ **Persistent** - Leave running and check anytime
✅ **Logging** - Activity log for troubleshooting

## API Endpoints

The web GUI exposes a REST API for automation:

### Modbus
- `POST /api/modbus/connect` - Connect to device
- `POST /api/modbus/disconnect` - Disconnect
- `GET /api/modbus/read_channels` - Read all channels
- `GET /api/modbus/device_info` - Get device info
- `POST /api/device/channel/<n>/toggle` - Enable/disable channel
- `POST /api/device/channel/<n>/setpoint` - Set relay setpoint

### Radio
- `POST /api/radio/connect` - Connect radio
- `POST /api/radio/disconnect` - Disconnect
- `GET /api/radio/status` - Get RSSI and MAC
- `POST /api/radio/configure` - Configure with AT commands
- `POST /api/radio/send_test` - Send test packet

### System
- `GET /api/ports` - List available COM ports
- `GET /api/gas_types` - Get gas type codes
- `GET /api/sensor_types` - Get sensor type codes

### WebSocket Events
- `connect` - Client connected
- `start_monitoring` - Start live updates
- `stop_monitoring` - Stop live updates
- `modbus_data` - Channel readings
- `radio_status` - Radio status updates

## Screenshots

### Main Dashboard
- Modbus connection panel
- Radio configuration tabs
- Live channel monitoring grid
- Activity log

### Channel Display
- Real-time PPM values
- Gas type labels
- Alert highlighting (>100 PPM)
- Auto-refresh

### Radio Configuration
- Network channel selector
- Primary/Secondary mode toggle
- AT command feedback
- Test packet transmission

## Troubleshooting

**"Port already in use"**
- Another program is using the serial port
- Close other connections (hardware_test.py, configure_radio.py, etc.)

**"Permission denied" on COM port**
- Run as Administrator (Windows)
- Check port isn't open in Arduino IDE or PuTTY

**"No active channels detected"**
- Verify Modbus connection
- Check baud rate (should be 9600)
- Ensure device is powered on

**Can't access from other devices**
- Check Windows Firewall allows port 5000
- Verify devices on same network
- Use correct PC IP address

**Radio configuration fails**
- Ensure radio is in receive mode first
- Wait for "OK" after +++
- Check baud rate is 9600
- Try power cycling the radio

## Development

### Project Structure
```
web_gui/
├── app.py                 # Flask server and API
├── templates/
│   └── index.html        # Web interface
├── requirements.txt      # Python dependencies
├── start_gui.bat        # Windows launcher
└── README.md            # This file
```

### Adding Features

To add new API endpoints, edit `app.py`:

```python
@app.route('/api/custom/endpoint')
def custom_endpoint():
    # Your code here
    return jsonify({'success': True, 'data': result})
```

To modify the UI, edit `templates/index.html`.

### Running in Debug Mode

```bash
python app.py
# Server runs with auto-reload on code changes
```

## Security Note

This web interface is designed for **local network use only**. Do not expose it to the internet without:
- Adding authentication
- Using HTTPS
- Implementing rate limiting
- Validating all inputs

For production deployments, consider using:
- nginx reverse proxy
- SSL certificates
- Authentication middleware

## Integration with Home Assistant

The web GUI can run alongside the HA add-on:

- **HA Add-on**: Production monitoring at home
- **Web GUI**: Testing and configuration at work

Both can operate independently!

## Future Enhancements

Potential features:
- [ ] Data export (CSV, JSON)
- [ ] Historical graphs
- [ ] Email/SMS alerts
- [ ] Multi-device comparison
- [ ] Calibration wizard
- [ ] Firmware update tool
- [ ] Batch configuration
- [ ] Custom dashboards

## License

Part of the OI Monitor Pipeline project.
