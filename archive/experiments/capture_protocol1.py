#!/usr/bin/env python3
"""
Capture and search for Protocol 1 packets (0x53 0x3F start sequence)
"""
import serial
import time
from datetime import datetime

def capture_and_search(port, duration=90):
    """Capture data and look for Protocol 1 start sequence"""
    print(f"Capturing from {port} @ 9600 baud for {duration} seconds...")
    print("Looking for Protocol 1 start sequence: 0x53 0x3F\n")
    
    ser = serial.Serial(port, 9600, timeout=0.1)
    buffer = bytearray()
    start_time = time.time()
    found_count = 0
    
    while time.time() - start_time < duration:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            buffer.extend(data)
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            hex_data = ' '.join(f'{b:02x}' for b in data)
            print(f"[{timestamp}] +{len(data)} bytes: {hex_data}")
            
            # Keep last 500 bytes
            if len(buffer) > 500:
                buffer = buffer[-500:]
            
            # Search for Protocol 1 start sequence
            search_pos = 0
            while True:
                idx = buffer.find(b'\x53\x3F', search_pos)
                if idx == -1:
                    break
                
                found_count += 1
                packet = buffer[idx:idx+30]
                print(f"\n{'='*60}")
                print(f"FOUND Protocol 1 packet #{found_count} at offset {idx}!")
                print(f"{'='*60}")
                print('Packet bytes: ' + ' '.join(f'{b:02x}' for b in packet))
                
                # Decode if we have enough bytes
                if len(packet) >= 20:
                    print(f"\nDecoded:")
                    print(f"  Start: 0x{packet[0]:02x} 0x{packet[1]:02x}")
                    print(f"  Channel: {packet[7]}")
                    reading = int.from_bytes(packet[8:10], byteorder='little', signed=True)
                    print(f"  Reading (raw): {reading}")
                    print(f"  Gas Type: {packet[16] & 0x7F}")
                    print(f"  Battery: {packet[18] * 0.1:.1f}V")
                    print(f"  Fault: {(packet[19] >> 4) & 0x0F}")
                    precision = packet[19] & 0x0F
                    print(f"  Precision: {precision}")
                    actual_reading = reading / (10 ** precision) if precision <= 7 else reading
                    print(f"  Reading (actual): {actual_reading:.1f}")
                print(f"{'='*60}\n")
                
                search_pos = idx + 1
        
        time.sleep(0.01)
    
    ser.close()
    
    print(f"\n{'='*60}")
    print(f"Capture complete!")
    print(f"Total bytes captured: {len(buffer)}")
    print(f"Protocol 1 packets found: {found_count}")
    print(f"\nLast 100 bytes in buffer:")
    for i in range(0, min(100, len(buffer)), 20):
        chunk = buffer[i:i+20]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        print(f"  {i:3d}: {hex_str}")
    print(f"{'='*60}")

if __name__ == "__main__":
    import sys
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    
    capture_and_search(port, duration)
