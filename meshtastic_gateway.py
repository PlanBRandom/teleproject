#!/usr/bin/env python3
"""
OI-7500 Meshtastic Gateway - Central Hub
Receives telemetry from Meshtastic mesh and republishes to central MQTT broker
"""

import json
import time
import struct
import argparse
import ssl
from datetime import datetime
from pathlib import Path
import paho.mqtt.client as mqtt
import meshtastic
import meshtastic.serial_interface
from pubsub import pub

# Configuration
CONFIG_FILE = "meshtastic_config.json"

# Gas types lookup
GAS_TYPES = {
    0: "None", 1: "LEL", 2: "O2", 3: "CO", 4: "H2S", 5: "SO2",
    6: "NH3", 7: "Cl2", 8: "ClO2", 9: "HCN", 10: "NO", 11: "NO2",
    12: "HCl", 13: "PH3", 14: "ETO", 15: "H2", 16: "AsH3",
    17: "Br2", 18: "COCl2", 19: "GeH4", 20: "SiH4", 21: "B2H6",
    22: "F2", 23: "O3", 24: "HF", 25: "N2H4", 26: "C2H4O"
}

FAULT_CODES = {
    0: "F0 - No Fault", 1: "F1 - Low Battery", 2: "F2 - Sensor Fail",
    3: "F3 - Calibration Due", 4: "F4 - Span Gas Out of Range",
    5: "F5 - Zero Fault", 6: "F6 - Span Fault", 7: "F7 - Communications Fault",
    8: "F8 - Duplicate Address Detected", 9: "F9 - Lost Link",
    10: "F10 - Sensor Disconnected", 11: "F11 - Sensor Saturated",
    12: "F12 - Over Range", 13: "F13 - Under Range",
    14: "F14 - Primary Link Timeout", 15: "F15 - System Fault"
}


class MeshtasticGateway:
    def __init__(self, config_file=CONFIG_FILE):
        self.config = self.load_config(config_file)
        self.mqtt_client = None
        self.mesh_interface = None
        self.running = False
        self.packet_count = 0
        self.mqtt_connected = False
        self.mesh_connected = False
        self.last_heartbeat = time.time()
        self.mesh_stats = {'total_received': 0, 'avg_rssi': 0, 'unique_nodes': set()}
        
    def load_config(self, config_file):
        """Load configuration"""
        config_path = Path(config_file)
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"[INFO] Loaded configuration from {config_file}")
        else:
            print(f"[ERROR] Configuration file not found: {config_file}")
            print("Run meshtastic_bridge.py first to create default config")
            exit(1)
        return config
    
    def log(self, message, level="INFO"):
        """Simple logging"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def decode_telemetry(self, data):
        """Decode binary telemetry data"""
        try:
            if len(data) < 15:
                return None
            
            # Unpack binary data
            unpacked = struct.unpack('<BhBBBIBBBBB', data[:15])
            
            channel = unpacked[0]
            reading = unpacked[1] / 10.0
            gas_type_code = unpacked[2]
            battery = unpacked[3] / 10.0
            fault_code = unpacked[4]
            timestamp = unpacked[5]
            sensor_info = unpacked[6]
            precision = unpacked[7]
            
            sensor_mode = (sensor_info >> 4) & 0x0F
            sensor_type = sensor_info & 0x0F
            
            return {
                'channel': channel,
                'reading': reading,
                'gas_type': GAS_TYPES.get(gas_type_code, f"Unknown({gas_type_code})"),
                'gas_type_code': gas_type_code,
                'sensor_mode': sensor_mode,
                'sensor_type': sensor_type,
                'battery': battery,
                'fault_code': fault_code,
                'fault_description': FAULT_CODES.get(fault_code, f"Unknown({fault_code})"),
                'precision': precision,
                'timestamp': datetime.fromtimestamp(timestamp).isoformat(),
                'received_at': datetime.now().isoformat()
            }
        except Exception as e:
            self.log(f"Decode error: {e}", "ERROR")
            return None
    
    def publish_to_mqtt(self, data):
        """Publish decoded data to central MQTT broker"""
        try:
            if not self.mqtt_client:
                return
            
            mqtt_cfg = self.config['mqtt_destination']
            topic = f"{mqtt_cfg['topic_prefix']}/channel{data['channel']:02d}"
            
            payload = json.dumps(data)
            self.mqtt_client.publish(topic, payload)
            
            fault_indicator = "⚠️" if data['fault_code'] > 0 else "✓"
            self.log(
                f"{fault_indicator} Published CH{data['channel']:02d} → {topic} | "
                f"{data['gas_type']} {data['reading']:.1f} | "
                f"Battery: {data['battery']:.1f}V | "
                f"{data['fault_description']}"
            )
            
        except Exception as e:
            self.log(f"MQTT publish error: {e}", "ERROR")
    
    def on_mesh_receive(self, packet, interface):
        """Handle incoming Meshtastic packet"""
        try:
            # Check if it's a data packet
            if 'decoded' not in packet:
                return
            
            decoded = packet['decoded']
            
            # Check if it's our private app port
            if decoded.get('portnum') != 'PRIVATE_APP':
                return
            
            # Get payload
            payload = decoded.get('payload')
            if not payload:
                return
            
            self.packet_count += 1
            
            # Track mesh stats
            self.mesh_stats['total_received'] += 1
            if 'fromId' in packet:
                self.mesh_stats['unique_nodes'].add(packet['fromId'])
            if 'rxRssi' in packet:
                # Running average of RSSI
                rssi = packet['rxRssi']
                count = self.mesh_stats['total_received']
                self.mesh_stats['avg_rssi'] = (
                    (self.mesh_stats['avg_rssi'] * (count - 1) + rssi) / count
                )
            
            # Try to decode as binary telemetry
            if len(payload) >= 15:
                data = self.decode_telemetry(payload)
                if data:
                    # Add source info
                    data['mesh_from'] = packet.get('fromId', 'unknown')
                    data['mesh_hop_limit'] = packet.get('hopLimit', 0)
                    
                    # Publish to MQTT
                    self.publish_to_mqtt(data)
                    return
            
            # Try JSON format
            try:
                data = json.loads(payload.decode('utf-8'))
                data['mesh_from'] = packet.get('fromId', 'unknown')
                self.publish_to_mqtt(data)
            except:
                self.log("Received unknown packet format", "WARN")
                
        except Exception as e:
            self.log(f"Mesh receive error: {e}", "ERROR")
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.mqtt_connected = True
            self.log(f"✓ MQTT connected to cloud broker")
        else:
            self.mqtt_connected = False
            self.log(f"MQTT connection failed with code: {rc}", "ERROR")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnect callback"""
        self.mqtt_connected = False
        if rc != 0:
            self.log(f"⚠️ MQTT disconnected unexpectedly (code {rc})", "WARN")
    
    def setup_mqtt(self):
        """Setup MQTT connection to central broker"""
        try:
            mqtt_cfg = self.config['mqtt_destination']
            
            self.mqtt_client = mqtt.Client()
            
            if mqtt_cfg['username']:
                self.mqtt_client.username_pw_set(
                    mqtt_cfg['username'],
                    mqtt_cfg['password']
                )
            
            if mqtt_cfg['use_tls']:
                self.mqtt_client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
            
            # Set callbacks
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
            
            self.log(f"Connecting to central MQTT: {mqtt_cfg['broker']}...")
            self.mqtt_client.connect(mqtt_cfg['broker'], mqtt_cfg['port'], 60)
            self.mqtt_client.loop_start()
            
            # Wait for connection
            timeout = 10
            while not self.mqtt_connected and timeout > 0:
                time.sleep(0.5)
                timeout -= 0.5
            
            if not self.mqtt_connected:
                raise Exception("MQTT connection timeout")
            
        except Exception as e:
            self.log(f"MQTT setup error: {e}", "ERROR")
            raise
    
    def setup_meshtastic(self):
        """Setup Meshtastic interface (serial or TCP)"""
        try:
            mesh_port = self.config['gateway_node']['meshtastic_port']
            conn_type = self.config['gateway_node'].get('connection_type', 'serial')
            
            self.log(f"Connecting to Meshtastic device: {mesh_port} ({conn_type})...")
            
            if conn_type == 'tcp':
                # WiFi/Network connection
                import meshtastic.tcp_interface
                self.mesh_interface = meshtastic.tcp_interface.TCPInterface(hostname=mesh_port)
            else:
                # Serial/USB connection
                self.mesh_interface = meshtastic.serial_interface.SerialInterface(mesh_port)
            
            # Subscribe to receive events
            pub.subscribe(self.on_mesh_receive, "meshtastic.receive")
            
            # Get node info
            node_info = self.mesh_interface.getMyNodeInfo()
            self.log(f"Meshtastic gateway connected: {node_info}")
            
        except Exception as e:
            self.log(f"Meshtastic setup error: {e}", "ERROR")
            raise
    
    def send_heartbeat(self):
        """Send periodic heartbeat with mesh health stats"""
        now = time.time()
        if now - self.last_heartbeat >= 60:  # Every minute
            self.last_heartbeat = now
            mqtt_status = "✓" if self.mqtt_connected else "✗"
            mesh_status = "✓" if self.mesh_connected else "✗"
            
            stats_msg = (
                f"💓 Status: MQTT {mqtt_status} | Mesh {mesh_status} | "
                f"Packets: {self.packet_count} | "
                f"Nodes: {len(self.mesh_stats['unique_nodes'])}"
            )
            
            if self.mesh_stats['avg_rssi'] != 0:
                stats_msg += f" | Avg RSSI: {self.mesh_stats['avg_rssi']:.1f} dBm"
            
            self.log(stats_msg)
    
    def run(self):
        """Main gateway loop"""
        self.log("="*80)
        self.log("OI-7500 Meshtastic Gateway - Central Hub")
        self.log("="*80)
        self.log(f"Location: {self.config['gateway_node']['location_name']}")
        
        # Setup connections
        try:
            self.setup_meshtastic()
        except Exception as e:
            self.log(f"Failed to setup Meshtastic: {e}", "ERROR")
            return
        
        try:
            self.setup_mqtt()
        except Exception as e:
            self.log(f"Failed to setup MQTT: {e}", "ERROR")
            return
        
        self.log("🚀 Gateway active - receiving from mesh and publishing to MQTT")
        self.log("Press Ctrl+C to stop")
        self.log("-"*80)
        
        self.running = True
        
        try:
            while self.running:
                time.sleep(1)
                self.send_heartbeat()
                
        except KeyboardInterrupt:
            self.log("Gateway stopped by user")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup connections"""
        self.log("="*80)
        self.log(f"Total packets received: {self.packet_count}")
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
        if self.mesh_interface:
            self.mesh_interface.close()
        
        self.log("Gateway shutdown complete")


def main():
    parser = argparse.ArgumentParser(
        description='OI-7500 Meshtastic Gateway - Receive from mesh and publish to MQTT'
    )
    parser.add_argument('--config', default=CONFIG_FILE, help='Configuration file')
    
    args = parser.parse_args()
    
    gateway = MeshtasticGateway(args.config)
    gateway.run()


if __name__ == "__main__":
    main()
