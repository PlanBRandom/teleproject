"""
Check MQTT retained messages from HiveMQ to see what channels were active
"""
import json
import paho.mqtt.client as mqtt
import time

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

mqtt_cfg = config['mqtt']

received_topics = {}

def on_connect(client, userdata, flags, rc):
    print(f"Connected to HiveMQ broker (rc={rc})")
    # Subscribe to all oi7530 channels
    client.subscribe("oi7530/#")
    print("Subscribed to oi7530/#, waiting for retained messages...")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        timestamp = payload.get('timestamp', 'unknown')
        channel = payload.get('channel', '?')
        gas_type = payload.get('gas_type', '?')
        reading = payload.get('reading', 0)
        
        received_topics[msg.topic] = {
            'channel': channel,
            'gas_type': gas_type,
            'reading': reading,
            'timestamp': timestamp
        }
        
        print(f"  {msg.topic}: Ch{channel:02d} {gas_type} = {reading} @ {timestamp}")
    except Exception as e:
        print(f"  {msg.topic}: Error parsing - {e}")

# Create MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Configure TLS and credentials
if mqtt_cfg.get('use_tls'):
    client.tls_set()

if mqtt_cfg.get('username'):
    client.username_pw_set(mqtt_cfg['username'], mqtt_cfg['password'])

# Connect
print(f"Connecting to {mqtt_cfg['broker']}:{mqtt_cfg['port']}...")
client.connect(mqtt_cfg['broker'], mqtt_cfg['port'], 60)

# Run for 5 seconds to collect retained messages
client.loop_start()
time.sleep(5)
client.loop_stop()

print(f"\n{'='*80}")
print(f"Found {len(received_topics)} retained messages:")
print(f"{'='*80}")

# Sort by channel number
sorted_topics = sorted(received_topics.items(), key=lambda x: x[1]['channel'])
for topic, data in sorted_topics:
    print(f"Ch{data['channel']:02d}: {data['gas_type']:8s} = {data['reading']:7.1f} @ {data['timestamp']}")

print(f"{'='*80}")
print(f"\nThis shows the last published message for each channel (retained messages).")
print(f"If you saw messages over the weekend, something was definitely publishing to HiveMQ.")
