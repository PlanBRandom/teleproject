# One-Click Home Assistant Add-on Installation

## 🎉 Quick Install

Click this button to add the repository to your Home Assistant:

[![Add Repository to Home Assistant][repository-badge]][repository-url]

Then install the "OI Gas Monitor Bridge" add-on!

## Manual Installation

If the button doesn't work, follow these steps:

1. **Add Repository**
   - In Home Assistant, go to **Settings** → **Add-ons** → **Add-on Store**
   - Click the **⋮** menu (top right) → **Repositories**
   - Add this URL:
     ```
     https://github.com/PlanBRandom/teleproject
     ```

2. **Install Add-on**
   - Refresh the add-on store
   - Find "OI Gas Monitor Bridge"
   - Click **Install**

3. **Configure**
   - Go to the **Configuration** tab
   - Set your Modbus port (e.g., `/dev/ttyUSB0`)
   - Set your MQTT password
   - Add your OI monitors with slave IDs

4. **Start**
   - Click **Start**
   - Check the **Log** tab for any issues

## Configuration Example

```yaml
modbus:
  connection_type: "rtu"
  port: "/dev/ttyUSB0"
  baudrate: 9600
  devices:
    - name: "Warehouse Monitor"
      slave_id: 1
      model: "OI-7530"
    - name: "Tank Farm Monitor"
      slave_id: 2
      model: "OI-7530"

mqtt:
  host: "core-mosquitto"
  port: 1883
  username: "homeassistant"
  password: "your_mqtt_password"

polling_interval: 30
```

## Finding Your Serial Port

To find which port your RS-485 adapter is using:

1. Go to **Settings** → **System** → **Hardware**
2. Click **All Hardware**
3. Look for your USB-to-RS485 adapter
4. The device path will be shown (e.g., `/dev/ttyUSB0`)

## Troubleshooting

**Add-on won't start:**
- Check the Log tab for errors
- Verify serial port exists: `ls /dev/tty*`
- Check Modbus slave addresses are correct
- Ensure MQTT broker is running

**No sensors appearing:**
- Check MQTT integration is configured in HA
- Verify devices list in configuration
- Check polling_interval isn't too long
- Look for errors in the add-on log

**Wireless radio not working:**
- Enable radio in configuration: `radio.enabled: true`
- Configure radio first with `configure_radio.py`
- Check network channel matches monitors
- Verify System ID is 37

## Next Steps

Once installed and running:

1. **Check Entities**: Go to **Settings** → **Devices & Services** → **MQTT**
2. **Create Dashboard**: Use generated Lovelace configs in `/share/oi-gas-monitor/`
3. **Set Up Automations**: Create alerts for high gas readings or faults
4. **Monitor Logs**: Check add-on logs periodically for communication errors

## Support

- **Issues**: https://github.com/PlanBRandom/teleproject/issues
- **Discussions**: https://github.com/PlanBRandom/teleproject/discussions
- **Documentation**: Full docs in repository

[repository-badge]: https://img.shields.io/badge/Add%20Repository-41BDF5?logo=home-assistant&style=for-the-badge
[repository-url]: https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FPlanBRandom%2Fteleproject
