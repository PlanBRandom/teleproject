"""Check channel activity and manage channel states"""
import serial
import struct
import time

def calculate_modbus_crc(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return struct.pack('<H', crc)

def read_holding_registers(ser, slave_id, start_address, count):
    request = bytes([slave_id, 0x03]) + struct.pack('>HH', start_address, count)
    request += calculate_modbus_crc(request)
    ser.write(request)
    time.sleep(0.05)
    response = ser.read(100)
    if len(response) < 5:
        return None
    byte_count = response[2]
    register_data = response[3:3+byte_count]
    registers = []
    for i in range(0, len(register_data), 2):
        registers.append(struct.unpack('>H', register_data[i:i+2])[0])
    return registers

def write_single_register(ser, slave_id, register_address, value):
    """Write to a single holding register (Modbus function 0x06)"""
    request = bytes([slave_id, 0x06]) + struct.pack('>HH', register_address, value)
    request += calculate_modbus_crc(request)
    ser.write(request)
    time.sleep(0.05)
    response = ser.read(100)
    return len(response) > 0

print('='*80)
print('OI-7032 CHANNEL ACTIVITY SCAN')
print('='*80)
print()

ser = serial.Serial('COM10', 9600, timeout=1)

active_channels = []
inactive_channels = []
unused_channels = []

print('Scanning all 32 channels...')
print()
print('Ch | Radio Addr | Time Since | Battery | Status')
print('---|------------|------------|---------|--------')

for channel in range(1, 33):
    # Radio address (PLC: 0x01+n, Modbus: 0x00+n)
    addr_reg = 0x00 + (channel - 1)
    regs = read_holding_registers(ser, 3, addr_reg, 1)
    radio_addr = regs[0] if regs else 0
    
    if radio_addr == 0:
        unused_channels.append(channel)
        continue
    
    # Time since last message (PLC: 0xC1+n, Modbus: 0xC0+n)
    time_reg = 0xC0 + (channel - 1)
    regs = read_holding_registers(ser, 3, time_reg, 1)
    time_since = regs[0] if regs else 9999
    
    # Battery (PLC: 0x81+n*2, Modbus: 0x80+n*2)
    battery_reg = 0x80 + (channel - 1) * 2
    regs = read_holding_registers(ser, 3, battery_reg, 2)
    battery = 0.0
    if regs and len(regs) == 2:
        bytes_data = struct.pack('>HH', regs[0], regs[1])
        battery = struct.unpack('>f', bytes_data)[0]
    
    status = "ACTIVE" if time_since < 600 else "INACTIVE"
    
    if time_since < 600:
        active_channels.append((channel, radio_addr, time_since, battery))
        marker = " ✓"
    else:
        inactive_channels.append((channel, radio_addr, time_since, battery))
        marker = ""
    
    print(f'{channel:2d} |     {radio_addr:3d}    | {time_since:6d}s   | {battery:5.1f}V  | {status}{marker}')
    time.sleep(0.02)

print()
print('='*80)
print('SUMMARY')
print('='*80)
print(f'Active channels (< 10 min): {len(active_channels)}')
for ch, addr, ts, batt in active_channels:
    print(f'  Channel {ch:2d}: Address {addr:3d}, {ts:3d}s ago, {batt:.1f}V')
print()
print(f'Inactive channels (> 10 min): {len(inactive_channels)}')
for ch, addr, ts, batt in inactive_channels[:5]:  # Show first 5
    print(f'  Channel {ch:2d}: Address {addr:3d}, {ts:4d}s ago, {batt:.1f}V')
if len(inactive_channels) > 5:
    print(f'  ... and {len(inactive_channels)-5} more')
print()
print(f'Unused channels (no address): {len(unused_channels)}')
print(f'  Channels: {unused_channels}')
print()

print('='*80)
print('RECOMMENDATIONS')
print('='*80)
print()
print('1. Keep active channels enabled (receiving data)')
print('2. Disable inactive channels to save resources')
print('3. Enable one unused channel for rogue radio scanning')
print()

# Find best channel for rogue scanning (first unused)
if unused_channels:
    scan_channel = unused_channels[0]
    print(f'Recommended scan channel: {scan_channel}')
    print(f'  - Set to address 255 (broadcast/scan mode)')
    print(f'  - Monitor for unrecognized radio addresses')
else:
    print('No unused channels available for scanning')

print()
print('Next steps:')
print('  1. Disable inactive channels')
print('  2. Enable scan channel with address 255')
print('  3. Monitor for rogue radio transmissions')
print('  4. Auto-assign found rogues to unused channels')

ser.close()
