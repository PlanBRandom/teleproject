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

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.mqtt import MQTTPublisher, MQTTConfig
from database.packet_database import PacketDatabase

# Gas type mapping
GAS_TYPES = {
    0: "H2S", 1: "SO2", 2: "O2", 3: "CO", 4: "CL2", 5: "CO2", 6: "LEL", 7: "VOC",
    8: "FEET", 9: "HCl", 10: "NH3", 11: "H2", 12: "ClO2", 13: "HCN", 14: "F2", 
    15: "HF", 16: "CH2O", 17: "NO2", 18: "O3", 19: "INCHES", 20: "4-20mA", 
    21: "Not Specified", 22: "°C", 23: "°F", 24: "CH4", 25: "NO", 26: "PH3", 
    27: "HBr", 28: "EtO", 29: "CH3SH", 30: "AsH3", 31: "R410A", 32: "R1234YF", 33: "R32"
}

# Sensor modes (bits 0-2 of byte 14)
SENSOR_MODES = {
    0: "Normal", 1: "Null", 2: "Calibration", 3: "Relay", 
    4: "Radio Address", 5: "Diagnostic", 6: "Advanced Menu", 7: "Administration Menu"
}

# Sensor types (bits 3-7 of byte 14)
SENSOR_TYPES = {
    0: "EC", 1: "IR", 2: "CB", 3: "MOS", 4: "PID", 5: "TANK LEVEL", 6: "4-20 mA",
    7: "SWITCH", 30: "OI-WF190", 31: "NONE SELECTED"
}

# Fault codes (bits 0-3 of byte 17) - Official Oldham Documentation
FAULT_CODES = {
    0: "None",
    1: "F1: Top card lost comm with digital sensor board",
    2: "F2: No longer assigned (update firmware)",
    3: "F3: Low Power IR sensor beyond repair",
    4: "F4: ADC/analog sensor board comm issue",
    5: "F5: Unit did not Null correctly",
    6: "F6: Unit did not Cal correctly (Autocal)",
    7: "F7: Internal fault (update firmware)",
    8: "F8: Two sensors with same address",
    9: "F9: Radio timeout (no comm from sensor)",
    10: "F10: Wired sensor not communicating",
    11: "F11: Low Power IR temp changing too quickly",
    12: "F12: Low Power IR element restarting",
    13: "F13: 4-20mA fault condition (check sensor)",
    14: "F14: Cannot see Primary Monitor (radio)",
    15: "F15: No longer assigned (update firmware)"
}

class MultiNetworkMonitor:
    def __init__(self, duration_hours=1, mqtt_broker="localhost", mqtt_port=1883, mqtt_username=None, mqtt_password=None, mqtt_use_tls=False):
        self.duration_hours = duration_hours
        self.running = False
        self.start_time = None
        
        # Radio configurations
        self.radios = {
            'Network_15': {'port': 'COM7', 'baudrate': 115200, 'monitor': 'OI-7530', 'modbus_slave': 30},
            'Network_20': {'port': 'COM12', 'baudrate': 115200, 'monitor': 'OI-7010', 'modbus_slave': 10},
            'Network_25': {'port': 'COM11', 'baudrate': 115200, 'monitor': 'OI-7032', 'modbus_slave': 32},
        }
        
        # Modbus configuration
        self.modbus_port = 'COM10'
        self.modbus_baudrate = 9600
        
        # MQTT configuration
        self.mqtt_enabled = mqtt_broker is not None
        self.mqtt_publisher = None
        if self.mqtt_enabled:
            mqtt_config = MQTTConfig(
                broker=mqtt_broker,
                port=mqtt_port,
                username=mqtt_username,
                password=mqtt_password,
                use_tls=mqtt_use_tls,
                client_id="oi_multi_network_monitor",
                base_topic="oi7500",
                device_name="OI Multi-Network Monitor",
                device_id="oi_network_monitor",
                discovery_enabled=True
            )
            self.mqtt_publisher = MQTTPublisher(mqtt_config)
        
        # Packet database for diagnostics
        self.packet_db = PacketDatabase()
        
        # Statistics
        self.stats = {
            'radios': {},
            'modbus': {
                'total_bytes': 0,
                'slave_10': {'requests': 0, 'responses': 0},
                'slave_30': {'requests': 0, 'responses': 0},
                'slave_32': {'requests': 0, 'responses': 0},
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
        """Decode RM024 API transmit packet (0x81 frame).
        
        The 0x81 frame contains Laird API mode headers + WireFree Protocol 1 payload:
        - Bytes 0-6: Laird API mode header (frame type, MAC, RSSI, etc)
        - Bytes 7+: WireFree Protocol 1 payload:
            - Bytes 7-8: Transmitter address (channel appears here at byte 8)
            - Byte 9: Protocol number
            - Bytes 10-13: Reading (IEEE 754 32-bit float, big-endian)
            - Byte 14: Sensor Mode (bits 0-2) + Sensor Type (bits 3-7)
            - Byte 15: Battery Reading  
            - Byte 16: Gas Type (bits 0-6) + Battery Scale (bit 7)
            - Byte 17: Fault Code (bits 0-3) + Precision (bits 4-6) + Text Flag (bit 7)
        """
        if len(data) < 24 or data[0] != 0x81:
            return None
        
        try:
            channel = data[8]
            reading_bytes = data[10:14]
            reading = struct.unpack('>f', reading_bytes)[0]
            
            # Byte 14: Mode/Type
            mode_type = data[14]
            sensor_mode = mode_type & 0x07  # Bits 0-2
            sensor_type = (mode_type >> 3) & 0x1F  # Bits 3-7
            
            # Byte 15: Battery Reading
            battery_reading = data[15]
            
            # Byte 16: Gas Type + Battery Scale
            gas_type_and_scale = data[16]  # Fixed: was data[14] (Mode/Type)
            gas_type = gas_type_and_scale & 0x7F  # Bits 0-6
            battery_scale = (gas_type_and_scale >> 7) & 0x01  # Bit 7
            
            # Byte 17: Fault/Precision/Text
            fault_prec_text = data[17] if len(data) > 17 else 0
            fault_code = fault_prec_text & 0x0F  # Bits 0-3
            precision = (fault_prec_text >> 4) & 0x07  # Bits 4-6
            has_text = (fault_prec_text >> 7) & 0x01  # Bit 7
            
            # Calculate actual battery voltage based on scale
            if battery_scale == 0:
                battery_voltage = battery_reading / 10.0
            else:
                battery_voltage = float(battery_reading)
            
            return {
                'transmitter_address': transmitter_address,  # Radio sensor's address
                'channel': channel,  # Monitor's receiving slot for this transmitter
                'reading': reading,
                'gas_type': gas_type,
                'gas_name': GAS_TYPES.get(gas_type, f"Unknown({gas_type})"),
                'sensor_mode': sensor_mode,
                'sensor_type': sensor_type,
                'battery_reading': battery_reading,
                'battery_voltage': battery_voltage,
                'battery_scale': battery_scale,
                'fault_code': fault_code,
                'precision': precision,
                'has_text': has_text,
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
                    
                    # Store raw data in database
                    self.packet_db.log_raw_packet(network_name, data, frame_type="0x81")
                    
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
                                
                                # Store decoded packet in database (with fault tracking)
                                decoded['transmitter_address'] = decoded['channel']  # Add address field
                                decoded['protocol'] = 1  # Protocol 1
                                fault_name = FAULT_CODES.get(decoded.get('fault_code', 0), "None")
                                decoded['fault_name'] = fault_name
                                self.packet_db.log_decoded_packet(network_name, decoded)
                                
                                # Log analysis
                                now = datetime.now().isoformat()
                                
                                # Format precision-aware reading
                                precision = decoded.get('precision', 2)
                                reading_str = f"{decoded['reading']:.{precision}f}"
                                transmitter_address = decoded.get('transmitter_address', 0)
                                
                                # Format fault if present
                                fault_str = ""
                                if decoded.get('fault_code', 0) != 0:
                                    fault_name = FAULT_CODES.get(decoded['fault_code'], f"Code{decoded['fault_code']}")
                                    fault_str = f" | FAULT: {fault_name}"
                                
                                self.analysis_log.write(
                                    f"[{now}] {network_name:12s} | "
                                    f"Addr {transmitter_address:5d} → Ch {decoded['channel']:2d} | "
                                    f"{decoded['gas_name']:8s} | "
                                    f"{reading_str:>10s} | "
                                    f"Batt {decoded.get('battery_voltage', 0):.1f}V"
                                    f"{fault_str}\n"
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
                        
                        if slave_id == 32:
                            self.stats['modbus']['slave_32']['responses'] += 1
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
            transmitter_address = decoded.get('transmitter_address', 0)
            channel = decoded['channel']
            reading = decoded['reading']
            gas_name = decoded['gas_name']
            gas_type = decoded.get('gas_type', 0)
            battery_voltage = decoded.get('battery_voltage', 0)
            fault_code = decoded.get('fault_code', 0)
            fault_name = FAULT_CODES.get(fault_code, "Unknown") if fault_code else "None"
            precision = decoded.get('precision', 2)
            sensor_mode = decoded.get('sensor_mode', 0)
            sensor_type = decoded.get('sensor_type', 0)
            
            # Publish to network-specific topic
            topic = f"oi7500/network/{network_name}/channel_{channel}/state"
            payload = {
                "transmitter_address": transmitter_address,  # Radio sensor's address
                "channel": channel,  # Monitor's receiving slot
                "reading": round(reading, precision),
                "gas_type": gas_name,
                "gas_type_code": gas_type,
                "battery_voltage": battery_voltage,
                "fault_code": fault_code,
                "fault": fault_name,
                "precision": precision,
                "sensor_mode": sensor_mode,
                "sensor_type": sensor_type,
                "network": network_name,
                "timestamp": datetime.now().isoformat()
            }
            self.mqtt_publisher.publish(topic, payload, retain=False)
            
            # Also publish to channel-aggregated topic (all networks for same channel)
            topic_agg = f"oi7500/channels/channel_{channel}/state"
            payload_agg = {
                "transmitter_address": transmitter_address,  # Radio sensor's address
                "channel": channel,  # Monitor's receiving slot
                "reading": round(reading, precision),
                "gas_type": gas_name,
                "battery_voltage": battery_voltage,
                "fault": fault_name,
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
        
        # Calculate elapsed time
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
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
        print(f"  Slave 32 (OI-7032): {self.stats['modbus']['slave_32']['responses']} responses")
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
    parser.add_argument('--mqtt-use-tls', action='store_true',
                        help='Enable TLS/SSL for MQTT (auto-enabled for port 8883)')
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
        mqtt_password=args.mqtt_password,
        mqtt_use_tls=args.mqtt_use_tls
    )
    monitor.run()
