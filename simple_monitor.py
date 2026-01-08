#!/usr/bin/env python3
"""
OI-7500 Simple Monitor - Lightweight version for Raspberry Pi / ESP32
Optimized for end-user deployment on resource-constrained devices
"""

import serial
import json
import time
import argparse
import paho.mqtt.client as mqtt
import ssl
from datetime import datetime
from pathlib import Path

# Configuration file
CONFIG_FILE = "simple_config.json"

# Default configuration
DEFAULT_CONFIG = {
    "device": {
        "model": "OI-7530",
        "radio_port": "COM11",
        "radio_baud": 115200,
        "network": "Network_25"
    },
    "modbus": {
        "enabled": False,
        "port": "COM10",
        "baud": 9600,
        "slave_id": 32
    },
    "mqtt": {
        "enabled": True,
        "broker": "a1bcc059f5f74a6d8271e8b567fecc6d.s1.eu.hivemq.cloud",
        "port": 8883,
        "username": "laird",
        "password": "LairdRM024",
        "use_tls": True,
        "topic_prefix": "oi7500"
    },
    "logging": {
        "enabled": True,
        "file": "simple_monitor.log",
        "console": True
    }
}

# Fault codes
FAULT_CODES = {
    0: "F0 - No Fault",
    1: "F1 - Low Battery",
    2: "F2 - Sensor Fail",
    3: "F3 - Calibration Due",
    4: "F4 - Span Gas Out of Range",
    5: "F5 - Zero Fault",
    6: "F6 - Span Fault",
    7: "F7 - Communications Fault",
    8: "F8 - Duplicate Address Detected",
    9: "F9 - Lost Link",
    10: "F10 - Sensor Disconnected",
    11: "F11 - Sensor Saturated",
    12: "F12 - Over Range",
    13: "F13 - Under Range",
    14: "F14 - Primary Link Timeout",
    15: "F15 - System Fault"
}

# Gas types
GAS_TYPES = {
    0: "None", 1: "LEL", 2: "O2", 3: "CO", 4: "H2S", 5: "SO2",
    6: "NH3", 7: "Cl2", 8: "ClO2", 9: "HCN", 10: "NO", 11: "NO2",
    12: "HCl", 13: "PH3", 14: "ETO", 15: "H2", 16: "AsH3",
    17: "Br2", 18: "COCl2", 19: "GeH4", 20: "SiH4", 21: "B2H6",
    22: "F2", 23: "O3", 24: "HF", 25: "N2H4", 26: "C2H4O"
}


class SimpleMonitor:
    def __init__(self, config_file=CONFIG_FILE):
        self.config = self.load_config(config_file)
        self.mqtt_client = None
        self.running = False
        self.packet_count = 0
        
    def load_config(self, config_file):
        """Load configuration from file or create default"""
        config_path = Path(config_file)
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"[INFO] Loaded configuration from {config_file}")
        else:
            config = DEFAULT_CONFIG
            self.save_config(config, config_file)
            print(f"[INFO] Created default configuration file: {config_file}")
        return config
    
    def save_config(self, config, config_file):
        """Save configuration to file"""
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def log(self, message, level="INFO"):
        """Simple logging"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        
        if self.config['logging']['console']:
            print(log_msg)
        
        if self.config['logging']['enabled']:
            with open(self.config['logging']['file'], 'a') as f:
                f.write(log_msg + "\n")
    
    def setup_mqtt(self):
        """Setup MQTT connection"""
        if not self.config['mqtt']['enabled']:
            return
        
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.username_pw_set(
                self.config['mqtt']['username'],
                self.config['mqtt']['password']
            )
            
            if self.config['mqtt']['use_tls']:
                self.mqtt_client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
            
            self.mqtt_client.connect(
                self.config['mqtt']['broker'],
                self.config['mqtt']['port'],
                60
            )
            self.mqtt_client.loop_start()
            self.log("Connected to MQTT broker")
        except Exception as e:
            self.log(f"MQTT connection failed: {e}", "ERROR")
            self.mqtt_client = None
    
    def publish_mqtt(self, topic, payload):
        """Publish data to MQTT"""
        if self.mqtt_client:
            try:
                full_topic = f"{self.config['mqtt']['topic_prefix']}/{topic}"
                self.mqtt_client.publish(full_topic, json.dumps(payload))
            except Exception as e:
                self.log(f"MQTT publish failed: {e}", "ERROR")
    
    def decode_protocol1(self, packet):
        """Decode Protocol 1 packet (8 fields)"""
        if len(packet) < 20:
            return None
        
        try:
            # Extract fields
            channel = packet[7]
            reading = int.from_bytes(packet[8:10], byteorder='little', signed=True)
            gas_type = packet[16] & 0x7F
            sensor_mode = (packet[17] >> 4) & 0x0F
            sensor_type = packet[17] & 0x0F
            battery = round(packet[18] * 0.1, 1)
            fault_code = (packet[19] >> 4) & 0x0F
            reading_precision = packet[19] & 0x0F
            
            # Calculate actual reading
            if reading_precision <= 7:
                actual_reading = reading / (10 ** reading_precision)
            else:
                actual_reading = reading
            
            return {
                'channel': channel,
                'reading': actual_reading,
                'gas_type': GAS_TYPES.get(gas_type, f"Unknown({gas_type})"),
                'gas_type_code': gas_type,
                'sensor_mode': sensor_mode,
                'sensor_type': sensor_type,
                'battery': battery,
                'fault_code': fault_code,
                'fault_description': FAULT_CODES.get(fault_code, f"Unknown({fault_code})"),
                'precision': reading_precision,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.log(f"Decode error: {e}", "ERROR")
            return None
    
    def format_packet_display(self, data):
        """Format packet for console display"""
        fault_indicator = "⚠️" if data['fault_code'] > 0 else "✓"
        return (f"{fault_indicator} CH{data['channel']:02d} | "
                f"{data['gas_type']:8s} | "
                f"{data['reading']:7.1f} | "
                f"Battery: {data['battery']:.1f}V | "
                f"{data['fault_description']}")
    
    def monitor(self, duration_minutes=None):
        """Main monitoring loop"""
        self.log(f"Starting Simple Monitor")
        self.log(f"Model: {self.config['device']['model']}")
        self.log(f"Radio: {self.config['device']['radio_port']} @ {self.config['device']['radio_baud']} baud")
        self.log(f"Network: {self.config['device']['network']}")
        
        # Setup MQTT
        self.setup_mqtt()
        
        # Open serial port
        try:
            ser = serial.Serial(
                self.config['device']['radio_port'],
                self.config['device']['radio_baud'],
                timeout=1
            )
            self.log(f"Opened radio port: {self.config['device']['radio_port']}")
        except Exception as e:
            self.log(f"Failed to open radio port: {e}", "ERROR")
            return
        
        # Print header
        print("\n" + "="*80)
        print(f"OI-7500 Simple Monitor - {self.config['device']['model']} - {self.config['device']['network']}")
        print("="*80)
        print("Status | Channel | Gas Type | Reading | Battery | Fault")
        print("-"*80)
        
        # Calculate end time if duration specified
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60) if duration_minutes else None
        
        self.running = True
        buffer = bytearray()
        
        try:
            while self.running:
                # Check duration
                if end_time and time.time() >= end_time:
                    self.log(f"Duration complete ({duration_minutes} minutes)")
                    break
                
                # Read data
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    buffer.extend(data)
                    
                    # Look for packet start (0x53, 0x3F)
                    while len(buffer) >= 20:
                        if buffer[0] == 0x53 and buffer[1] == 0x3F:
                            packet = buffer[:20]
                            buffer = buffer[20:]
                            
                            # Decode packet
                            decoded = self.decode_protocol1(packet)
                            if decoded:
                                self.packet_count += 1
                                
                                # Display
                                print(self.format_packet_display(decoded))
                                
                                # Publish to MQTT
                                if self.mqtt_client:
                                    topic = f"channel{decoded['channel']:02d}"
                                    self.publish_mqtt(topic, decoded)
                        else:
                            buffer = buffer[1:]
                
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            self.log("Monitoring stopped by user")
        except Exception as e:
            self.log(f"Error during monitoring: {e}", "ERROR")
        finally:
            ser.close()
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            
            print("\n" + "="*80)
            self.log(f"Monitoring complete. Total packets: {self.packet_count}")


def main():
    parser = argparse.ArgumentParser(description='OI-7500 Simple Monitor for Raspberry Pi / ESP32')
    parser.add_argument('--duration', type=float, help='Duration in minutes (default: continuous)')
    parser.add_argument('--config', default=CONFIG_FILE, help='Configuration file')
    parser.add_argument('--setup', action='store_true', help='Interactive setup wizard')
    
    args = parser.parse_args()
    
    if args.setup:
        print("\n" + "="*80)
        print("OI-7500 Simple Monitor - Setup Wizard")
        print("="*80)
        print("\nPress Enter to use default values shown in [brackets]\n")
        
        config = DEFAULT_CONFIG.copy()
        
        # Device configuration
        model = input(f"Device Model [OI-7530]: ").strip() or "OI-7530"
        config['device']['model'] = model
        
        radio_port = input(f"Radio COM Port [COM11]: ").strip() or "COM11"
        config['device']['radio_port'] = radio_port
        
        network = input(f"Radio Network [Network_25]: ").strip() or "Network_25"
        config['device']['network'] = network
        
        # MQTT configuration
        mqtt_enable = input(f"Enable MQTT? [Y/n]: ").strip().lower()
        config['mqtt']['enabled'] = mqtt_enable != 'n'
        
        if config['mqtt']['enabled']:
            broker = input(f"MQTT Broker [{config['mqtt']['broker']}]: ").strip()
            if broker:
                config['mqtt']['broker'] = broker
        
        # Save configuration
        with open(args.config, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✓ Configuration saved to {args.config}")
        print("\nRun without --setup to start monitoring\n")
        return
    
    # Start monitoring
    monitor = SimpleMonitor(args.config)
    monitor.monitor(duration_minutes=args.duration)


if __name__ == "__main__":
    main()
