#!/usr/bin/env python3
"""
Test OI-7500 Meshtastic Bridge - Simulate sensor data
Publishes test data to localhost MQTT to test the bridge → mesh → gateway flow
"""

import json
import time
from datetime import datetime
import paho.mqtt.client as mqtt

# Test data - simulates 3 OI-7500 channels
TEST_CHANNELS = [
    {
        'channel': 1,
        'reading': 12.3,
        'gas_type': 'LEL',
        'gas_type_code': 1,
        'sensor_mode': 0,
        'sensor_type': 1,
        'battery': 3.2,
        'fault_code': 0,
        'fault_description': 'F0 - No Fault',
        'precision': 1,
        'timestamp': None
    },
    {
        'channel': 2,
        'reading': 20.9,
        'gas_type': 'O2',
        'gas_type_code': 2,
        'sensor_mode': 0,
        'sensor_type': 2,
        'battery': 3.4,
        'fault_code': 0,
        'fault_description': 'F0 - No Fault',
        'precision': 1,
        'timestamp': None
    },
    {
        'channel': 3,
        'reading': 125.0,
        'gas_type': 'CO',
        'gas_type_code': 3,
        'sensor_mode': 0,
        'sensor_type': 3,
        'battery': 2.8,
        'fault_code': 1,
        'fault_description': 'F1 - Low Battery',
        'precision': 0,
        'timestamp': None
    }
]

def publish_test_data():
    """Publish test sensor data to local MQTT"""
    print("="*80)
    print("OI-7500 Meshtastic Bridge Test - Simulated Sensor Data")
    print("="*80)
    print()
    print("This script simulates OI-7500 sensor data and publishes to localhost MQTT")
    print("The bridge will:")
    print("  1. Subscribe to localhost MQTT")
    print("  2. Encode data to 15 bytes")
    print("  3. Forward to Meshtastic mesh (Heltec V3 COM16)")
    print("  4. Mesh routes to roof node (10.20.0.172)")
    print("  5. Gateway receives and publishes to cloud MQTT")
    print()
    print("Starting in 3 seconds...")
    time.sleep(3)
    
    # Connect to localhost MQTT
    client = mqtt.Client()
    
    try:
        client.connect("localhost", 1883, 60)
        client.loop_start()
        print("✓ Connected to localhost MQTT (port 1883)")
        print()
        
        print("Publishing test data every 10 seconds...")
        print("Press Ctrl+C to stop")
        print("-"*80)
        
        count = 0
        while True:
            count += 1
            print(f"\nPublish #{count} - {datetime.now().strftime('%H:%M:%S')}")
            
            for sensor in TEST_CHANNELS:
                # Update timestamp
                sensor['timestamp'] = datetime.now().isoformat()
                
                # Add some variation to readings
                import random
                if sensor['gas_type'] == 'LEL':
                    sensor['reading'] = round(12.3 + random.uniform(-1, 1), 1)
                elif sensor['gas_type'] == 'O2':
                    sensor['reading'] = round(20.9 + random.uniform(-0.5, 0.5), 1)
                elif sensor['gas_type'] == 'CO':
                    sensor['reading'] = round(125.0 + random.uniform(-10, 10), 0)
                
                # Publish to MQTT
                topic = f"oi7500/channel{sensor['channel']:02d}"
                payload = json.dumps(sensor)
                client.publish(topic, payload)
                
                fault_indicator = "⚠️" if sensor['fault_code'] > 0 else "✓"
                print(f"  {fault_indicator} {topic} → {sensor['gas_type']} {sensor['reading']:.1f} | Battery: {sensor['battery']:.1f}V")
            
            print(f"\n💬 Bridge should now forward these to Meshtastic mesh...")
            print(f"   Check bridge terminal for forwarding logs")
            
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure Mosquitto is running:")
        print('  & "C:\\Program Files\\mosquitto\\mosquitto.exe" -v -p 1883')
    finally:
        client.loop_stop()
        client.disconnect()
        print("\nDisconnected from MQTT")


if __name__ == "__main__":
    publish_test_data()
