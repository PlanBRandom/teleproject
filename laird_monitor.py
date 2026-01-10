#!/usr/bin/env python3
"""
Laird Radio Monitor for OI-7500 System
Receives Gen2 protocol packets from Laird radios and publishes to MQTT
"""

import argparse
import json
import time
import signal
import sys
from pathlib import Path
from pipeline.radio_receiver import RadioReceiver, RadioMessage, GAS_TYPE_NAMES, FAULT_NAMES
import paho.mqtt.client as mqtt


class LairdMonitor:
    def __init__(self, config_file):
        self.config = self._load_config(config_file)
        self.running = False
        self.packet_count = 0
        self.mqtt_client = None
        self.receiver = None
        
    def _load_config(self, config_file):
        """Load configuration from JSON file"""
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def setup_mqtt(self):
        """Connect to MQTT broker"""
        if not self.config['mqtt']['enabled']:
            return
        
        try:
            self.mqtt_client = mqtt.Client()
            
            mqtt_cfg = self.config['mqtt']
            if mqtt_cfg.get('username'):
                self.mqtt_client.username_pw_set(mqtt_cfg['username'], mqtt_cfg['password'])
            
            if mqtt_cfg.get('use_tls'):
                self.mqtt_client.tls_set()
            
            self.mqtt_client.connect(mqtt_cfg['broker'], mqtt_cfg['port'], 60)
            self.mqtt_client.loop_start()
            print(f"[MQTT] Connected to {mqtt_cfg['broker']}:{mqtt_cfg['port']}")
        except Exception as e:
            print(f"[ERROR] MQTT connection failed: {e}")
    
    def publish_mqtt(self, channel, data):
        """Publish sensor data to MQTT"""
        if not self.mqtt_client:
            return
        
        try:
            topic = f"{self.config['mqtt']['topic_prefix']}/channel{channel:02d}"
            payload = json.dumps(data)
            self.mqtt_client.publish(topic, payload, qos=1, retain=True)
        except Exception as e:
            print(f"[ERROR] MQTT publish failed: {e}")
    
    def on_sensor_message(self, msg: RadioMessage):
        """Callback for received sensor messages"""
        self.packet_count += 1
        
        if msg.protocol == 1:
            gas_name = GAS_TYPE_NAMES.get(msg.gas_type, f"Gas {msg.gas_type}")
            fault_name = FAULT_NAMES.get(msg.fault_code, "None")
            
            print(f"[Ch{msg.channel:02d}] {gas_name}: {msg.reading:.{msg.precision}f} | "
                  f"Battery: {msg.battery_voltage:.1f}V | Fault: {fault_name}")
            
            # Publish to MQTT
            mqtt_data = {
                'channel': msg.channel,
                'reading': msg.reading,
                'gas_type': gas_name,
                'gas_type_code': msg.gas_type,
                'battery': msg.battery_voltage,
                'fault_code': msg.fault_code,
                'fault_description': fault_name,
                'precision': msg.precision,
                'sensor_mode': msg.sensor_mode,
                'transmitter_address': msg.transmitter_address,
                'timestamp': time.time()
            }
            
            if msg.rssi:
                mqtt_data['rssi'] = msg.rssi
            
            self.publish_mqtt(msg.channel, mqtt_data)
            
        elif msg.protocol == 2:
            print(f"[ALERT] Ch{msg.channel}: {msg.reading:.2f}")
        
        elif msg.protocol == 7:
            print(f"[MAINT] Ch{msg.channel} - Days since null: {msg.days_since_null}, cal: {msg.days_since_cal}")
    
    def run(self, duration_minutes=None):
        """Main monitoring loop"""
        device_cfg = self.config['device']
        
        print("="*80)
        print(f"Laird Monitor - {device_cfg['model']} - {device_cfg['network']}")
        print("="*80)
        print(f"Radio: {device_cfg['radio_port']} @ {device_cfg['radio_baud']} baud")
        print(f"Network: {device_cfg['network']}")
        print("="*80)
        
        # Setup MQTT
        self.setup_mqtt()
        
        # Create radio receiver
        self.receiver = RadioReceiver(
            device_cfg['radio_port'],
            baudrate=device_cfg['radio_baud'],
            api_mode=True,
            api_type='rm024'  # Laird RM024 API format (0x81 frames)
        )
        
        if not self.receiver.connect():
            print("[ERROR] Failed to connect to radio")
            return
        
        print("[OK] Radio connected")
        
        # Register callback
        self.receiver.register_callback(self.on_sensor_message)
        self.receiver.start()
        
        print("\nListening for sensor packets...")
        print("Press Ctrl+C to stop\n")
        
        # Calculate end time
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60) if duration_minutes else None
        
        self.running = True
        
        try:
            while self.running:
                if end_time and time.time() >= end_time:
                    print(f"\n[INFO] Duration complete ({duration_minutes} minutes)")
                    break
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n[INFO] Stopped by user")
        finally:
            self.receiver.stop()
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            
            print("\n" + "="*80)
            print(f"Monitoring complete. Total packets: {self.packet_count}")
            print("="*80)


def main():
    parser = argparse.ArgumentParser(description='OI Laird Radio Monitor')
    parser.add_argument('--config', default='simple_config_com11.json', help='Configuration file')
    parser.add_argument('--duration', type=float, help='Duration in minutes (default: continuous)')
    
    args = parser.parse_args()
    
    monitor = LairdMonitor(args.config)
    monitor.run(duration_minutes=args.duration)


if __name__ == "__main__":
    main()
