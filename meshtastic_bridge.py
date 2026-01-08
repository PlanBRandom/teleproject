#!/usr/bin/env python3
"""
OI-7500 Meshtastic Bridge - Edge Node
Subscribes to local MQTT telemetry and forwards over Meshtastic mesh network
"""

import json
import time
import struct
import argparse
from datetime import datetime
from pathlib import Path
import paho.mqtt.client as mqtt
import meshtastic
import meshtastic.serial_interface
from pubsub import pub

# Configuration
CONFIG_FILE = "meshtastic_config.json"

DEFAULT_CONFIG = {
    "edge_node": {
        "name": "OI-7500-Edge",
        "meshtastic_port": "/dev/ttyUSB2",  # Or COM port for Meshtastic device
        "location_name": "Site A"
    },
    "mqtt_source": {
        "broker": "localhost",  # Local MQTT from simple_monitor
        "port": 1883,
        "username": "",
        "password": "",
        "use_tls": False,
        "topic_prefix": "oi7500"
    },
    "bridge": {
        "enabled": True,
        "forward_interval": 5,  # Minimum seconds between forwards per channel
        "compress_data": True,
        "only_forward_faults": False  # If true, only send when fault detected
    }
}


class MeshtasticBridge:
    def __init__(self, config_file=CONFIG_FILE):
        self.config = self.load_config(config_file)
        self.mqtt_client = None
        self.mesh_interface = None
        self.running = False
        self.last_forward_time = {}  # Track last forward time per channel
        self.packet_count = 0
        self.mqtt_connected = False
        self.mesh_connected = False
        self.last_heartbeat = time.time()
        self.reconnect_attempts = 0
        self.max_reconnect_delay = 300  # 5 minutes max
        
    def load_config(self, config_file):
        """Load configuration"""
        config_path = Path(config_file)
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"[INFO] Loaded configuration from {config_file}")
        else:
            config = DEFAULT_CONFIG
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"[INFO] Created default configuration: {config_file}")
        return config
    
    def log(self, message, level="INFO"):
        """Simple logging"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def encode_telemetry(self, data):
        """Encode telemetry data into compact binary format for LoRa
        
        Format (15 bytes):
        - 1 byte: Channel number (1-32)
        - 2 bytes: Reading (signed int16, divide by 10 for decimal)
        - 1 byte: Gas type code (0-26)
        - 1 byte: Battery voltage (0-255, multiply by 0.1 for volts)
        - 1 byte: Fault code (0-15)
        - 4 bytes: Timestamp (Unix epoch)
        - 1 byte: Sensor mode (4 bits) + Sensor type (4 bits)
        - 1 byte: Reading precision
        - 3 bytes: Reserved for future use
        """
        try:
            # Extract values
            channel = data['channel']
            reading = int(data['reading'] * 10)  # Convert to int16
            gas_type = data['gas_type_code']
            battery = int(data['battery'] * 10)  # Convert to byte
            fault_code = data['fault_code']
            timestamp = int(time.time())
            sensor_info = ((data['sensor_mode'] & 0x0F) << 4) | (data['sensor_type'] & 0x0F)
            precision = data['precision']
            
            # Pack into binary
            packed = struct.pack(
                '<BhBBBIBBBBB',  # Little-endian format
                channel,
                reading,
                gas_type,
                battery,
                fault_code,
                timestamp,
                sensor_info,
                precision,
                0, 0, 0  # Reserved bytes
            )
            
            return packed
        except Exception as e:
            self.log(f"Encoding error: {e}", "ERROR")
            return None
    
    def should_forward(self, channel, fault_code):
        """Determine if packet should be forwarded based on interval and fault settings"""
        # Check if only forwarding faults
        if self.config['bridge']['only_forward_faults'] and fault_code == 0:
            return False
        
        # Check forward interval
        now = time.time()
        last_time = self.last_forward_time.get(channel, 0)
        interval = self.config['bridge']['forward_interval']
        
        if now - last_time >= interval:
            self.last_forward_time[channel] = now
            return True
        
        # Always forward if fault code changed
        if fault_code > 0:
            return True
            
        return False
    
    def forward_to_mesh(self, data):
        """Forward telemetry data over Meshtastic mesh"""
        try:
            channel = data['channel']
            fault_code = data['fault_code']
            
            # Check if should forward
            if not self.should_forward(channel, fault_code):
                return
            
            # Encode data
            if self.config['bridge']['compress_data']:
                payload = self.encode_telemetry(data)
                message_type = "BINARY"
            else:
                payload = json.dumps(data).encode('utf-8')
                message_type = "JSON"
            
            if not payload:
                return
            
            # Send via Meshtastic
            if self.mesh_interface:
                self.mesh_interface.sendData(
                    payload,
                    portNum=meshtastic.portnums_pb2.PRIVATE_APP,
                    wantAck=False,  # No ACK for faster transmission
                    wantResponse=False
                )
                
                self.packet_count += 1
                
                fault_indicator = "⚠️" if fault_code > 0 else "✓"
                self.log(
                    f"{fault_indicator} Forwarded CH{channel:02d} [{message_type}] "
                    f"{data['gas_type']} {data['reading']:.1f} "
                    f"({len(payload)} bytes)"
                )
        except Exception as e:
            self.log(f"Mesh forward error: {e}", "ERROR")
    
    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT message"""
        try:
            # Decode payload
            data = json.loads(msg.payload.decode('utf-8'))
            
            # Forward to mesh
            self.forward_to_mesh(data)
            
        except Exception as e:
            self.log(f"MQTT message error: {e}", "ERROR")
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.mqtt_connected = True
            self.reconnect_attempts = 0
            mqtt_cfg = self.config['mqtt_source']
            topic = f"{mqtt_cfg['topic_prefix']}/channel+"
            client.subscribe(topic)
            self.log(f"✓ MQTT connected - Subscribed to: {topic}")
        else:
            self.mqtt_connected = False
            self.log(f"MQTT connection failed with code: {rc}", "ERROR")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnect callback"""
        self.mqtt_connected = False
        if rc != 0:
            self.log(f"⚠️ MQTT disconnected unexpectedly (code {rc})", "WARN")
    
    def setup_mqtt(self):
        """Setup MQTT connection to local broker"""
        try:
            mqtt_cfg = self.config['mqtt_source']
            
            self.mqtt_client = mqtt.Client()
            
            if mqtt_cfg['username']:
                self.mqtt_client.username_pw_set(
                    mqtt_cfg['username'],
                    mqtt_cfg['password']
                )
            
            if mqtt_cfg['use_tls']:
                import ssl
                self.mqtt_client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
            
            # Set callbacks
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
            self.mqtt_client.on_message = self.on_mqtt_message
            
            self.log(f"Connecting to MQTT broker: {mqtt_cfg['broker']}...")
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
        """Setup Meshtastic serial interface"""
        try:
            mesh_port = self.config['edge_node']['meshtastic_port']
            
            self.log(f"Connecting to Meshtastic device: {mesh_port}...")
            self.mesh_interface = meshtastic.serial_interface.SerialInterface(mesh_port)
            
            # Wait for connection
            time.sleep(2)
            
            # Get node info
            try:
                node_info = self.mesh_interface.getMyNodeInfo()
                self.mesh_connected = True
                self.log(f"✓ Meshtastic connected: {node_info.get('user', {}).get('longName', 'Unknown')}")
            except:
                self.mesh_connected = True  # Interface created, might get info later
                self.log("✓ Meshtastic interface created")
            
        except Exception as e:
            self.mesh_connected = False
            self.log(f"Meshtastic setup error: {e}", "ERROR")
            raise
    
    def check_connections(self):
        """Monitor and reconnect if needed"""
        # Check MQTT
        if not self.mqtt_connected:
            self.log("⚠️ MQTT disconnected, attempting reconnect...", "WARN")
            try:
                self.mqtt_client.reconnect()
            except:
                pass
        
        # Check Meshtastic
        if self.mesh_interface is None:
            self.log("⚠️ Meshtastic disconnected, attempting reconnect...", "WARN")
            try:
                self.setup_meshtastic()
            except:
                pass
    
    def send_heartbeat(self):
        """Send periodic heartbeat/status update"""
        now = time.time()
        if now - self.last_heartbeat >= 60:  # Every minute
            self.last_heartbeat = now
            mqtt_status = "✓" if self.mqtt_connected else "✗"
            mesh_status = "✓" if self.mesh_connected else "✗"
            self.log(
                f"💓 Status: MQTT {mqtt_status} | Mesh {mesh_status} | "
                f"Forwarded: {self.packet_count} packets"
            )
    
    def run(self):
        """Main bridge loop"""
        self.log("="*80)
        self.log("OI-7500 Meshtastic Bridge - Edge Node")
        self.log("="*80)
        self.log(f"Location: {self.config['edge_node']['location_name']}")
        self.log(f"Forward interval: {self.config['bridge']['forward_interval']}s")
        self.log(f"Compression: {self.config['bridge']['compress_data']}")
        self.log(f"Faults only: {self.config['bridge']['only_forward_faults']}")
        
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
        
        self.log("🚀 Bridge active - forwarding telemetry to mesh network")
        self.log("Press Ctrl+C to stop")
        self.log("-"*80)
        
        self.running = True
        health_check_interval = 0
        
        try:
            while self.running:
                time.sleep(1)
                health_check_interval += 1
                
                # Health check every 30 seconds
                if health_check_interval >= 30:
                    self.check_connections()
                    health_check_interval = 0
                
                # Send heartbeat
                self.send_heartbeat()
                
        except KeyboardInterrupt:
            self.log("Bridge stopped by user")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup connections"""
        self.log("="*80)
        self.log(f"Total packets forwarded: {self.packet_count}")
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
        if self.mesh_interface:
            self.mesh_interface.close()
        
        self.log("Bridge shutdown complete")


def main():
    parser = argparse.ArgumentParser(
        description='OI-7500 Meshtastic Bridge - Forward telemetry over mesh network'
    )
    parser.add_argument('--config', default=CONFIG_FILE, help='Configuration file')
    
    args = parser.parse_args()
    
    bridge = MeshtasticBridge(args.config)
    bridge.run()


if __name__ == "__main__":
    main()
