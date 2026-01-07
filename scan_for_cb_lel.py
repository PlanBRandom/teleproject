"""Scan for sensor type value 2 (CB) and gas type value 6 (LEL)"""
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

ser = serial.Serial('COM10', 9600, timeout=1)

print('='*80)
print('SCANNING FOR CB (value 2) AND LEL (value 6) IN REGISTERS')
print('='*80)
print()
print('Scanning registers 0x00E0 to 0x0110 for Channel 6 configuration...')
print()
print('Address | Value | Interpretation')
print('--------|-------|----------------')

found_cb = []
found_lel = []

for addr in range(0xE0, 0x111):
    regs = read_holding_registers(ser, 3, addr, 1)
    if regs:
        if regs[0] == 2:
            found_cb.append(addr)
            print(f'0x{addr:04X}  |   {regs[0]}   | ← Possible CB (Catalytic Bead)')
        elif regs[0] == 6:
            found_lel.append(addr)
            print(f'0x{addr:04X}  |   {regs[0]}   | ← Possible LEL gas type')
    time.sleep(0.02)

print()
print('='*80)
print('SUMMARY')
print('='*80)
print(f'Found {len(found_cb)} register(s) with value 2 (CB):')
for addr in found_cb:
    print(f'  0x{addr:04X} (decimal {addr})')
print()
print(f'Found {len(found_lel)} register(s) with value 6 (LEL):')
for addr in found_lel:
    print(f'  0x{addr:04X} (decimal {addr})')

ser.close()
