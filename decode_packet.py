"""Quick packet decoder to understand the data format"""
import struct

# Sample packet from the logs
# Format: 81 11 00 11 e0 88 49 00 04 81 00 00 00 00 00 16 80 00 9b c8 b1 75 5f 03
data = bytes.fromhex('81110011e0884900048100000000001680009bc8b1755f03')

print('Raw packet:', data.hex())
print('Length:', len(data))
print()

# Parse according to Gen2 Protocol 1 format
print('Gen2 Protocol Format:')
print(f'  [0-1] Addr: 0x{data[0]:02X}{data[1]:02X} = {(data[0]<<8)|data[1]}')
print(f'  [2] Channel: {data[2]}')
print(f'  [3] Protocol: {data[3]}')
print('Gen2 Protocol Format:')
print(f'  [0-1] Addr: 0x{data[0]:02X}{data[1]:02X} = {(data[0]<<8)|data[1]}')
print(f'  [2] Channel: {data[2]}')
print(f'  [3] Protocol: {data[3]}')
print(f'  [4-7] Reading: {data[4]:02X} {data[5]:02X} {data[6]:02X} {data[7]:02X}')

reading = struct.unpack('>f', data[4:8])[0]
print(f'        As float: {reading:.2f}')

print(f'  [8] Sensor byte: 0x{data[8]:02X} = {data[8]:08b}b')
sensor_mode = data[8] & 0x07
sensor_type = (data[8] >> 3) & 0x1F
print(f'      Mode (bits 0-2): {sensor_mode}')
print(f'      Type (bits 3-7): {sensor_type}')

print(f'  [9] Battery: {data[9]} = {data[9]/10.0}V')

print(f'  [10] Gas byte: 0x{data[10]:02X} = {data[10]:08b}b')
gas_type = data[10] & 0x7F
battery_scale = (data[10] >> 7) & 0x01
print(f'      Gas type (bits 0-6): {gas_type}')
print(f'      Battery scale (bit 7): {battery_scale}')

print(f'  [11] Flags: 0x{data[11]:02X} = {data[11]:08b}b')
fault = (data[11] >> 4) & 0x0F
precision = (data[11] >> 1) & 0x07
has_text = data[11] & 0x01
print(f'      Fault (bits 4-7): {fault}')
print(f'      Precision (bits 1-3): {precision}')
print(f'      Has text (bit 0): {has_text}')

print()
print('Now let\'s check byte 7 for "Unknown" sensor types...')
print()

# The analyzer showed Unknown(128), Unknown(174), Unknown(175), Unknown(192)
# These might be byte 7 values, not the extracted sensor_type field

test_values = [128, 174, 175, 192]
for val in test_values:
    mode = val & 0x07
    s_type = (val >> 3) & 0x1F
    print(f'  Raw value {val} (0x{val:02X} = {val:08b}b): mode={mode}, type={s_type}')

print()
print('Checking gas types 63, 64, 65...')
for val in [63, 64, 65]:
    gas = val & 0x7F
    scale = (val >> 7) & 0x01  
    print(f'  Raw value {val} (0x{val:02X} = {val:08b}b): gas_type={gas}, scale={scale}')
