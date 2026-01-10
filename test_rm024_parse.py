"""
Test if logged hex data is RM024 API format without 0xCC header
RM024 API format: [0xCC][SrcMAC 4 bytes][RSSI][Gen2 Payload...]
Maybe the 0xCC was stripped during logging?
"""
import struct

# Sample packets from log
test_packets = [
    "81110016e0882b000f81000000000824060042e087e92377",
    "81110015e0882b000d8100000000082306003fc8afc03c71",
    "81120015e08849000487000000000018fde80008c8b1755fdd",
]

def try_parse_as_rm024_no_header(hex_data):
    """Try parsing as RM024 without 0xCC"""
    data = bytes.fromhex(hex_data)
    
    print(f"\n{'='*80}")
    print(f"Packet: {hex_data}")
    print(f"Length: {len(data)} bytes")
    
    # If this is RM024 without 0xCC:
    # [0-3]: Source MAC (4 bytes)
    # [4]: RSSI (1 byte)
    # [5+]: Gen2 packet
    
    if len(data) < 6:
        print("Too short for RM024 format")
        return
    
    src_mac = data[0:4]
    rssi = data[4]
    gen2_data = data[5:]
    
    print(f"\nTrying RM024 format (no 0xCC):")
    print(f"  SrcMAC: {src_mac.hex()} = {' '.join(f'{b:02x}' for b in src_mac)}")
    print(f"  RSSI: {rssi} (0x{rssi:02x})")
    print(f"  Gen2 payload ({len(gen2_data)} bytes): {gen2_data.hex()}")
    
    if len(gen2_data) >= 3:
        print(f"\n  Gen2 parsing:")
        print(f"    Bytes [0-1]: Address = 0x{gen2_data[0]:02x}{gen2_data[1]:02x} = {(gen2_data[0] << 8) | gen2_data[1]}")
        print(f"    Byte [2]: Protocol = {gen2_data[2]} (0x{gen2_data[2]:02x})")
        
        if gen2_data[2] == 1 and len(gen2_data) >= 12:
            # Protocol 1
            print(f"    ✓ Protocol 1 detected!")
            address = (gen2_data[0] << 8) | gen2_data[1]
            
            # Reading (bytes 3-6)
            reading_bytes = gen2_data[3:7]
            reading = struct.unpack('>f', reading_bytes)[0]
            
            # Sensor info
            sensor_mode = gen2_data[7] & 0x07
            sensor_type = (gen2_data[7] >> 3) & 0x1F
            
            # Battery
            battery_reading = gen2_data[8]
            
            # Gas type
            gas_type = gen2_data[9] & 0x7F
            battery_scale = (gen2_data[9] >> 7) & 0x01
            
            if battery_scale == 0:
                battery_v = battery_reading / 10.0
            else:
                battery_v = float(battery_reading)
            
            # Fault
            fault = (gen2_data[10] >> 4) & 0x0F
            
            print(f"    Address: {address}")
            print(f"    Reading: {reading}")
            print(f"    Sensor: mode={sensor_mode}, type={sensor_type}")
            print(f"    Gas type: {gas_type}")
            print(f"    Battery: {battery_v}V")
            print(f"    Fault: {fault}")
            
            # Validate checksum
            has_text = gen2_data[10] & 0x01
            if has_text and len(gen2_data) > 11:
                text_len = gen2_data[11]
                checksum_idx = 12 + text_len
            else:
                checksum_idx = 11
            
            if checksum_idx < len(gen2_data):
                calc_checksum = sum(gen2_data[:checksum_idx]) & 0xFF
                actual_checksum = gen2_data[checksum_idx]
                print(f"    Checksum: calc={calc_checksum:02x}, actual={actual_checksum:02x} {'✓' if calc_checksum == actual_checksum else '✗'}")

# Try other offsets too
def try_different_offsets(hex_data):
    """Try Gen2 packet at different byte offsets"""
    data = bytes.fromhex(hex_data)
    
    print(f"\n{'='*80}")
    print(f"Trying different Gen2 start offsets for: {hex_data[:40]}...")
    
    for offset in [0, 2, 4, 5, 6]:
        if offset + 3 > len(data):
            continue
        
        gen2_data = data[offset:]
        protocol = gen2_data[2] if len(gen2_data) > 2 else None
        
        print(f"\n  Offset {offset}: protocol byte = {protocol} (0x{protocol:02x} if protocol else 'N/A')")
        
        if protocol in [1, 2, 7]:
            print(f"    ✓ Valid protocol {protocol} found at offset {offset}!")
            print(f"    Address: 0x{gen2_data[0]:02x}{gen2_data[1]:02x}")

for packet in test_packets:
    try_parse_as_rm024_no_header(packet)

print(f"\n{'='*80}")
print("Trying to find valid protocol markers at different offsets:")
print('='*80)

for packet in test_packets:
    try_different_offsets(packet)
