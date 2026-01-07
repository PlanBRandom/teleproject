#!/usr/bin/env python3
"""
Multi-Network Radio & Modbus Monitor with MQTT Reporting
Monitors 3-tier repeater network topology simultaneously:
  - Network 15 (COM7) → OI-7530 (Modbus slave 30)
  - Network 20 (COM12) → OI-7010 (Modbus slave 10)
  - Network 25 (COM11) → OI-7032 (Modbus slave 3) - Primary via repeaters

Reports data to Hive MQTT broker for remote monitoring.
"""

import serial
import threading
import time
import struct
from datetime import datetime
from collections import defaultdict
import json
import os
import sys

# Add pipeline to path for MQTT imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline.mqtt import MQTTPublisher, MQTTConfig

# Gas type mapping
GAS_TYPES = {
    0: "H2S", 1: "SO2", 2: "O2", 3: "CO", 4: "CL2", 5: "CO2", 6: "LEL", 7: "VOC",
    8: "FEET", 9: "HCl", 10: "NH3", 11: "H2", 12: "ClO2", 13: "HCN", 14: "F2", 
    15: "HF", 16: "CH2O", 17: "NO2", 18: "O3", 19: "INCHES", 20: "4-20mA", 
    21: "Not Specified", 22: "°C", 23: "°F", 24: "CH4", 25: "NO", 26: "PH3", 
    27: "HBr", 28: "EtO", 29: "CH3SH", 30: "AsH3", 31: "R410A", 32: "R1234YF", 33: "R32"
}

class MultiNetworkMonitor:
    def __init__(self, duration_hours=1, mqtt_broker="localhost", mqtt_port=1883, mqtt_username=None, mqtt_password=None):
        self.duration_hours = duration_hours
        self.running = False
        self.start_time = None
        
        # Radio configurations
        self.radios = {
            'Network_15': {'port': 'COM7', 'baudrate': 115200, 'monitor': 'OI-7530', 'modbus_slave': 30},
            'Network_20': {'port': 'COM12', 'baudrate': 115200, 'monitor': 'OI-7010', 'modbus_slave': 10},
            'Network_25': {'port': 'COM11', 'baudrate': 115200, 'monitor': 'OI-7032', 'modbus_slave': 3},
        }
        
        # Modbus configuration
        self.modbus_port = 'COM10'
        self.modbus_baudrate = 19200
        
        # MQTT configuration
        self.mqtt_enabled = mqtt_broker is not None
        self.mqtt_publisher = None
        if self.mqtt_enabled:
            mqtt_config = MQTTConfig(
                broker=mqtt_broker,
                port=mqtt_port,
                username=mqtt_username,
                password=mqtt_password,
                client_id="oi_multi_network_monitor",
                base_topic="oi7500",
                device_name="OI Multi-Network Monitor",
                device_id="oi_network_monitor",
                discovery_enabled=True
            )
            self.mqtt_publisher = MQTTPublisher(mqtt_config)
        
        # Statistics
        self.stats = {
            'radios': {},
            'modbus': {
                'total_bytes': 0,
                'slave_10': {'requests': 0, 'responses': 0},
                'slave_30': {'requests': 0, 'responses': 0},
                'slave_3': {'requests': 0, 'responses': 0},
            },
            'start_time': None,
            'last_update': None,
        }
        
        # Initialize radio stats
        for network in self.radios.keys():
            self.stats['radios'][network] = {
                'total_bytes': 0,
                'total_packets': 0,
                'channels': defaultdict(int),
                'gas_types': defaultdict(int),
            }
        
        # Log files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = 'protocol_logs'
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.log_files = {}
        for network in self.radios.keys():
            self.log_files[network] = open(f'{self.log_dir}/{network}_{timestamp}.log', 'w')
        
        self.modbus_log = open(f'{self.log_dir}/modbus_{timestamp}.log', 'w')
        self.analysis_log = open(f'{self.log_dir}/analysis_{timestamp}.log', 'w')
        self.stats_file = f'{self.log_dir}/stats_{timestamp}.json'
    
    def decode_packet(self, data):
        """Decode RM024 API transmit packet (0x81 frame)."""
        if len(data) < 24 or data[0] != 0x81:
            return None
        
        try:
            channel = data[8]
            reading_bytes = data[10:14]
            reading = struct.unpack('>f', reading_bytes)[0]
            gas_type = data[14]
            status = data[15]
            
            return {
                'channel': channel,
                'reading': reading,
                'gas_type': gas_type,
                'gas_name': GAS_TYPES.get(gas_type, f"Unknown({gas_type})"),
                'status': status,
            }
        except:
            return None
    
    def monitor_radio(self, network_name, config):
        """Monitor a specific radio network."""
        port = config['port']
        baudrate = config['baudrate']
        
        log_file = self.log_files[network_name]
        now = datetime.now().isoformat()
        log_file.write(f"[{now}] Connected to {port} at {baudrate} baud ({network_name})\n")
        log_file.flush()
        
        try:
            ser = serial.Serial(port=port, baudrate=baudrate, timeout=1, rtscts=True)
            
            buffer = bytearray()
            
            while self.running:
                if ser.in_waiting:
                    data = ser.read(ser.in_waiting)
                    buffer.extend(data)
                    
                    self.stats['radios'][network_name]['total_bytes'] += len(data)
                    
                    # Log raw data
                    now = datetime.now().isoformat()
                    log_file.write(f"[{now}] RX: {len(data)} bytes - {data.hex()}\n")
                    log_file.flush()
                    
                    # Try to extract complete 24-byte 0x81 packets
                    while len(buffer) >= 24:
                        # Look for 0x81 frame
                        if buffer[0] == 0x81 and buffer[1] == 0x11 and buffer[2] == 0x00:
                            packet = bytes(buffer[:24])
                            buffer = buffer[24:]
                            
                            self.stats['radios'][network_name]['total_packets'] += 1
                            
                            # Decode packet
                            decoded = self.decode_packet(packet)
                            if decoded:
                                self.stats['radios'][network_name]['channels'][decoded['channel']] += 1
                                self.stats['radios'][network_name]['gas_types'][decoded['gas_name']] += 1
                                
                                # Log analysis
                                now = datetime.now().isoformat()
                                self.analysis_log.write(
                                    f"[{now}] {network_name:12s} | "
                                    f"Ch {decoded['channel']:2d} | "
                                    f"{decoded['gas_name']:8s} | "
                                    f"{decoded['reading']:8.2f} ppm | "
                                    f"Status 0x{decoded['status']:02X}\n"
                                )
                                self.analysis_log.flush()
                                
                                # Publish to MQTT
                                if self.mqtt_enabled and self.mqtt_publisher and self.mqtt_publisher.connected:
                                    self._publish_channel_to_mqtt(network_name, decoded)
                        else:
                            # Skip byte and continue
                            buffer = buffer[1:]
                
                time.sleep(0.01)
            
            ser.close()
        except Exception as e:
            log_file.write(f"[{datetime.now().isoformat()}] ERROR: {e}\n")
            log_file.flush()
    
    def monitor_modbus(self):
        """Monitor Modbus traffic on shared bus."""
        log_file = self.modbus_log
        now = datetime.now().isoformat()
        log_file.write(f"[{now}] Connected to {self.modbus_port} at {self.modbus_baudrate} baud\n")
        log_file.write(f"[{now}] Monitoring slave IDs: 3 (OI-7032), 10 (OI-7010), 30 (OI-7530)\n")
        log_file.flush()
        
        try:
            ser = serial.Serial(port=self.modbus_port, baudrate=self.modbus_baudrate, timeout=1)
            
            while self.running:
                if ser.in_waiting:
                    data = ser.read(ser.in_waiting)
                    self.stats['modbus']['total_bytes'] += len(data)
                    
                    now = datetime.now().isoformat()
                    log_file.write(f"[{now}] RX: {len(data)} bytes - {data.hex()}\n")
                    log_file.flush()
                    
                    # Try to identify slave ID
                    if len(data) >= 2:
                        slave_id = data[0]
                        function_code = data[1]
                        
                        if slave_id == 3:
                            self.stats['modbus']['slave_3']['responses'] += 1
                        elif slave_id == 10:
                            self.stats['modbus']['slave_10']['responses'] += 1
                        elif slave_id == 30:
                            self.stats['modbus']['slave_30']['responses'] += 1
                        
                        self.analysis_log.write(
                            f"[{now}] MODBUS        | Slave {slave_id:2d} | "
                            f"Function 0x{function_code:02X} | {len(data)} bytes\n"
                        )
                        self.analysis_log.flush()
                
                time.sleep(0.01)
            
            ser.close()
        except Exception as e:
            log_file.write(f"[{datetime.now().isoformat()}] ERROR: {e}\n")
            log_file.flush()
    
    def update_stats(self):
        """Periodically update statistics file."""
        while self.running:
            self.stats['last_update'] = datetime.now().isoformat()
            
            # Calculate elapsed time
            if self.start_time:
                elapsed = (datetime.now() - self.start_time).total_seconds()
                self.stats['elapsed_seconds'] = elapsed
            
            # Convert defaultdicts to regular dicts for JSON
            stats_copy = {
                'start_time': self.stats['start_time'],
                'last_update': self.stats['last_update'],
                'elapsed_seconds': self.stats.get('elapsed_seconds', 0),
                'radios': {},
                'modbus': self.stats['modbus'].copy()
            }
            
            for network, data in self.stats['radios'].items():
                stats_copy['radios'][network] = {
                    'total_bytes': data['total_bytes'],
                    'total_packets': data['total_packets'],
                    'channels': dict(data['channels']),
                    'gas_types': dict(data['gas_types']),
                }
            
            with open(self.stats_file, 'w') as f:
                json.dump(stats_copy, f, indent=2)
            
            # Publish stats to MQTT
            self._publish_stats_to_mqtt()
            
            time.sleep(60)  # Update every minute
    
    def _publish_channel_to_mqtt(self, network_name, decoded):
        """Publish channel reading to MQTT."""
        try:
            channel = decoded['channel']
            reading = decoded['reading']
            gas_name = decoded['gas_name']
            status = decoded['status']
            
            # Publish to network-specific topic
            topic = f"oi7500/network/{network_name}/channel_{channel}/state"
            payload = {
                "channel": channel,
                "reading": reading,
                "gas_type": gas_name,
                "status": status,
                "network": network_name,
                "timestamp": datetime.now().isoformat()
            }
            self.mqtt_publisher.publish(topic, payload, retain=False)
            
            # Also publish to channel-aggregated topic (all networks for same channel)
            topic_agg = f"oi7500/channels/channel_{channel}/state"
            payload_agg = {
                "channel": channel,
                "reading": reading,
                "gas_type": gas_name,
                "status": status,
                "source_network": network_name,
                "timestamp": datetime.now().isoformat()
            }
            self.mqtt_publisher.publish(topic_agg, payload_agg, retain=False)
            
        except Exception as e:
            self.analysis_log.write(f"[{datetime.now().isoformat()}] MQTT publish error: {e}\n")
            self.analysis_log.flush()
    
    def _publish_stats_to_mqtt(self):
        """Publish statistics to MQTT."""
        if not self.mqtt_enabled or not self.mqtt_publisher or not self.mqtt_publisher.connected:
            return
        
        try:
            # Publish overall stats
            topic = "oi7500/monitor/stats"
            stats_copy = {
                'start_time': self.stats['start_time'],
                'last_update': self.stats['last_update'],
                'elapsed_seconds': self.stats.get('elapsed_seconds', 0),
                'radios': {},
                'modbus': self.stats['modbus'].copy()
            }
            
            for network, data in self.stats['radios'].items():
                stats_copy['radios'][network] = {
                    'total_bytes': data['total_bytes'],
                    'total_packets': data['total_packets'],
                    'channels': dict(data['channels']),
                    'gas_types': dict(data['gas_types']),
                }
            
            self.mqtt_publisher.publish(topic, stats_copy, retain=True)
            
            # Publish per-network stats
            for network, data in self.stats['radios'].items():
                topic = f"oi7500/network/{network}/stats"
                network_stats = {
                    'total_bytes': data['total_bytes'],
                    'total_packets': data['total_packets'],
                    'channel_count': len(data['channels']),
                    'channels': sorted(list(data['channels'].keys())),
                    'timestamp': datetime.now().isoformat()
                }
                self.mqtt_publisher.publish(topic, network_stats, retain=True)
                
        except Exception as e:
            print(f"MQTT stats publish error: {e}")
    
    def print_status(self):
        """Print periodic status updates to console."""
        while self.running:
            time.sleep(30)  # Print every 30 seconds
            
            elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            hours = elapsed / 3600
            
            print(f"\n{'='*80}")
            print(f"Status Update - Elapsed: {hours:.2f} hours")
            print(f"{'='*80}")
            
            for network, data in self.stats['radios'].items():
                print(f"\n{network}:")
                print(f"  Bytes: {data['total_bytes']:,} | Packets: {data['total_packets']:,}")
                if data['channels']:
                    channels = sorted(data['channels'].keys())
                    print(f"  Channels: {channels}")
                if data['gas_types']:
                    gases = sorted(data['gas_types'].items(), key=lambda x: x[1], reverse=True)[:5]
                    print(f"  Top Gases: {', '.join([f'{g}({c})' for g, c in gases])}")
            
            print(f"\nModbus (COM10):")
            print(f"  Total bytes: {self.stats['modbus']['total_bytes']:,}")
            for slave_name, slave_data in sorted(self.stats['modbus'].items()):
                if isinstance(slave_data, dict) and 'responses' in slave_data:
                    print(f"  {slave_name}: {slave_data['responses']} responses")
            
            print(f"\n{'='*80}")
    
    def run(self):
        """Run the monitor."""
        print("="*80)
        print("MULTI-NETWORK RADIO & MODBUS MONITOR")
        print("="*80)
        print(f"\nRadio Networks:")
        for network, config in self.radios.items():
            print(f"  {network:12s}: {config['port']} @ {config['baudrate']} baud → "
                  f"{config['monitor']} (Modbus slave {config['modbus_slave']})")
        print(f"\nModbus Bus:")
        print(f"  {self.modbus_port} @ {self.modbus_baudrate} baud")
        print(f"  Monitoring slaves: 3 (OI-7032), 10 (OI-7010), 30 (OI-7530)")
        
        if self.mqtt_enabled:
            print(f"\nMQTT Reporting:")
            print(f"  Broker: {self.mqtt_publisher.config.broker}:{self.mqtt_publisher.config.port}")
            print(f"  Base Topic: {self.mqtt_publisher.config.base_topic}")
        else:
            print(f"\nMQTT: Disabled")
        
        print(f"\nDuration: {self.duration_hours} hour(s)")
        print(f"Logs: {self.log_dir}/")
        print("="*80)
        print("\nStarting monitors...")
        
        # Connect to MQTT if enabled
        if self.mqtt_enabled:
            try:
                print("  Connecting to MQTT...")
                self.mqtt_publisher.connect()
                self.mqtt_publisher.publish_availability(True)
                print(f"  ✓ MQTT connected to {self.mqtt_publisher.config.broker}")
                
                # Publish initial status
                topic = "oi7500/monitor/status"
                status = {
                    "state": "starting",
                    "duration_hours": self.duration_hours,
                    "networks": list(self.radios.keys()),
                    "timestamp": datetime.now().isoformat()
                }
                self.mqtt_publisher.publish(topic, status)
            except Exception as e:
                print(f"  ⚠️  MQTT connection failed: {e}")
                print(f"  Continuing without MQTT...")
                self.mqtt_enabled = False
        
        self.running = True
        self.start_time = datetime.now()
        self.stats['start_time'] = self.start_time.isoformat()
        
        # Start threads for each radio
        threads = []
        for network, config in self.radios.items():
            t = threading.Thread(target=self.monitor_radio, args=(network, config), daemon=True)
            t.start()
            threads.append(t)
            print(f"  ✓ {network} monitor started")
        
        # Start Modbus monitor
        modbus_thread = threading.Thread(target=self.monitor_modbus, daemon=True)
        modbus_thread.start()
        threads.append(modbus_thread)
        print(f"  ✓ Modbus monitor started")
        
        # Start stats updater
        stats_thread = threading.Thread(target=self.update_stats, daemon=True)
        stats_thread.start()
        threads.append(stats_thread)
        print(f"  ✓ Stats updater started")
        
        # Start status printer
        status_thread = threading.Thread(target=self.print_status, daemon=True)
        status_thread.start()
        threads.append(status_thread)
        print(f"  ✓ Status printer started")
        
        print(f"\n✓ All monitors running!")
        print(f"  Press Ctrl+C to stop early")
        print(f"  Will automatically stop after {self.duration_hours} hour(s)")
        
        if self.mqtt_enabled:
            print(f"  Publishing data to MQTT: {self.mqtt_publisher.config.broker}")
        
        print("="*80)
        
        # Publish running status to MQTT
        if self.mqtt_enabled and self.mqtt_publisher and self.mqtt_publisher.connected:
            topic = "oi7500/monitor/status"
            status = {
                "state": "running",
                "start_time": self.start_time.isoformat(),
                "duration_hours": self.duration_hours,
                "timestamp": datetime.now().isoformat()
            }
            self.mqtt_publisher.publish(topic, status)
        
        # Run for specified duration
        try:
            end_time = self.start_time.timestamp() + (self.duration_hours * 3600)
            while datetime.now().timestamp() < end_time and self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping monitors (Ctrl+C pressed)...")
        
        self.running = False
        
        # Wait for threads to finish
        time.sleep(2)
        
        # Close log files
        for log_file in self.log_files.values():
            log_file.close()
        self.modbus_log.close()
        self.analysis_log.close()
        
        # Publish final status to MQTT
        if self.mqtt_enabled and self.mqtt_publisher and self.mqtt_publisher.connected:
            topic = "oi7500/monitor/status"
            status = {
                "state": "stopped",
                "end_time": datetime.now().isoformat(),
                "elapsed_seconds": elapsed,
                "timestamp": datetime.now().isoformat()
            }
            self.mqtt_publisher.publish(topic, status)
            
            # Disconnect from MQTT
            self.mqtt_publisher.publish_availability(False)
            self.mqtt_publisher.disconnect()
            print("\n✓ MQTT disconnected")
        
        # Final stats
        self.stats['last_update'] = datetime.now().isoformat()
        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.stats['elapsed_seconds'] = elapsed
        
        print("\n" + "="*80)
        print("MONITORING COMPLETE")
        print("="*80)
        print(f"\nTotal duration: {elapsed/3600:.2f} hours")
        
        for network, data in self.stats['radios'].items():
            print(f"\n{network}:")
            print(f"  Total bytes: {data['total_bytes']:,}")
            print(f"  Total packets: {data['total_packets']:,}")
            print(f"  Unique channels: {len(data['channels'])}")
            print(f"  Unique gas types: {len(data['gas_types'])}")
            
            if data['channels']:
                print(f"  Channels detected: {sorted(data['channels'].keys())}")
        
        print(f"\nModbus:")
        print(f"  Total bytes: {self.stats['modbus']['total_bytes']:,}")
        print(f"  Slave 3 (OI-7032): {self.stats['modbus']['slave_3']['responses']} responses")
        print(f"  Slave 10 (OI-7010): {self.stats['modbus']['slave_10']['responses']} responses")
        print(f"  Slave 30 (OI-7530): {self.stats['modbus']['slave_30']['responses']} responses")
        
        print(f"\nLog files saved to: {self.log_dir}/")
        print("="*80)

if __name__ == '__main__':
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-Network Radio & Modbus Monitor with MQTT')
    parser.add_argument('duration', type=float, nargs='?', default=1.0,
                        help='Duration in hours (default: 1.0)')
    parser.add_argument('--mqtt-broker', type=str, default='localhost',
                        help='MQTT broker address (default: localhost)')
    parser.add_argument('--mqtt-port', type=int, default=1883,
                        help='MQTT broker port (default: 1883)')
    parser.add_argument('--mqtt-username', type=str, default=None,
                        help='MQTT username (optional)')
    parser.add_argument('--mqtt-password', type=str, default=None,
                        help='MQTT password (optional)')
    parser.add_argument('--no-mqtt', action='store_true',
                        help='Disable MQTT reporting')
    
    args = parser.parse_args()
    
    # Disable MQTT if requested
    mqtt_broker = None if args.no_mqtt else args.mqtt_broker
    
    monitor = MultiNetworkMonitor(
        duration_hours=args.duration,
        mqtt_broker=mqtt_broker,
        mqtt_port=args.mqtt_port,
        mqtt_username=args.mqtt_username,
        mqtt_password=args.mqtt_password
    )
    monitor.run()
