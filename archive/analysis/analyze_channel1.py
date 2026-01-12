#!/usr/bin/env python3
"""
Analyze Channel 1 (OI-6900 SO2) for anomalies
Focus on oven testing and Saudi Arabia field issues
"""

import re
import struct
from pathlib import Path
from collections import defaultdict
from datetime import datetime

LOG_DIR = Path('protocol_logs')

class Channel1Analyzer:
    def __init__(self):
        self.radio_packets = []
        self.modbus_packets = []
        self.sensor_readings = []
        self.anomalies = []
        
    def parse_radio_logs(self):
        """Parse radio log files for channel 1 data"""
        radio_files = sorted(LOG_DIR.glob('radio_*.log'))
        hexdump_files = sorted(LOG_DIR.glob('hexdump_*.log'))
        
        if not radio_files:
            print("No radio log files found!")
            return
        
        print(f"Analyzing {len(radio_files)} radio log files...")
        
        for log_file in radio_files:
            with open(log_file, 'r') as f:
                for line in f:
                    if 'RX:' in line:
                        # Extract timestamp and hex data
                        match = re.search(r'\[(.*?)\].*?RX: (\d+) bytes - ([0-9a-f]+)', line)
                        if match:
                            timestamp = match.group(1)
                            byte_count = int(match.group(2))
                            hex_data = match.group(3)
                            
                            try:
                                data = bytes.fromhex(hex_data)
                                self.analyze_packet(timestamp, data)
                            except:
                                pass
        
        print(f"Found {len(self.radio_packets)} radio packets")
        print(f"Found {len(self.sensor_readings)} sensor readings")
    
    def analyze_packet(self, timestamp, data):
        """Analyze individual packet"""
        self.radio_packets.append({'timestamp': timestamp, 'data': data, 'length': len(data)})
        
        # Try to decode Gen2 Protocol 1 (full sensor data)
        if len(data) >= 12:
            # Check for 0x81 framing
            if data[0] == 0x81 and len(data) >= 24:
                payload_len = data[1]
                if payload_len >= 17:
                    gen2_data = data[3:3+payload_len]
                    self.decode_gen2_protocol1(timestamp, gen2_data)
            
            # Raw Gen2
            elif data[2] == 1:  # Protocol 1
                self.decode_gen2_protocol1(timestamp, data)
    
    def decode_gen2_protocol1(self, timestamp, data):
        """Decode OI Gen2 Protocol 1 packet"""
        if len(data) < 12:
            return
        
        try:
            # Gen2 Protocol 1 structure:
            # [0-1]: Transmitter Address (16-bit)
            # [2]: Protocol (0x01)
            # [3-6]: Reading (32-bit float, big-endian)
            # [7]: Gas Type
            # [8]: Status Byte
            # [9-10]: Flags
            # [11]: Checksum (or text length if text present)
            
            tx_addr = (data[0] << 8) | data[1]
            protocol = data[2]
            
            # Skip if not protocol 1
            if protocol != 1:
                return
            
            # Read sensor value (big-endian float)
            reading_bytes = bytes([data[3], data[4], data[5], data[6]])
            reading = struct.unpack('>f', reading_bytes)[0]
            
            gas_type = data[7]
            status = data[8]
            flags_high = data[9]
            flags_low = data[10]
            
            # Gas type 1 = SO2
            if gas_type == 1:
                self.sensor_readings.append({
                    'timestamp': timestamp,
                    'tx_addr': tx_addr,
                    'reading': reading,
                    'gas_type': gas_type,
                    'status': status,
                    'flags': (flags_high << 8) | flags_low
                })
                
                # Check for anomalies
                self.check_anomalies(timestamp, tx_addr, reading, status, flags_high, flags_low)
        
        except Exception as e:
            pass
    
    def check_anomalies(self, timestamp, tx_addr, reading, status, flags_high, flags_low):
        """Check for anomalies in sensor data"""
        flags = (flags_high << 8) | flags_low
        
        # Check for common issues in Saudi Arabia environment
        
        # 1. Temperature extremes (high heat issue)
        if flags_high & 0x10:  # Temperature fault bit
            self.anomalies.append({
                'timestamp': timestamp,
                'type': 'TEMPERATURE_FAULT',
                'details': f'TX {tx_addr:04x}: Temperature fault flag set',
                'severity': 'HIGH'
            })
        
        # 2. Sensor out of range
        if reading < -999 or reading > 9999:
            self.anomalies.append({
                'timestamp': timestamp,
                'type': 'READING_OUT_OF_RANGE',
                'details': f'TX {tx_addr:04x}: Reading {reading:.2f} out of range',
                'severity': 'MEDIUM'
            })
        
        # 3. Negative readings (unusual for SO2)
        if reading < 0:
            self.anomalies.append({
                'timestamp': timestamp,
                'type': 'NEGATIVE_READING',
                'details': f'TX {tx_addr:04x}: Negative SO2 reading {reading:.2f}',
                'severity': 'LOW'
            })
        
        # 4. Sensor fault flags
        if status & 0x01:  # Inhibit fault
            self.anomalies.append({
                'timestamp': timestamp,
                'type': 'INHIBIT_FAULT',
                'details': f'TX {tx_addr:04x}: Inhibit fault active',
                'severity': 'HIGH'
            })
        
        if status & 0x02:  # Gas fault
            self.anomalies.append({
                'timestamp': timestamp,
                'type': 'GAS_FAULT',
                'details': f'TX {tx_addr:04x}: Gas fault active',
                'severity': 'HIGH'
            })
        
        if status & 0x04:  # Sensor alarm
            self.anomalies.append({
                'timestamp': timestamp,
                'type': 'SENSOR_ALARM',
                'details': f'TX {tx_addr:04x}: Sensor alarm triggered, reading {reading:.2f}',
                'severity': 'MEDIUM'
            })
        
        # 5. Communication quality (check if text field present)
        if flags_low & 0x01:  # Text present flag
            # Text present might indicate warnings
            pass
        
        # 6. Rapid reading changes (drift/instability)
        if len(self.sensor_readings) > 1:
            last_reading = self.sensor_readings[-2]['reading']
            if abs(reading - last_reading) > 10:  # > 10 ppm change
                self.anomalies.append({
                    'timestamp': timestamp,
                    'type': 'RAPID_CHANGE',
                    'details': f'TX {tx_addr:04x}: Large reading change {last_reading:.2f} → {reading:.2f}',
                    'severity': 'MEDIUM'
                })
    
    def generate_report(self):
        """Generate analysis report"""
        print("\n" + "="*80)
        print("CHANNEL 1 (OI-6900 SO2) ANALYSIS REPORT")
        print("Oven Testing - Saudi Arabia Field Issue Investigation")
        print("="*80)
        
        if not self.sensor_readings:
            print("\n⚠️  NO SENSOR DATA FOUND")
            print("Possible issues:")
            print("  - Channel 1 not transmitting")
            print("  - Wrong transmitter address")
            print("  - Radio not receiving Gen2 Protocol 1 packets")
            print("  - Sensor powered off or in fault mode")
            return
        
        # Calculate statistics
        readings = [r['reading'] for r in self.sensor_readings]
        avg_reading = sum(readings) / len(readings)
        min_reading = min(readings)
        max_reading = max(readings)
        
        print(f"\n📊 SENSOR STATISTICS:")
        print(f"  Total readings: {len(self.sensor_readings)}")
        print(f"  Average: {avg_reading:.2f} ppm")
        print(f"  Min: {min_reading:.2f} ppm")
        print(f"  Max: {max_reading:.2f} ppm")
        print(f"  Range: {max_reading - min_reading:.2f} ppm")
        
        # Time span
        if len(self.sensor_readings) > 1:
            first_time = datetime.fromisoformat(self.sensor_readings[0]['timestamp'])
            last_time = datetime.fromisoformat(self.sensor_readings[-1]['timestamp'])
            duration = last_time - first_time
            print(f"  Time span: {duration}")
        
        # Transmitter addresses
        tx_addrs = set(r['tx_addr'] for r in self.sensor_readings)
        print(f"\n📡 TRANSMITTERS:")
        for addr in sorted(tx_addrs):
            count = sum(1 for r in self.sensor_readings if r['tx_addr'] == addr)
            print(f"  0x{addr:04x}: {count} packets")
        
        # Anomalies
        print(f"\n⚠️  ANOMALIES DETECTED: {len(self.anomalies)}")
        if self.anomalies:
            # Group by type
            by_type = defaultdict(list)
            for anomaly in self.anomalies:
                by_type[anomaly['type']].append(anomaly)
            
            for anom_type, anoms in sorted(by_type.items()):
                print(f"\n  {anom_type}: {len(anoms)} occurrences")
                # Show first 5 examples
                for anom in anoms[:5]:
                    print(f"    [{anom['timestamp']}] {anom['details']} (Severity: {anom['severity']})")
                if len(anoms) > 5:
                    print(f"    ... and {len(anoms) - 5} more")
        
        # Saudi Arabia specific checks
        print("\n🌡️  SAUDI ARABIA FIELD CONDITIONS CHECK:")
        
        # High temperature issues
        temp_faults = [a for a in self.anomalies if a['type'] == 'TEMPERATURE_FAULT']
        if temp_faults:
            print(f"  ❌ Temperature faults detected: {len(temp_faults)}")
            print(f"     This may indicate sensor operating outside spec in high heat")
        else:
            print(f"  ✅ No temperature faults detected")
        
        # Drift/stability
        rapid_changes = [a for a in self.anomalies if a['type'] == 'RAPID_CHANGE']
        if len(rapid_changes) > len(self.sensor_readings) * 0.1:  # > 10% of readings
            print(f"  ❌ High reading instability: {len(rapid_changes)} rapid changes")
            print(f"     This may indicate sensor drift or environmental interference")
        else:
            print(f"  ✅ Reading stability acceptable")
        
        # Sensor faults
        sensor_faults = [a for a in self.anomalies if a['type'] in ['INHIBIT_FAULT', 'GAS_FAULT']]
        if sensor_faults:
            print(f"  ❌ Sensor faults detected: {len(sensor_faults)}")
            print(f"     Check sensor calibration and cell condition")
        else:
            print(f"  ✅ No sensor faults detected")
        
        # Reading range analysis
        if max_reading - min_reading > 50:
            print(f"  ⚠️  Large reading range ({max_reading - min_reading:.2f} ppm)")
            print(f"     May indicate environmental changes or sensor issues")
        else:
            print(f"  ✅ Reading range acceptable")
        
        print("\n" + "="*80)
        
        # Recommendations
        print("\n📋 RECOMMENDATIONS:")
        if temp_faults:
            print("  1. Check sensor operating temperature")
            print("  2. Verify oven temperature matches Saudi Arabia ambient (40-50°C)")
            print("  3. Review sensor thermal specifications")
        
        if rapid_changes:
            print("  4. Investigate rapid reading changes")
            print("  5. Check for electromagnetic interference")
            print("  6. Verify sensor mounting and vibration")
        
        if not self.sensor_readings:
            print("  1. Verify sensor is powered on")
            print("  2. Check radio link quality")
            print("  3. Confirm transmitter address configuration")
            print("  4. Check for sensor fault LEDs")
        
        print("\n")

if __name__ == '__main__':
    analyzer = Channel1Analyzer()
    analyzer.parse_radio_logs()
    analyzer.generate_report()
