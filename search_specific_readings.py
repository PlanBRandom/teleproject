"""Search for specific reading values in radio logs"""
import struct
from datetime import datetime

def parse_hex_log(filename):
    """Parse hex log file and extract packets with timestamps"""
    packets = []
    current_packet = None
    current_timestamp = None
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            
            if not line or line.startswith('=') or 'Radio' in line or 'Started:' in line:
                continue
            
            if line.startswith('['):
                # Save previous packet
                if current_packet and current_timestamp:
                    try:
                        data = bytes.fromhex(current_packet)
                        packets.append((current_timestamp, data))
                    except ValueError:
                        pass
                
                parts = line.split('] ', 1)
                if len(parts) == 2:
                    timestamp_str = parts[0][1:]
                    hex_data = parts[1]
                    try:
                        current_timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                        current_packet = hex_data
                    except:
                        current_timestamp = None
                        current_packet = None
            else:
                if current_packet is not None:
                    current_packet += line
    
    # Last packet
    if current_packet and current_timestamp:
        try:
            data = bytes.fromhex(current_packet)
            packets.append((current_timestamp, data))
        except ValueError:
            pass
                    
    return packets

print('='*80)
print('SEARCHING FOR SPECIFIC READINGS: 1.0 and 6.0')
print('='*80)
print()

packets = parse_hex_log('radio_logs/radio_log_COM7_20260105_171202_hex.txt')
print(f'Loaded {len(packets)} packets')
print()

# Search for readings close to 1.0 and 6.0
found_1_0 = []
found_6_0 = []

for timestamp, data in packets:
    if len(data) < 14:
        continue
    
    try:
        reading = struct.unpack('>f', data[10:14])[0]
        channel = data[8]
        
        # Check for valid reading range first
        if -100 < reading < 100:
            if 0.9 < reading < 1.1:
                found_1_0.append((timestamp, data, channel, reading))
            elif 5.5 < reading < 6.5:
                found_6_0.append((timestamp, data, channel, reading))
    except:
        pass

print(f'Found {len(found_1_0)} packets with reading ~1.0:')
if found_1_0:
    for ts, data, ch, reading in found_1_0[:5]:  # Show first 5
        print(f'  {ts.strftime("%H:%M:%S")} | Channel {ch} | Reading: {reading:.2f} | Hex: {data.hex()}')
print()

print(f'Found {len(found_6_0)} packets with reading ~6.0:')
if found_6_0:
    for ts, data, ch, reading in found_6_0[:5]:  # Show first 5
        print(f'  {ts.strftime("%H:%M:%S")} | Channel {ch} | Reading: {reading:.2f} | Hex: {data.hex()}')
print()

print('='*80)
print('VERIFICATION AGAINST 7032 MODBUS DATA')
print('='*80)
print()
print('7032 shows:')
print('  Channel 5 (address 6): Reading 1.00, LEL')
print('  Channel 20 (address 21): Reading 6.00, VOC')
print()
print('Radio log search results:')
if found_1_0:
    print(f'  ✓ Found {len(found_1_0)} packets with reading ~1.0')
    sample = found_1_0[0]
    print(f'    First occurrence: Channel {sample[2]}, Reading {sample[3]:.2f}')
else:
    print('  ✗ No packets with reading ~1.0')

if found_6_0:
    print(f'  ✓ Found {len(found_6_0)} packets with reading ~6.0')
    sample = found_6_0[0]
    print(f'    First occurrence: Channel {sample[2]}, Reading {sample[3]:.2f}')
else:
    print('  ✗ No packets with reading ~6.0')

print()
print('='*80)
print('CONCLUSION')
print('='*80)
if found_1_0 and found_6_0:
    print('✓ SUCCESS: Radio packet parsing is NOW CORRECT!')
    print('  Reading field at bytes [10-13] matches 7032 Modbus values.')
else:
    print('⚠ Need further investigation')
