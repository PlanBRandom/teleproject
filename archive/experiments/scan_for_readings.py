"""
Try to extract sensor readings pragmatically by scanning for valid floats
Maybe the Gen2 structure is embedded but at unexpected offsets
"""
import struct

packet_hex = "81110011e0882b000f81000000000824060042e087e92377"
data = bytes.fromhex(packet_hex)

print(f"Packet ({len(data)} bytes): {packet_hex}")
print()

# Try every possible 4-byte window as a big-endian float
print("Scanning for potential readings (big-endian floats):")
for i in range(len(data) - 3):
    try:
        reading = struct.unpack('>f', data[i:i+4])[0]
        # Check if it's a reasonable sensor reading (-1000 to 10000 range)
        if -1000 < reading < 10000 and not (reading == 0.0):
            print(f"  Offset {i:2d}: {reading:12.6f}  bytes={data[i:i+4].hex()}")
    except:
        pass

print()
print("All byte sequences as hex:")
for i in range(0, len(data), 4):
    chunk = data[i:min(i+4, len(data))]
    print(f"  [{i:2d}-{i+len(chunk)-1:2d}]: {chunk.hex():12s} = {' '.join(f'{b:02x}' for b in chunk)}")

# Check if the common pattern 81 00 00 00 00 might indicate a zero reading
print()
print("Looking for zero reading pattern (00 00 00 00):")
for i in range(len(data) - 3):
    if data[i:i+4] == b'\x00\x00\x00\x00':
        print(f"  Found at offset {i}")
        
# The packet has addresses 0x8111 - maybe these sensors just transmit zeros?
# Or maybe the reading format is little-endian?
print()
print("Try little-endian floats:")
for i in range(len(data) - 3):
    try:
        reading = struct.unpack('<f', data[i:i+4])[0]
        if -1000 < reading < 10000 and not (reading == 0.0):
            print(f"  Offset {i:2d}: {reading:12.6f}  bytes={data[i:i+4].hex()}")
    except:
        pass
