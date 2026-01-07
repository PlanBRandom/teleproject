"""Manual packet decoder to understand structure"""
import struct

packet_hex = "81110016e0882b00078100000000002303002ec8ae905f41"
data = bytes.fromhex(packet_hex)

print(f"Packet length: {len(data)} bytes")
print(f"Hex: {packet_hex}")
print()

# Try parsing with different assumptions
print("=== Assumption 1: Standard Protocol 1 (address at [0-1], protocol at [2]) ===")
print(f"Bytes [0-1]: Address = 0x{data[0]:02x}{data[1]:02x} = {(data[0] << 8) | data[1]}")
print(f"Byte [2]: Protocol/Channel? = 0x{data[2]:02x} = {data[2]}")
print(f"Byte [3]: Next byte = 0x{data[3]:02x} = {data[3]}")
print(f"Bytes [3-6]: Reading? = {' '.join(f'{b:02x}' for b in data[3:7])}")
try:
    reading = struct.unpack('>f', data[3:7])[0]
    print(f"  As float: {reading}")
except:
    print(f"  Cannot parse as float")
print()

print("=== Assumption 2: Maybe [2-3] are overhead, data starts at [4] ===")
print(f"Bytes [4-7]: Reading? = {' '.join(f'{b:02x}' for b in data[4:8])}")
try:
    reading = struct.unpack('>f', data[4:8])[0]
    print(f"  As float: {reading}")
except:
    print(f"  Cannot parse as float")
print()

print("=== Assumption 3: Maybe it's shifted - address at [2-3], reading at [6-9] ===")
if len(data) >= 10:
    print(f"Bytes [2-3]: Address? = 0x{data[2]:02x}{data[3]:02x} = {(data[2] << 8) | data[3]}")
    print(f"Bytes [6-9]: Reading? = {' '.join(f'{b:02x}' for b in data[6:10])}")
    try:
        reading = struct.unpack('>f', data[6:10])[0]
        print(f"  As float: {reading}")
    except:
        print(f"  Cannot parse as float")
print()

print("=== Looking for patterns ===")
# Check for repeated bytes (might be zeroes for reading=0.0)
print(f"Full hex dump:")
for i in range(0, len(data), 16):
    hex_part = ' '.join(f'{b:02x}' for b in data[i:i+16])
    ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
    print(f"  [{i:3d}] {hex_part:48s} {ascii_part}")
