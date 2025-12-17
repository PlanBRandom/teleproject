#!/usr/bin/with-contenv bashio

bashio::log.info "Starting OI Gas Monitor Bridge..."

# Read configuration
export CONNECTION_MODE=$(bashio::config 'connection_mode')
export MODBUS_PORT=$(bashio::config 'modbus.port')
export MODBUS_BAUDRATE=$(bashio::config 'modbus.baudrate')
export RADIO_ENABLED=$(bashio::config 'radio.enabled')
export RADIO_PORT=$(bashio::config 'radio.port')
export MQTT_BROKER=$(bashio::config 'mqtt.broker')
export MQTT_PORT=$(bashio::config 'mqtt.port')
export MQTT_USERNAME=$(bashio::config 'mqtt.username')
export MQTT_PASSWORD=$(bashio::config 'mqtt.password')
export POLL_INTERVAL=$(bashio::config 'poll_interval')

bashio::log.info "Connection mode: ${CONNECTION_MODE}"
bashio::log.info "Modbus port: ${MODBUS_PORT}"
bashio::log.info "MQTT broker: ${MQTT_BROKER}:${MQTT_PORT}"

# Generate config file from add-on options
cat > /app/config.yaml << EOF
modbus:
  port: '${MODBUS_PORT}'
  baudrate: ${MODBUS_BAUDRATE}
  connection_type: 'rtu'

radio:
  enabled: ${RADIO_ENABLED}
  port: '${RADIO_PORT}'

mqtt:
  broker: '${MQTT_BROKER}'
  port: ${MQTT_PORT}
  username: '${MQTT_USERNAME}'
  password: '${MQTT_PASSWORD}'
  discovery_prefix: 'homeassistant'

poll_interval: ${POLL_INTERVAL}
EOF

# Add devices from config
bashio::log.info "Configuring devices..."
python3 << 'PYEOF'
import json
import sys

# This would parse the devices array from bashio
# For now, we'll let the main script handle it
PYEOF

# Start the bridge
bashio::log.info "Starting bridge application..."
cd /app
exec python3 -m pipeline.main
