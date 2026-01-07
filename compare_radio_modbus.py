"""
Compare radio log data with OI-7032 Modbus readings
The 7032 receives the same radio sensor data and outputs via Modbus
This validates our radio packet parsing
"""
import serial
import struct
import time
from collections import defaultdict

# Modbus configuration
MODBUS_PORT = 'COM10'
MODBUS_BAUD = 9600
SLAVE_ID = 3

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
    return crc

def read_holding_registers(ser, slave_id, start_addr, count):
    """Read Modbus holding registers (function code 0x03)"""
    # Build request: [SlaveID][Function][StartAddrH][StartAddrL][CountH][CountL][CRC]
    request = bytearray([
        slave_id,
        0x03,  # Read Holding Registers
        (start_addr >> 8) & 0xFF,
        start_addr & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF
    ])
    
    crc = calculate_modbus_crc(request)
    request.append(crc & 0xFF)
    request.append((crc >> 8) & 0xFF)
    
    # Send request
    ser.write(request)
    time.sleep(0.1)
    
    # Read response
    response = ser.read(1000)
    
    if len(response) < 5:
        return None
    
    # Validate response
    if response[0] != slave_id or response[1] != 0x03:
        return None
    
    byte_count = response[2]
    if len(response) < 3 + byte_count + 2:
        return None
    
    # Extract register values (big-endian 16-bit)
    registers = []
    for i in range(0, byte_count, 2):
        reg_val = (response[3 + i] << 8) | response[3 + i + 1]
        registers.append(reg_val)
    
    return registers

def get_sensor_data_from_7032(ser, channel):
    """Get sensor data for a specific channel from OI-7032
    
    OI-7032 Modbus register map:
    - Radio Address: 0x01 + (channel-1)  [1-32]
    - Reading: 0x21 + (channel-1)*2      [33-95, Float32]
    - Mode: 0x61 + (channel-1)           [97-128]
    - Battery: 0x81 + (channel-1)*2      [129-191, Float32]
    - Gas Type: 0x101 + (channel-1)      [257-288]
    - Fault: 0x121 + (channel-1)         [289-320]
    """
    if not (1 <= channel <= 32):
        return None
    
    ch_offset = channel - 1
    
    try:
        # Read radio address
        radio_addr_reg = 0x01 + ch_offset
        radio_addr_regs = read_holding_registers(ser, SLAVE_ID, radio_addr_reg, 1)
        radio_addr = radio_addr_regs[0] if radio_addr_regs else 0
        
        # Read reading (Float32, 2 registers)
        reading_reg = 0x21 + (ch_offset * 2)
        reading_regs = read_holding_registers(ser, SLAVE_ID, reading_reg, 2)
        reading = None
        if reading_regs and len(reading_regs) >= 2:
            float_bytes = struct.pack('>HH', reading_regs[0], reading_regs[1])
            reading = struct.unpack('>f', float_bytes)[0]
        
        # Read gas type
        gas_type_reg = 0x101 + ch_offset
        gas_type_regs = read_holding_registers(ser, SLAVE_ID, gas_type_reg, 1)
        gas_type = gas_type_regs[0] if gas_type_regs else None
        
        # Read battery (Float32, 2 registers)
        battery_reg = 0x81 + (ch_offset * 2)
        battery_regs = read_holding_registers(ser, SLAVE_ID, battery_reg, 2)
        battery = None
        if battery_regs and len(battery_regs) >= 2:
            float_bytes = struct.pack('>HH', battery_regs[0], battery_regs[1])
            battery = struct.unpack('>f', float_bytes)[0]
        
        # Read fault
        fault_reg = 0x121 + ch_offset
        fault_regs = read_holding_registers(ser, SLAVE_ID, fault_reg, 1)
        fault = fault_regs[0] if fault_regs else None
        
        # Read mode
        mode_reg = 0x61 + ch_offset
        mode_regs = read_holding_registers(ser, SLAVE_ID, mode_reg, 1)
        mode = mode_regs[0] if mode_regs else None
        
        return {
            'channel': channel,
            'radio_addr': radio_addr,
            'reading': reading,
            'gas_type': gas_type,
            'battery': battery,
            'fault': fault,
            'mode': mode
        }
        
    except Exception as e:
        print(f"Error reading channel {channel}: {e}")
        return None

def scan_7032_channels(ser, max_channels=32):
    """Scan all channels on the 7032"""
    print(f"Scanning OI-7032 on {MODBUS_PORT} (Slave ID {SLAVE_ID})...")
    print("="*80)
    print()
    
    # Gas type names
    gas_names = {
        0: "H2S", 1: "SO2", 2: "O2", 3: "CO", 4: "CL2", 5: "CO2",
        6: "LEL", 7: "VOC", 8: "FEET", 9: "HCl", 10: "NH3", 11: "H2",
        12: "ClO2", 13: "HCN", 14: "F2", 15: "HF", 16: "CH2O",
        17: "NO2", 18: "O3", 19: "INCHES", 20: "4-20mA", 21: "Not Specified",
        22: "°C", 23: "PH3", 24: "N2O", 25: "AsH3", 26: "NO", 27: "Br2"
    }
    
    sensors = {}
    active_count = 0
    
    for channel in range(1, max_channels + 1):
        data = get_sensor_data_from_7032(ser, channel)
        
        if data and data['radio_addr'] > 0:
            active_count += 1
            sensors[channel] = data
            
            gas_name = gas_names.get(data['gas_type'], f"Unknown({data['gas_type']})")
            
            print(f"Channel {channel:2d} | Addr: {data['radio_addr']:5d} (0x{data['radio_addr']:04X}) | "
                  f"Reading: {data['reading']:8.2f} | Gas: {gas_name:10s} | "
                  f"Battery: {data['battery']:5.2f}V | Fault: {data['fault']}")
    
    print()
    print(f"Found {active_count} active channels")
    
    return sensors

def main():
    print("OI-7032 Modbus Query Tool")
    print("="*80)
    print(f"Port: {MODBUS_PORT}")
    print(f"Baud: {MODBUS_BAUD}")
    print(f"Slave ID: {SLAVE_ID}")
    print()
    
    try:
        # Open Modbus serial port
        ser = serial.Serial(
            port=MODBUS_PORT,
            baudrate=MODBUS_BAUD,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        
        print(f"✓ Connected to {MODBUS_PORT}")
        print()
        
        # Scan for sensors
        sensors = scan_7032_channels(ser)
        
        print()
        print("="*80)
        print("COMPARISON WITH RADIO LOGS")
        print("="*80)
        print()
        
        if sensors:
            print("7032 Modbus sensors found:")
            for ch, data in sorted(sensors.items()):
                print(f"  Channel {ch}: Addr {data['radio_addr']} | "
                      f"Reading: {data['reading']:.2f} | Battery: {data['battery']:.2f}V")
        
        print()
        print("Radio log analysis (from analyze_radio_logs.py):")
        print("  - 26 sensors detected")
        print("  - Most common addresses: 33041 (0x8111), 33042 (0x8112)")
        print("  - All readings showing as 0.00 (parsing issue)")
        print("  - Gas types: 1 (SO2), 7 (VOC), 13 (HCN)")
        print()
        
        # Check for matching addresses
        radio_addrs_from_log = [33041, 33042, 0, 385, 1153, 1409, 1665, 2177]
        
        print("Address comparison:")
        for ch, data in sorted(sensors.items()):
            modbus_addr = data['radio_addr']
            if modbus_addr in radio_addrs_from_log:
                print(f"  ✓ Match: Channel {ch} addr {modbus_addr} found in both radio log and Modbus")
            else:
                print(f"  • 7032 Channel {ch} addr {modbus_addr} NOT in radio log")
        
        print()
        print("CONCLUSION:")
        if sensors:
            non_zero = [s for s in sensors.values() if abs(s['reading']) > 0.01]
            if non_zero:
                print(f"  ✓ 7032 shows {len(non_zero)} sensors with non-zero readings")
                print(f"  ✗ Radio logs show all zeros - PARSING IS INCORRECT")
                print()
                print("  The radio packet format needs correction.")
                print("  Likely the reading bytes are at a different offset than [3-6].")
            else:
                print(f"  • All sensors reading zero in both radio and Modbus")
                print(f"  • This could mean no gas detected, or sensors in standby")
        else:
            print("  No active sensors found on 7032")
        
        ser.close()
        
    except serial.SerialException as e:
        print(f"✗ Error opening {MODBUS_PORT}: {e}")
        return 1
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
