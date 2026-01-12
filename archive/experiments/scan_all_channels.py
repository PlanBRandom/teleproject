"""
Scan all channels from a Modbus device to find the O2 sensor reading 21.9%
"""

import serial
import struct
import time
import sys

# Gas type mapping
GAS_TYPES = {
    0: "H2S",
    1: "SO2", 
    2: "O2",
    3: "CO",
    4: "Combustibles",
    5: "CO2",
    6: "NH3",
    7: "NO2",
    8: "Cl2",
    9: "HCN",
    10: "PH3",
    11: "NO",
    12: "HCl",
    13: "ClO2",
    14: "AsH3",
    15: "B2H6",
    16: "Br2",
    17: "C2H4O",
    18: "GeH4",
    19: "SiH4",
    20: "F2"
}

def calculate_crc(data: bytes) -> int:
    """Calculate Modbus RTU CRC16"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

def read_channel_registers(ser, slave_id: int, channel: int):
    """Read all registers for a specific channel"""
    # Calculate starting register address
    base_address = (channel - 1) * 6
    
    # Build Modbus request: Function 0x03, read 6 registers
    request = struct.pack('>BBHHxx', slave_id, 0x03, base_address, 6)
    crc = calculate_crc(request[:-2])
    request = request[:-2] + struct.pack('<H', crc)
    
    # Send request
    ser.write(request)
    time.sleep(0.05)  # Wait for response
    
    # Read response
    response = ser.read(100)
    if len(response) < 5:
        return None
        
    # Validate response
    if response[0] != slave_id or response[1] != 0x03:
        return None
        
    byte_count = response[2]
    if byte_count != 12:  # 6 registers * 2 bytes
        return None
        
    # Extract register values
    registers = struct.unpack('>6H', response[3:15])
    
    # Parse channel data
    reading_raw = (registers[0] << 16) | registers[1]
    reading = struct.unpack('>f', struct.pack('>I', reading_raw))[0]
    gas_type_code = registers[2]
    status = registers[3]
    
    return {
        'channel': channel,
        'reading': reading,
        'gas_type_code': gas_type_code,
        'gas_type': GAS_TYPES.get(gas_type_code, f"Unknown({gas_type_code})"),
        'status': status,
        'raw_registers': registers
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python scan_all_channels.py <slave_id> [max_channel]")
        print("\nExample:")
        print("  python scan_all_channels.py 32 32")
        sys.exit(1)
    
    slave_id = int(sys.argv[1])
    max_channel = int(sys.argv[2]) if len(sys.argv) > 2 else 32
    
    print(f"\n{'='*80}")
    print(f"SCANNING CHANNELS 1-{max_channel} FROM SLAVE {slave_id}")
    print(f"{'='*80}\n")
    
    ser = serial.Serial(
        port='COM10',
        baudrate=9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1.0
    )
    
    print(f"✓ Connected to COM10 @ 9600 baud\n")
    print(f"{'Ch':<4} {'Reading':<10} {'Gas Type':<15} {'Status':<8} {'Registers'}")
    print(f"{'-'*80}")
    
    active_channels = []
    
    try:
        for channel in range(1, max_channel + 1):
            data = read_channel_registers(ser, slave_id, channel)
            
            if data and (data['reading'] != 0.0 or data['status'] != 0):
                # Channel has some data
                reading_str = f"{data['reading']:.2f}"
                gas_str = data['gas_type']
                status_str = f"0x{data['status']:04X}"
                regs_str = ' '.join([f"{r:04X}" for r in data['raw_registers']])
                
                print(f"{channel:<4} {reading_str:<10} {gas_str:<15} {status_str:<8} {regs_str}")
                active_channels.append(data)
                
                # Highlight if this might be our O2 sensor
                if abs(data['reading'] - 21.9) < 0.5:
                    print(f"     ← POSSIBLE MATCH! Reading close to 21.9")
                if data['gas_type'] == 'O2':
                    print(f"     ← O2 SENSOR FOUND!")
            
            time.sleep(0.1)  # Small delay between requests
        
        print(f"\n{'='*80}")
        print(f"SUMMARY: Found {len(active_channels)} active channels")
        print(f"{'='*80}\n")
        
        # Look for O2 sensors
        o2_channels = [c for c in active_channels if c['gas_type'] == 'O2']
        if o2_channels:
            print(f"O2 Sensors found:")
            for c in o2_channels:
                print(f"  Channel {c['channel']}: {c['reading']:.2f}%")
        
        # Look for readings near 21.9
        near_21_9 = [c for c in active_channels if abs(c['reading'] - 21.9) < 0.5]
        if near_21_9:
            print(f"\nChannels reading ~21.9:")
            for c in near_21_9:
                print(f"  Channel {c['channel']}: {c['gas_type']} = {c['reading']:.2f}")
        
    finally:
        ser.close()
        print(f"\n✓ Disconnected")

if __name__ == '__main__':
    main()
