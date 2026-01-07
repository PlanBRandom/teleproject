"""
Parse RM024 API packets with proper frame reconstruction
The logged data appears to be fragmented - need to reassemble before parsing
"""
import struct
from collections import defaultdict
from datetime import datetime

def reassemble_packets(hex_log_file):
    """Reassemble fragmented packets from hex log"""
    packets = []
    buffer = bytearray()
    last_timestamp = None
    
    with open(hex_log_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('=') or 'Radio' in line or 'Started' in line:
                continue
            
            if line.startswith('['):
                parts = line.split('] ', 1)
                if len(parts) == 2:
                    timestamp_str = parts[0][1:]
                    hex_data = parts[1]
                    
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                        data = bytes.fromhex(hex_data)
                        
                        # Add to buffer
                        buffer.extend(data)
                        
                        # Try to extract complete packets from buffer
                        while len(buffer) >= 12:
                            # Look for potential Gen2 packet start (after RM024 header)
                            # Pattern: could start with address bytes 0x81xx or similar
                            
                            # Try parsing from current position
                            extracted = try_extract_packet(buffer)
                            if extracted:
                                packet_data, packet_len = extracted
                                packets.append((timestamp, packet_data))
                                buffer = buffer[packet_len:]
                            else:
                                # Skip one byte and try again
                                buffer.pop(0)
                                
                    except Exception as e:
                        pass
            else:
                # Continuation line
                if buffer and line:
                    try:
                        data = bytes.fromhex(line)
                        buffer.extend(data)
                    except:
                        pass
    
    return packets

def try_extract_packet(buffer):
    """Try to extract a complete RM024 API + Gen2 packet from buffer"""
    if len(buffer) < 12:
        return None
    
    # RM024 API format (without 0xCC): [MAC 4][RSSI 1][Gen2...]
    # Gen2 format: [Addr 2][Proto 1][Data...][Checksum 1]
    
    # Try different interpretations:
    # 1. Maybe MAC + RSSI + Gen2
    # 2. Maybe just Gen2 with weird prefix
    
    # Look for Gen2 Protocol 1 marker at different offsets
    for offset in range(min(8, len(buffer) - 12)):
        if offset + 12 > len(buffer):
            continue
        
        # Check if there's a protocol 1 marker at this offset + 2
        if buffer[offset + 2] == 0x01:
            # Found potential Protocol 1!
            gen2_start = offset
            gen2_data = buffer[gen2_start:]
            
            # Determine packet length
            has_text = (gen2_data[10] & 0x01) == 1 if len(gen2_data) > 10 else False
            if has_text:
                if len(gen2_data) > 11:
                    text_len = gen2_data[11]
                    total_len = 12 + text_len + 1
                else:
                    continue
            else:
                total_len = 12
            
            if len(gen2_data) < total_len:
                continue
            
            # Validate checksum
            checksum_idx = total_len - 1
            calc_checksum = sum(gen2_data[:checksum_idx]) & 0xFF
            actual_checksum = gen2_data[checksum_idx]
            
            if calc_checksum == actual_checksum:
                # Valid packet!
                packet = buffer[:gen2_start + total_len]
                return (packet, gen2_start + total_len)
    
    return None

def parse_gen2_protocol1(gen2_data):
    """Parse Gen2 Protocol 1 packet"""
    if len(gen2_data) < 12:
        return None
    
    address = (gen2_data[0] << 8) | gen2_data[1]
    protocol = gen2_data[2]
    
    if protocol != 1:
        return None
    
    reading = struct.unpack('>f', gen2_data[3:7])[0]
    sensor_mode = gen2_data[7] & 0x07
    sensor_type = (gen2_data[7] >> 3) & 0x1F
    battery_reading = gen2_data[8]
    gas_type = gen2_data[9] & 0x7F
    battery_scale = (gen2_data[9] >> 7) & 0x01
    
    if battery_scale == 0:
        battery_v = battery_reading / 10.0
    else:
        battery_v = float(battery_reading)
    
    fault = (gen2_data[10] >> 4) & 0x0F
    
    return {
        'address': address,
        'protocol': protocol,
        'reading': reading,
        'sensor_mode': sensor_mode,
        'sensor_type': sensor_type,
        'gas_type': gas_type,
        'battery_v': battery_v,
        'fault': fault
    }

# Test on the hex log
print("Reassembling and parsing packets...")
packets = reassemble_packets('radio_logs/radio_log_COM7_20260105_171202_hex.txt')

print(f"\nFound {len(packets)} complete packets")

if packets:
    print("\nFirst 5 packets:")
    for i, (ts, pkt) in enumerate(packets[:5]):
        print(f"\n[{i+1}] {ts} - {len(pkt)} bytes")
        print(f"    Hex: {pkt.hex()}")
        
        # Try to parse as Gen2
        for offset in range(min(6, len(pkt) - 12)):
            gen2 = pkt[offset:]
            if len(gen2) >= 3 and gen2[2] == 0x01:
                parsed = parse_gen2_protocol1(gen2)
                if parsed:
                    print(f"    ✓ Parsed at offset {offset}:")
                    print(f"      Address: {parsed['address']}")
                    print(f"      Reading: {parsed['reading']:.2f}")
                    print(f"      Gas: {parsed['gas_type']}, Sensor: {parsed['sensor_type']}")
                    print(f"      Battery: {parsed['battery_v']:.1f}V")
                    break
