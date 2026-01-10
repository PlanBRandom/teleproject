#!/usr/bin/env python3
"""
12-Hour Multi-Network Monitor with Hive MQTT
Launches the multi-network monitor with pre-configured Hive MQTT settings.
Loads configuration from config.yaml (web app config file).
"""

import subprocess
import sys
import yaml
import os

# Load MQTT config from web app config file
def load_mqtt_config():
    """Load MQTT configuration from config.yaml"""
    config_file = os.path.join(os.path.dirname(__file__), 'config.yaml')
    
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            mqtt_config = config.get('mqtt', {})
            return {
                'broker': mqtt_config.get('broker', 'localhost'),
                'port': mqtt_config.get('port', 1883),
                'username': mqtt_config.get('username'),
                'password': mqtt_config.get('password'),
                'use_tls': mqtt_config.get('use_tls', False)
            }
    else:
        print(f"⚠️  Config file not found: {config_file}")
        print(f"   Using default localhost settings")
        return {
            'broker': 'localhost',
            'port': 1883,
            'username': None,
            'password': None,
            'use_tls': False
        }

# Load MQTT settings from web app config
mqtt_cfg = load_mqtt_config()
MQTT_BROKER = mqtt_cfg['broker']
MQTT_PORT = mqtt_cfg['port']
MQTT_USERNAME = mqtt_cfg['username']
MQTT_PASSWORD = mqtt_cfg['password']
MQTT_USE_TLS = mqtt_cfg['use_tls']

# Duration
DURATION_HOURS = 12

def main():
    """Launch the monitor with Hive MQTT configuration."""
    
    print("="*80)
    print("STARTING 12-HOUR MULTI-NETWORK MONITOR")
    print("="*80)
    print(f"\nConfiguration (loaded from config.yaml):")
    print(f"  Duration: {DURATION_HOURS} hours")
    print(f"  MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  MQTT Auth: {'Yes' if MQTT_USERNAME else 'No'}")
    print()
    print("Monitoring:")
    print("  - Network 15 (COM7) → OI-7530")
    print("  - Network 20 (COM12) → OI-7010")
    print("  - Network 25 (COM11) → OI-7032")
    print("  - Modbus (COM10)")
    print()
    print("MQTT Topics:")
    print("  - oi7500/network/<network>/channel_<ch>/state")
    print("  - oi7500/channels/channel_<ch>/state")
    print("  - oi7500/monitor/stats")
    print("  - oi7500/monitor/status")
    print()
    print("Press Ctrl+C to stop early")
    print("="*80)
    print()
    
    # Build command
    cmd = [
        sys.executable,
        "monitor_multi_network.py",
        str(DURATION_HOURS),
        "--mqtt-broker", MQTT_BROKER,
        "--mqtt-port", str(MQTT_PORT)
    ]
    
    if MQTT_USERNAME:
        cmd.extend(["--mqtt-username", MQTT_USERNAME])
    if MQTT_PASSWORD:
        cmd.extend(["--mqtt-password", MQTT_PASSWORD])
    if MQTT_USE_TLS:
        cmd.append("--mqtt-use-tls")
    
    # Run monitor
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\nStopped by user (Ctrl+C)")
    except subprocess.CalledProcessError as e:
        print(f"\n\nMonitor failed with error code {e.returncode}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
