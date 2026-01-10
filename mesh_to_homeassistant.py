#!/usr/bin/env python3
"""
Meshtastic to Home Assistant Bridge
Configures Channel 1 for OI-7500 telemetry and publishes decoded data to Home Assistant MQTT
"""

import argparse
import json
import struct
import sys
import time
from datetime import datetime
import meshtastic
import meshtastic.serial_interface
import meshtastic.tcp_interface
from pubsub import pub
import paho.mqtt.client as mqtt

# Gas type codes
GAS_TYPES = {
    0: "LEL", 1: "O2", 2: "CO", 3: "H2S", 4: "SO2", 5: "NO2",
    6: "Cl2", 7: "NH3", 8: "HCN", 9: "PH3", 10: "ClO2",
    11: "NO", 12: "HCl", 13: "O3", 14: "CO2", 15: "CH4",
    16: "ETO", 17: "H2", 18: "AsH3", 19: "SiH4", 20: "GeH4",
    21: "B2H6", 22: "F2", 23: "COCl2", 24: "HF", 25: "N2H4", 26: "C2H4O"
}

# Fault codes
FAULT_CODES = {
    0: "Normal", 1: "Cal Error", 2: "Sensor Error", 3: "Low Battery",
    4: "High Reading", 5: "Low Reading", 6: "Sensor Fail",
    7: "Comm Error", 8: "Out of Range", 9: "Not Calibrated",
    10: "Warmup", 11: "Maintenance", 12: "Disabled",
    13: "Unknown", 14: "Reserved", 15: "Multiple Faults"
}

class MeshToHomeAssistant:
    def __init__(self, device, ha_mqtt_host, ha_mqtt_port=1883, 
                 ha_mqtt_user=None, ha_mqtt_pass=None):
        self.device = device
        self.ha_mqtt_host = ha_mqtt_host
        self.ha_mqtt_port = ha_mqtt_port
        self.ha_mqtt_user = ha_mqtt_user
        self.ha_mqtt_pass = ha_mqtt_pass
        self.interface = None
        self.mqtt_client = None
        self.packet_count = 0
        
    def connect_mqtt(self):
        """Connect to Home Assistant MQTT broker"""
        print(f"Connecting to Home Assistant MQTT: {self.ha_mqtt_host}:{self.ha_mqtt_port}")
        
        self.mqtt_client = mqtt.Client("meshtastic_oi7500_bridge")
        
        if self.ha_mqtt_user and self.ha_mqtt_pass:
            self.mqtt_client.username_pw_set(self.ha_mqtt_user, self.ha_mqtt_pass)
        
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        try:
            self.mqtt_client.connect(self.ha_mqtt_host, self.ha_mqtt_port, 60)
            self.mqtt_client.loop_start()
            time.sleep(2)  # Give it time to connect
            return True
        except Exception as e:
            print(f"[ERROR] Failed to connect to MQTT: {e}")
            return False
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("[OK] Connected to Home Assistant MQTT broker")
            # Publish discovery configs for all possible channels
            self.publish_discovery_configs()
        else:
            print(f"[ERROR] MQTT connection failed with code {rc}")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        print(f"[WARN] Disconnected from MQTT broker (code: {rc})")
    
    def publish_discovery_configs(self):
        """Publish Home Assistant MQTT discovery configs for all channels"""
        print("Publishing Home Assistant discovery configs...")
        
        for channel_num in range(1, 33):
            base_topic = f"homeassistant/sensor/oi7500_ch{channel_num:02d}"
            state_topic = f"oi7500/channel{channel_num:02d}"
            
            # Main sensor entity
            config = {
                "name": f"OI-7500 Channel {channel_num:02d}",
                "unique_id": f"oi7500_ch{channel_num:02d}_reading",
                "state_topic": state_topic,
                "value_template": "{{ value_json.reading }}",
                "unit_of_measurement": "ppm",
                "device_class": "gas",
                "state_class": "measurement",
                "json_attributes_topic": state_topic,
                "device": {
                    "identifiers": [f"oi7500_ch{channel_num:02d}"],
                    "name": f"OI-7500 Channel {channel_num:02d}",
                    "manufacturer": "RKI Instruments",
                    "model": "OI-7500"
                }
            }
            self.mqtt_client.publish(f"{base_topic}_reading/config", 
                                    json.dumps(config), retain=True)
            
            # Battery sensor
            battery_config = {
                "name": f"OI-7500 Ch{channel_num:02d} Battery",
                "unique_id": f"oi7500_ch{channel_num:02d}_battery",
                "state_topic": state_topic,
                "value_template": "{{ value_json.battery }}",
                "unit_of_measurement": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "device": {
                    "identifiers": [f"oi7500_ch{channel_num:02d}"]
                }
            }
            self.mqtt_client.publish(f"{base_topic}_battery/config", 
                                    json.dumps(battery_config), retain=True)
            
            # Fault sensor
            fault_config = {
                "name": f"OI-7500 Ch{channel_num:02d} Fault",
                "unique_id": f"oi7500_ch{channel_num:02d}_fault",
                "state_topic": state_topic,
                "value_template": "{{ value_json.fault }}",
                "icon": "mdi:alert-circle",
                "device": {
                    "identifiers": [f"oi7500_ch{channel_num:02d}"]
                }
            }
            self.mqtt_client.publish(f"{base_topic}_fault/config", 
                                    json.dumps(fault_config), retain=True)
        
        print(f"[OK] Published discovery configs for 32 channels")
    
    def verify_channel(self):
        """Verify Channel 1 is configured for OI-7500 telemetry"""
        print("\n=== Verifying Meshtastic Channel 1 ===")
        
        try:
            # Get current channel configuration
            channels = self.interface.localNode.channels
            
            # Check if Channel 1 exists and is configured
            if len(channels) > 1:
                ch1 = channels[1]
                channel_name = ch1.settings.name if hasattr(ch1.settings, 'name') else "Unknown"
                
                if channel_name == "OI7500":
                    print("[OK] Channel 1 configured as 'OI7500'")
                    return True
                else:
                    print(f"[WARN] Channel 1 name: '{channel_name}' (expected 'OI7500')")
                    print("\nPlease configure Channel 1 using Meshtastic CLI:")
                    print("  meshtastic --ch-index 1 --ch-add OI7500")
                    print("  meshtastic --ch-index 1 --ch-set psk \"everythingisfine\"")
                    print("  meshtastic --ch-index 1 --ch-set uplink_enabled true")
                    print("  meshtastic --ch-index 1 --ch-set downlink_enabled true")
                    print("\nContinuing anyway - will listen for any PRIVATE_APP packets...")
                    return True
            else:
                print("[WARN] Channel 1 not found")
                print("\nPlease configure Channel 1 using Meshtastic CLI:")
                print("  meshtastic --ch-index 1 --ch-add OI7500")
                print("  meshtastic --ch-index 1 --ch-set psk \"everythingisfine\"")
                print("  meshtastic --ch-index 1 --ch-set uplink_enabled true")
                print("  meshtastic --ch-index 1 --ch-set downlink_enabled true")
                print("\nContinuing anyway - will listen for any PRIVATE_APP packets...")
                return True
            
        except Exception as e:
            print(f"[WARN] Could not verify channel: {e}")
            print("Continuing anyway - will listen for all PRIVATE_APP packets...")
            return True
    
    def connect_meshtastic(self):
        """Connect to Meshtastic device"""
        print(f"\nConnecting to Meshtastic device: {self.device}")
        
        try:
            if self.device.startswith('COM') or self.device.startswith('/dev/'):
                # Serial connection
                self.interface = meshtastic.serial_interface.SerialInterface(self.device)
                print(f"[OK] Connected via serial: {self.device}")
            else:
                # TCP/IP connection
                self.interface = meshtastic.tcp_interface.TCPInterface(self.device)
                print(f"[OK] Connected via TCP: {self.device}")
            
            # Wait for node info
            time.sleep(2)
            
            # Get node info
            node_info = self.interface.getMyNodeInfo()
            print(f"[OK] Node: {node_info.get('user', {}).get('longName', 'Unknown')}")
            print(f"  ID: {node_info.get('user', {}).get('id', 'Unknown')}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to connect to Meshtastic: {e}")
            return False
    
    def decode_telemetry(self, payload):
        """Decode 15-byte OI-7500 telemetry packet"""
        if len(payload) < 15:
            return None
        
        try:
            channel = payload[0]
            reading_raw = struct.unpack('<h', payload[1:3])[0]
            gas_type = payload[3]
            battery = payload[4] * 0.1
            fault_code = payload[5]
            timestamp = struct.unpack('<I', payload[6:10])[0]
            mode_type = payload[10]
            precision = payload[11]
            
            # Calculate actual reading with precision
            actual_reading = reading_raw / (10 ** precision)
            
            return {
                'channel': channel,
                'reading': round(actual_reading, precision),
                'gas_type': GAS_TYPES.get(gas_type, f"Unknown ({gas_type})"),
                'battery': round(battery, 1),
                'fault': FAULT_CODES.get(fault_code, f"Unknown ({fault_code})"),
                'timestamp': datetime.fromtimestamp(timestamp).isoformat(),
                'mode_type': mode_type,
                'precision': precision
            }
        except Exception as e:
            print(f"[ERROR] Error decoding telemetry: {e}")
            return None
    
    def on_receive(self, packet, interface):
        """Handle incoming Meshtastic packet"""
        try:
            decoded = packet.get('decoded', {})
            
            # Only process PRIVATE_APP packets (our OI-7500 telemetry)
            if decoded.get('portnum') != 'PRIVATE_APP':
                return
            
            payload = decoded.get('payload', b'')
            if len(payload) < 15:
                return
            
            # Decode telemetry
            data = self.decode_telemetry(payload)
            if not data:
                return
            
            self.packet_count += 1
            
            # Get mesh metadata
            from_id = packet.get('fromId', 'Unknown')
            rssi = packet.get('rxRssi', 0)
            snr = packet.get('rxSnr', 0.0)
            hop_limit = packet.get('hopLimit', 0)
            
            # Print to console
            print(f"\n{'='*60}")
            print(f"Packet #{self.packet_count} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"From Node: {from_id}")
            print(f"Signal: RSSI {rssi} dBm, SNR {snr:.1f} dB, Hops: {hop_limit}")
            print(f"{'='*60}")
            print(f"Channel {data['channel']:02d} | {data['gas_type']}")
            print(f"Reading: {data['reading']} ppm")
            print(f"Battery: {data['battery']} V")
            print(f"Fault: {data['fault']}")
            print(f"Timestamp: {data['timestamp']}")
            
            # Add mesh metadata
            data['from_node'] = from_id
            data['rssi'] = rssi
            data['snr'] = snr
            data['hop_limit'] = hop_limit
            
            # Publish to Home Assistant MQTT
            topic = f"oi7500/channel{data['channel']:02d}"
            self.mqtt_client.publish(topic, json.dumps(data), retain=True)
            print(f"[OK] Published to Home Assistant: {topic}")
            
        except Exception as e:
            print(f"[ERROR] Error processing packet: {e}")
    
    def run(self):
        """Main run loop"""
        print("\n" + "="*60)
        print("Meshtastic to Home Assistant Bridge")
        print("="*60)
        
        # Connect to Home Assistant MQTT
        if not self.connect_mqtt():
            return False
        
        # Connect to Meshtastic
        if not self.connect_meshtastic():
            return False
        
        # Verify Channel 1 (but don't fail if not configured)
        self.verify_channel()
        
        # Subscribe to incoming packets
        pub.subscribe(self.on_receive, "meshtastic.receive")
        
        print("\n" + "="*60)
        print("[ACTIVE] Bridge running - listening for OI-7500 telemetry on Channel 1")
        print("  Data will be published to Home Assistant MQTT")
        print("  Press Ctrl+C to stop")
        print("="*60 + "\n")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            self.interface.close()
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            print("[OK] Disconnected cleanly")
            return True

def main():
    parser = argparse.ArgumentParser(
        description='Meshtastic to Home Assistant Bridge - Configures Channel 1 and publishes OI-7500 telemetry'
    )
    parser.add_argument('device', 
                       help='Meshtastic device (COM port or IP address, e.g., COM3 or 192.168.1.100)')
    parser.add_argument('--ha-host', required=True,
                       help='Home Assistant MQTT broker host (e.g., 192.168.1.50 or homeassistant.local)')
    parser.add_argument('--ha-port', type=int, default=1883,
                       help='Home Assistant MQTT port (default: 1883)')
    parser.add_argument('--ha-user', 
                       help='Home Assistant MQTT username (optional)')
    parser.add_argument('--ha-pass',
                       help='Home Assistant MQTT password (optional)')
    
    args = parser.parse_args()
    
    bridge = MeshToHomeAssistant(
        args.device,
        args.ha_host,
        args.ha_port,
        args.ha_user,
        args.ha_pass
    )
    
    success = bridge.run()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
