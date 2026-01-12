"""Query Channel 6 using the correct register addresses (PLC/Base-1 addressing)"""
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
print('CHANNEL 6 - CORRECT REGISTER ADDRESSES')
print('='*80)
print()

# User-provided register addresses (hex, PLC/Base-1 addressing)
# Note: Modbus protocol uses 0-based, but these are already in the correct format

print('Reading Channel 6 registers...')
print()

# 1. Radio Address - Hex 0x06 (readable/writable)
print('1. Radio Address (0x0006):')
regs = read_holding_registers(ser, 3, 0x0006, 1)
if regs:
    print(f'   Value: {regs[0]}')
print()

# 2. Reading - Hex 0x2B (32-bit float)
print('2. Reading (0x002B, Float32):')
regs = read_holding_registers(ser, 3, 0x002B, 2)
if regs and len(regs) == 2:
    bytes_data = struct.pack('>HH', regs[0], regs[1])
    reading = struct.unpack('>f', bytes_data)[0]
    print(f'   Value: {reading:.3f}')
print()

# 3. Time Since Last Message - Hex 0xC6 (16-bit integer)
print('3. Time Since Last Message (0x00C6, Int16):')
regs = read_holding_registers(ser, 3, 0x00C6, 1)
if regs:
    print(f'   Value: {regs[0]} seconds')
print()

# 4. Sensor Type - Hex 0xE6 (16-bit enumeration, should be 2 = CB)
print('4. Sensor Type (0x00E6, Enumeration):')
regs = read_holding_registers(ser, 3, 0x00E6, 1)
if regs:
    sensor_type = regs[0]
    sensor_names = {
        0: 'EC (Electrochemical)',
        1: 'IR (Infrared)',
        2: 'CB (Catalytic Bead)',
        3: 'MOS (Metal Oxide Semiconductor)',
        4: 'PID (Photo-Ionization Detector)',
    }
    print(f'   Value: {sensor_type} = {sensor_names.get(sensor_type, "Unknown")}')
    if sensor_type == 2:
        print('   ✓ MATCHES: CB (Catalytic Bead)')
print()

# 5. Gas Type - Hex 0x106 (16-bit enumeration, should be 6 = LEL)
print('5. Gas Type (0x0106, Enumeration):')
regs = read_holding_registers(ser, 3, 0x0106, 1)
if regs:
    gas_type = regs[0]
    gas_names = {
        0: 'H2S (Hydrogen Sulfide)',
        1: 'SO2 (Sulfur Dioxide)',
        2: 'O2 (Oxygen)',
        3: 'CO (Carbon Monoxide)',
        4: 'CL2 (Chlorine)',
        5: 'CO2 (Carbon Dioxide)',
        6: 'LEL / %LEL (Combustible/Explosive)',
        7: 'VOC (Volatile Organic Compounds)',
        8: 'HCl (Hydrogen Chloride)',
        9: 'NH3 (Ammonia)',
    }
    print(f'   Value: {gas_type} = {gas_names.get(gas_type, "Unknown")}')
    if gas_type == 6:
        print('   ✓ MATCHES: LEL / %LEL')
print()

print('='*80)
print('VERIFICATION SUMMARY')
print('='*80)
print('User says touchscreen shows:')
print('  - Sensor Type: CATBEAD (CB) = value 2')
print('  - Gas Type: %LEL = value 6')
print('  - Reading: 0.000')
print('  - Battery: 23V')
print()
print('Modbus query results:')
print('  Checking if values match...')

ser.close()
