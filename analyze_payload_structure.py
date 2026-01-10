import re
import struct

def analyze_packet_structure(log_file, num_samples=30):
    """Analyze packet structure to find where channel number is located."""
    
    print("DETAILED PACKET STRUCTURE ANALYSIS")
    print("="*80)
    
    packets = []
    with open(log_file, 'r') as f:
        for line in f:
            match = re.search(r'RX: 24 bytes - (81[0-9a-f]{46})', line)
            if match:
                packets.append(match.group(1))
                if len(packets) >= num_samples:
                    break
    
    print(f"\nAnalyzing {len(packets)} complete 24-byte 0x81 packets:\n")
    
    for i, hex_data in enumerate(packets[:10]):
        print(f"Packet {i+1}:")
        print(f"  Raw: {hex_data}")
        
        # Parse frame structure
        frame_type = hex_data[0:2]
        payload_len = int(hex_data[2:4], 16)
        zero_byte = hex_data[4:6]
        payload = hex_data[6:6+payload_len*2]
        trailer = hex_data[6+payload_len*2:]
        
        print(f"  Frame: 0x{frame_type}, PayloadLen: {payload_len}, Zero: 0x{zero_byte}")
        print(f"  Payload ({len(payload)//2} bytes): {payload}")
        print(f"  Trailer: {trailer}")
        
        # Analyze payload structure
        print(f"  Payload breakdown:")
        for pos in range(0, min(len(payload), 34), 2):
            byte_val = int(payload[pos:pos+2], 16)
            print(f"    [{pos//2}]: 0x{payload[pos:pos+2]} = {byte_val}")
        
        print()
    
    # Find patterns - look for bytes that change consistently
    print("\nLOOKING FOR CHANNEL PATTERN:")
    print("Testing different byte positions for small numbers (likely channel):")
    
    for test_pos in range(0, 17):
        values = []
        for hex_data in packets:
            if len(hex_data) >= 6 + test_pos*2 + 2:
                payload_start = 6  # After 0x81, len, 0x00
                byte_pos = payload_start + test_pos*2
                val = int(hex_data[byte_pos:byte_pos+2], 16)
                values.append(val)
        
        # Check if values look like channel numbers (0-32 range)
        small_vals = [v for v in values if 0 <= v <= 32]
        if len(small_vals) > len(values) * 0.3:  # If 30%+ are in channel range
            unique = set(values[:20])
            print(f"  Byte [{test_pos}]: Values = {sorted(unique)} (looks like channel!)")
    
    print("\n" + "="*80)
    print("USER'S NETWORK INFO:")
    print("  - Network 25 (primary): OI-7032 on COM7/COM10")
    print("  - Network 15: Repeater network")
    print("  - Network 20: Repeater network")
    print("  - Looking for: Channel 1 (OI-6900 SO2 in oven)")
    print("="*80)

if __name__ == '__main__':
    analyze_packet_structure('protocol_logs/radio_20260106_181937.log')
