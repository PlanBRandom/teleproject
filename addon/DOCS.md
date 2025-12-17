# Home Assistant Add-on: OI Gas Monitor Bridge

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]
![Supports armhf Architecture][armhf-shield]
![Supports armv7 Architecture][armv7-shield]
![Supports i386 Architecture][i386-shield]

## About

This add-on provides a Modbus to MQTT bridge for OI Analytical gas monitors (OI-7530, OI-7010, OI-7032), with support for wireless sensors via Laird LT1110/RM024 radio modules.

## Features

- **Multi-Device Support**: Monitor multiple OI-7530/7010/7032 units simultaneously
- **Wireless Radio**: Direct support for OI Gen II wireless sensors via Laird radios
- **Home Assistant Integration**: Automatic MQTT discovery for all channels
- **Real-time Monitoring**: Gas readings, battery levels, fault detection
- **Device Control**: Reset devices, change settings, control relays
- **32 Channels**: Full support for all 32 sensor channels per monitor

## Installation

### One-Click Installation

1. Click this button to add the repository:

   [![Add Repository][repository-badge]][repository-url]

2. Click **Install** on the "OI Gas Monitor Bridge" add-on
3. Configure your settings (see Configuration below)
4. Start the add-on

### Manual Installation

1. In Home Assistant, go to **Settings** → **Add-ons** → **Add-on Store**
2. Click the **⋮** menu (top right) → **Repositories**
3. Add this repository URL:
   ```
   https://github.com/PlanBRandom/teleproject
   ```
4. Find "OI Gas Monitor Bridge" in the add-on store
5. Click **Install**

## Configuration

```yaml
modbus:
  connection_type: "rtu"          # "rtu" or "tcp"
  port: "/dev/ttyUSB0"            # Serial port for RTU
  host: "192.168.1.100"           # IP address for TCP
  baudrate: 9600
  devices:
    - name: "OI-7530-1"
      slave_id: 1
      model: "OI-7530"
    - name: "OI-7530-2"
      slave_id: 2
      model: "OI-7530"

mqtt:
  host: "core-mosquitto"          # Use "core-mosquitto" for HA MQTT broker
  port: 1883
  username: "homeassistant"
  password: "your_mqtt_password"
  discovery_prefix: "homeassistant"

radio:
  enabled: false                   # Set to true if using Laird radio
  port: "/dev/ttyUSB1"
  network_channel: 25
  mode: "secondary"                # "primary" or "secondary"
  api_mode: true

polling_interval: 30               # Seconds between reads
```

## Configuration Options

### Modbus Settings

| Option | Default | Description |
|--------|---------|-------------|
| `connection_type` | `rtu` | Connection type: `rtu` or `tcp` |
| `port` | `/dev/ttyUSB0` | Serial port for RTU connections |
| `host` | `192.168.1.100` | IP address for TCP connections |
| `baudrate` | `9600` | Serial baud rate (usually 9600) |
| `devices` | [] | List of OI monitors to read |

### Device Configuration

| Option | Required | Description |
|--------|----------|-------------|
| `name` | Yes | Friendly name for the device |
| `slave_id` | Yes | Modbus slave address (1-247) |
| `model` | Yes | Device model: `OI-7530`, `OI-7010`, or `OI-7032` |

### MQTT Settings

| Option | Default | Description |
|--------|---------|-------------|
| `host` | `core-mosquitto` | MQTT broker hostname |
| `port` | `1883` | MQTT broker port |
| `username` | - | MQTT username |
| `password` | - | MQTT password |
| `discovery_prefix` | `homeassistant` | HA MQTT discovery prefix |

### Radio Settings (Optional)

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | `false` | Enable wireless radio support |
| `port` | `/dev/ttyUSB1` | Serial port for Laird radio module |
| `network_channel` | `25` | RF network channel (1-78) |
| `mode` | `secondary` | `primary` (transmit/receive) or `secondary` (receive only) |
| `api_mode` | `true` | Use API mode (recommended) |

## Hardware Setup

### Modbus RTU (RS-485)

Connect your OI monitor to your Home Assistant device via USB-to-RS485 adapter:

```
OI Monitor          USB-RS485 Adapter
-----------         ------------------
A (RS485+)   →      A/D+ (Green)
B (RS485-)   →      B/D- (White)
GND          →      GND (Black)
```

### Wireless Radio (Optional)

For direct wireless sensor monitoring, connect a Laird LT1110 or RM024:

```
Laird Radio         USB-Serial Adapter
-----------         ------------------
TX (Green)   →      RX
RX (White)   →      TX
GND (Black)  →      GND
VCC (Red)    →      3.3V or 5V
```

Configure the radio first using the included `configure_radio.py` script.

## Entities Created

For each device, the add-on creates:

**Per Channel (x32):**
- `sensor.oi_7530_1_ch1_reading` - Gas reading
- `sensor.oi_7530_1_ch1_battery` - Battery voltage
- `binary_sensor.oi_7530_1_ch1_fault` - Fault status
- `sensor.oi_7530_1_ch1_gas_type` - Gas type (H2S, CO, O2, etc.)

**Device-Level:**
- `sensor.oi_7530_1_uptime` - Device uptime
- `sensor.oi_7530_1_serial_errors` - Communication errors
- `binary_sensor.oi_7530_1_relay1` - Relay 1 status
- `binary_sensor.oi_7530_1_relay2` - Relay 2 status

## Support

- **Repository**: https://github.com/PlanBRandom/teleproject
- **Issues**: https://github.com/PlanBRandom/teleproject/issues
- **Documentation**: See README.md and docs/ folder in repository

## Gas Types Supported

H2S, CO, O2, LEL, SO2, Cl2, HCN, NH3, PH3, NO, NO2, O3, ClO2, HCl, HF, ETO, VOC, CO2, H2, AsH3, COCl2, B2H6, C2H4O, GeH4, SiH4, F2, HBr, and Distance (LPIR)

## License

MIT License - See LICENSE file in repository

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg
[repository-badge]: https://img.shields.io/badge/Add%20to%20Home%20Assistant-41BDF5?logo=home-assistant&style=for-the-badge
[repository-url]: https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FPlanBRandom%2Fteleproject
