"""
Simple MQTT Monitor - View sensor data from OI-7500 pipeline
Subscribes to MQTT topics and displays enhanced telemetry with fault codes
"""

import paho.mqtt.client as mqtt
import json
import ssl
from datetime import datetime

# MQTT Configuration
BROKER = "a1bcc059f5f74a6d8271e8b567fecc6d.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "laird"
PASSWORD = "LairdRM024"
BASE_TOPIC = "oi7500/#"

def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print("=" * 80)
        print("✓ Connected to MQTT Broker")
        print(f"  Broker: {BROKER}:{PORT}")
        print(f"  Subscribing to: {BASE_TOPIC}")
        print("=" * 80)
        print()
        client.subscribe(BASE_TOPIC)
    else:
        error_codes = {
            1: "Connection refused - incorrect protocol version",
            2: "Connection refused - invalid client identifier",
            3: "Connection refused - server unavailable",
            4: "Connection refused - bad username or password",
            5: "Connection refused - not authorized"
        }
        print(f"✗ Connection failed: {error_codes.get(rc, f'Unknown error ({rc})')}")

def on_message(client, userdata, msg):
    """Callback when message received"""
    try:
        # Parse JSON payload
        data = json.loads(msg.payload.decode())
        
        # Format timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Extract data
        channel = data.get('channel', '?')
        reading = data.get('reading', 0)
        gas_type = data.get('gas_type', 'Unknown')
        battery = data.get('battery_voltage', 0)
        fault = data.get('fault', 'None')
        fault_code = data.get('fault_code', 0)
        precision = data.get('precision', 2)
        sensor_mode = data.get('sensor_mode', 0)
        sensor_type = data.get('sensor_type', 0)
        network = data.get('network', 'Unknown')
        
        # Format reading with precision
        reading_str = f"{reading:.{precision}f}"
        
        # Color code fault
        if fault_code == 0:
            fault_display = f"✓ {fault}"
            color = "\033[92m"  # Green
        elif fault_code in [11, 12]:  # Auto-clearing
            fault_display = f"⚠ {fault}"
            color = "\033[94m"  # Blue
        else:
            fault_display = f"✗ F{fault_code}: {fault}"
            color = "\033[91m"  # Red
        
        # Print formatted message
        print(f"{color}[{timestamp}] {network:12s} | Ch {channel:2d} | {gas_type:8s} | {reading_str:>10s} | Batt {battery:.1f}V | {fault_display}\033[0m")
        
        # Print additional details if not normal
        if sensor_mode != 0 or fault_code != 0:
            mode_names = {0: "Normal", 1: "Null", 2: "Calibration", 3: "Relay", 
                         4: "Radio Address", 5: "Diagnostic", 6: "Advanced Menu", 7: "Administration Menu"}
            type_names = {0: "EC", 1: "IR", 2: "CB", 3: "MOS", 4: "PID", 
                         5: "TANK LEVEL", 6: "4-20mA", 7: "SWITCH", 30: "OI-WF190", 31: "NONE"}
            
            mode_name = mode_names.get(sensor_mode, f"Mode{sensor_mode}")
            type_name = type_names.get(sensor_type, f"Type{sensor_type}")
            
            print(f"    └─ Mode: {mode_name} | Sensor Type: {type_name}")
        
    except json.JSONDecodeError:
        # Raw message (non-JSON)
        print(f"[{msg.topic}] {msg.payload.decode()}")
    except Exception as e:
        print(f"Error processing message: {e}")

def on_disconnect(client, userdata, rc):
    """Callback when disconnected"""
    if rc != 0:
        print(f"\n⚠ Unexpected disconnection (code {rc})")

# Create MQTT client
client = mqtt.Client()
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)

# Set callbacks
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

# Connect and start loop
print("Connecting to MQTT broker...")
try:
    client.connect(BROKER, PORT, 60)
    print("\nMonitoring sensor data (Press Ctrl+C to stop)...\n")
    client.loop_forever()
except KeyboardInterrupt:
    print("\n\n✓ Stopped by user")
    client.disconnect()
except Exception as e:
    print(f"✗ Connection error: {e}")
