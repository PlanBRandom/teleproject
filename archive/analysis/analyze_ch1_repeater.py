#!/usr/bin/env python3
"""
Analyze Channel 1 from repeater network logs

Network topology:
- Network 25: Primary OI-7032 (COM10 Modbus)
- Network 15: Repeater → Network 25
- Network 20: Repeater → Network 25

Repeater radios wrap Gen2 packets in RM024 API transmit frames
"""

import struct
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

LOG_DIR = Path('protocol_logs')

GAS_TYPES = {
    0: "H2S", 1: "SO2", 2: "O2", 3: "CO", 4: "CL2",
    5: "CO2", 6: "LEL", 7: "VOC", 8: "FEET", 9: "HCl",
    10: "NH3", 11: "H2", 12: "ClO2", 13: "HCN", 14: "F2",
    15: "HF", 16: "CH2O", 17: "NO2", 18: "O3", 19: "INCHES",
    20: "4-20mA", 21: "Not Specified", 22: "°C", 23: "°F",
    24: "CH4", 25: "NO", 26: "PH3", 27: "HBr",
    28: "EtO", 29: "CH3SH", 30: "AsH3",
    31: "R410A", 32: "R1234YF", 33: "R32"
}

channel_data = defaultdict(lambda: {'readings': [], 'gas_types': set(), 'statuses': [], 'timestamps': []})

def decode_rm024_packet(data):
    """Decode RM024 API transmit packet from repeater"""
    if data[0] != 0x81 or len(data) < 24:
        return None
    
    payload_len = data[1]
    payload = data[3:3+payload_len]
    
    if len(payload) < 15:
        return None
    
    # RM024 API payload structure (from repeater client radio):
    # [0-1]: Radio address
    # [2-3]: Unknown field
    # [4]: CHANNEL NUMBER 
    # [5-6]: Sub-field
    # [7]: Marker (0x81 common)
    # [8-11]: Reading (32-bit float, big-endian)
    # [12]: Gas type
    # [13]: Status byte
    # [14]: Flags
    
    try:
        channel = payload[4]
        reading = struct.unpack('>f', payload[8:12])[0]
        gas_type = payload[12]
        status = payload[13]
        flags = payload[14] if len(payload) > 14 else 0
        
        return {
            'channel': channel,
            'reading': reading,
            'gas_type': gas_type,
            'status': status,
            'flags': flags
        }
    except:
        return None

# Parse hex dump log
hexdump_files = sorted(LOG_DIR.glob('hexdump_*.log'))

if not hexdump_files:
    print("No hex dump files found!")
    exit(1)

print(f"Analyzing {len(hexdump_files)} log files...")

for log_file in hexdump_files:
    with open(log_file, 'r') as f:
        timestamp = None
        for line in f:
            if 'RADIO_RX:' in line:
                # Extract timestamp
                match = re.search(r'\[(.*?)\]', line)
                if match:
                    timestamp = match.group(1)
                
                # Extract hex data
                hex_match = re.search(r'RADIO_RX:\s*([0-9a-f]+)', line, re.IGNORECASE)
                if hex_match and timestamp:
                    try:
                        hex_data = hex_match.group(1)
                        data = bytes.fromhex(hex_data)
                        
                        decoded = decode_rm024_packet(data)
                        if decoded:
                            ch = decoded['channel']
                            channel_data[ch]['readings'].append(decoded['reading'])
                            channel_data[ch]['gas_types'].add(decoded['gas_type'])
                            channel_data[ch]['statuses'].append(decoded['status'])
                            channel_data[ch]['timestamps'].append(timestamp)
                    except:
                        pass

# Generate report
print("\n" + "="*80)
print("CHANNEL 1 (OI-6900 SO2) OVEN TESTING ANALYSIS")
print("Saudi Arabia Field Issue Investigation")
print("Multi-tier Repeater Network (15, 20 → 25)")
print("="*80)

if 1 not in channel_data or not channel_data[1]['readings']:
    print("\n❌ CHANNEL 1 DATA NOT FOUND")
    print("\nPossible reasons:")
    print("  1. Channel 1 transmitting on Network 15 or 20 (not captured)")
    print("  2. Sensor powered off or in fault mode")
    print("  3. Radio communication issue")
    print("  4. Repeater not forwarding Channel 1 packets")
    
    print(f"\nChannels detected: {sorted(channel_data.keys())}")
    exit(0)

# Channel 1 found - analyze
ch1 = channel_data[1]
readings = ch1['readings']
gas_types = ch1['gas_types']
statuses = ch1['statuses']
timestamps = ch1['timestamps']

print(f"\n✅ CHANNEL 1 FOUND: {len(readings)} readings captured")

# Gas type verification
print(f"\n📊 SENSOR CONFIGURATION:")
print(f"  Gas Types Detected: {', '.join(GAS_TYPES.get(g, f'Unknown({g})') for g in gas_types)}")
expected_gas = 1  # SO2
if expected_gas in gas_types:
    print(f"  ✅ Correct gas type (SO2) confirmed")
else:
    print(f"  ❌ WARNING: Expected SO2 (type 1), got {gas_types}")

# Reading statistics
print(f"\n📈 READING STATISTICS:")
print(f"  Total readings: {len(readings)}")
print(f"  Average: {sum(readings)/len(readings):.3f} ppm")
print(f"  Min: {min(readings):.3f} ppm")
print(f"  Max: {max(readings):.3f} ppm")
print(f"  Range: {max(readings) - min(readings):.3f} ppm")
print(f"  Std Dev: {(sum((r - sum(readings)/len(readings))**2 for r in readings) / len(readings))**0.5:.3f} ppm")

# Time analysis
if len(timestamps) > 1:
    first = datetime.fromisoformat(timestamps[0])
    last = datetime.fromisoformat(timestamps[-1])
    duration = last - first
    print(f"\n⏱️  TIME SPAN:")
    print(f"  Start: {first.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  End: {last.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Duration: {duration}")
    if duration.total_seconds() > 0:
        rate = len(readings) / (duration.total_seconds() / 60)
        print(f"  Sample rate: {rate:.2f} readings/minute")

# Status byte analysis
print(f"\n⚠️  STATUS FLAGS ANALYSIS:")
unique_statuses = set(statuses)
for status in sorted(unique_statuses):
    count = statuses.count(status)
    pct = (count / len(statuses)) * 100
    print(f"  Status 0x{status:02x}: {count} occurrences ({pct:.1f}%)")
    
    # Decode status bits
    if status & 0x01:
        print(f"    ❌ Inhibit fault active")
    if status & 0x02:
        print(f"    ❌ Gas fault active")
    if status & 0x04:
        print(f"    ⚠️  Sensor alarm")
    if status & 0x08:
        print(f"    ⚠️  Warning condition")
    if status == 0:
        print(f"    ✅ Normal operation")

# Saudi Arabia specific analysis
print(f"\n🌡️  SAUDI ARABIA OVEN TEST ANALYSIS:")

# Reading drift
if len(readings) > 10:
    first_avg = sum(readings[:5]) / 5
    last_avg = sum(readings[-5:]) / 5
    drift = last_avg - first_avg
    print(f"  Reading drift: {drift:+.3f} ppm (first 5 vs last 5)")
    if abs(drift) > 5:
        print(f"    ⚠️  Significant drift detected - may indicate sensor aging or temp effect")
    else:
        print(f"    ✅ Acceptable drift")

# Stability
changes = [abs(readings[i] - readings[i-1]) for i in range(1, len(readings))]
if changes:
    avg_change = sum(changes) / len(changes)
    max_change = max(changes)
    print(f"  Average change between readings: {avg_change:.3f} ppm")
    print(f"  Maximum single change: {max_change:.3f} ppm")
    if max_change > 10:
        print(f"    ⚠️  Large reading jumps - check sensor stability")
    else:
        print(f"    ✅ Stable readings")

# Fault conditions
fault_count = sum(1 for s in statuses if s & 0x03)  # Inhibit or gas fault
if fault_count > 0:
    fault_pct = (fault_count / len(statuses)) * 100
    print(f"  Fault conditions: {fault_count} ({fault_pct:.1f}%)")
    print(f"    ❌ CRITICAL: Sensor faults detected during oven test")
    print(f"    This matches Saudi Arabia field reports")
else:
    print(f"  ✅ No sensor faults detected")

print("\n" + "="*80)
print("RECOMMENDATIONS:")
print("="*80)

if fault_count > 0:
    print("1. ❌ Sensor showing faults in oven - likely thermal issue")
    print("2. Verify oven temperature matches Saudi conditions (40-50°C ambient)")
    print("3. Check sensor thermal specifications vs. Saudi deployment temps")
    print("4. Consider thermal shielding or different sensor model for extreme heat")

if abs(drift) > 5:
    print("5. ⚠️  Significant drift - may need recalibration or cell replacement")

if max_change > 10:
    print("6. ⚠️  Unstable readings - check sensor mounting, EMI, power quality")

if fault_count == 0 and abs(drift) < 5 and max_change < 10:
    print("✅ Sensor performing well in oven test")
    print("   If Saudi issues persist, check:")
    print("   - Radio communication quality in field")
    print("   - Power supply stability")
    print("   - Physical mounting and vibration")
    print("   - Dust/sand ingress protection")

print("\n")
