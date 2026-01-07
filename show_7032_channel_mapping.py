"""Show the complete 7032 channel to sensor address mapping"""
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
    # Build request: slave_id, function, address_hi, address_lo, count_hi, count_lo
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
print('OI-7032 CHANNEL TO SENSOR ADDRESS MAPPING')
print('='*80)
print()

# Connect to 7032
ser = serial.Serial('COM10', 9600, timeout=1)
print(f'Connected to COM10 @ 9600 baud')
print(f'Slave ID: 3')
print()

print('Reading channel assignments...')
print()
print('Channel | Sensor Addr | Status')
print('--------|-------------|--------')

# Read addresses for channels 1-32
# Register 0x01 + (channel-1) contains the sensor address
for channel in range(1, 33):
    register_addr = 0x01 + (channel - 1)
    regs = read_holding_registers(ser, 3, register_addr, 1)
    
    if regs:
        sensor_addr = regs[0]
        if sensor_addr > 0:
            print(f'   {channel:2d}   |     {sensor_addr:3d}     | Active')
    
    time.sleep(0.02)

ser.close()

print()
print('='*80)
print('SUMMARY')
print('='*80)
print()
print('The 7032 assigns each radio channel to a sensor address.')
print('When a sensor transmits on a channel, the radio packet contains:')
print('  - Transmitter Address (0x8111) = Radio module')
print('  - Channel Number = Which sensor (1-32)')
print()
print('The 7032 looks up the channel number and reports the configured')
print('sensor address via Modbus.')
print()
print('Example:')
print('  Radio packet: Transmitter 0x8111, Channel 5, Reading 1.0')
print('  7032 Modbus: Channel 5 -> Sensor Address 6, Reading 1.0')
