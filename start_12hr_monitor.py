#!/usr/bin/env python3
"""
12-Hour Multi-Network Monitor with Hive MQTT
Launches the multi-network monitor with pre-configured Hive MQTT settings.
"""

import subprocess
import sys

# Hive MQTT Configuration
MQTT_BROKER = "localhost"  # Change to your Hive MQTT broker address
MQTT_PORT = 1883           # Change if using different port (e.g., 8883 for TLS)
MQTT_USERNAME = None       # Add username if required
MQTT_PASSWORD = None       # Add password if required

# Duration
DURATION_HOURS = 12

def main():
    """Launch the monitor with Hive MQTT configuration."""
    
    print("="*80)
    print("STARTING 12-HOUR MULTI-NETWORK MONITOR")
    print("="*80)
    print(f"\nConfiguration:")
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
