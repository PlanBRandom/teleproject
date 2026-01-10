"""Verify Channel 6 sensor type and gas type details"""
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

channel = 6
print('='*80)
print('CHANNEL 6 DETAILED SENSOR INFORMATION')
print('='*80)
print()

# Gas type
gas_reg = 0x101 + (channel - 1)
regs = read_holding_registers(ser, 3, gas_reg, 1)
gas_type = regs[0] if regs else 0

gas_names = {
    0: 'H2S (Hydrogen Sulfide)',
    1: 'SO2 (Sulfur Dioxide)', 
    2: 'O2 (Oxygen)',
    3: 'CO (Carbon Monoxide)',
    4: 'CL2 (Chlorine)',
    5: 'CO2 (Carbon Dioxide)',
    6: 'LEL (Combustible/Explosive)',
    7: 'VOC (Volatile Organic Compounds)',
    8: 'HCl (Hydrogen Chloride)',
    9: 'NH3 (Ammonia)',
    10: 'H2 (Hydrogen)',
    11: 'ClO2 (Chlorine Dioxide)',
    12: 'HCN (Hydrogen Cyanide)',
    13: 'NO2 (Nitrogen Dioxide)',
    14: 'PH3 (Phosphine)',
}

print(f'Gas Type Register: {gas_type}')
print(f'Gas Name: {gas_names.get(gas_type, f"Unknown({gas_type})")}')
print()

# Mode register might contain sensor type
mode_reg = 0x61 + (channel - 1)
regs = read_holding_registers(ser, 3, mode_reg, 1)
mode_value = regs[0] if regs else 0

print(f'Mode Register (0x{mode_reg:04X}): {mode_value} (0x{mode_value:04X})')
print(f'  Mode bits (0-2): {mode_value & 0x07}')
print(f'  Sensor type bits (3-7): {(mode_value >> 3) & 0x1F}')
print()

sensor_types = {
    0: 'EC (Electrochemical)',
    1: 'IR (Infrared)',
    2: 'CB (Catalytic Bead)',
    3: 'MOS (Metal Oxide Semiconductor)',
    4: 'PID (Photo-Ionization Detector)',
    5: 'Tank Level',
    6: '4-20mA',
    7: 'Switch',
    8: 'Pressure',
    9: 'Temperature',
    10: 'Humidity',
}

sensor_type_code = (mode_value >> 3) & 0x1F
print(f'Sensor Type Code: {sensor_type_code}')
print(f'Sensor Type: {sensor_types.get(sensor_type_code, f"Unknown({sensor_type_code})")}')
print()

# Reading
reading_reg = 0x21 + (channel - 1) * 2
regs = read_holding_registers(ser, 3, reading_reg, 2)
if regs and len(regs) == 2:
    bytes_data = struct.pack('>HH', regs[0], regs[1])
    reading = struct.unpack('>f', bytes_data)[0]
    print(f'Current Reading: {reading:.3f}')
print()

# Battery
battery_reg = 0x81 + (channel - 1) * 2
regs = read_holding_registers(ser, 3, battery_reg, 2)
if regs and len(regs) == 2:
    bytes_data = struct.pack('>HH', regs[0], regs[1])
    battery = struct.unpack('>f', bytes_data)[0]
    print(f'Battery: {battery:.2f}V')
print()

print('='*80)
print('USER PROVIDED INFORMATION (TOUCHSCREEN)')
print('='*80)
print('Channel: 6')
print('Radio Address: 6 (display) / 7 (Modbus)')
print('Sensor Type: CATBEAD (Catalytic Bead)')
print('Gas: LEL')
print('Measurement: %LEL')
print('Reading: 0.000')
print('Battery: 23V')
print('Location: "UPUP"')
print('RSSI: 95')
print()

print('='*80)
print('VERIFICATION')
print('='*80)
if gas_type == 6:
    print('✓ Gas type MATCHES: LEL (type 6)')
else:
    print(f'⚠ Gas type MISMATCH: Modbus shows type {gas_type} ({gas_names.get(gas_type)}), user says LEL')

if sensor_type_code == 2:
    print('✓ Sensor type MATCHES: Catalytic Bead (CB)')
else:
    print(f'⚠ Sensor type shows: type {sensor_type_code} ({sensor_types.get(sensor_type_code)}), user says Catalytic Bead')

print()
print('NOTE: Catalytic Bead (CB) sensors are the standard sensor type for')
print('      measuring combustible gases in %LEL units.')

ser.close()
