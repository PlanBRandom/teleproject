"""
Debug Modbus register structure by reading raw register blocks
"""

import serial
import struct
import time
import sys

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

def read_registers(ser, slave_id: int, start_addr: int, count: int):
    """Read holding registers"""
    # Build Modbus request: Function 0x03
    request = struct.pack('>BBHHxx', slave_id, 0x03, start_addr, count)
    crc = calculate_crc(request[:-2])
    request = request[:-2] + struct.pack('<H', crc)
    
    # Send request
    ser.write(request)
    time.sleep(0.1)  # Wait for response
    
    # Read response
    response = ser.read(256)
    if len(response) < 5:
        return None
        
    # Validate response
    if response[0] != slave_id or response[1] != 0x03:
        print(f"  Invalid response header: {response[:5].hex()}")
        return None
        
    byte_count = response[2]
    expected = count * 2
    if byte_count != expected:
        print(f"  Unexpected byte count: got {byte_count}, expected {expected}")
        return None
        
    # Extract register values
    registers = struct.unpack(f'>{count}H', response[3:3+byte_count])
    return registers

def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_modbus_registers.py <slave_id>")
        sys.exit(1)
    
    slave_id = int(sys.argv[1])
    
    print(f"\n{'='*80}")
    print(f"DEBUGGING MODBUS REGISTERS - SLAVE {slave_id}")
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
    
    try:
        # First, try reading device status at 0x0190 (400 decimal)
        print("Reading device status register (0x0190)...")
        status_regs = read_registers(ser, slave_id, 0x0190, 1)
        if status_regs:
            print(f"  Status: 0x{status_regs[0]:04X}")
        print()
        
        # Read first 20 registers (0x0000 - 0x0013)
        print("Reading registers 0x0000 - 0x0013 (first 20 registers)...")
        regs = read_registers(ser, slave_id, 0x0000, 20)
        if regs:
            for i, reg in enumerate(regs):
                # Try interpreting as different types
                print(f"  Reg {i:2d} (0x{i:04X}): 0x{reg:04X} = {reg:5d} dec", end='')
                
                # If we have pairs, try as float
                if i % 2 == 0 and i + 1 < len(regs):
                    try:
                        float_val = struct.unpack('>f', struct.pack('>HH', regs[i], regs[i+1]))[0]
                        print(f"  | as float with next: {float_val:.4f}", end='')
                    except:
                        pass
                
                print()
        print()
        
        # Try reading channel 16's registers if they follow (ch-1)*6 pattern
        print("Trying channel 16 at address (16-1)*6 = 90 (0x005A)...")
        ch16_regs = read_registers(ser, slave_id, 90, 6)
        if ch16_regs:
            print(f"  Raw: {' '.join([f'{r:04X}' for r in ch16_regs])}")
            # Try different interpretations
            try:
                # Registers 0-1 as float
                float_01 = struct.unpack('>f', struct.pack('>HH', ch16_regs[0], ch16_regs[1]))[0]
                print(f"  Regs 0-1 as float: {float_01:.4f}")
            except:
                pass
            print(f"  Reg 2: 0x{ch16_regs[2]:04X} ({ch16_regs[2]} dec)")
            print(f"  Reg 3: 0x{ch16_regs[3]:04X} ({ch16_regs[3]} dec)")
        print()
        
        # Let's try scanning for a value near 21.9
        print("Scanning all registers 0-200 for value ~21.9...")
        for start in range(0, 200, 50):
            regs = read_registers(ser, slave_id, start, min(50, 200-start))
            if regs:
                for i in range(0, len(regs)-1, 2):
                    try:
                        float_val = struct.unpack('>f', struct.pack('>HH', regs[i], regs[i+1]))[0]
                        if 20.0 <= float_val <= 23.0:
                            addr = start + i
                            print(f"  Found {float_val:.4f} at registers {addr}-{addr+1} (0x{addr:04X}-0x{addr+1:04X})")
                            print(f"    Raw: 0x{regs[i]:04X} 0x{regs[i+1]:04X}")
                            if i+2 < len(regs):
                                print(f"    Next reg: 0x{regs[i+2]:04X} ({regs[i+2]} dec) - might be gas type?")
                    except:
                        pass
            time.sleep(0.1)
        
    finally:
        ser.close()
        print(f"\n✓ Disconnected")

if __name__ == '__main__':
    main()
