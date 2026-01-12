#!/usr/bin/env python3
"""
Analyze Channel 1 (OI-6900 SO2) Oven Test Data
Saudi Arabia Field Issue Investigation
Correct byte offset: Channel at payload byte [5]
"""

import re
import struct
from datetime import datetime
from collections import defaultdict

# Gas type mapping
GAS_TYPES = {
    0: "H2S", 1: "SO2", 2: "O2", 3: "CO", 4: "CL2", 5: "CO2", 6: "LEL", 7: "VOC",
    8: "FEET", 9: "HCl", 10: "NH3", 11: "H2", 12: "ClO2", 13: "HCN", 14: "F2", 
    15: "HF", 16: "CH2O", 17: "NO2", 18: "O3", 19: "INCHES", 20: "4-20mA", 
    21: "Not Specified", 22: "°C", 23: "°F", 24: "CH4", 25: "NO", 26: "PH3", 
    27: "HBr", 28: "EtO", 29: "CH3SH", 30: "AsH3", 31: "R410A", 32: "R1234YF", 33: "R32"
}

def decode_rm024_packet(hex_data):
    """Decode RM024 API transmit packet (0x81 frame) from repeater."""
    if len(hex_data) < 48:  # Need full 24-byte packet
        return None
    
    frame = int(hex_data[0:2], 16)
    if frame != 0x81:
        return None
    
    payload_len = int(hex_data[2:4], 16)
    if payload_len != 17:  # Expected payload length
        return None
    
    # Payload starts at byte 3 (position 6 in hex)
    payload = hex_data[6:6+17*2]
    
    # Extract fields from payload
    radio_addr = int(payload[0:4], 16)
    field1 = int(payload[4:8], 16)  # 0x882b or 0x8849
    unknown1 = int(payload[8:10], 16)
    channel = int(payload[10:12], 16)  # CHANNEL NUMBER at payload[5]
    marker = int(payload[12:14], 16)   # Usually 0x81
    
    # Reading is 32-bit float at payload bytes 7-10 (positions 14-21)
    reading_bytes = bytes.fromhex(payload[14:22])
    try:
        reading = struct.unpack('>f', reading_bytes)[0]  # Big-endian float
    except:
        reading = 0.0
    
    # Gas type and status
    gas_type = int(payload[22:24], 16)
    status = int(payload[24:26], 16)
    flags = int(payload[26:28], 16)
    
    return {
        'radio_addr': radio_addr,
        'channel': channel,
        'reading': reading,
        'gas_type': gas_type,
        'gas_name': GAS_TYPES.get(gas_type, f"Unknown({gas_type})"),
        'status': status,
        'flags': flags,
        'marker': marker
    }

def analyze_channel(log_file, target_channel=1):
    """Analyze specific channel data from radio log."""
    
    print("="*80)
    print(f"CHANNEL {target_channel} (OI-6900 SO2) OVEN TESTING ANALYSIS")
    print("Saudi Arabia Field Issue Investigation")
    print("Multi-tier Repeater Network (15, 20 → 25)")
    print("="*80)
    print()
    
    channel_data = []
    all_channels = set()
    
    # Parse log file
    with open(log_file, 'r') as f:
        for line in f:
            # Look for timestamp and packet data
            ts_match = re.match(r'\[([^\]]+)\] RX: 24 bytes - (81[0-9a-f]{46})', line)
            if ts_match:
                timestamp_str = ts_match.group(1)
                hex_data = ts_match.group(2)
                
                packet = decode_rm024_packet(hex_data)
                if packet:
                    all_channels.add(packet['channel'])
                    if packet['channel'] == target_channel:
                        packet['timestamp'] = timestamp_str
                        packet['raw'] = hex_data
                        channel_data.append(packet)
    
    if not channel_data:
        print(f"❌ CHANNEL {target_channel} DATA NOT FOUND")
        print()
        print("Possible reasons:")
        print(f"  1. Channel {target_channel} transmitting on Network 15 or 20 (not captured)")
        print("  2. Sensor powered off or in fault mode")
        print("  3. Radio communication issue")
        print(f"  4. Repeater not forwarding Channel {target_channel} packets")
        print()
        print(f"Channels detected: {sorted(all_channels)}")
        return
    
    # Analysis
    print(f"✅ FOUND {len(channel_data)} CHANNEL {target_channel} PACKETS")
    print()
    
    # Verify gas type
    gas_types = set(p['gas_name'] for p in channel_data)
    print(f"Gas Type(s): {', '.join(gas_types)}")
    if 'SO2' not in gas_types:
        print(f"  ⚠️  WARNING: Expected SO2 but found {gas_types}")
    print()
    
    # Time span
    first_time = channel_data[0]['timestamp']
    last_time = channel_data[-1]['timestamp']
    print(f"Time Range:")
    print(f"  First: {first_time}")
    print(f"  Last:  {last_time}")
    print()
    
    # Reading statistics
    readings = [p['reading'] for p in channel_data]
    valid_readings = [r for r in readings if -100 < r < 1000]  # Filter outliers
    
    if valid_readings:
        avg_reading = sum(valid_readings) / len(valid_readings)
        min_reading = min(valid_readings)
        max_reading = max(valid_readings)
        reading_range = max_reading - min_reading
        
        print(f"Reading Statistics:")
        print(f"  Average: {avg_reading:.2f} ppm")
        print(f"  Min:     {min_reading:.2f} ppm")
        print(f"  Max:     {max_reading:.2f} ppm")
        print(f"  Range:   {reading_range:.2f} ppm")
        
        # Calculate standard deviation
        variance = sum((r - avg_reading)**2 for r in valid_readings) / len(valid_readings)
        std_dev = variance ** 0.5
        print(f"  Std Dev: {std_dev:.2f} ppm")
        print()
    
    # Status analysis
    status_counts = defaultdict(int)
    fault_count = 0
    for p in channel_data:
        status_counts[p['status']] += 1
        # Check for fault bits (bit 0 = inhibit fault, bit 7 = gas fault)
        if p['status'] & 0x01 or p['status'] & 0x80:
            fault_count += 1
    
    print(f"Status Flags:")
    for status, count in sorted(status_counts.items()):
        inhibit = "INHIBIT" if status & 0x01 else ""
        gas_fault = "GAS_FAULT" if status & 0x80 else ""
        alarm = "ALARM" if status & 0x06 else ""
        flags_str = " | ".join(filter(None, [inhibit, gas_fault, alarm]))
        print(f"  0x{status:02X} ({status:3d}): {count:4d} packets  {flags_str}")
    
    if fault_count > 0:
        fault_pct = (fault_count / len(channel_data)) * 100
        print(f"  ⚠️  FAULT CONDITIONS: {fault_count}/{len(channel_data)} packets ({fault_pct:.1f}%)")
    print()
    
    # Saudi Arabia specific: Check for drift
    if len(valid_readings) >= 10:
        first_5_avg = sum(valid_readings[:5]) / 5
        last_5_avg = sum(valid_readings[-5:]) / 5
        drift = last_5_avg - first_5_avg
        
        print(f"OVEN TEST ANALYSIS (Saudi Arabia Thermal Issues):")
        print(f"  First 5 readings avg: {first_5_avg:.2f} ppm")
        print(f"  Last 5 readings avg:  {last_5_avg:.2f} ppm")
        print(f"  Drift over time:      {drift:+.2f} ppm")
        
        if abs(drift) > 5:
            print(f"  ⚠️  SIGNIFICANT DRIFT DETECTED")
        
        # Check stability (average change between consecutive readings)
        changes = [abs(valid_readings[i+1] - valid_readings[i]) for i in range(len(valid_readings)-1)]
        avg_change = sum(changes) / len(changes)
        max_change = max(changes)
        
        print(f"  Average change:       {avg_change:.2f} ppm")
        print(f"  Max change:           {max_change:.2f} ppm")
        
        if max_change > 10:
            print(f"  ⚠️  UNSTABLE READINGS DETECTED")
        
        print()
    
    # Sample readings
    print("Sample Readings (first 10):")
    for i, p in enumerate(channel_data[:10]):
        print(f"  {i+1}. [{p['timestamp']}] {p['reading']:.2f} ppm  "
              f"Status=0x{p['status']:02X}  Gas={p['gas_name']}")
    
    print()
    print("="*80)
    print("RECOMMENDATIONS:")
    print("  - Review fault conditions and status flags")
    print("  - Check for correlation between temperature and readings")
    print("  - Compare with known good units in controlled environment")
    print("  - Monitor for continued drift over extended oven test")
    print("="*80)

if __name__ == '__main__':
    import sys
    import glob
    
    # Find log files
    log_files = glob.glob('protocol_logs/radio_*.log')
    
    if not log_files:
        print("ERROR: No radio log files found in protocol_logs/")
        sys.exit(1)
    
    print(f"Analyzing {len(log_files)} log files...")
    print()
    
    for log_file in log_files:
        analyze_channel(log_file, target_channel=1)
