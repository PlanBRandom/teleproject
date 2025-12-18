#!/bin/bash
# Deploy OI Gas Monitor Add-on to Home Assistant

echo "==================================="
echo "OI Gas Monitor Add-on Deployment"
echo "==================================="
echo ""

# Configuration
read -p "Enter Home Assistant IP address: " HA_IP
read -p "Enter SSH username (default: root): " SSH_USER
SSH_USER=${SSH_USER:-root}

echo ""
echo "This will:"
echo "  1. Copy add-on files to Home Assistant"
echo "  2. Create add-on directory structure"
echo "  3. Install the add-on"
echo ""
read -p "Continue? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Cancelled."
    exit 0
fi

# Create temporary build directory
echo ""
echo "Creating build package..."
mkdir -p build/oi-gas-monitor

# Copy files
cp oi-gas-monitor/config.yaml build/oi-gas-monitor/
cp oi-gas-monitor/Dockerfile build/oi-gas-monitor/
cp oi-gas-monitor/run.sh build/oi-gas-monitor/
cp -r pipeline build/oi-gas-monitor/

# Create icon
cat > build/oi-gas-monitor/icon.png << 'EOF'
# Placeholder - add actual icon image
EOF

# Copy to Home Assistant
echo "Copying to Home Assistant at ${SSH_USER}@${HA_IP}..."
ssh ${SSH_USER}@${HA_IP} "mkdir -p /addons/local"
scp -r build/oi-gas-monitor ${SSH_USER}@${HA_IP}:/addons/local/

echo ""
echo "✓ Files copied successfully!"
echo ""
echo "Next steps:"
echo "  1. Go to Home Assistant → Settings → Add-ons"
echo "  2. Click ⋮ menu → Check for updates"
echo "  3. Find 'OI Gas Monitor Bridge' in local add-ons"
echo "  4. Click Install"
echo "  5. Configure your devices in the Configuration tab"
echo "  6. Start the add-on"
echo ""
echo "Configuration example:"
echo "---"
cat << 'YAML'
connection_mode: modbus_rtu
modbus:
  port: /dev/ttyUSB0
  baudrate: 9600
radio:
  enabled: false
devices:
  - slave_id: 1
    name: "OI-7530-1"
    model: "7530"
  - slave_id: 2
    name: "OI-7530-2"
    model: "7530"
mqtt:
  broker: core-mosquitto
  port: 1883
  username: ""
  password: ""
poll_interval: 30
YAML

# Cleanup
rm -rf build

echo ""
echo "Deployment complete!"
