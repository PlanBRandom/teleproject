"""
Capture radio packets and show what Channel 16 is currently transmitting
"""

import serial
import struct
import time
import sys

GAS_TYPES = {
    0: "H2S",
    1: "SO2", 
    2: "O2",
    3: "CO",
    4: "Combustibles",
    5: "CO2",
    6: "NH3",
    7: "NO2",
    8: "Cl2",
    9: "HCN",
    10: "PH3",
    11: "NO",
    12: "HCl",
    13: "ClO2",
    14: "AsH3",
    15: "B2H6",
    16: "Br2",
    17: "C2H4O",
    18: "GeH4",
    19: "SiH4",
    20: "F2"
}

def decode_0x81_packet(data):
    """Decode RM024 0x81 sensor data frame"""
    if len(data) < 4:
        return None
        
    frame_length = (data[1] << 8) | data[2]
    if len(data) != frame_length + 4:
        return None
        
    payload = data[3:-1]  # Remove start, length, checksum
    
    if len(payload) < 2:
        return None
        
    frame_type = payload[0]
    
    # Only decode 0x81 frames (sensor data)
    if frame_type == 0x81 and len(payload) >= 16:
        channel = payload[8]
        
        # Extract reading value (bytes 10-13)
        reading_bytes = payload[10:14]
        reading = struct.unpack('>f', reading_bytes)[0]
        
        # Extract gas type code (byte 14)
        gas_type_code = payload[14]
        gas_type = GAS_TYPES.get(gas_type_code, f"Unknown({gas_type_code})")
        
        # Status byte
        status = payload[15] if len(payload) > 15 else 0
        
        # Full payload hex for analysis
        payload_hex = ' '.join(f'{b:02X}' for b in payload)
        
        return {
            'channel': channel,
            'reading': reading,
            'gas_type_code': gas_type_code,
            'gas_type': gas_type,
            'status': status,
            'payload_hex': payload_hex
        }
    
    return None

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM11'
    target_channel = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    
    print(f"\n{'='*80}")
    print(f"CAPTURING RADIO PACKETS FOR CHANNEL {target_channel}")
    print(f"Port: {port} | Duration: {duration} seconds")
    print(f"{'='*80}\n")
    
    ser = serial.Serial(port=port, baudrate=115200, timeout=0.1)
    print(f"✓ Connected to {port}\n")
    print(f"Waiting for Channel {target_channel} packets...")
    print(f"{'-'*80}\n")
    
    buffer = bytearray()
    packets_found = []
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration:
            data = ser.read(256)
            if data:
                buffer.extend(data)
                
                # Look for RM024 frames
                while len(buffer) >= 4:
                    if buffer[0] == 0x7E:
                        frame_length = (buffer[1] << 8) | buffer[2]
                        total_length = frame_length + 4
                        
                        if len(buffer) >= total_length:
                            frame = bytes(buffer[:total_length])
                            buffer = buffer[total_length:]
                            
                            decoded = decode_0x81_packet(frame)
                            if decoded and decoded['channel'] == target_channel:
                                packets_found.append(decoded)
                                
                                print(f"[{len(packets_found)}] Time: {time.time() - start_time:.1f}s")
                                print(f"    Channel: {decoded['channel']}")
                                print(f"    Reading: {decoded['reading']:.2f}")
                                print(f"    Gas Type: {decoded['gas_type']} (code 0x{decoded['gas_type_code']:02X})")
                                print(f"    Status: 0x{decoded['status']:02X}")
                                print(f"    Payload: {decoded['payload_hex']}")
                                print()
                        else:
                            break
                    else:
                        buffer = buffer[1:]
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        ser.close()
        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}\n")
        print(f"Captured {len(packets_found)} packets for Channel {target_channel}")
        
        if packets_found:
            readings = [p['reading'] for p in packets_found]
            gas_types = set([p['gas_type'] for p in packets_found])
            print(f"  Reading range: {min(readings):.2f} - {max(readings):.2f}")
            print(f"  Gas types seen: {', '.join(gas_types)}")
        
        print(f"\n✓ Disconnected")

if __name__ == '__main__':
    main()
