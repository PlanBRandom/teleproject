#!/usr/bin/env python3
"""Test Laird API packet capture at 115200 baud"""
import serial
import time
from datetime import datetime

port = "COM11"
baud = 115200
duration = 60

print(f"Capturing {port} @ {baud} baud for {duration} seconds...")
print("Looking for Laird API packets (0x82) and Protocol 1 (0x53 0x3F)\n")

ser = serial.Serial(port, baud, timeout=0.1)
buffer = bytearray()
start_time = time.time()
packet_count = 0

while time.time() - start_time < duration:
    if ser.in_waiting > 0:
        data = ser.read(ser.in_waiting)
        buffer.extend(data)
        packet_count += 1
        
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        hex_data = ' '.join(f'{b:02x}' for b in data[:100])  # Show first 100 bytes
        print(f"[{timestamp}] Packet {packet_count}: {len(data)} bytes")
        print(f"  {hex_data}")
        
        # Check for markers
        if 0x82 in data:
            idx = data.index(0x82)
            print(f"  >>> Found 0x82 (Laird RX packet marker) at offset {idx}!")
        if b'\x53\x3F' in data:
            idx = data.index(b'\x53\x3F')
            print(f"  >>> Found 0x53 0x3F (Protocol 1 start) at offset {idx}!")
        print()
    
    time.sleep(0.01)

ser.close()

print(f"\n{'='*60}")
print(f"Capture complete!")
print(f"Total bytes: {len(buffer)}")
print(f"Total packets: {packet_count}")
print(f"\nSearching entire buffer:")
print(f"  0x82 (Laird RX) found: {0x82 in buffer}")
print(f"  0x53 0x3F (Protocol 1) found: {b'\\x53\\x3F' in buffer}")

if len(buffer) > 0:
    print(f"\nLast 100 bytes:")
    for i in range(max(0, len(buffer)-100), len(buffer), 20):
        chunk = buffer[i:i+20]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        print(f"  {i:4d}: {hex_str}")
print(f"{'='*60}")
