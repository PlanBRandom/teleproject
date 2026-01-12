"""Query detailed information for Channel 6 from OI-7032"""
import serial
import struct
import time

def calculate_modbus_crc(data):
    """Calculate Modbus RTU CRC-16"""
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
    """Read holding registers using Modbus function 0x03"""
    request = bytes([slave_id, 0x03]) + struct.pack('>HH', start_address, count)
    request += calculate_modbus_crc(request)
    
    ser.write(request)
    time.sleep(0.05)
    
    response = ser.read(100)
    if len(response) < 5:
        return None
    
    byte_count = response[2]
    if len(response) < 3 + byte_count + 2:
        return None
    
    register_data = response[3:3+byte_count]
    registers = []
    for i in range(0, len(register_data), 2):
        registers.append(struct.unpack('>H', register_data[i:i+2])[0])
    
    return registers

print('='*80)
print('OI-7032 CHANNEL 6 DETAILED INFORMATION')
print('='*80)
print()

ser = serial.Serial('COM10', 9600, timeout=1)
channel = 6

# Register addresses for channel 6
radio_addr_reg = 0x01 + (channel - 1)  # 0x06
reading_reg = 0x21 + (channel - 1) * 2  # 0x2B (2 registers for Float32)
mode_reg = 0x61 + (channel - 1)  # 0x66
battery_reg = 0x81 + (channel - 1) * 2  # 0x8B (2 registers for Float32)
gas_type_reg = 0x101 + (channel - 1)  # 0x106
fault_reg = 0x121 + (channel - 1)  # 0x126

print('Querying Channel 6 registers...')
print()

# Read radio address
regs = read_holding_registers(ser, 3, radio_addr_reg, 1)
radio_addr = regs[0] if regs else 0
print(f'Radio Address: {radio_addr}')

# Read reading (Float32)
regs = read_holding_registers(ser, 3, reading_reg, 2)
if regs and len(regs) == 2:
    bytes_data = struct.pack('>HH', regs[0], regs[1])
    reading = struct.unpack('>f', bytes_data)[0]
    print(f'Reading: {reading:.3f}')

# Read mode
regs = read_holding_registers(ser, 3, mode_reg, 1)
mode = regs[0] if regs else 0
mode_names = {0: "Normal", 1: "Calibration", 2: "Maintenance", 3: "Fault"}
print(f'Mode: {mode_names.get(mode, f"Unknown({mode})")}')

# Read battery (Float32)
regs = read_holding_registers(ser, 3, battery_reg, 2)
if regs and len(regs) == 2:
    bytes_data = struct.pack('>HH', regs[0], regs[1])
    battery = struct.unpack('>f', bytes_data)[0]
    print(f'Battery: {battery:.2f}V')

# Read gas type
regs = read_holding_registers(ser, 3, gas_type_reg, 1)
gas_type = regs[0] if regs else 0
gas_names = {
    0: "H2S", 1: "SO2", 2: "O2", 3: "CO", 4: "CL2", 
    5: "CO2", 6: "LEL", 7: "VOC", 8: "HCl", 9: "NH3"
}
print(f'Gas Type: {gas_names.get(gas_type, f"Unknown({gas_type})")}')

# Read fault
regs = read_holding_registers(ser, 3, fault_reg, 1)
fault = regs[0] if regs else 0
print(f'Fault Code: {fault}')

print()
print('='*80)
print('COMPARISON WITH TOUCHSCREEN DISPLAY')
print('='*80)
print()
print('Touchscreen shows:')
print('  Radio Address: 6')
print('  Battery: 23V')
print('  Mode: Normal')
print('  Reading: 0.000')
print('  Location: "UPUP"')
print('  RSSI: 95')
print()
print('Modbus query shows:')
print(f'  Radio Address: {radio_addr}')
if regs and len(regs) == 2:
    print(f'  Battery: {battery:.2f}V')
    print(f'  Mode: {mode_names.get(mode, "Unknown")}')
    print(f'  Reading: {reading:.3f}')
print()

if radio_addr == 6:
    print('✓ Radio address MATCHES touchscreen (6)')
else:
    print(f'⚠ Radio address MISMATCH: Modbus shows {radio_addr}, touchscreen shows 6')

print()
print('Note: Relay setpoints, location name, and RSSI are likely in')
print('      different register ranges not yet mapped.')

ser.close()
