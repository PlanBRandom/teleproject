"""
Radio Log Analyzer
Parses 6-hour radio logs and extracts sensor data, statistics, and patterns
"""

import sys
from datetime import datetime
from collections import defaultdict
# from pipeline.radio_receiver import RadioReceiver  # Not needed for log analysis

def parse_hex_log(filename):
    """Parse hex log file and extract packets"""
    packets = []
    
    current_packet = None
    current_timestamp = None
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines and headers
            if not line or line.startswith('=') or 'Radio' in line or 'Started:' in line:
                continue
            
            if line.startswith('['):
                # If we have a previous packet, save it
                if current_packet and current_timestamp:
                    try:
                        data = bytes.fromhex(current_packet)
                        packets.append((current_timestamp, data))
                    except ValueError:
                        pass
                
                # Format: [2026-01-05 17:12:02.123] hexdata
                parts = line.split('] ', 1)
                if len(parts) == 2:
                    timestamp_str = parts[0][1:]  # Remove leading [
                    hex_data = parts[1]
                    
                    try:
                        current_timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                        current_packet = hex_data
                    except:
                        current_timestamp = None
                        current_packet = None
            else:
                # Continuation of current packet (hex data on next line)
                if current_packet is not None:
                    current_packet += line
    
    # Don't forget the last packet
    if current_packet and current_timestamp:
        try:
            data = bytes.fromhex(current_packet)
            packets.append((current_timestamp, data))
        except ValueError:
            pass
                    
    return packets

def analyze_sensors(packets):
    """Analyze sensor data from packets"""
    
    # Storage for sensor data
    sensors = defaultdict(lambda: {
        'readings': [],
        'timestamps': [],
        'channels': set(),
        'gas_types': set(),
        'sensor_types': set(),
        'sensor_modes': set(),  # Added to fix missing key error
        'faults': [],
        'battery_readings': []
    })
    
    protocol_counts = defaultdict(int)
    parse_errors = 0
    
    print(f"Parsing {len(packets)} packets...")
    print()
    
    for timestamp, data in packets:
        # Try to parse as Gen2 protocol
        if len(data) < 12:
            continue
            
        # Check protocol byte (data[2])
        # Note: Field data shows protocol=0 is common, not just 1/2/7
        protocol = data[2] if len(data) > 2 else None
        
        # Accept protocol 0, 1, 2, 7 for parsing
        if protocol in [0x00, 0x01, 0x02, 0x07]:
            if protocol == 0x00:
                protocol_counts['Protocol 0 (Field Data)'] += 1
            elif protocol == 0x01:
                protocol_counts['Protocol 1'] += 1
            elif protocol == 0x02:
                protocol_counts['Protocol 2'] += 1
            elif protocol == 0x07:
                protocol_counts['Protocol 7'] += 1
            
            if len(data) >= 14:  # Minimum length for corrected format
                try:
                    # CORRECTED PACKET STRUCTURE (verified against OI-7032):
                    # [0-1]: Transmitter address (16-bit big-endian)
                    # [2]: Protocol (0=Field, 1=Standard, 2/7=Other)
                    # [3]: Sequence number or flags
                    # [4-7]: Unknown (possibly timestamp)
                    # [8]: 7032 Channel Number ← CORRECTED
                    # [9]: Unknown (always 0x81)
                    # [10-13]: Reading (Float32) ← CORRECTED OFFSET
                    # [14+]: Additional data
                    
                    # Extract sensor address (bytes 0-1)
                    sensor_addr = (data[0] << 8) | data[1]
                    
                    # Extract channel number (byte 8) - this is the 7032 channel
                    channel = data[8]
                    
                    # Extract reading (bytes 10-13, float, big-endian) - CORRECTED!
                    import struct
                    reading = struct.unpack('>f', data[10:14])[0]
                    
                    # Remaining bytes at original positions (need to verify these too)
                    # Byte 7: sensor mode + type (may need adjustment)
                    sensor_mode = data[7] & 0x07 if len(data) > 7 else 0
                    sensor_type = (data[7] >> 3) & 0x1F if len(data) > 7 else 0
                    
                    # Battery and gas need to be found at new offsets
                    # For now, use placeholder values until we verify correct positions
                    battery_reading = data[14] if len(data) > 14 else 0
                    
                    # Gas type likely at different offset too
                    gas_type = data[15] if len(data) > 15 else 0
                    battery_scale = 0  # TBD
                    
                    # Calculate battery voltage
                    if battery_scale == 0:
                        battery_voltage = battery_reading / 10.0
                    else:
                        battery_voltage = float(battery_reading)
                    
                    # Byte 10: fault + precision + has_text
                    fault_code = (data[10] >> 4) & 0x0F
                    precision = (data[10] >> 1) & 0x07
                    has_text = data[10] & 0x01
                    
                    # Store data
                    sensors[sensor_addr]['readings'].append(reading)
                    sensors[sensor_addr]['timestamps'].append(timestamp)
                    sensors[sensor_addr]['channels'].add(channel)
                    sensors[sensor_addr]['gas_types'].add(gas_type)
                    sensors[sensor_addr]['sensor_types'].add(sensor_type)
                    sensors[sensor_addr]['sensor_modes'].add(sensor_mode)
                    if fault_code != 0:
                        sensors[sensor_addr]['faults'].append((timestamp, fault_code))
                    if battery_voltage and battery_voltage < 100:  # Sanity check
                        sensors[sensor_addr]['battery_readings'].append(battery_voltage)
                        
                except Exception as e:
                    parse_errors += 1
                    
        elif protocol == 0x02:  # Protocol 2: Quick gas detection
            protocol_counts['Protocol 2'] += 1
            # Similar parsing for protocol 2...
            
        elif protocol == 0x07:  # Protocol 7: Maintenance timing
            protocol_counts['Protocol 7'] += 1
            # Similar parsing for protocol 7...
    
    return sensors, protocol_counts, parse_errors

def print_analysis(sensors, protocol_counts, parse_errors, packets):
    """Print comprehensive analysis"""
    
    print("=" * 80)
    print("RADIO LOG ANALYSIS REPORT")
    print("=" * 80)
    print()
    
    print(f"Total Packets: {len(packets)}")
    print(f"Parse Errors: {parse_errors}")
    print()
    
    print("Protocol Distribution:")
    for protocol, count in sorted(protocol_counts.items()):
        print(f"  {protocol}: {count} packets")
    print()
    
    print(f"Unique Sensors Detected: {len(sensors)}")
    print()
    
    # Gas type names
    gas_names = {
        0: 'Oxygen', 1: 'Combustible', 2: 'Carbon Monoxide', 3: 'Hydrogen Sulfide',
        4: 'Carbon Dioxide', 5: 'Ammonia', 6: 'Chlorine', 7: 'Hydrogen',
        8: 'Hydrogen Cyanide', 9: 'Nitrogen Dioxide', 10: 'Sulfur Dioxide',
        11: 'Phosphine', 12: 'Methane'
    }
    
    # Sensor type names
    sensor_names = {
        0: 'Electrochemical', 1: 'Catalytic Bead', 2: 'Infrared', 3: 'PID'
    }
    
    # Fault code names
    fault_names = {
        0: 'None', 1: 'Sensor Fault', 2: 'Over Range', 3: 'Under Range',
        4: 'Low Battery', 5: 'Calibration Error'
    }
    
    print("=" * 80)
    print("SENSOR DETAILS")
    print("=" * 80)
    print()
    
    for sensor_addr in sorted(sensors.keys()):
        data = sensors[sensor_addr]
        
        print(f"Sensor @{sensor_addr} (0x{sensor_addr:04X})")
        print("-" * 80)
        
        # Basic info
        channels = ', '.join(str(ch) for ch in sorted(data['channels']))
        print(f"  Channels: {channels}")
        
        gas_types = ', '.join(gas_names.get(gt, f'Unknown({gt})') for gt in sorted(data['gas_types']))
        print(f"  Gas Types: {gas_types}")
        
        sensor_types = ', '.join(sensor_names.get(st, f'Unknown({st})') for st in sorted(data['sensor_types']))
        print(f"  Sensor Types: {sensor_types}")
        
        # Timing
        print(f"  Total Readings: {len(data['readings'])}")
        if len(data['timestamps']) >= 2:
            duration = (data['timestamps'][-1] - data['timestamps'][0]).total_seconds()
            avg_interval = duration / len(data['timestamps'])
            print(f"  Duration: {duration/3600:.2f} hours")
            print(f"  Average Interval: {avg_interval:.1f} seconds")
            print(f"  First Reading: {data['timestamps'][0].strftime('%H:%M:%S')}")
            print(f"  Last Reading: {data['timestamps'][-1].strftime('%H:%M:%S')}")
        
        # Statistics
        if data['readings']:
            readings = data['readings']
            print(f"  Reading Stats:")
            print(f"    Min: {min(readings):.2f}")
            print(f"    Max: {max(readings):.2f}")
            print(f"    Average: {sum(readings)/len(readings):.2f}")
            print(f"    Latest: {readings[-1]:.2f}")
        
        # Battery
        if data['battery_readings']:
            batteries = data['battery_readings']
            print(f"  Battery Stats:")
            print(f"    Min: {min(batteries):.2f}V")
            print(f"    Max: {max(batteries):.2f}V")
            print(f"    Average: {sum(batteries)/len(batteries):.2f}V")
            print(f"    Latest: {batteries[-1]:.2f}V")
        
        # Faults
        if data['faults']:
            print(f"  Faults Detected: {len(data['faults'])}")
            for ts, fault in data['faults'][-5:]:  # Show last 5
                fault_name = fault_names.get(fault, f'Unknown({fault})')
                print(f"    [{ts.strftime('%H:%M:%S')}] {fault_name}")
        
        print()

def export_csv(sensors, output_file):
    """Export sensor data to CSV for analysis in Excel/Python"""
    import csv
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp', 'Sensor_Address', 'Channel', 'Reading', 
                        'Battery_V', 'Fault_Code'])
        
        for sensor_addr, data in sensors.items():
            for i, timestamp in enumerate(data['timestamps']):
                reading = data['readings'][i] if i < len(data['readings']) else ''
                battery = data['battery_readings'][i] if i < len(data['battery_readings']) else ''
                channel = list(data['channels'])[0] if data['channels'] else ''
                fault = 0  # Simplified
                
                writer.writerow([
                    timestamp.strftime('%Y-%m-%d %H:%M:%S.%f'),
                    sensor_addr,
                    channel,
                    f"{reading:.2f}" if isinstance(reading, float) else reading,
                    f"{battery:.2f}" if isinstance(battery, float) else battery,
                    fault
                ])
    
    print(f"✓ Exported to CSV: {output_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_radio_logs.py <hex_log_file>")
        print()
        print("Example: python analyze_radio_logs.py radio_logs/radio_log_COM7_20260105_171202_hex.txt")
        return 1
    
    log_file = sys.argv[1]
    
    print(f"Analyzing: {log_file}")
    print()
    
    # Parse log
    packets = parse_hex_log(log_file)
    
    if not packets:
        print("✗ No packets found in log file")
        return 1
    
    # Analyze
    sensors, protocol_counts, parse_errors = analyze_sensors(packets)
    
    # Print report
    print_analysis(sensors, protocol_counts, parse_errors, packets)
    
    # Export CSV
    csv_file = log_file.replace('_hex.txt', '_data.csv')
    export_csv(sensors, csv_file)
    
    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    exit(main())
